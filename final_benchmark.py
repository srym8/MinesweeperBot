import time
import statistics

import minesweeper_bot as bot
from simulator import DIFFICULTIES, play_game
from compare_strategies import entropy_findsafestcell


DIFFICULTY = "expert"
GAMES = 200
STARTING_SEED = 200000


def run_strategy(name, strategy, seeds):
    rows, cols, total_mines = DIFFICULTIES[DIFFICULTY]
    first_move = (rows // 2, cols // 2)

    original_function = bot.findsafestcell
    original_config = bot.LOOKAHEAD_CONFIG.copy()

    results = []

    print(f"\nRunning {name}...", flush=True)
    start = time.perf_counter()

    try:
        if strategy == "entropy":
            bot.findsafestcell = entropy_findsafestcell
        else:
            bot.findsafestcell = original_function
            bot.LOOKAHEAD_CONFIG = strategy.copy()

        for index, seed in enumerate(seeds, 1):
            result = play_game(
                rows,
                cols,
                total_mines,
                seed=seed,
                first_move=first_move,
            )

            results.append(result)

            if index % 20 == 0:
                wins = sum(
                    r.result == "Win"
                    for r in results
                )
                print(
                    f"  {index}/{len(seeds)} games | "
                    f"{wins} wins",
                    flush=True
                )

    finally:
        bot.findsafestcell = original_function
        bot.LOOKAHEAD_CONFIG = original_config

    elapsed = time.perf_counter() - start

    wins = sum(r.result == "Win" for r in results)
    failures = [
        r for r in results
        if r.result not in ("Win", "Loss")
    ]

    print(
        f"{name}: {wins}/{len(results)} wins "
        f"({wins / len(results):.1%}) | "
        f"Errors: {len(failures)} | "
        f"Time: {elapsed:.1f}s"
    )

    return results


def compare_pair(name_a, results_a, name_b, results_b):
    both_win = 0
    both_lose = 0
    only_a = 0
    only_b = 0
    invalid = 0

    for a, b in zip(results_a, results_b):
        if a.result not in ("Win", "Loss") or \
           b.result not in ("Win", "Loss"):
            invalid += 1
            continue

        if a.result == "Win" and b.result == "Win":
            both_win += 1
        elif a.result == "Loss" and b.result == "Loss":
            both_lose += 1
        elif a.result == "Win":
            only_a += 1
        else:
            only_b += 1

    print(f"\n{name_a} vs {name_b}")
    print(f"  Both win: {both_win}")
    print(f"  Both lose: {both_lose}")
    print(f"  Only {name_a} wins: {only_a}")
    print(f"  Only {name_b} wins: {only_b}")
    print(f"  Invalid comparisons: {invalid}")


def main():
    seeds = list(
        range(STARTING_SEED, STARTING_SEED + GAMES)
    )

    original_config = {
        "sample_count": 80,
        "max_candidates": 6,
        "reveal_weight": 1.0,
        "deduction_weight": 1.0,
        "entropy_weight": 0.0,
    }

    optimised_config = {
        "sample_count": 80,
        "max_candidates": 6,
        "reveal_weight": 1.0,
        "deduction_weight": 1.0,
        "entropy_weight": 1.0,
    }

    entropy_results = run_strategy(
        "Entropy",
        "entropy",
        seeds
    )

    original_results = run_strategy(
        "Original lookahead",
        original_config,
        seeds
    )

    optimised_results = run_strategy(
        "Optimised lookahead",
        optimised_config,
        seeds
    )

    print("\n=== FINAL COMPARISON ===")

    for name, results in [
        ("Entropy", entropy_results),
        ("Original lookahead", original_results),
        ("Optimised lookahead", optimised_results),
    ]:
        wins = sum(r.result == "Win" for r in results)

        print(
            f"{name}: {wins}/{len(results)} "
            f"({wins / len(results):.1%})"
        )

    compare_pair(
        "Original lookahead",
        original_results,
        "Optimised lookahead",
        optimised_results
    )

    compare_pair(
        "Entropy",
        entropy_results,
        "Optimised lookahead",
        optimised_results
    )


if __name__ == "__main__":
    main()
