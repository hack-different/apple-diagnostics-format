import io
import struct
from typing import *
from enum import IntFlag
from datetime import datetime, time
from enum import *
from dataclasses import *


BYTE_PARSE_STRUCT = b'B'


class ManifestError(Exception):
    pass


def apple_time_to_datetime(epoch_milliseconds: int) -> datetime:
    unix_epoch = epoch_milliseconds / 1000
    micros = (epoch_milliseconds % 1000) * 1000
    base_date_time = datetime.utcfromtimestamp(unix_epoch)
    return datetime(base_date_time.year, base_date_time.month, base_date_time.day, hour=base_date_time.hour,
                    minute=base_date_time.minute, second=base_date_time.second, microsecond=micros,
                    tzinfo=base_date_time.tzinfo)


class TagType(IntFlag):
    NONE = 0b000
    # Guess: Size Fixed known from format, encapsulated C struct
    EXTENSION = 0b001
    LENGTH_PREFIX = 0b010
    REPEATED = 0b100


TEnum = TypeVar('T', int, IntEnum)


@dataclass(kw_only=True)
class Tag(Generic[TEnum]):
    index: TEnum
    tag_type: TagType
    length: int
    value: any


class VariableLengthInteger(NamedTuple):
    value: int
    size: int


def decode_variable_length_int(reader: Union[BinaryIO, io.BytesIO]) -> Optional[VariableLengthInteger]:
    def read_bytes() -> Generator[int, None, None]:
        data = reader.read(struct.calcsize(BYTE_PARSE_STRUCT))
        if data is None or len(data) == 0:
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

    return VariableLengthInteger(value=result, size=len(result_bytes))


"""
Reads in a single tag and it's associated data.  If the low order bits indicate that there is a length
prefix (as is in the case of strings and constructed object types).  For scalar primitives, the high order
bit of the value indicates if there are more bytes to be read.  Finally the remaining 7 bits are 7 to 8 bit
encoded as in email 7bit encoding (MIME)  
"""


def decode_tag(data: Union[io.IOBase, bytes], enum: Optional[Type] = int) -> Optional[Tag]:
    reader = io.BytesIO(data) if isinstance(data, bytes) else data

    result = decode_variable_length_int(reader)
    if result is None:
        return None

    encoded_tag, length = result

    type_bits = TagType(encoded_tag & 0b111)
    index_bits = encoded_tag >> 3

    if enum == int:
        index = index_bits
    else:
        index = enum(index_bits)

    if type_bits & TagType.LENGTH_PREFIX:
        string_length, length_length = decode_variable_length_int(reader)
        value = reader.read(string_length)
        return Tag(index=index, tag_type=type_bits, length=length + length_length + string_length,
                   value=value)

    else:
        value, value_length = decode_variable_length_int(reader)

        return Tag(index=index, tag_type=type_bits, length=length + value_length, value=value)


def decode_tags(data: Union[bytes, io.IOBase], enum: Optional[Type] = int) -> List[Tag]:
    reader = io.BytesIO(data) if isinstance(data, bytes) else data

    result = []
    while tag := decode_tag(reader, enum):
        result.append(tag)

    return result

