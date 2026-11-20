import argparse
import math
import statistics
import time

import minesweeper_bot as bot
from simulator import DIFFICULTIES, play_game


lookahead_findsafestcell = bot.findsafestcell


def entropy_findsafestcell(
    probabilities,
    board,
    total_mines,
    sample_count=300,
    max_candidates=12,
):
    if not probabilities:
        raise ValueError("No available cells to choose from.")

    minimum = min(probabilities.values())

    safest = [
        cell
        for cell, probability in probabilities.items()
        if math.isclose(
            probability,
            minimum,
            rel_tol=0,
            abs_tol=1e-12,
        )
    ]

    if len(safest) == 1:
        return safest[0]

    safest.sort(
        key=lambda cell: (
            -bot.getinformationscore(board, cell),
            cell[0],
            cell[1],
        )
    )

    candidates = safest[:max_candidates]

    sampled_boards = bot.samplevalidboards(
        board,
        total_mines,
        sample_count=sample_count,
    )

    if not sampled_boards:
        return candidates[0]

    scores = {
        cell: bot.getexpectedinformationgain(
            board,
            cell,
            sampled_boards,
        )
        for cell in candidates
    }

    return max(
        candidates,
        key=lambda cell: (
            scores[cell],
            bot.getinformationscore(board, cell),
            -cell[0],
            -cell[1],
        )
    )


def evaluate_strategy(
    strategy_function,
    rows,
    cols,
    total_mines,
    seeds,
    first_move,
):
    previous_function = bot.findsafestcell

    try:
        bot.findsafestcell = strategy_function

        results = []

        for seed in seeds:
            result = play_game(
                rows,
                cols,
                total_mines,
                seed=seed,
                first_move=first_move,
            )

            results.append(result)

        return results

    finally:
        bot.findsafestcell = previous_function


def summarise(name, results):
    wins = sum(r.result == "Win" for r in results)
    losses = sum(r.result == "Loss" for r in results)

    failures = len(results) - wins - losses

    completed = [
        r for r in results
        if r.result in ("Win", "Loss")
    ]

    print(f"\n{name}")
    print("-" * len(name))
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Errors/incomplete: {failures}")

    if completed:
        print(
            f"Win rate: "
            f"{100 * wins / len(completed):.2f}%"
        )

        print(
            f"Average guesses: "
            f"{statistics.mean(r.guesses for r in completed):.2f}"
        )

        print(
            f"Average moves: "
            f"{statistics.mean(r.moves for r in completed):.2f}"
        )

        print(
            f"Average game time: "
            f"{statistics.mean(r.seconds for r in completed):.4f}s"
        )

    if failures:
        for r in results:
            if r.result not in ("Win", "Loss"):
                print(
                    f" Seed {r.seed}: "
                    f"{r.result} - {r.reason}"
                )

    return wins, losses, failures


def compare(
    difficulty="expert",
    games=100,
    starting_seed=0,
    first_move=None,
):
    if games < 1:
        raise ValueError("Games must be at least 1.")

    rows, cols, total_mines = DIFFICULTIES[difficulty]

    if first_move is None:
        first_move = (rows // 2, cols // 2)

    if not (
        0 <= first_move[0] < rows
        and 0 <= first_move[1] < cols
    ):
        raise ValueError("First move is outside the board.")

    seeds = list(
        range(starting_seed, starting_seed + games)
    )

    print("\n=== MINESWEEPER A/B BENCHMARK ===")
    print(f"Difficulty: {difficulty}")
    print(f"Board: {rows} x {cols}")
    print(f"Mines: {total_mines}")
    print(f"Games per strategy: {games}")
    print(f"Starting seed: {starting_seed}")
    print(f"Fixed first move: {first_move}")
    print()

    start = time.perf_counter()

    print("Running entropy strategy...", flush=True)

    entropy_results = evaluate_strategy(
        entropy_findsafestcell,
        rows,
        cols,
        total_mines,
        seeds,
        first_move,
    )

    print("Running lookahead strategy...", flush=True)

    lookahead_results = evaluate_strategy(
        lookahead_findsafestcell,
        rows,
        cols,
        total_mines,
        seeds,
        first_move,
    )

    print("\n=== RESULTS ===")

    entropy_wins, _, entropy_failures = summarise(
        "Entropy strategy",
        entropy_results,
    )

    lookahead_wins, _, lookahead_failures = summarise(
        "Lookahead strategy",
        lookahead_results,
    )

    print("\n=== HEAD-TO-HEAD ===")

    both_win = 0
    both_lose = 0
    entropy_only = 0
    lookahead_only = 0
    unpaired = 0

    for entropy, lookahead in zip(
        entropy_results,
        lookahead_results,
    ):
        if (
            entropy.result not in ("Win", "Loss")
            or lookahead.result not in ("Win", "Loss")
        ):
            unpaired += 1
            continue

        if (
            entropy.result == "Win"
            and lookahead.result == "Win"
        ):
            both_win += 1

        elif (
            entropy.result == "Loss"
            and lookahead.result == "Loss"
        ):
            both_lose += 1

        elif entropy.result == "Win":
            entropy_only += 1

        else:
            lookahead_only += 1

    print(f"Both win: {both_win}")
    print(f"Both lose: {both_lose}")
    print(f"Only entropy wins: {entropy_only}")
    print(f"Only lookahead wins: {lookahead_only}")
    print(f"Unpaired/error games: {unpaired}")

    if unpaired == 0:
        difference = (
            100 * (lookahead_wins - entropy_wins) / games
        )

        print(
            f"\nLookahead win-rate difference: "
            f"{difference:+.2f} percentage points"
        )

    else:
        print(
            "\nWin-rate difference omitted because "
            "some games did not finish normally."
        )

    print(
        f"Total comparison time: "
        f"{time.perf_counter() - start:.2f}s"
    )

    return entropy_results, lookahead_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare Minesweeper guessing strategies"
    )

    parser.add_argument(
        "--difficulty",
        choices=list(DIFFICULTIES),
        default="expert",
    )

    parser.add_argument(
        "--games",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--first-row",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--first-col",
        type=int,
        default=None,
    )

    args = parser.parse_args()

    if (args.first_row is None) != (args.first_col is None):
        parser.error(
            "Specify both --first-row and --first-col."
        )

    opening = None

    if args.first_row is not None:
        opening = (args.first_row, args.first_col)

    compare(
        difficulty=args.difficulty,
        games=args.games,
        starting_seed=args.seed,
        first_move=opening,
    )