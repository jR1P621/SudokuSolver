'''
This is a demo of our Sudoku solver capabilities.
It solves 500 puzzles that were randomly selected from the original 3 million.
There are 100 of each difficulty.

The last 2 puzzles are 16x16 and were hand-picked to keep runtime low.

The dataset is stored in 'sudoku-trunc.csv'
Results are saved to 'results-demo.csv'

This demo should take ~10 seconds to run on modern hardware.
'''

import pandas as pd
from Sudoku import Sudoku
import numpy as np
from time import time_ns
from multiprocessing import get_context
from typing import List
import tqdm
import os

# Get files
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
INPUT_FILE = os.path.join(ROOT_DIR, 'sudoku-trunc.csv')
OUTPUT_FILE = os.path.join(ROOT_DIR, 'results-demo.csv')


# Create a list of ints from a state as a string
def parse_puzzle(p_str: str):
    '''
    '.' -> None
    '0-9' -> 0-9
    'A, B, ...' -> 10, 11, ...
    '''
    p_list = []
    for char in p_str:
        if char == '.':
            p_list.append(None)
        elif char > '9':
            p_list.append(ord(char) - 55)
        else:
            p_list.append(int(char))
    return p_list


# Solve a puzzle (for multiprocessing)
def run_puzzle(args) -> dict:
    '''
    args = [puzzle index in dataset: int, puzzle state: List(int)]}
    returns dict{'i': puzzle index in dataset, 'r': stats, 's': solved state}
    '''
    index, state = args[0], args[1]
    n = len(state)
    game = Sudoku(state, round(n**(1. / 4.)))
    Sudoku.reset_stats()
    game.solve()
    return {
        'i': index,
        'r': (Sudoku.stats['cycles'], Sudoku.stats['recurse']),
        's': game.get_state()
    }


if __name__ == "__main__":

    # Read and prep data
    data: pd.DataFrame = pd.read_csv(INPUT_FILE)

    data['parsed'] = data['puzzle'].map(lambda x: parse_puzzle(x))
    data['results'] = np.nan
    data['results'] = data['results'].astype(object)
    data['solution'] = np.nan
    data['solution'] = data['solution'].astype(object)

    # Setup multiprocessing pool and run
    print('Solving Puzzles...')
    pool = get_context("spawn").Pool()
    pool_args = []
    for i, r in data.iterrows():
        pool_args.append([i, r['parsed']])
    data.drop(columns=['parsed'], inplace=True)
    t = time_ns()
    res = list(
        tqdm.tqdm(pool.imap(run_puzzle, pool_args, chunksize=1),
                  total=len(pool_args)))
    pool.close()
    pool.join()
    print(
        f'\nTime taken to solve {len(res)} puzzles: {(time_ns() - t) // 1000000} ms\n'
    )

    # Extract results
    for r in res:
        data.at[r['i'], 'results'] = r['r']
        data.at[r['i'], 'solution'] = r['s']

    # Print output
    print('Would you like to print one of the solved boards?')
    while True:
        selection = -1
        selection = input(
            f'Enter the index of the board you\'d like to see (0-{len(res)-1} or -1 to quit): '
        )
        try:
            selection = int(selection)
            if selection < 0:
                break
            print(
                f'\nPuzzle Difficulty: {data["difficulty"][selection]}/5\nAI Effort: {data["results"][selection][0]}'
            )
            state = pool_args[selection][1]
            n = len(state)
            Sudoku(state, round(n**(1. / 4.))).print()
            state = data['solution'][selection]
            Sudoku(state, round(n**(1. / 4.))).print()
        except Exception as e:
            print(e)

    # Save results to csv
    try:
        data.to_csv(OUTPUT_FILE, mode='w', header=True)
        print('Results saved to sudoku-demo.csv')
    except:
        print('Error saving results to file')