import argparse
import random
import statistics
import time

from collections import deque
from dataclasses import dataclass

from minesweeper_bot import (
    UNKNOWN,
    SAFE,
    MINE,
    solveboard,
)

DIFFICULTIES = {
    "beginner": (9, 9, 10),
    "intermediate": (16, 16, 40),
    "expert": (16, 30, 99),
}


@dataclass
class GameResult:
    seed: int
    result: str
    moves: int
    guesses: int
    seconds: float
    reason: str = ""


class MinesweeperGame:
    def __init__(self, rows, cols, total_mines, seed=None):
        if rows <= 0 or cols <= 0:
            raise ValueError("Board dimensions must be positive.")

        if not 0 <= total_mines < rows * cols:
            raise ValueError("Invalid number of mines.")

        self.rows = rows
        self.cols = cols
        self.total_mines = total_mines
        self.seed = seed
        self.rng = random.Random(seed)

        self.mines = set()

        self.visible = [
            [UNKNOWN for _ in range(cols)]
            for _ in range(rows)
        ]

        self.revealed = set()
        self.first_click = True
        self.lost = False
        self.won = False
        self.clues = None

    def neighbours(self, row, col):
        for r in range(max(0, row - 1), min(self.rows, row + 2)):
            for c in range(max(0, col - 1), min(self.cols, col + 2)):
                if (r, c) != (row, col):
                    yield (r, c)

    def calculate_clues(self):
        clues = [
            [0 for _ in range(self.cols)]
            for _ in range(self.rows)
        ]

        for row in range(self.rows):
            for col in range(self.cols):
                if (row, col) in self.mines:
                    continue

                clues[row][col] = sum(
                    neighbour in self.mines
                    for neighbour in self.neighbours(row, col)
                )

        return clues

    def make_first_click_safe(self, row, col):
        available = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) != (row, col)
        ]

        self.mines = set(
            self.rng.sample(available, self.total_mines)
        )

        self.clues = self.calculate_clues()


    def reveal(self, row, col):
        if self.lost or self.won:
            return

        if not (0 <= row < self.rows and 0 <= col < self.cols):
            raise ValueError("Move is outside the board.")

        if (row, col) in self.revealed:
            raise ValueError("Cell has already been revealed.")

        if self.first_click:
            self.make_first_click_safe(row, col)
            self.first_click = False

        if (row, col) in self.mines:
            self.lost = True
            return

        queue = deque([(row, col)])

        while queue:
            r, c = queue.popleft()

            if (r, c) in self.revealed:
                continue

            if (r, c) in self.mines:
                continue

            self.revealed.add((r, c))
            self.visible[r][c] = self.clues[r][c]

            if self.clues[r][c] == 0:
                for neighbour in self.neighbours(r, c):
                    if neighbour not in self.revealed:
                        queue.append(neighbour)

        safe_cell_count = (
            self.rows * self.cols - self.total_mines
        )

        if len(self.revealed) == safe_cell_count:
            self.won = True

    def get_visible_board(self):
        return [row.copy() for row in self.visible]

    def print_board(self, show_mines=False):
        for row in range(self.rows):
            symbols = []

            for col in range(self.cols):
                cell = self.visible[row][col]

                if show_mines and (row, col) in self.mines:
                    symbol = "*"
                elif cell == UNKNOWN:
                    symbol = "."
                elif cell == 0:
                    symbol = " "
                else:
                    symbol = str(cell)

                symbols.append(symbol)

            print(" ".join(symbols))


