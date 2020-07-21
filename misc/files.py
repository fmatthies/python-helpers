# -*- coding: utf-8 -*-
from collections import defaultdict

from typing import List, Dict, Union
import numpy as np
import glob
import os
import sys
import argparse
import logging


class CmdParser(argparse.ArgumentParser):

    def __init__(self):
        super().__init__()

        self.add_argument('folder', action='store', nargs='+', type=os.path.abspath,
                          help="The folder where all documents are located")
        self.add_argument('subsets', action='store', nargs='+', type=int,
                          help="On how many subsets all documents should be split up")
        self.add_argument('-e', '--endings', action='store', nargs='*', type=str, default='*',
                          help="What document types should be included (file endings); default='*' (i.e. all)")
        self.add_argument('-r', '--random-seed', action='store', nargs='*', type=int, default=42,
                          help="Random seed for shuffling and splitting the subsets; default=42")
        self.add_argument('-g', '--group-by-ending', action='store_true',
                          help="Whether files shall be grouped by its ending, so that ech file ending is regarded"
                               "separately when 'count' is evaluated. This is a flag and evaluates to True if present.")
        self.add_argument('-s', '--suppress_empty', action='store_true',
                          help="Whether groups that are empty (because there were fewer documents than subsets)"
                               "shall be suppressed. This is a flag and evaluates to True if present.")


def _gather_into_groups(file_index: Dict[int, str], group_count: int, r_seed: int = 42, suppress_empty: bool = False):
    np.random.seed(r_seed)
    np_file_array = np.array(list(file_index.keys()))
    np.random.shuffle(np_file_array)

    if suppress_empty:
        return [x.tolist() for x in np.array_split(np_file_array, group_count) if len(x) != 0]
    return [x.tolist() for x in np.array_split(np_file_array, group_count)]


def _file_size_distribution(groups: Union[Dict[str, List[List[int]]], List[List[int]]], file_index: Dict[int, str],
                            ending: str = "ungrouped", return_dict: dict = {}):
    if isinstance(groups, dict):
        for ending, groups in groups.items():
            _file_size_distribution(groups, file_index, ending, return_dict)
    else:
        size_means = list()
        for group_index, group in enumerate(groups):
            if len(group) > 0:
                size_means.append(np.mean([os.stat(file_index[f]).st_size for f in group]))
            else:
                logging.warning("'{}': subset at index {} is empty!\n\t---> subsets: {}"
                                .format(ending, group_index, groups))
        sizes_std = np.std(size_means)
        for group_index, group_mean in enumerate(size_means):
            if group_mean < sizes_std:
                logging.warning("'{}': subset at index {} is significantly smaller than the other subsets (size: {})!"
                                "\n\t---> size means: [{}]\n\t---> subsets: {}"
                                .format(ending, group_index, size_means[group_index],
                                        ", ".join([str(i) for i in size_means]), groups))
        return_dict[ending] = size_means
    return return_dict


def subset_documents(root_folder: str, subsets: int, endings: List[str], random_seed: int,
                     group_endings: bool = False, suppress_empty: bool = False):
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
        groups = {group_name: _gather_into_groups(endings_file_index[group_name], subsets, random_seed, suppress_empty)
                  for group_name in file_types}
    else:
        groups = _gather_into_groups(file_index, subsets, random_seed, suppress_empty)

    size_distro = _file_size_distribution(groups, file_index)
    print(groups)
    print(size_distro)


if __name__ == "__main__":
    parser = CmdParser()
    args = parser.parse_args(sys.argv[1:])
    subset_documents(root_folder=args.folder[0], subsets=args.subsets[0], endings=args.endings,
                     random_seed=args.random_seed, group_endings=args.group_by_ending,
                     suppress_empty=args.suppress_empty)
