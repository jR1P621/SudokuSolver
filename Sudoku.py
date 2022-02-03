from queue import Queue
from typing import Iterable, List
from itertools import combinations


def powerset(iter: Iterable) -> 'set[tuple]':
    '''
    Returns all subsets 's' of iterable 'iter' as a set of tuples where #s >= 2.
    '''
    comb = set([combinations(iter, i) for i in range(2, len(iter) + 1)])
    p_set = set()
    for c in comb:
        for s in c:
            p_set.add(s)
    return p_set


class UniqueQueue():
    '''
    Queue wrapper.

    Maintains a set of current items in Queue to prevent duplicates from being added.
    '''
    def __init__(self) -> None:
        self.que: Queue = Queue()
        self.set: set = set()

    def put(self, item):
        if item not in self.set:
            self.set.add(item)
            self.que.put(item)

    def get(self):
        if not self.empty():
            item = self.que.get()
            self.set.remove(item)
            return item
        return None

    def empty(self):
        return self.que.qsize() == 0


class Space:
    '''
    Contains a value (None or int), constraints, and neighbors.
    '''
    def __init__(self, value=None, n=3) -> None:
        self.value = value
        self.n = n
        if value is not None:
            self.futures = []
        else:
            self.futures = [*range(1, n**2 + 1)]
        self.neighbors: set = set()

    def set_groups(self, groups):
        for g in groups:
            self.neighbors.update(g)
        self.neighbors.remove(self)


