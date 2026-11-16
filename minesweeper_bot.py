from itertools import product
import math
import random
from collections import Counter

UNKNOWN = -1
SAFE = -2
MINE = -3


def getneighbours(board, row, col):
    neighbours = []

    for neighbour_row in range(max(0, row - 1), min(len(board), row + 2)):
        for neighbour_col in range(
            max(0, col - 1), min(len(board[neighbour_row]), col + 2)
        ):
            if (neighbour_row, neighbour_col) != (row, col):
                neighbours.append((neighbour_row, neighbour_col))

    return neighbours


def analysecells(board, row, col):

    known_mines = 0
    unknown_cells = []

    neighbours = getneighbours(board, row, col)
    for neighbour_row, neighbour_col in neighbours:
        if board[neighbour_row][neighbour_col] == MINE:
            known_mines += 1
        elif board[neighbour_row][neighbour_col] == UNKNOWN:
            unknown_cells.append((neighbour_row, neighbour_col))

    return known_mines, unknown_cells


def findmines(board):

    for row_index, row in enumerate(board):
        for col_index, cell in enumerate(row):
            if cell > 0:
                known_mines, unknown_cells = analysecells(board, row_index, col_index)

                remaining_mines = cell - known_mines

                if unknown_cells and remaining_mines == len(unknown_cells):
                    for unknown_row, unknown_col in unknown_cells:
                        board[unknown_row][unknown_col] = MINE


def findsafe(board):

    for row_index, row in enumerate(board):
        for col_index, cell in enumerate(row):
            if cell > 0:
                known_mines, unknown_cells = analysecells(board, row_index, col_index)

                remaining_mines = cell - known_mines

                if unknown_cells and remaining_mines == 0:
                    for unknown_row, unknown_col in unknown_cells:
                        board[unknown_row][unknown_col] = SAFE


def getconstraints(board):
    constraints = []

    for row_index, row in enumerate(board):
        for col_index, cell in enumerate(row):
            if cell > 0:
                known_mines, unknown_cells = analysecells(board, row_index, col_index)

                remaining_mines = cell - known_mines

                if remaining_mines < 0 or remaining_mines > len(unknown_cells):
                   raise ValueError(
                       f"Inconsistent state at cell ({row_index}, {col_index}): "
                       f"cell value={cell}, "
                       f"known mines={known_mines}, "
                       f"unknown neighbours={len(unknown_cells)}, "
                       f"remaining mines={remaining_mines}"
                       )

                if unknown_cells:
                    constraints.append((set(unknown_cells), remaining_mines))

    return constraints


def findsubsetdeductions(constraints):

    safe_cells = set()
    mine_cells = set()

    for i in range(len(constraints)):
        for j in range(i + 1, len(constraints)):
            cells_A, mines_A = constraints[i]
            cells_B, mines_B = constraints[j]

            if cells_A == cells_B and mines_A != mines_B:
                raise ValueError(f"Conflicting constraints for {cells_A}: {mines_A} vs {mines_B}")

            diff = set()
            mine_diff = 0

            if cells_A.issubset(cells_B):
                diff = cells_B - cells_A
                mine_diff = mines_B - mines_A

            elif cells_B.issubset(cells_A):
                diff = cells_A - cells_B
                mine_diff = mines_A - mines_B


            if (mine_diff < 0 or mine_diff > len(diff)) and diff:
                raise ValueError(f"Conflicting constraints between {cells_A} and {cells_B}: {mines_A} vs {mines_B}")
            elif diff and mine_diff == 0:
                safe_cells.update(diff)
            elif diff and mine_diff == len(diff):
                mine_cells.update(diff)

    return safe_cells, mine_cells


