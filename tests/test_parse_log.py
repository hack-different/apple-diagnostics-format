import io

import pytest
import os
from glob import glob
from awdd.parser import LogParser


def test_parse_manifests():
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.dirname(path_to_current_file)
    awdd_fixture = os.path.join(current_directory, "../rosetta/awdd.bin")

    parser = LogParser()

    # Parse a fixture piece of data
    result = parser.parse(awdd_fixture)

    output_buffer = io.StringIO()
    parser.output_text(output_buffer)

    print(output_buffer.getvalue())