import math
from contextlib import contextmanager

import minesweeper_bot as bot
from simulator import MinesweeperGame
from compare_strategies import entropy_findsafestcell


ROLLOUT_CONFIG = {
    "sample_count": 8,
    "max_candidates": 3,
    "risk_tolerance": 0.03,
    "max_moves": 500,
}


@contextmanager
def use_entropy_strategy():
    previous = bot.findsafestcell

    try:
        bot.findsafestcell = entropy_findsafestcell
        yield

    finally:
        bot.findsafestcell = previous


def create_simulated_game(board, mines, total_mines):
    rows = len(board)
    cols = len(board[0])

    game = MinesweeperGame(
        rows,
        cols,
        total_mines,
    )

    game.mines = set(mines)
    game.clues = game.calculate_clues()
    game.first_click = False

    for row in range(rows):
        for col in range(cols):
            value = board[row][col]

            if value >= 0:
                if (row, col) in game.mines:
                    raise ValueError(
                        "Sample contradicts revealed cell."
                    )

                if game.clues[row][col] != value:
                    raise ValueError(
                        "Sample contradicts revealed clue."
                    )

                game.visible[row][col] = value
                game.revealed.add((row, col))

    game.won = (
        len(game.revealed)
        == rows * cols - total_mines
    )

    return game


def simulate_continuation(
    board,
    mines,
    total_mines,
    first_move,
    max_moves=500,
):
    game = create_simulated_game(
        board,
        mines,
        total_mines,
    )

    known_mines = {
        (r, c)
        for r, row in enumerate(board)
        for c, value in enumerate(row)
        if value == bot.MINE
    }

    pending_safe = {
        (r, c)
        for r, row in enumerate(board)
        for c, value in enumerate(row)
        if value == bot.SAFE
    }

    if first_move in game.revealed:
        raise ValueError("Candidate already revealed.")

    if first_move in game.mines:
        return False

    game.reveal(*first_move)

    if game.won:
        return True

    with use_entropy_strategy():
        for _ in range(max_moves):
            if game.won:
                return True

            if game.lost:
                return False

            visible = game.get_visible_board()

            pending_safe = {
                cell
                for cell in pending_safe
                if cell not in game.revealed
            }

            for r, c in known_mines:
                if visible[r][c] == bot.UNKNOWN:
                    visible[r][c] = bot.MINE

            for r, c in pending_safe:
                if visible[r][c] == bot.UNKNOWN:
                    visible[r][c] = bot.SAFE

            before = [
                row.copy()
                for row in visible
            ]

            move = bot.solveboard(
                visible,
                total_mines,
            )

            for r in range(game.rows):
                for c in range(game.cols):
                    if (
                        before[r][c] == bot.UNKNOWN
                        and visible[r][c] == bot.MINE
                    ):
                        known_mines.add((r, c))

                    if (
                        before[r][c] == bot.UNKNOWN
                        and visible[r][c] == bot.SAFE
                    ):
                        pending_safe.add((r, c))

            if move is None:
                return False

            row, col = move

            if not (
                0 <= row < game.rows
                and 0 <= col < game.cols
            ):
                raise ValueError(
                    f"Invalid rollout move: {move}"
                )

            if move in game.revealed:
                raise ValueError(
                    f"Rollout repeated move: {move}"
                )

            if move in known_mines:
                raise ValueError(
                    f"Rollout clicked known mine: {move}"
                )

            game.reveal(row, col)

    raise RuntimeError(
        "Rollout exceeded maximum move count."
    )


def rollout_findsafestcell(
    probabilities,
    board,
    total_mines,
):
    if not probabilities:
        raise ValueError("No available cells.")

    config = ROLLOUT_CONFIG

    minimum_risk = min(probabilities.values())

    eligible = [
        cell
        for cell, risk in probabilities.items()
        if risk <= (
            minimum_risk
            + config["risk_tolerance"]
            + 1e-12
        )
    ]

    eligible.sort(
        key=lambda cell: (
            probabilities[cell],
            -bot.getinformationscore(board, cell),
            cell[0],
            cell[1],
        )
    )

    candidates = eligible[
        :config["max_candidates"]
    ]

    if len(candidates) == 1:
        return candidates[0]

    sampled_boards = bot.samplevalidboards(
        board,
        total_mines,
        sample_count=config["sample_count"],
    )

    scores = {}

    for cell in candidates:
        wins = 0

        for mines in sampled_boards:
            won = simulate_continuation(
                board,
                mines,
                total_mines,
                cell,
                max_moves=config["max_moves"],
            )

            if won:
                wins += 1

        scores[cell] = wins / len(sampled_boards)

    return max(
        candidates,
        key=lambda cell: (
            scores[cell],
            -probabilities[cell],
            bot.getinformationscore(board, cell),
            -cell[0],
            -cell[1],
        )
    )