def applydeductions(board, safe_cells, mine_cells):

    if safe_cells & mine_cells:
        raise ValueError(f"Conflicting deductions: {safe_cells & mine_cells} cannot be both safe and mines.")

    for row, col in safe_cells:
        if board[row][col] == MINE:
            raise ValueError(f"Conflicting deduction: Cell ({row}, {col}) cannot be both safe and a mine.")

    for row, col in mine_cells:
        if board[row][col] == SAFE:
            raise ValueError(f"Conflicting deduction: Cell ({row}, {col}) cannot be both safe and a mine.")

    for row, col in safe_cells:
        if board[row][col] == UNKNOWN:
            board[row][col] = SAFE

    for row, col in mine_cells:
        if board[row][col] == UNKNOWN:
            board[row][col] = MINE


def generatearrangements(num_cells):
    return product((0,1), repeat=num_cells)


def isvalidarrangement(assignment, constraints):
    for cells, mines in constraints:
        mine_count = sum(assignment[cell] for cell in cells)
        if mine_count != mines:
            return False
    return True


def findvalidarrangements(cells, constraints):
    cells = list(cells)

    # Map each cell to the constraints that contain it.
    cell_constraints = {cell: [] for cell in cells}

    constraint_mines = []
    constraint_remaining = []

    for index, (constraint_cells, mines) in enumerate(constraints):
        constraint_mines.append(mines)
        constraint_remaining.append(len(constraint_cells))

        for cell in constraint_cells:
            if cell in cell_constraints:
                cell_constraints[cell].append(index)

    # Process cells involved in the most constraints first.
    cells.sort(
        key=lambda cell: len(cell_constraints[cell]),
        reverse=True
    )

    assigned_mines = [0] * len(constraints)
    assignment = {}
    valid_arrangements = []

    def backtrack(index):
        if index == len(cells):
            # All constraints must be satisfied.
            if all(
                assigned_mines[i] == constraint_mines[i]
                for i in range(len(constraints))
            ):
                valid_arrangements.append(assignment.copy())
            return

        cell = cells[index]
        affected = cell_constraints[cell]

        for value in (0, 1):
            assignment[cell] = value
            valid = True

            # Update only constraints involving this cell.
            for constraint_index in affected:
                assigned_mines[constraint_index] += value
                constraint_remaining[constraint_index] -= 1

                mines = assigned_mines[constraint_index]
                remaining = constraint_remaining[constraint_index]
                target = constraint_mines[constraint_index]

                if mines > target:
                    valid = False

                if mines + remaining < target:
                    valid = False

            if valid:
                backtrack(index + 1)

            # Restore state before trying the next value.
            for constraint_index in affected:
                assigned_mines[constraint_index] -= value
                constraint_remaining[constraint_index] += 1

            del assignment[cell]

    backtrack(0)

    return valid_arrangements


def isvalidpartialassignment(assignment, constraints):
    for cells, mines in constraints:
        assigned_cells = [cell for cell in cells if cell in assignment]

        assigned_mines = sum(assignment[cell] for cell in assigned_cells)
        remaining_cells = len(cells) - len(assigned_cells)

        if assigned_mines > mines:
            return False

        if assigned_mines + remaining_cells < mines:
            return False

    return True


def findguaranteedcells(valid_arrangements):
    if not valid_arrangements:
        raise ValueError("No valid arrangements found. The board is in an inconsistent state.")

    safe_cells = set()
    mine_cells = set()

    for cell in valid_arrangements[0]:
        if all(assignment[cell] == 0 for assignment in valid_arrangements):
            safe_cells.add(cell)
        elif all(assignment[cell] == 1 for assignment in valid_arrangements):
            mine_cells.add(cell)


    return safe_cells, mine_cells


def groupconstraints(constraints):
    groups = []
    remaining = constraints.copy()

    while remaining:
        first_constraint = remaining.pop(0)
        group = [first_constraint]

        group_cells = first_constraint[0].copy()

        changed = True

        while changed:
            changed = False
            for constraint in remaining.copy():
                if group_cells & constraint[0]:
                    group.append(constraint)
                    group_cells.update(constraint[0])
                    remaining.remove(constraint)
                    changed = True

        groups.append(group)

    return groups


