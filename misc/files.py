# -*- coding: utf-8 -*-
from collections import defaultdict
from typing import List, Dict, Union

import sys
import os
import glob
import shutil
import random
import argparse
import logging
import numpy as np

OUT_SUBSET_FOLDER = "subsets"
UNGROUPED_STR = "ungrouped"
NO_ENDING_TYPE = "none"


class CmdParser(argparse.ArgumentParser):

    def __init__(self):
        super().__init__()

        self.add_argument('input_folder', action='store', nargs=1, type=os.path.abspath,
                          help="The folder where all documents are located.")
        self.add_argument('subsets', action='store', nargs=1, type=int,
                          help="On how many subsets all documents should be split up.")
        self.add_argument('-o', '--output_folder', action='store', nargs='*', type=os.path.abspath, default=[None],
                          help="The root where the subset documents are stored. (default: 'input-folder/{}')"
                          .format(OUT_SUBSET_FOLDER))
        self.add_argument('-e', '--extensions', action='store', nargs='*', type=str, default='*',
                          help="What document types should be included (file extensions). (default: '*'"
                               " - i.e. all files with an extension)")
        self.add_argument('-r', '--random_seed', action='store', nargs='*', type=int, default=42,
                          help="Random seed for shuffling and splitting the subsets. (default: 42)")
        self.add_argument('-n', '--group_names', action='store', nargs='*', type=str,
                          help="Space separated list of names for each subset."
                               " If unused, subsets will be named with numbers.")
        self.add_argument('-m', '--max_per_subset', action='store', nargs='*', type=int,
                          help="Gives the maximum number of files for each subset. If one integer, this counts for all"
                               " subsets. But you can also give a space separated list of integers to specify the"
                               " maximum for each individual subset. (default: all)")
        self.add_argument('-c', '--include_extensionless', action='store_true',
                          help="Whether files without extension shall be included from source folder."
                               " (This is a flag and only evaluates to True if present.)")
        self.add_argument('-d', '--folders_for_ext', action='store_true',
                          help="Whether sub-folders for each extension shall be created under each subset folder."
                               " (This is a flag and only evaluates to True if present.)")
        self.add_argument('-g', '--group_by_extension', action='store_true',
                          help="Whether files shall be grouped by their extension, so that each file extension is"
                               " regarded separately when 'subsets' is evaluated."
                               " (This is a flag and only evaluates to True if present.)")
        self.add_argument('-x', '--dont_suppress_empty', action='store_true',
                          help="Whether groups that are empty (because there were fewer documents than subsets)"
                               " shouldn't be suppressed."
                               " (This is a flag and only evaluates to True if present.)")
        self.add_argument('-s', '--same_for_all', action='store_true',
                          help="Whether all subsets should contain the same files."
                               " (This is a flag and only evaluates to True if present.)")


def _gather_into_groups(file_index: Dict[int, str], group_count: int, suppress_empty: bool = True,
                        max_per_subset: List[int] = None, same_for_all: bool = False):
    if max_per_subset is not None:
        if len(max_per_subset) == 1:
            logging.info("Using max count of {} of files for each subset.".format(max_per_subset[0]))
            max_per_subset = [max_per_subset[0] for x in range(group_count)]
        elif len(max_per_subset) != group_count:
            logging.error("Number of subsets is given as {}, but arguments for '--max_per_subset' contain {}"
                          " values ([{}]).\nPlease align the number of the latter with the number of the former."
                          .format(group_count, len(max_per_subset), ", ".join([str(s) for s in max_per_subset])))
            sys.exit(-1)

    np_file_array = np.array(list(file_index.keys()))
    np.random.shuffle(np_file_array)

    if same_for_all:
        files = list()
        for i in range(group_count):
            files.append(
                np_file_array.tolist()[:max_per_subset[i] if max_per_subset is not None else np_file_array.size])
        return files
    if suppress_empty:
        return [x.tolist()[:max_per_subset[i] if max_per_subset is not None else x.size]
                for i, x in enumerate(np.array_split(np_file_array, group_count)) if len(x) != 0]
    return [x.tolist()[:max_per_subset[i] if max_per_subset is not None else x.size]
            for i, x in enumerate(np.array_split(np_file_array, group_count))]


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


