import argparse
import csv
import math
import random
import time

import minesweeper_bot as bot
from simulator import DIFFICULTIES, MinesweeperGame
from compare_strategies import entropy_findsafestcell
from rollout_strategy import simulate_continuation


FEATURE_NAMES = [
    "mine_probability",
    "unknown_neighbours",
    "revealed_neighbours",
    "adjacent_known_mines",
    "adjacent_safe_cells",
    "row_position",
    "col_position",
    "board_revealed_fraction",
    "remaining_mine_fraction",
    "clue_entropy",
]

FIELD_NAMES = [
    "game_seed",
    "decision",
    "row",
    "col",
    *FEATURE_NAMES,
    "wins",
    "samples",
    "target_win_rate",
]


def get_features(
    board,
    cell,
    mine_probability,
    total_mines,
    sampled_boards,
):
    rows = len(board)
    cols = len(board[0])

    r, c = cell

    neighbours = bot.getneighbours(board, r, c)

    unknown = sum(
        board[nr][nc] == bot.UNKNOWN
        for nr, nc in neighbours
    )

    revealed = sum(
        board[nr][nc] >= 0
        for nr, nc in neighbours
    )

    known_mines = sum(
        board[nr][nc] == bot.MINE
        for nr, nc in neighbours
    )

    safe = sum(
        board[nr][nc] == bot.SAFE
        for nr, nc in neighbours
    )

    revealed_total = sum(
        value >= 0
        for row in board
        for value in row
    )

    remaining_mines = bot.countremainingmines(
        board,
        total_mines,
    )

    unknown_total = sum(
        value == bot.UNKNOWN
        for row in board
        for value in row
    )

    entropy = bot.getexpectedinformationgain(
        board,
        cell,
        sampled_boards,
    )

    return {
        "mine_probability": mine_probability,
        "unknown_neighbours": unknown / 8,
        "revealed_neighbours": revealed / 8,
        "adjacent_known_mines": known_mines / 8,
        "adjacent_safe_cells": safe / 8,
        "row_position": r / max(1, rows - 1),
        "col_position": c / max(1, cols - 1),
        "board_revealed_fraction": (
            revealed_total / (rows * cols)
        ),
        "remaining_mine_fraction": (
            remaining_mines / max(1, unknown_total)
        ),
        "clue_entropy": entropy / math.log2(9),
    }


def select_candidates(
    probabilities,
    board,
    max_candidates,
    risk_tolerance,
):
    minimum = min(probabilities.values())

    eligible = [
        cell
        for cell, probability in probabilities.items()
        if probability <= minimum + risk_tolerance + 1e-12
    ]

    eligible.sort(
        key=lambda cell: (
            probabilities[cell],
            -bot.getinformationscore(board, cell),
            cell[0],
            cell[1],
        )
    )

    return eligible[:max_candidates]


def generate(
    difficulty,
    games,
    starting_seed,
    samples,
    max_candidates,
    output,
):
    rows, cols, total_mines = DIFFICULTIES[difficulty]

    rng = random.Random(12345)

    examples = 0
    decisions = 0

    start = time.perf_counter()

    original_strategy = bot.findsafestcell

    try:
        with open(output, "w", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELD_NAMES,
            )

            writer.writeheader()

            bot.findsafestcell = entropy_findsafestcell

            for game_index in range(games):
                seed = starting_seed + game_index

                game = MinesweeperGame(
                    rows,
                    cols,
                    total_mines,
                    seed,
                )

                game.reveal(rows // 2, cols // 2)

                known_mines = set()
                decision_index = 0

                while not game.won and not game.lost:
                    board = game.get_visible_board()

                    for r, c in known_mines:
                        if board[r][c] == bot.UNKNOWN:
                            board[r][c] = bot.MINE

                    original_board = [
                        row.copy()
                        for row in board
                    ]

                    move = bot.solveboard(
                        board,
                        total_mines,
                    )

                    for r in range(rows):
                        for c in range(cols):
                            if (
                                original_board[r][c] == bot.UNKNOWN
                                and board[r][c] == bot.MINE
                            ):
                                known_mines.add((r, c))

                    if move is None:
                        break

                    is_guess = (
                        board[move[0]][move[1]]
                        != bot.SAFE
                    )

                    if is_guess:
                        probabilities = (
                            bot.getboardprobabilities(
                                board,
                                total_mines,
                            )
                        )

                        candidates = select_candidates(
                            probabilities,
                            board,
                            max_candidates,
                            risk_tolerance=0.03,
                        )

                        if len(candidates) > 1:
                            sample_seed = rng.randrange(
                                2**32
                            )

                            sampled_boards = (
                                bot.samplevalidboards(
                                    board,
                                    total_mines,
                                    sample_count=samples,
                                    seed=sample_seed,
                                )
                            )

                            for candidate in candidates:
                                features = get_features(
                                    board,
                                    candidate,
                                    probabilities[candidate],
                                    total_mines,
                                    sampled_boards,
                                )

                                wins = 0

                                for mines in sampled_boards:
                                    if simulate_continuation(
                                        board,
                                        mines,
                                        total_mines,
                                        candidate,
                                    ):
                                        wins += 1

                                writer.writerow({
                                    "game_seed": seed,
                                    "decision": decision_index,
                                    "row": candidate[0],
                                    "col": candidate[1],
                                    **features,
                                    "wins": wins,
                                    "samples": samples,
                                    "target_win_rate": (
                                        wins / samples
                                    ),
                                })

                                examples += 1

                            file.flush()
                            decisions += 1

                    decision_index += 1

                    game.reveal(*move)

                print(
                    f"Game {game_index + 1}/{games} | "
                    f"Examples: {examples} | "
                    f"Decision positions: {decisions} | "
                    f"Elapsed: {time.perf_counter() - start:.1f}s",
                    flush=True,
                )

    finally:
        bot.findsafestcell = original_strategy

    print("\n=== DATA GENERATION COMPLETE ===")
    print(f"Examples: {examples}")
    print(f"Decision positions: {decisions}")
    print(f"Output: {output}")

    print(
        f"Total time: "
        f"{time.perf_counter() - start:.1f}s"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--difficulty",
        choices=list(DIFFICULTIES),
        default="beginner",
    )

    parser.add_argument(
        "--games",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=400000,
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--candidates",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--output",
        default="minesweeper_training.csv",
    )

    args = parser.parse_args()

    if (
        args.games < 1
        or args.samples < 1
        or args.candidates < 1
    ):
        parser.error(
            "Games, samples and candidates must be positive."
        )

    generate(
        difficulty=args.difficulty,
        games=args.games,
        starting_seed=args.seed,
        samples=args.samples,
        max_candidates=args.candidates,
        output=args.output,
    )