def findmineprobabilties(valid_arrangements):
    total = len(valid_arrangements)
    probabilities = {}

    if total < 1:
        raise ValueError("Cannot find mine probabilities as there are no valid arrangements.")

    for cell in valid_arrangements[0]:
        mine_count = sum(assignment[cell] for assignment in valid_arrangements)
        probabilities[cell] = mine_count / total

    return probabilities


def getinformationscore(board, cell):
    row, col = cell
    neighbours = getneighbours(board, row, col)

    unknown_neighbours = 0
    revealed_neighbours = 0

    for neighbour_row, neighbour_col in neighbours:
        value = board[neighbour_row][neighbour_col]

        if value == UNKNOWN:
            unknown_neighbours += 1
        elif value >= 0:
            revealed_neighbours += 1

    # Reward opportunities to explore unknown territory.
    exploration_score = unknown_neighbours

    # Reward moves that connect to existing revealed information.
    constraint_score = revealed_neighbours

    return exploration_score + constraint_score * 0.5


def weightedchoice(items, weights, rng):
    total = sum(weights)
    if total <= 0:
        raise ValueError("No valid weighted choices.")

    target = rng.randrange(total)
    cumulative = 0

    for item, weight in zip(items, weights):
        cumulative += weight
        if target < cumulative:
            return item

    raise RuntimeError("Weighted selection failed.")


def samplevalidboards(board, total_mines, sample_count=300, seed=42):
    rng = random.Random(seed)

    constraints = getconstraints(board)
    groups = groupconstraints(constraints)

    group_arrangements = []
    for group in groups:
        cells = set()

        for constraint in group:
            cells.update(constraint[0])

        arrangements = findvalidarrangements(sorted(cells), group)

        if not arrangements:
            raise ValueError("No valid arrangements in constraint group.")

        group_arrangements.append(arrangements)

    remaining_mines = countremainingmines(board, total_mines)
    unconstrained_cells = sorted(
        findunconstrainedcells(board, constraints)
    )
    num_unconstrained = len(unconstrained_cells)

    group_buckets = []

    for arrangements in group_arrangements:
        buckets = {}

        for assignment in arrangements:
            mine_count = sum(assignment.values())
            buckets.setdefault(mine_count, []).append(assignment)

        group_buckets.append(buckets)

    suffix_counts = [None] * (len(group_buckets) + 1)
    suffix_counts[-1] = {0: 1}

    for i in range(len(group_buckets) - 1, -1, -1):
        local_counts = {
            mine_count: len(assignments)
            for mine_count, assignments in group_buckets[i].items()
        }

        suffix_counts[i] = combinecounts(
            local_counts,
            suffix_counts[i + 1]
        )

    def completioncount(group_index, mines_left):
        total = 0

        for group_mines, count in suffix_counts[group_index].items():
            outside_mines = mines_left - group_mines

            if 0 <= outside_mines <= num_unconstrained:
                total += count * math.comb(
                    num_unconstrained,
                    outside_mines
                )

        return total

    if completioncount(0, remaining_mines) == 0:
        raise ValueError("No globally valid mine arrangements.")

    known_mines = {
        (r, c)
        for r, row in enumerate(board)
        for c, value in enumerate(row)
        if value == MINE
    }

    samples = []

    for _ in range(sample_count):
        sampled_mines = set(known_mines)
        mines_left = remaining_mines

        for group_index, buckets in enumerate(group_buckets):
            options = []
            weights = []

            for mine_count, assignments in buckets.items():
                completions = completioncount(
                    group_index + 1,
                    mines_left - mine_count
                )

                weight = len(assignments) * completions

                if weight > 0:
                    options.append(mine_count)
                    weights.append(weight)

            selected_count = weightedchoice(options, weights, rng)
            assignment = rng.choice(buckets[selected_count])

            for cell, is_mine in assignment.items():
                if is_mine:
                    sampled_mines.add(cell)

            mines_left -= selected_count

        if mines_left < 0 or mines_left > num_unconstrained:
            raise ValueError("Invalid unconstrained mine count.")

        sampled_mines.update(
            rng.sample(unconstrained_cells, mines_left)
        )

        samples.append(sampled_mines)

    return samples