class Sudoku:
    '''
    Sudoku board and solver logic.
    '''
    stats = {'cycles': 0, 'recurse': 0}

    def reset_stats() -> None:
        Sudoku.stats = {'cycles': 0, 'recurse': 0}

    def __init__(self, starting_layout, n) -> None:
        self.mod_q: UniqueQueue = UniqueQueue()
        self.spaces: 'dict[Space]' = {}
        self.blocks = {}
        self.rows = {}
        self.cols = {}
        # Create set for each row, col, block
        for i in range(n**2):
            self.blocks[i] = set()
            self.rows[i] = set()
            self.cols[i] = set()
        # Create spaces and add to groups
        for i in range(n**4):
            s: Space = Space(starting_layout[i], n)
            b = (i // n % n) + n * (i // ((n**2) * n))
            h = i // (n**2)
            v = i % (n**2)
            self.blocks[b].add(s)
            self.rows[h].add(s)
            self.cols[v].add(s)
            self.spaces[i] = s
            self.mod_q.put(s)  # Mark Space as modified
        # Link Spaces with their neighbors
        for i in range(n**4):
            b = (i // n % n) + n * (i // ((n**2) * n))
            h = i // (n**2)
            v = i % (n**2)
            self.spaces[i].set_groups([
                self.blocks[b],
                self.rows[h],
                self.cols[v],
            ])
        self.n = n
        self.states = set()
        self.depth = 0
        self.iter_wide = 0

    def solve(self) -> None:
        '''
        Solves the Sudoku puzzle.
        '''
        # Loop through naive constraint search and naked set search
        while not self.is_solved() and not self.has_conflict():
            start_state = self.get_state()
            self.constraint_solve()
            self.update_naked_sets()
            # Did we win?
            if self.get_state() == start_state and self.mod_q.empty():
                break
            Sudoku.stats['cycles'] += 1
        # If stuck, begin recursive backtrace
        if not self.is_solved() and not self.has_conflict():
            if self.depth == 0:  # Root
                self.states.clear()
                # Start with Spaces containing 2 future (constraint) values, then increase
                for i in range(2, self.n**2):
                    self.spaces = self.recursive_backtrack(i)
            else:  # Non-root
                self.spaces = self.recursive_backtrack(self.iter_wide)

    def recursive_backtrack(self, i) -> 'set[Space]':
        '''
        Creates a new game instance, makes a move,
        then attempts to solve to see if the move was correct.

        Returns the set of spaces for the solved board if the move was correct.
        Otherwise, removes the move from the respective Space's constraints and
        returns the current set of spaces (no change).
        '''
        s: Space
        for k, s in self.spaces.items():
            if 2 <= len(s.futures) <= i:
                for j in range(len(s.futures) - 1, 0, -1):
                    Sudoku.stats['recurse'] += 1
                    new_state = self.get_state()
                    new_state[k] = s.futures[j]
                    if str(new_state) not in self.states:
                        self.states.add(str(new_state))
                        new_game: Sudoku = Sudoku(new_state, self.n)
                        new_game.states = self.states
                        new_game.depth = self.depth + 1
                        new_game.iter_wide = i
                        new_game.solve()
                        if new_game.is_solved():
                            return new_game.spaces
                        else:
                            s.futures.remove(s.futures[j])
                            if len(s.futures) == 1:
                                s.value = s.futures[0]
                                s.futures = []
                                break
        return self.spaces

    def constraint_solve(self) -> None:
        '''
        Update's each space's value and/or constraints based on the values of
        it's neighbors (spaces in the same row/col/block).  Each space also updates
        its neighbors values.

        When a space is changed in any way (value or constraints), it is placed onto
        the modified queue.  Function loops until queue is empty.
        '''
        while not self.mod_q.empty():
            curr_space: Space = self.mod_q.get()
            # Only one constraint, set my value
            if len(curr_space.futures) == 1:
                curr_space.value = curr_space.futures[0]
                curr_space.futures = []
            n: Space
            for n in curr_space.neighbors:
                # Remove neighbor values from my constraints
                if n.value in curr_space.futures:
                    curr_space.futures.remove(n.value)
                    self.mod_q.put(curr_space)
                # Remove my value from neighbor constraints
                if curr_space.value in n.futures:
                    n.futures.remove(curr_space.value)
                    self.mod_q.put(n)
                # Only one constraint, set neighbor value
                if len(n.futures) == 1:
                    n.value = n.futures[0]
                    n.futures = []
                    self.mod_q.put(n)

    def update_naked_sets(self) -> None:
        '''
        Finds all naked sets and updates inverse set constraints.
        '''
        groups = []
        # Populate list of every group on board
        for i in range(self.n**2):
            groups.extend([self.blocks[i], self.rows[i], self.cols[i]])
        for g in groups:
            unk_s: List[Space] = []
            s: Space
            # Populate unknown set with blank spaces in group
            for s in g:
                if s.value is None:
                    unk_s.append(s)
            if len(unk_s) > 0:
                # check every subset of unknown set
                p_set = powerset(unk_s)
                for subset in p_set:
                    set_nums: set = set()
                    # Get all constraint values for subset
                    for s in subset:
                        set_nums.update(s.futures)
                    # If #subset == #constraints then subset is naked set
                    # Remove constraints from inverse set members' futures
                    if len(set_nums) == len(subset) < len(unk_s):
                        for s in unk_s:
                            if s not in subset:
                                for n in set_nums:
                                    if n in s.futures:
                                        s.futures.remove(n)
                                        self.mod_q.put(s)

    def is_solved(self) -> bool:
        '''
        Checks is board is solved without conflicts
        '''
        s: Space
        if not self.mod_q.empty(): return False
        for s in self.spaces.values():
            if s.value is None:
                return False
        if self.has_conflict(): return False
        return True

    def has_conflict(self) -> bool:
        '''
        Checks for conflicts
        '''
        s: Space
        for s in self.spaces.values():
            if s.value is None and len(s.futures) == 0:
                return True
        for s in self.spaces.values():
            if s.value is not None:
                n: Space
                for n in s.neighbors:
                    if s.value == n.value:
                        return True
        return False

    def get_state(self) -> List[int]:
        '''
        Returns the current board state as a list
        '''
        return [s.value for s in self.spaces.values()]

    def clone(self) -> object:
        '''
        Creates a clone of the board
        '''
        return Sudoku(self.get_state(), self.n)

    def print(self) -> None:
        '''
        Prints the current board to the terminal

        None -> ' '
        0-9 -> '0-9'
        10, 11, ... -> 'A, B, ...'
        '''
        n = self.n
        for i in range(len(self.spaces)):
            if self.spaces[i].value is None:
                print_val = ' '
            elif self.spaces[i].value < 10:
                print_val = self.spaces[i].value
            else:
                print_val = chr(self.spaces[i].value + 55)
            if i % ((n**2) * n) == 0:
                for _ in range(n):
                    print(' ', end='')
                    for _ in range(n):
                        print('--', end='')
                    print('-', end='')
                print()
            if i % n == 0:
                print('|', end=' ')
            print(print_val, end=' ')
            if (i + 1) % n**2 == 0:
                print('|')
        for _ in range(n):
            print(' ', end='')
            for _ in range(n):
                print('--', end='')
            print('-', end='')
        print()