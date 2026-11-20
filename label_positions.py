import argparse
import csv
import json
import math
import random

import minesweeper_bot as bot
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


def features(board, cell, probability, total_mines, samples):
    rows = len(board)
    cols = len(board[0])

    r, c = cell

    neighbours = bot.getneighbours(board, r, c)

    counts = {
        "unknown_neighbours": sum(
            board[nr][nc] == bot.UNKNOWN
            for nr, nc in neighbours
        ) / 8,
        "revealed_neighbours": sum(
            board[nr][nc] >= 0
            for nr, nc in neighbours
        ) / 8,
        "adjacent_known_mines": sum(
            board[nr][nc] == bot.MINE
            for nr, nc in neighbours
        ) / 8,
        "adjacent_safe_cells": sum(
            board[nr][nc] == bot.SAFE
            for nr, nc in neighbours
        ) / 8,
    }

    unknown = sum(
        value == bot.UNKNOWN
        for row in board
        for value in row
    )

    revealed = sum(
        value >= 0
        for row in board
        for value in row
    )

    return {
        "mine_probability": probability,
        **counts,
        "row_position": r / max(1, rows - 1),
        "col_position": c / max(1, cols - 1),
        "board_revealed_fraction": (
            revealed / (rows * cols)
        ),
        "remaining_mine_fraction": (
            bot.countremainingmines(board, total_mines)
            / max(1, unknown)
        ),
        "clue_entropy": (
            bot.getexpectedinformationgain(
                board,
                cell,
                samples,
            ) / math.log2(9)
        ),
    }


def stage(board):
    revealed = sum(
        value >= 0
        for row in board
        for value in row
    )

    fraction = revealed / (
        len(board) * len(board[0])
    )

    if fraction < 1 / 3:
        return "early"

    if fraction < 2 / 3:
        return "middle"

    return "late"


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default="minesweeper_positions.jsonl",
    )

    parser.add_argument(
        "--output",
        default="minesweeper_labels.csv",
    )

    parser.add_argument(
        "--positions",
        type=int,
        default=15,
    )

    parser.add_argument(
        "--samples",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=123456,
    )

    args = parser.parse_args()

    if args.positions < 1 or args.samples < 1:
        parser.error(
            "Positions and samples must be positive."
        )

    rng = random.Random(args.seed)

    buckets = {
        "early": [],
        "middle": [],
        "late": [],
    }

    with open(args.input, encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            position = json.loads(line)

            if len(position["candidates"]) >= 2:
                game_stage = stage(position["board"])
                buckets[game_stage].append(position)

    for bucket in buckets.values():
        rng.shuffle(bucket)

    chosen = []

    while (
        len(chosen) < args.positions
        and any(buckets.values())
    ):
        for name in ("early", "middle", "late"):
            if (
                buckets[name]
                and len(chosen) < args.positions
            ):
                chosen.append(buckets[name].pop())

    fieldnames = [
        "game_seed",
        "decision",
        "stage",
        "row",
        "col",
        *FEATURE_NAMES,
        "wins",
        "samples",
        "target_win_rate",
    ]

    with open(
        args.output,
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for index, position in enumerate(chosen, 1):
            board = position["board"]
            total_mines = position["total_mines"]

            samples = bot.samplevalidboards(
                board,
                total_mines,
                sample_count=args.samples,
                seed=rng.randrange(2**32),
            )

            for candidate in position["candidates"]:
                cell = (
                    candidate["row"],
                    candidate["col"],
                )

                wins = sum(
                    simulate_continuation(
                        board,
                        mines,
                        total_mines,
                        cell,
                    )
                    for mines in samples
                )

                writer.writerow({
                    "game_seed": position["game_seed"],
                    "decision": position["decision"],
                    "stage": stage(board),
                    "row": cell[0],
                    "col": cell[1],
                    **features(
                        board,
                        cell,
                        candidate["mine_probability"],
                        total_mines,
                        samples,
                    ),
                    "wins": wins,
                    "samples": len(samples),
                    "target_win_rate": (
                        wins / len(samples)
                    ),
                })

            file.flush()

            print(
                f"Labeled {index}/{len(chosen)} positions",
                flush=True,
            )

    print(
        f"Finished: {len(chosen)} positions "
        f"saved to {args.output}"
    )


if __name__ == "__main__":
    main()