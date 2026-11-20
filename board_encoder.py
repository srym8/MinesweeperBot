"""Encode visible Minesweeper positions for a future CNN."""

import argparse
import json

UNKNOWN = -1
SAFE = -2
MINE = -3

PATCH_SIZE = 7

CHANNEL_NAMES = (
    "unknown",
    "deduced_safe",
    "deduced_mine",
    "clue_0",
    "clue_1",
    "clue_2",
    "clue_3",
    "clue_4",
    "clue_5",
    "clue_6",
    "clue_7",
    "clue_8",
    "outside_board",
)

CHANNEL_COUNT = len(CHANNEL_NAMES)


def encode_patch(board, cell, size=PATCH_SIZE):
    """Return a one-hot patch: [channels][height][width]."""

    if size < 1 or size % 2 != 1:
        raise ValueError("Patch size must be a positive odd number.")

    if (
        not board
        or not board[0]
        or any(len(row) != len(board[0]) for row in board)
    ):
        raise ValueError("Board must be a nonempty rectangle.")

    rows = len(board)
    cols = len(board[0])
    r, c = cell

    if not (0 <= r < rows and 0 <= c < cols):
        raise ValueError("Candidate is outside the board.")

    if board[r][c] != UNKNOWN:
        raise ValueError("Candidate must be unknown.")

    patch = [
        [
            [0.0 for _ in range(size)]
            for _ in range(size)
        ]
        for _ in range(CHANNEL_COUNT)
    ]

    radius = size // 2

    for y in range(size):
        for x in range(size):
            br = r + y - radius
            bc = c + x - radius

            if not (0 <= br < rows and 0 <= bc < cols):
                channel = 12
            else:
                value = board[br][bc]

                if value == UNKNOWN:
                    channel = 0
                elif value == SAFE:
                    channel = 1
                elif value == MINE:
                    channel = 2
                elif isinstance(value, int) and 0 <= value <= 8:
                    channel = value + 3
                else:
                    raise ValueError(
                        f"Invalid board value {value!r} "
                        f"at {(br, bc)}"
                    )

            patch[channel][y][x] = 1.0

    return patch


def encode_scalars(
    board,
    cell,
    mine_probability,
    total_mines,
):
    """Return normalized numerical features."""

    rows = len(board)
    cols = len(board[0])
    r, c = cell

    if not 0 <= mine_probability <= 1:
        raise ValueError("Invalid mine probability.")

    if not 0 <= total_mines < rows * cols:
        raise ValueError("Invalid total mine count.")

    revealed = sum(
        value >= 0
        for row in board
        for value in row
    )

    unknown = sum(
        value == UNKNOWN
        for row in board
        for value in row
    )

    known_mines = sum(
        value == MINE
        for row in board
        for value in row
    )

    remaining = total_mines - known_mines

    if remaining < 0 or remaining > unknown:
        raise ValueError("Inconsistent remaining mines.")

    return [
        float(mine_probability),
        revealed / (rows * cols),
        remaining / max(1, unknown),
        r / max(1, rows - 1),
        c / max(1, cols - 1),
        unknown / (rows * cols),
    ]


def encode_candidate(
    board,
    cell,
    mine_probability,
    total_mines,
):
    return {
        "patch": encode_patch(board, cell),
        "scalars": encode_scalars(
            board,
            cell,
            mine_probability,
            total_mines,
        ),
    }


def inspect_positions(path):
    position_count = 0
    candidate_count = 0

    stages = {
        "early": 0,
        "middle": 0,
        "late": 0,
    }

    with open(path, encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            position = json.loads(line)

            board = position["board"]
            total_mines = position["total_mines"]

            rows = len(board)
            cols = len(board[0])

            revealed = sum(
                value >= 0
                for row in board
                for value in row
            )

            fraction = revealed / (rows * cols)

            if fraction < 1 / 3:
                stage = "early"
            elif fraction < 2 / 3:
                stage = "middle"
            else:
                stage = "late"

            stages[stage] += 1

            for candidate in position["candidates"]:
                cell = (
                    candidate["row"],
                    candidate["col"],
                )

                encoded = encode_candidate(
                    board,
                    cell,
                    candidate["mine_probability"],
                    total_mines,
                )

                assert len(encoded["patch"]) == CHANNEL_COUNT
                assert len(encoded["scalars"]) == 6

                candidate_count += 1

            position_count += 1

            if position_count <= 5:
                print(
                    f"Position {position_count}: "
                    f"{stage}, "
                    f"{len(position['candidates'])} candidates"
                )

    print("\n=== ENCODING COMPLETE ===")
    print(f"Positions: {position_count}")
    print(f"Candidates: {candidate_count}")
    print(f"Stages: {stages}")
    print(f"Patch shape: ({CHANNEL_COUNT}, 7, 7)")
    print("Scalar shape: (6,)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default="minesweeper_positions.jsonl",
    )

    args = parser.parse_args()

    inspect_positions(args.input)