def _distribute_files(groups: Dict[str, List[List[int]]], group_names: List[str], file_index: Dict[int, str],
                      root_out: str, folders_for_extensions: bool = False):
    file_dist = defaultdict(set)
    for ext_name, group in groups.items():
        random.shuffle(group_names)
        for x in zip(group_names, group):
            if ext_name == UNGROUPED_STR or not folders_for_extensions:
                file_dist[os.path.join(x[0])].update(x[1])
            else:
                file_dist[os.path.join(x[0], ext_name)].update(x[1])
    for _path, _files in file_dist.items():
        _path_complete = os.path.join(root_out, _path)
        if not os.path.exists(_path_complete):
            os.makedirs(_path_complete)
        for _fi in _files:
            shutil.copy(file_index[_fi], _path_complete)


def _check_group_names(group_names: Union[None, List[str]], subsets: int):
    if group_names is not None:
        if len(group_names) != subsets:
            logging.error("Number of subsets is given as {}, but {} group names are declared (i.e. [{}]).\n"
                          "Either omit '--group_names' argument or give the same amount of names as subsets."
                          .format(subsets, len(group_names), ",".join(group_names)))
            sys.exit(-1)
    else:
        group_names = [str(n) for n in range(subsets)]
    return group_names


def subset_documents(root_folder: str, out_folder: str, subsets: int, extensions: List[str], random_seed: int,
                     group_extensions: bool = False, suppress_empty: bool = True, include_extensionless: bool = False,
                     group_names: List[str] = None, folders_for_extensions: bool = False, same_for_all: bool = False,
                     max_per_subset: List[int] = None):
    group_names = _check_group_names(group_names=group_names, subsets=subsets)
    files = set()
    file_types = set(extensions)
    for ending in extensions:  # ToDo: strip potential dot from input
        fi_pattern = os.path.join(root_folder, "*.{}".format(ending))
        files.update(glob.glob(fi_pattern))
    if len(extensions) == 1 and extensions[0] == "*":
        file_types = set([os.path.splitext(e)[-1][1:] for e in files])
    if include_extensionless:
        extensionless = [f for f in glob.glob(os.path.join(root_folder, "*"))
                         if len(os.path.splitext(os.path.split(f)[-1])[-1]) == 0 and os.path.isfile(f)]
        files.update(extensionless)
        file_types.update([NO_ENDING_TYPE])

    file_index = {i: f for i, f in enumerate(files) if os.path.isfile(f)}
    rev_file_index = {f: i for i, f in file_index.items()}

    np.random.seed(random_seed)
    if group_extensions:
        endings_file_index = defaultdict(dict)
        for i, file in file_index.items():
            end = os.path.splitext(file)[-1]
            endings_file_index[end[1:] if len(end) != 0 else NO_ENDING_TYPE][i] = file
        groups = {group_name: _gather_into_groups(file_index=endings_file_index[group_name], group_count=subsets,
                                                  suppress_empty=suppress_empty, max_per_subset=max_per_subset,
                                                  same_for_all=same_for_all)
                  for group_name in file_types}
    else:
        groups = {UNGROUPED_STR: _gather_into_groups(file_index=file_index, group_count=subsets,
                                                     suppress_empty=suppress_empty, max_per_subset=max_per_subset,
                                                     same_for_all=same_for_all)}

    size_distro = _file_size_distribution(groups=groups, file_index=file_index)
    output_folder = _get_output_folder(root_folder=root_folder, out_folder=out_folder)

    random.seed(random_seed)
    _distribute_files(groups=groups, group_names=group_names, file_index=file_index, root_out=output_folder,
                      folders_for_extensions=folders_for_extensions)


def main(cmd_args: list):
    parser = CmdParser()
    if len(cmd_args) <= 1:
        parser.print_help()
        logging.error("Not enough arguments given; see help above.")
        sys.exit(-1)
    args = parser.parse_args(cmd_args[1:])
    subset_documents(root_folder=args.input_folder[0], out_folder=args.output_folder[0], subsets=args.subsets[0],
                     extensions=args.extensions, random_seed=args.random_seed, group_extensions=args.group_by_extension,
                     suppress_empty=not args.dont_suppress_empty, include_extensionless=args.include_extensionless,
                     group_names=args.group_names, folders_for_extensions=args.folders_for_ext,
                     max_per_subset=args.max_per_subset, same_for_all=args.same_for_all)


if __name__ == "__main__":
    main(sys.argv)
