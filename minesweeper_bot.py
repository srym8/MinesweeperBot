from itertools import product
import math

UNKNOWN = -1
SAFE = -2
MINE = -3

board = [
    [UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN],
    [1, 1, 1, 0],
    [0, 0, 0, 0]
]

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
                   raise ValueError(f"Warning: Inconsistent state at cell ({row_index}, {col_index}).")

                if unknown_cells and remaining_mines >= 0 and remaining_mines <= len(unknown_cells):
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
    valid_arrangements = []
    for arrangement in generatearrangements(len(cells)):
        assignment = dict(zip(cells, arrangement))
        if isvalidarrangement(assignment, constraints):
            valid_arrangements.append(assignment)
    return valid_arrangements


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


def findsafestcell(probabilities):
    if not probabilities:
        raise ValueError("Cannot find safest cell: no probabilities to check.")
    return min(probabilities, key=probabilities.get)


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

    return findsafestcell(probabilities)


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
            print(e)
            return

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
        


board = [
    [1, MINE],
    [1, 1]
]

cells = [(0, 0), (0, 1), (0, 2), (0, 3)]

constraints = [
    ({(0, 1), (1, 0), (1, 1)}, 1)
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