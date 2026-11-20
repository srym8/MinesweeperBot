import argparse
import json

import minesweeper_bot as bot
from compare_strategies import entropy_findsafestcell
from simulator import DIFFICULTIES, play_game


def candidate_cells(probabilities, board, limit, tolerance):
    lowest = min(probabilities.values())

    eligible = [
        cell for cell, risk in probabilities.items()
        if risk <= lowest + tolerance + 1e-12
    ]

    eligible.sort(
        key=lambda cell: (
            probabilities[cell],
            -bot.getinformationscore(board, cell),
            cell[0],
            cell[1],
        )
    )

    return eligible[:limit]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--difficulty",
        choices=DIFFICULTIES,
        default="expert",
    )

    parser.add_argument("--games", type=int, default=100)
    parser.add_argument("--seed", type=int, default=500000)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--risk-tolerance", type=float, default=0.03)

    parser.add_argument(
        "--output",
        default="minesweeper_positions.jsonl",
    )

    args = parser.parse_args()

    if (
        args.games < 1
        or args.candidates < 1
        or args.risk_tolerance < 0
    ):
        parser.error(
            "Games and candidates must be positive, "
            "and risk tolerance cannot be negative."
        )

    rows, cols, mines = DIFFICULTIES[args.difficulty]

    original_strategy = bot.findsafestcell

    positions = 0
    errors = 0
    current_seed = None
    decision_number = 0
    writer = None

    def capture_strategy(probabilities, board, total_mines):
        nonlocal positions, decision_number

        candidates = candidate_cells(
            probabilities,
            board,
            args.candidates,
            args.risk_tolerance,
        )

        if len(candidates) >= 2:
            record = {
                "game_seed": current_seed,
                "decision": decision_number,
                "difficulty": args.difficulty,
                "total_mines": total_mines,
                "board": [row.copy() for row in board],
                "candidates": [
                    {
                        "row": r,
                        "col": c,
                        "mine_probability": probabilities[(r, c)],
                    }
                    for r, c in candidates
                ],
            }

            writer.write(json.dumps(record) + "\n")
            positions += 1

        decision_number += 1

        return entropy_findsafestcell(
            probabilities,
            board,
            total_mines,
        )

    try:
        with open(args.output, "w", encoding="utf-8") as file:
            writer = file
            bot.findsafestcell = capture_strategy

            for index in range(args.games):
                current_seed = args.seed + index
                decision_number = 0

                result = play_game(
                    rows,
                    cols,
                    mines,
                    seed=current_seed,
                    first_move=(rows // 2, cols // 2),
                )

                if result.result not in ("Win", "Loss"):
                    errors += 1
                    print(
                        f"WARNING seed {current_seed}: "
                        f"{result.result}: {result.reason}"
                    )

                if (
                    (index + 1) % 10 == 0
                    or index + 1 == args.games
                ):
                    print(
                        f"{index + 1}/{args.games} games | "
                        f"{positions} positions | "
                        f"{errors} errors",
                        flush=True,
                    )

    finally:
        bot.findsafestcell = original_strategy

    print(
        f"Finished: {positions} positions saved "
        f"to {args.output}; errors={errors}"
    )


if __name__ == "__main__":
    main()