def play_game(
    rows,
    cols,
    total_mines,
    seed,
    max_moves=None,
    verbose=False,
):
    game = MinesweeperGame(rows, cols, total_mines, seed)

    start_time = time.perf_counter()
    moves = 0
    guesses = 0
    known_mines = set()

    if max_moves is None:
        max_moves = rows * cols + 10

    while not game.won and not game.lost:
        if moves >= max_moves:
            return GameResult(
                seed,
                "Incomplete",
                moves,
                guesses,
                time.perf_counter() - start_time,
                "Move limit reached",
            )

        board = game.get_visible_board()

        for row, col in known_mines:
            if board[row][col] == UNKNOWN:
                board[row][col] = MINE

        original_board = [row.copy() for row in board]

        try:
            move = solveboard(board, total_mines)
        except Exception as error:
            return GameResult(
                seed,
                "Error",
                moves,
                guesses,
                time.perf_counter() - start_time,
                f"{type(error).__name__}: {error}",
            )

        for row in range(rows):
            for col in range(cols):
                if (
                    original_board[row][col] == UNKNOWN
                    and board[row][col] == MINE
                ):
                    known_mines.add((row, col))

        if move is None:
            return GameResult(
                seed,
                "Incomplete",
                moves,
                guesses,
                time.perf_counter() - start_time,
                "Solver returned no move",
            )

        row, col = move

        if not (
            isinstance(row, int)
            and isinstance(col, int)
            and 0 <= row < rows
            and 0 <= col < cols
        ):
            return GameResult(
                seed,
                "Error",
                moves,
                guesses,
                time.perf_counter() - start_time,
                f"Invalid move: {move}",
            )

        if original_board[row][col] != UNKNOWN:
            return GameResult(
                seed,
                "Error",
                moves,
                guesses,
                time.perf_counter() - start_time,
                f"Solver selected unavailable cell {move}",
            )

        is_guess = board[row][col] != SAFE

        if is_guess and moves > 0:
            guesses += 1

        if verbose:
            kind = "Guess" if is_guess else "Safe deduction"
            print(f"Move {moves + 1}: {move} [{kind}]")

        game.reveal(row, col)
        moves += 1

        if verbose:
            game.print_board()
            print()

    elapsed = time.perf_counter() - start_time

    return GameResult(
        seed=seed,
        result="Win" if game.won else "Loss",
        moves=moves,
        guesses=guesses,
        seconds=elapsed,
    )


def run_benchmark(
    difficulty="intermediate",
    total_games=100,
    starting_seed=0,
    verbose=False,
):
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"Unknown difficulty: {difficulty}")

    if total_games < 1:
        raise ValueError("total_games must be at least 1.")

    rows, cols, total_mines = DIFFICULTIES[difficulty]

    print(f"\n--- {difficulty.upper()} BENCHMARK ---")
    print(f"Board: {rows} x {cols}")
    print(f"Mines: {total_mines}")
    print(f"Games requested: {total_games}")
    print(f"Starting seed: {starting_seed}")
    print()

    results = []
    benchmark_start = time.perf_counter()

    for game_index in range(total_games):
        seed = starting_seed + game_index

        result = play_game(
            rows,
            cols,
            total_mines,
            seed=seed,
            verbose=verbose,
        )

        results.append(result)

        if verbose or (game_index + 1) % 10 == 0:
            print(
                f"Game {game_index + 1}/{total_games}: "
                f"{result.result} | "
                f"{result.moves} moves | "
                f"{result.guesses} guesses | "
                f"{result.seconds:.3f}s"
            )

        if result.result not in ("Win", "Loss"):
            print(
                f"Game {game_index + 1}, seed {seed}: "
                f"{result.result} - {result.reason}"
            )

    wins = [r for r in results if r.result == "Win"]
    losses = [r for r in results if r.result == "Loss"]

    completed = wins + losses

    failures = [
        r for r in results
        if r.result not in ("Win", "Loss")
    ]

    print("\n--- BENCHMARK RESULTS ---")
    print(f"Games requested: {total_games}")
    print(f"Games completed: {len(completed)}")
    print(f"Wins: {len(wins)}")
    print(f"Losses: {len(losses)}")
    print(f"Errors/incomplete: {len(failures)}")

    if completed:
        win_rate = 100 * len(wins) / len(completed)

        print(f"Win rate: {win_rate:.2f}%")

        print(
            "Average moves: "
            f"{statistics.mean(r.moves for r in completed):.2f}"
        )

        print(
            "Average guesses: "
            f"{statistics.mean(r.guesses for r in completed):.2f}"
        )

        print(
            "Average game time: "
            f"{statistics.mean(r.seconds for r in completed):.4f}s"
        )

        if wins:
            print(
                "Average winning time: "
                f"{statistics.mean(r.seconds for r in wins):.4f}s"
            )

    total_time = time.perf_counter() - benchmark_start

    print(f"Total benchmark time: {total_time:.2f}s")

    if failures:
        print("\nFirst five unsuccessful simulations:")

        for result in failures[:5]:
            print(
                f"Seed {result.seed}: "
                f"{result.result} - {result.reason}"
            )

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Minesweeper solver benchmark simulator"
    )

    parser.add_argument(
        "--difficulty",
        choices=list(DIFFICULTIES),
        default="intermediate",
    )

    parser.add_argument(
        "--games",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
    )

    args = parser.parse_args()

    run_benchmark(
        difficulty=args.difficulty,
        total_games=args.games,
        starting_seed=args.seed,
        verbose=args.verbose,
    )