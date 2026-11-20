import argparse
import json
import statistics
import time
from pathlib import Path

import minesweeper_bot as bot
from simulator import DIFFICULTIES, play_game


CONFIGURATIONS = [
    (1.0, 1.0, 0.0),  # Current lookahead
    (1.0, 0.5, 0.0),
    (1.0, 2.0, 0.0),
    (1.0, 4.0, 0.0),
    (1.0, 0.0, 0.0),
    (1.0, 1.0, 1.0),
    (1.0, 2.0, 1.0),
    (1.0, 1.0, 3.0),
]


def make_config(weights, samples=80, candidates=6):
    reveal, deduction, entropy = weights

    return {
        "sample_count": samples,
        "max_candidates": candidates,
        "reveal_weight": reveal,
        "deduction_weight": deduction,
        "entropy_weight": entropy,
    }


def evaluate(config, difficulty, seeds):
    rows, cols, total_mines = DIFFICULTIES[difficulty]

    # Every configuration uses the same first click.
    first_move = (rows // 2, cols // 2)

    previous_config = bot.LOOKAHEAD_CONFIG.copy()

    results = []
    start = time.perf_counter()

    try:
        bot.LOOKAHEAD_CONFIG = config.copy()

        for seed in seeds:
            result = play_game(
                rows,
                cols,
                total_mines,
                seed=seed,
                first_move=first_move,
            )

            results.append(result)

            if result.result not in ("Win", "Loss"):
                print(
                    f"  Warning: seed {seed}: "
                    f"{result.result} - {result.reason}",
                    flush=True
                )

    finally:
        bot.LOOKAHEAD_CONFIG = previous_config

    completed = [
        r for r in results
        if r.result in ("Win", "Loss")
    ]

    wins = sum(r.result == "Win" for r in completed)
    failures = len(results) - len(completed)

    return {
        "config": config.copy(),
        "wins": wins,
        "losses": len(completed) - wins,
        "failures": failures,
        "games": len(results),
        "win_rate": (
            wins / len(completed) if completed else 0.0
        ),
        "avg_guesses": (
            statistics.mean(r.guesses for r in completed)
            if completed else None
        ),
        "avg_game_time": (
            statistics.mean(r.seconds for r in completed)
            if completed else None
        ),
        "total_time": time.perf_counter() - start,
    }


def print_result(result):
    config = result["config"]

    print(
        f"Win rate: {result['win_rate']:.1%} | "
        f"Wins: {result['wins']}/{result['games']} | "
        f"Failures: {result['failures']} | "
        f"Time: {result['total_time']:.1f}s | "
        f"Weights: "
        f"({config['reveal_weight']}, "
        f"{config['deduction_weight']}, "
        f"{config['entropy_weight']})",
        flush=True
    )


def rank_key(result):
    # Failed simulations must not be rewarded.
    # Among equally successful configurations, prefer speed.
    return (
        -result["failures"],
        result["wins"],
        -result["total_time"],
    )


def optimise(difficulty, train_games, validation_games):
    if train_games < 1 or validation_games < 1:
        raise ValueError("Game counts must be positive.")

    # Separate, non-overlapping seed ranges.
    training_seeds = range(0, train_games)
    validation_seeds = range(
        100000,
        100000 + validation_games
    )

    print("\n=== TRAINING ===", flush=True)

    training_results = []

    for index, weights in enumerate(CONFIGURATIONS, 1):
        config = make_config(weights)

        print(
            f"\nConfiguration {index}/{len(CONFIGURATIONS)}",
            flush=True
        )

        result = evaluate(
            config,
            difficulty,
            training_seeds
        )

        training_results.append(result)
        print_result(result)

    training_results.sort(key=rank_key, reverse=True)

    print("\n=== TRAINING RANKING ===")

    for index, result in enumerate(training_results, 1):
        print(f"{index}. ", end="")
        print_result(result)

    # Advance the three strongest configurations.
    finalists = training_results[:3]

    print("\n=== VALIDATION ===", flush=True)

    validation_results = []

    for index, finalist in enumerate(finalists, 1):
        print(
            f"\nFinalist {index}/{len(finalists)}",
            flush=True
        )

        result = evaluate(
            finalist["config"],
            difficulty,
            validation_seeds
        )

        validation_results.append(result)
        print_result(result)

    validation_results.sort(key=rank_key, reverse=True)

    print("\n=== VALIDATION RANKING ===")

    for index, result in enumerate(validation_results, 1):
        print(f"{index}. ", end="")
        print_result(result)

    winner = validation_results[0]

    output = {
        "difficulty": difficulty,
        "configuration": winner["config"],
        "training_games": train_games,
        "validation_games": validation_games,
        "validation_win_rate": winner["win_rate"],
        "validation_wins": winner["wins"],
        "validation_failures": winner["failures"],
    }

    path = Path("best_minesweeper_config.json")

    with path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=4)

    print("\n=== BEST VALIDATED CONFIGURATION ===")
    print_result(winner)
    print(f"Saved to: {path.resolve()}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--difficulty",
        choices=list(DIFFICULTIES),
        default="expert"
    )

    parser.add_argument(
        "--train",
        type=int,
        default=30
    )

    parser.add_argument(
        "--validate",
        type=int,
        default=100
    )

    args = parser.parse_args()

    optimise(
        args.difficulty,
        args.train,
        args.validate
    )
