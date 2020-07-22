# -*- coding: utf-8 -*-
from collections import defaultdict

from typing import List, Dict, Union
import numpy as np
import glob
import os
import sys
import argparse
import logging

OUT_SUBSET_FOLDER = "subsets"
UNGROUPED_STR = "ungrouped"
NO_ENDING_TYPE = "none"


class CmdParser(argparse.ArgumentParser):

    def __init__(self):
        super().__init__()

        self.add_argument('input_folder', action='store', nargs='+', type=os.path.abspath,
                          help="The folder where all documents are located")
        self.add_argument('subsets', action='store', nargs='+', type=int,
                          help="On how many subsets all documents should be split up")
        self.add_argument('-o', '--output_folder', action='store', nargs='*', type=os.path.abspath, default=[None],
                          help="The root where the subset documents are stored (defaults to 'input-folder/{}'"
                          .format(OUT_SUBSET_FOLDER))
        self.add_argument('-e', '--endings', action='store', nargs='*', type=str, default='*',
                          help="What document types should be included (file endings); default='*' (i.e. all)")
        self.add_argument('-r', '--random_seed', action='store', nargs='*', type=int, default=42,
                          help="Random seed for shuffling and splitting the subsets; default=42")
        self.add_argument('-g', '--group_by_ending', action='store_true',
                          help="Whether files shall be grouped by its ending, so that ech file ending is regarded"
                               "separately when 'count' is evaluated. This is a flag and evaluates to True if present.")
        self.add_argument('-s', '--dont_suppress_empty', action='store_true',
                          help="Whether groups that are empty (because there were fewer documents than subsets)"
                               "shouldn't be suppressed. This is a flag and evaluates to True if present.")
        self.add_argument('-c', '--include_endingless', action='store_true',
                          help="")


def _gather_into_groups(file_index: Dict[int, str], group_count: int, suppress_empty: bool = True):
    np_file_array = np.array(list(file_index.keys()))
    np.random.shuffle(np_file_array)

    if suppress_empty:
        return [x.tolist() for x in np.array_split(np_file_array, group_count) if len(x) != 0]
    return [x.tolist() for x in np.array_split(np_file_array, group_count)]


def _file_size_distribution(groups: Union[Dict[str, List[List[int]]], List[List[int]]], file_index: Dict[int, str],
                            ending: str = UNGROUPED_STR, return_dict: dict = {}):
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


def _get_output_folder(root_folder: str, out_folder: Union[None, str]):
    foo = out_folder
    if out_folder is None:
        foo = os.path.join(root_folder, OUT_SUBSET_FOLDER)
    os.makedirs(foo, exist_ok=True)
    return foo


def _distribute_files(groups, file_index):
    print(file_index)
    print(groups)


def subset_documents(root_folder: str, out_folder: str, subsets: int, endings: List[str], random_seed: int,
                     group_endings: bool = False, suppress_empty: bool = True, include_endingless: bool = False):
    files = set()
    file_types = set(endings)
    for ending in endings:
        fi_pattern = os.path.join(root_folder, "*.{}".format(ending))
        files.update(glob.glob(fi_pattern))
    if len(endings) == 1 and endings[0] == "*":
        file_types = set([os.path.splitext(e)[-1] for e in files])
    if include_endingless:
        endingless = [f for f in glob.glob(os.path.join(root_folder, "*"))
                      if len(os.path.splitext(os.path.split(f)[-1])[-1]) == 0 and os.path.isfile(f)]
        files.update(endingless)
        file_types.update([NO_ENDING_TYPE])

    file_index = {i: f for i, f in enumerate(files) if os.path.isfile(f)}
    rev_file_index = {f: i for i, f in file_index.items()}

    np.random.seed(random_seed)
    if group_endings:
        endings_file_index = defaultdict(dict)
        for i, file in file_index.items():
            end = os.path.splitext(file)[-1]
            endings_file_index[end if len(end) != 0 else NO_ENDING_TYPE][i] = file
        groups = {group_name: _gather_into_groups(endings_file_index[group_name], subsets, suppress_empty)
                  for group_name in file_types}
    else:
        groups = {UNGROUPED_STR: _gather_into_groups(file_index, subsets, suppress_empty)}

    size_distro = _file_size_distribution(groups, file_index)
    output_folder = _get_output_folder(root_folder, out_folder)

    _distribute_files(groups, file_index)


if __name__ == "__main__":
    parser = CmdParser()
    args = parser.parse_args(sys.argv[1:])
    subset_documents(root_folder=args.input_folder[0], out_folder=args.output_folder[0], subsets=args.subsets[0],
                     endings=args.endings, random_seed=args.random_seed, group_endings=args.group_by_ending,
                     suppress_empty=not args.dont_suppress_empty, include_endingless=args.include_endingless)
