import io
import struct
from typing import *

BYTE_PARSE_STRUCT = b'B'


def decode_variable_length_int(reader: io.IOBase) -> Optional[Tuple[int, int]]:
    def read_bytes() -> Generator[int, None, None]:
        data = reader.read(struct.calcsize(BYTE_PARSE_STRUCT))
        if data is None:
            return

        byte, *_ = struct.unpack(BYTE_PARSE_STRUCT, data)

        while byte & 0b1000_0000 != 0:
            yield byte & 0b0111_1111
            byte, *_ = struct.unpack(BYTE_PARSE_STRUCT, reader.read(struct.calcsize(BYTE_PARSE_STRUCT)))

        yield byte

    result = 0

    result_bytes = list(read_bytes())
    if len(result_bytes) == 0:
        return None

    for single_byte in reversed(result_bytes):
        result <<= 7
        result |= single_byte

    return result, len(result_bytes)
