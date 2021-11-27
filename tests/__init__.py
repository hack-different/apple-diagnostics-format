from typing import *
from glob import glob
from pathlib import *
import os


def for_each_log_file(function: Callable[[str, BinaryIO], None]) -> None:
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.dirname(path_to_current_file)
    log_fixtures = os.path.join(current_directory, "./fixtures/*.metriclog")

    for file in glob(log_fixtures):
        path = Path(file)
        print(f"\n\nReading File: {path.name}\n")

        with open(file, "rb") as stream:
            function(file, stream)