def getcluedistribution(board, cell, sampled_boards):
    neighbours = getneighbours(board, *cell)

    clue_counts = Counter()
    safe_samples = 0

    for mines in sampled_boards:
        if cell in mines:
            continue

        safe_samples += 1

        clue = sum(
            neighbour in mines
            for neighbour in neighbours
        )

        clue_counts[clue] += 1

    return clue_counts, safe_samples


def getexpectedinformationgain(board, cell, sampled_boards):
    clue_counts, safe_samples = getcluedistribution(
        board,
        cell,
        sampled_boards
    )

    if safe_samples == 0:
        return 0.0

    entropy = 0.0

    for count in clue_counts.values():
        probability = count / safe_samples
        entropy -= probability * math.log2(probability)

    return entropy


def lookahead_reveal(board, cell, mines):
    """
    Simulate revealing a safe cell on one sampled minefield.

    Includes the automatic opening of zero regions.
    Returns a new visible board without exposing hidden mines.
    """
    simulated = [row.copy() for row in board]
    rows = len(board)
    cols = len(board[0])

    queue = [cell]
    visited = set()

    while queue:
        row, col = queue.pop()

        if (row, col) in visited:
            continue

        visited.add((row, col))

        if (row, col) in mines:
            continue

        if simulated[row][col] >= 0:
            continue

        neighbours = getneighbours(simulated, row, col)

        clue = sum(
            (nr, nc) in mines
            for nr, nc in neighbours
        )

        simulated[row][col] = clue

        if clue == 0:
            for nr, nc in neighbours:
                if (
                    (nr, nc) not in visited
                    and simulated[nr][nc] == UNKNOWN
                ):
                    queue.append((nr, nc))

    return simulated


def lookahead_deduction_count(board):
    """
    Count guaranteed-safe unknown cells obtainable through
    basic constraint propagation and subset deductions.

    This evaluator uses visible clues only.
    """
    rows = len(board)
    cols = len(board[0])

    known_safe = set()
    known_mines = {
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if board[r][c] == MINE
    }

    # SAFE markers are already known safe.
    known_safe.update(
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if board[r][c] == SAFE
    )

    initial_safe = set(known_safe)

    while True:
        constraints = []
        new_safe = set()
        new_mines = set()

        for row in range(rows):
            for col in range(cols):
                clue = board[row][col]

                if clue < 0:
                    continue

                neighbours = getneighbours(board, row, col)

                remaining = {
                    cell
                    for cell in neighbours
                    if board[cell[0]][cell[1]] == UNKNOWN
                    and cell not in known_safe
                    and cell not in known_mines
                }

                mines_found = sum(
                    cell in known_mines
                    for cell in neighbours
                )

                mines_needed = clue - mines_found

                if not 0 <= mines_needed <= len(remaining):
                    return len(known_safe - initial_safe)

                if not remaining:
                    continue

                constraints.append(
                    (frozenset(remaining), mines_needed)
                )

        # Basic deductions.
        for cells, mines_needed in constraints:
            if mines_needed == 0:
                new_safe.update(cells)
            elif mines_needed == len(cells):
                new_mines.update(cells)

        # Subset deductions.
        for i, (cells_a, mines_a) in enumerate(constraints):
            for j, (cells_b, mines_b) in enumerate(constraints):
                if i == j or not cells_a < cells_b:
                    continue

                difference = cells_b - cells_a
                difference_mines = mines_b - mines_a

                if difference_mines == 0:
                    new_safe.update(difference)

                elif difference_mines == len(difference):
                    new_mines.update(difference)

        new_safe -= known_safe
        new_mines -= known_mines

        if new_safe & new_mines:
            return len(known_safe - initial_safe)

        if not new_safe and not new_mines:
            break

        known_safe.update(new_safe)
        known_mines.update(new_mines)

    return len(known_safe - initial_safe)


