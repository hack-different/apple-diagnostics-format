from . import for_each_log_file
from awdd import decode_tag
import os


def test_parse_tags_and_type():
    def print_each_tag(filename, stream):
        while tag := decode_tag(stream):
            print(tag)

    for_each_log_file(print_each_tag)
