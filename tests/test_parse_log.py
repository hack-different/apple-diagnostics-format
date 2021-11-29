import io

import pytest
import os
from glob import glob
from awdd.metadata import *
from awdd.parser import LogParser
from tests import for_each_log_file


def test_resolve_manifests():
    metadata = Metadata()
    metadata.resolve()


def test_parse_logs():
    parser = LogParser()

    def print_each_log(filename, stream):
        print(f"Parsing Log: {filename}")
        output = io.StringIO()

        result = parser.parse(stream)
        print(result)

    for_each_log_file(print_each_log)