def getlookaheadscore(board, cell, sampled_boards):
    """
    Estimate the number of newly revealed or deducible
    safe cells after clicking a candidate.

    Scores are conditional on the click being safe.
    """
    total_score = 0.0
    safe_samples = 0

    already_revealed = sum(
        value >= 0
        for row in board
        for value in row
    )

    for mines in sampled_boards:
        if cell in mines:
            continue

        simulated = lookahead_reveal(board, cell, mines)

        revealed_after = sum(
            value >= 0
            for row in simulated
            for value in row
        )

        newly_revealed = (
            revealed_after - already_revealed
        )

        deductions = lookahead_deduction_count(simulated)

        total_score += newly_revealed + deductions
        safe_samples += 1

    if safe_samples == 0:
        return 0.0

    return total_score / safe_samples


def findsafestcell(
    probabilities,
    board,
    total_mines,
    sample_count=80,
    max_candidates=6,
):
    if not probabilities:
        raise ValueError("No available cells to choose from.")

    min_probability = min(probabilities.values())

    safest_cells = [
        cell
        for cell, probability in probabilities.items()
        if math.isclose(
            probability,
            min_probability,
            rel_tol=0,
            abs_tol=1e-12,
        )
    ]

    if len(safest_cells) == 1:
        return safest_cells[0]

    # Shortlist candidates using the previous heuristic.
    safest_cells.sort(
        key=lambda cell: (
            -getinformationscore(board, cell),
            cell[0],
            cell[1],
        )
    )

    candidates = safest_cells[:max_candidates]

    # Sample complete minefields consistent with visible clues.
    sampled_boards = samplevalidboards(
        board,
        total_mines,
        sample_count=sample_count,
    )

    if not sampled_boards:
        return candidates[0]

    scores = {
        cell: getlookaheadscore(
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
            getinformationscore(board, cell),
            -cell[0],
            -cell[1],
        )
    )


def countremainingmines(board, total_mines):
    if total_mines < 0:
        raise ValueError("Total mines cannot be negative.")

    known_mines = 0

    for row in board:
        for cell in row:
            if cell == MINE:
                known_mines += 1

    remaining_mines = total_mines - known_mines

    if remaining_mines < 0:
        raise ValueError("More cells have been marked MINE than total_mines indicates.")
    
    return remaining_mines


def findunconstrainedcells(board, constraints):
    constrained_cells = set()
    unknown_cells = set()

    for constraint in constraints:
        constrained_cells.update(constraint[0])

    for row_index, row in enumerate(board):
        for col_index, cell in enumerate(row):
            if cell == UNKNOWN:
                unknown_cells.add((row_index, col_index))

    return unknown_cells - constrained_cells


def getassignmentweight(assignment, remaining_mines, num_unconstrained):
    mines_in_group = sum(assignment.values())
    mines_outside_group = remaining_mines - mines_in_group
    
    if mines_outside_group < 0 or mines_outside_group > num_unconstrained:
        return 0
    return math.comb(num_unconstrained, mines_outside_group)


def countcompleteboards(valid_arrangements, remaining_mines, num_unconstrained):
    total = 0

    for assignment in valid_arrangements:
        total += getassignmentweight(assignment, remaining_mines, num_unconstrained)

    return total


def findweightedprobabilities(valid_arrangements, remaining_mines, num_unconstrained):
    total_boards = countcompleteboards(valid_arrangements, remaining_mines, num_unconstrained)

    if total_boards == 0:
        raise ValueError("No valid compelte board arrangements exist.")

    probabilities = {}

    for cell in valid_arrangements[0]:
        weighted_mine_count = 0

        for assignment in valid_arrangements:
            weight = getassignmentweight(assignment, remaining_mines, num_unconstrained)

            if assignment[cell] == 1:
                weighted_mine_count += weight

        probabilities[cell] = weighted_mine_count / total_boards

    return probabilities


