import io

import pytest
import os
from glob import glob
from awdd.parser import LogParser


def test_parse_manifests():
    metadata_path = os.path.join(os.path.dirname(__file__), "../rosetta/awdd.bin")

    parser = LogParser(open(metadata_path, "rb"), use_default_manifests=True)

    output_buffer = io.StringIO()
    parser.output_text(output_buffer)

    print(output_buffer.getvalue())