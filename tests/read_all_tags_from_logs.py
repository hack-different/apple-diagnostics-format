import io
from . import for_each_log_file
from awdd import decode_tag


def test_parse_tags_and_type():
    def print_each_tag(filename, stream):
        while tag := decode_tag(stream):
            if tag.index == 15:  # metricsLog entry
                print("\n\nmetricsLog entry:\n")
                reader = io.BytesIO(tag.value)
                while metrics_tag := decode_tag(reader):
                    print(f"\t{metrics_tag}")
            else:
                print(tag)

    for_each_log_file(print_each_tag)
