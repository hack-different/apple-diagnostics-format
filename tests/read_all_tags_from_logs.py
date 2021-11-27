from glob import glob
from pathlib import *
from awdd import decode_tag
import os


def test_parse_tags_and_type():
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.dirname(path_to_current_file)
    log_fixtures = os.path.join(current_directory, "./fixtures/*.metriclog")

    for file in glob(log_fixtures):
        path = Path(file)
        print(f"Reading File: {path.name}\n")

        with open(file, "rb") as stream:
            while tag := decode_tag(stream):
                print(tag)