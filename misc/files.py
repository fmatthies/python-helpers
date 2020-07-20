# -*- coding: utf-8 -*-
from collections import defaultdict

import numpy as np
import glob
import os
import sys
import random
import shutil
import argparse
from typing import List, Dict


class CmdParser(argparse.ArgumentParser):

    def __init__(self):
        super().__init__()

        self.add_argument('folder', action='store', nargs='+', type=os.path.abspath,
                          help="The folder where all documents are located")
        self.add_argument('count', action='store', nargs='+', type=int,
                          help="On how many subsets all documents should be split up")
        self.add_argument('-e', '--endings', action='store', nargs='*', type=str, default='*',
                          help="What document types should be included (file endings)")
        self.add_argument('-g', '--group-by-ending', action='store_true',
                          help="Whether files shall be grouped by its ending, so that ech file ending is regarded"
                               "separately when 'count' is evaluated.")


def _gather_into_groups(file_index: Dict[int, str], group_count: int, r_seed: int = 42):
    np.random.seed(r_seed)
    np_file_array = np.array(list(file_index.keys()))
    np.random.shuffle(np_file_array)

    return np.array_split(np_file_array, group_count)


def subset_documents(root_folder: str, count: int, endings: List[str], group_endings: bool):
    files = []
    file_types = set(endings)
    for ending in endings:
        fi_pattern = os.path.join(root_folder, "*.{}".format(ending))
        files.extend(glob.glob(fi_pattern))
    if len(endings) == 1 and endings[0] == "*":
        file_types = set([os.path.splitext(e)[-1] for e in files])

    file_index = {i: f for i, f in enumerate(files)}
    rev_file_index = {f: i for i, f in file_index.items()}

    if group_endings:
        endings_file_index = defaultdict(dict)
        for i, file in file_index.items():
            endings_file_index[os.path.splitext(file)[-1]][i] = file
        groups = {group_name: _gather_into_groups(endings_file_index[group_name], count) for group_name in file_types}
    else:
        groups = _gather_into_groups(file_index, count)
    print(groups)


if __name__ == "__main__":
    parser = CmdParser()
    args = parser.parse_args(sys.argv[1:])
    subset_documents(root_folder=args.folder[0], count=args.count[0], endings=args.endings,
                     group_endings=args.group_by_ending)