def findunconstrainedprobability(valid_arrangements, remaining_mines, num_unconstrained):
    if num_unconstrained == 0:
        raise ValueError("There are no unconstrained cells")

    total_boards = countcompleteboards(valid_arrangements, remaining_mines, num_unconstrained)

    if total_boards == 0:
        raise ValueError("No valid compelte board arrangements exist.")

    weighted_mine_count = 0

    for assignment in valid_arrangements:
        weight = getassignmentweight(assignment, remaining_mines, num_unconstrained)

        mines_outside_group = remaining_mines - sum(assignment.values())
        weighted_mine_count += mines_outside_group * weight

    return weighted_mine_count / (total_boards * num_unconstrained)


def countassignmentbymines(valid_arrangements):
    counts = {}

    for assignment in valid_arrangements:
        mine_count = sum(assignment.values())

        if mine_count in counts:
            counts[mine_count] += 1
        else:
            counts[mine_count] = 1

    return counts


def combinecounts(counts_a, counts_b):
    combined = {}

    for mines_a, arrangements_a in counts_a.items():
        for mines_b, arrangements_b in counts_b.items():
            total_mines = mines_a + mines_b
            total_arrangements = arrangements_a * arrangements_b

            if total_mines in combined:
                combined[total_mines] += total_arrangements
            else:
                combined[total_mines] = total_arrangements

    return combined


def combineallcounts(group_counts):
    combined = {0: 1}

    for group in group_counts:
        combined = combinecounts(combined, group)

    return combined


def countallcompleteboards(combined_counts, remaining_mines, num_unconstrained):
    total_boards = 0

    for mines_in_groups, arrangement_count in combined_counts.items():
        mines_outside_groups = remaining_mines - mines_in_groups
        if mines_outside_groups < 0 or mines_outside_groups > num_unconstrained:
            continue

        total_boards += arrangement_count * math.comb(num_unconstrained, mines_outside_groups)

    return total_boards


def countassignmentsbymines(valid_arrangements, cell):
    counts = {}

    for assignment in valid_arrangements:
        if assignment[cell] == 1:
            mine_count = sum(assignment.values())

            if mine_count in counts:
                counts[mine_count] += 1
            else:
                counts[mine_count] = 1

    return counts


def findmultigroupprobability(group_arrangements, target_group_index, cell, remaining_mines, num_unconstrained):
    group_counts = []

    for arrangements in group_arrangements:
        group_counts.append(countassignmentbymines(arrangements))

    other_groups = []

    for group_index, group in enumerate(group_counts):
        if group_index != target_group_index:
            other_groups.append(group)

    other_counts = combineallcounts(other_groups)
    target_counts = countassignmentsbymines(group_arrangements[target_group_index], cell)

    mine_counts = combinecounts(other_counts, target_counts)
    mine_boards = countallcompleteboards(mine_counts, remaining_mines, num_unconstrained)

    all_counts = combineallcounts(group_counts)

    total_boards = countallcompleteboards(all_counts, remaining_mines, num_unconstrained)

    if total_boards == 0:
        raise ValueError("No valid complete boards exist.")

    return mine_boards / total_boards


def findmultiunconstrainedprobability(group_arrangements, remaining_mines, num_unconstrained):
    if num_unconstrained == 0:
        raise ValueError("There are no unconstrained cells.")

    group_counts = []

    for arrangements in group_arrangements:
        group_counts.append(countassignmentbymines(arrangements))

    combined_counts = combineallcounts(group_counts)

    total_boards = countallcompleteboards(combined_counts, remaining_mines, num_unconstrained)

    if total_boards == 0:
        raise ValueError("No valid complete boards exist.")

    weighted_mine_count = 0

    for mines_in_groups, arrangement_count in combined_counts.items():
        mines_outside_group = remaining_mines - mines_in_groups

        if mines_outside_group < 0 or mines_outside_group > num_unconstrained:
            continue

        weight = arrangement_count * math.comb(num_unconstrained, mines_outside_group)

        weighted_mine_count += mines_outside_group * weight

    return weighted_mine_count / (total_boards * num_unconstrained)


