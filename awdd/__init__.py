import io
import struct


def decode_variable_length_int(reader: io.BufferedReader) -> int:
    result = 0
    (byte) = struct.unpack(b'B', reader.read(1))

    while byte & 0b1000_0000 != 0:
        result <<= 7
        result |= (byte & 0b0111_1111)
        (byte) = struct.unpack(b'B', reader.read(1))

    result <<= 7
    result |= byte

    return result
