import subprocess
import sys
import os
import logging
import argparse
import glob

TOO_SMALL_ERROR_ANTIWORD = "I'm afraid the text stream of this file is too small to handle."
ANTIWORD_CMD = "antiword"
CATDOC_CMD = "catdoc"
EXTRACTION_FLAG = ""


class CmdParser(argparse.ArgumentParser):

    def __init__(self):
        super().__init__()
        self.add_argument('input', action='store', nargs=1, type=os.path.abspath,
                          help="A specific file or the folder where all documents are located.")
        self.add_argument('-a', '--antiword', action='store', nargs='?', type=str, default=ANTIWORD_CMD,
                          help="")
        self.add_argument('-c', '--catdoc', action='store', nargs='?', type=str, default=CATDOC_CMD,
                          help="")


def run_batch(files: list, args):
    for fi in files:
        result = run_text_extraction(args.antiword if EXTRACTION_FLAG == ANTIWORD_CMD else args.catdoc, fi)
        if TOO_SMALL_ERROR_ANTIWORD in result.stderr:
            logging.warning("'antiword' could not read the file, trying with 'catdoc'!")
            result = run_text_extraction(args.catdoc, fi)

        process_text(result.stdout)


def run_text_extraction(cmd: str, d_path: str):
    return subprocess.run([cmd, d_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)


def process_text(txt_string: str):
    print(txt_string)


def main(cmd_args: list):
    global EXTRACTION_FLAG
    parser = CmdParser()
    if len(cmd_args) <= 1:
        parser.print_help()
        logging.error("Not enough arguments given; see help above.")
        sys.exit(-1)
    args = parser.parse_args(cmd_args[1:])

    try:
        run_text_extraction(args.antiword, '')
        EXTRACTION_FLAG = ANTIWORD_CMD
    except FileNotFoundError:
        logging.warning("No 'antiword' found, switching to 'catdoc'!")
        EXTRACTION_FLAG = CATDOC_CMD

    d_path = os.path.abspath(args.input[0])
    if os.path.isfile(d_path):
        d_path = [d_path]
    else:
        d_path = glob.glob(os.path.join(d_path, "*.doc"))
    run_batch(d_path, args)


if __name__ == '__main__':
    main(sys.argv)