def getboardprobabilities(board, total_mines):
    constraints = getconstraints(board)

    groups = groupconstraints(constraints)

    group_arrangements = []

    for group in groups:
        cells = set()

        for constraint in group:
            cells.update(constraint[0])

        arrangements = findvalidarrangements(cells, group)
        group_arrangements.append(arrangements)

    remaining_mines = countremainingmines(board, total_mines)

    unconstrained_cells = findunconstrainedcells(board, constraints)
    num_unconstrained = len(unconstrained_cells)

    probabilities = {}

    for group_index, arrangements in enumerate(group_arrangements):
        for cell in arrangements[0]:
            probabilities[cell] = findmultigroupprobability(group_arrangements, group_index, cell, remaining_mines, num_unconstrained)

    if num_unconstrained > 0:
        unconstrained_probability = findmultiunconstrainedprobability(group_arrangements, remaining_mines, num_unconstrained)

        for cell in unconstrained_cells:
            probabilities[cell] = unconstrained_probability

    return probabilities


def choosemove(board, total_mines):
    probabilities = getboardprobabilities(board, total_mines)

    return findsafestcell(
        probabilities,
        board,
        total_mines
    )


def solveboard(board, total_mines):

    while True:
        original = [row.copy() for row in board]

        try:
            getconstraints(board)

            findmines(board)
            findsafe(board)

        
            constraints = getconstraints(board)


            safe_cells, mine_cells = findsubsetdeductions(constraints)

            applydeductions(board, safe_cells, mine_cells)

            constraints = getconstraints(board)

            groups = groupconstraints(constraints)

            
            for group in groups:
                cells = set()

                for constraint in group:
                    cells.update(constraint[0])

                cells = sorted(cells)

                valid_arrangements = findvalidarrangements(cells, group)

                safe_cells, mine_cells = findguaranteedcells(valid_arrangements)

                applydeductions(board, safe_cells, mine_cells)


        except ValueError as e:
            raise ValueError(f"SOlver encountered an inconsistent state: {e}") from e

        if board == original:
            safe_cells = []
            
            for row_index, row in enumerate(board):
                for col_index, cell in enumerate(row):
                    if cell == SAFE:
                        safe_cells.append((row_index, col_index))


            if safe_cells:
                return safe_cells[0]

            if any(UNKNOWN in row for row in board):
                return choosemove(board, total_mines)
                
            return None
        

# if __name__ == "__main__":

    board = [
        [1, MINE],
        [1, 1]
    ]

    cells = [(0, 0), (0, 1), (0, 2), (0, 3)]

    constraints = [
        ({(0, 1), (0, 2), (1, 1)}, 1)
    ]

    valid_arrangements = [
        {(0, 0): 1, (0, 1): 0},
        {(0, 0): 0, (0, 1): 1},
        {(0, 0): 1, (0, 1): 1},
        {(0, 0): 0, (0, 1): 0}
    ]

    probabilities = {
        (0, 0): 0.6,
        (0, 1): 0.2,
        (0, 2): 0.8
    }

    counts_a = {0: 2, 1: 3}
    counts_b = {1: 4, 2: 2}

    group_counts = [
        {0: 2, 1: 3},
        {1: 4, 2: 2},
        {0: 1, 1: 2}
    ]

    combined_counts = {1: 8, 2: 32, 3: 38, 4: 12}

    group_arrangements = [
        [
            {(0, 0): 1, (0, 1): 0},
            {(0, 0): 0, (0, 1): 0}
        ],
        [
            {(0, 4): 1, (0, 5): 0},
            {(0, 4): 0, (0, 5): 1}
        ]
    ]

    print(solveboard(board, 1))



    test_board = [
        [0, 1, UNKNOWN, UNKNOWN],
        [0, 1, UNKNOWN, UNKNOWN],
        [0, 1, UNKNOWN, UNKNOWN],
        [0, 0, UNKNOWN, UNKNOWN]
    ]

    test_probabilities = {
        (0, 2): 0.20,
        (1, 2): 0.20,
        (2, 2): 0.20,
        (3, 2): 0.20
    }

    for cell in test_probabilities:
        print(cell, getinformationscore(test_board, cell))

    print("Selected:", findsafestcell(test_probabilities, test_board))


