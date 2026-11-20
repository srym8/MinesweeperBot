import argparse
import time

import minesweeper_bot as bot
from simulator import DIFFICULTIES, play_game
from compare_strategies import entropy_findsafestcell
from rollout_strategy import (
    rollout_findsafestcell,
    ROLLOUT_CONFIG,
)


def evaluate(name, strategy, seeds, difficulty):
    rows, cols, total_mines = DIFFICULTIES[difficulty]
    first_move = (rows // 2, cols // 2)

    previous = bot.findsafestcell
    results = []

    print(f"\nRunning {name}...", flush=True)
    start = time.perf_counter()

    try:
        bot.findsafestcell = strategy

        for index, seed in enumerate(seeds, 1):
            result = play_game(
                rows,
                cols,
                total_mines,
                seed=seed,
                first_move=first_move,
            )

            results.append(result)

            print(
                f"{index}/{len(seeds)} | "
                f"Seed {seed} | "
                f"{result.result} | "
                f"{result.seconds:.2f}s",
                flush=True,
            )

            if result.result not in ("Win", "Loss"):
                print(
                    f"  Reason: {result.reason}",
                    flush=True,
                )

    finally:
        bot.findsafestcell = previous

    elapsed = time.perf_counter() - start
    wins = sum(r.result == "Win" for r in results)

    print(
        f"\n{name}: {wins}/{len(results)} wins "
        f"({wins / len(results):.1%})"
    )
    print(f"Total time: {elapsed:.1f}s")

    return results


def compare(difficulty, games, starting_seed):
    seeds = list(
        range(starting_seed, starting_seed + games)
    )

    print("\n=== MONTE CARLO BENCHMARK ===")
    print(f"Difficulty: {difficulty}")
    print(f"Games: {games}")
    print(f"Starting seed: {starting_seed}")
    print(f"Rollout configuration: {ROLLOUT_CONFIG}")

    entropy_results = evaluate(
        "Entropy",
        entropy_findsafestcell,
        seeds,
        difficulty,
    )

    rollout_results = evaluate(
        "Monte Carlo",
        rollout_findsafestcell,
        seeds,
        difficulty,
    )

    both_win = 0
    both_lose = 0
    entropy_only = 0
    rollout_only = 0
    invalid = 0

    for entropy, rollout in zip(
        entropy_results,
        rollout_results,
    ):
        if (
            entropy.result not in ("Win", "Loss")
            or rollout.result not in ("Win", "Loss")
        ):
            invalid += 1
            continue

        if (
            entropy.result == "Win"
            and rollout.result == "Win"
        ):
            both_win += 1
        elif (
            entropy.result == "Loss"
            and rollout.result == "Loss"
        ):
            both_lose += 1
        elif entropy.result == "Win":
            entropy_only += 1
        else:
            rollout_only += 1

    print("\n=== PAIRED RESULTS ===")
    print(f"Both win: {both_win}")
    print(f"Both lose: {both_lose}")
    print(f"Only entropy wins: {entropy_only}")
    print(f"Only Monte Carlo wins: {rollout_only}")
    print(f"Invalid: {invalid}")

    if invalid == 0:
        difference = (
            100 * (rollout_only - entropy_only) / games
        )
        print(
            f"Monte Carlo advantage: "
            f"{difference:+.1f} percentage points"
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
        default=3,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=300000,
    )

    args = parser.parse_args()

    if args.games < 1:
        parser.error("--games must be positive.")

    compare(
        args.difficulty,
        args.games,
        args.seed,
    )
