import abc
import io
import os
from pathlib import *
import struct
from typing import *
from awdd import *
from enum import Enum


class ManifestError(Exception):
    pass


class ManifestFooter:
    def __init__(self, offset: int, size: int):
        self.offset = offset
        self.size = size


class IntegerFormat(Enum):
    TIMESTAMP = 0x01


class StringFormat(Enum):
    UNKNOWN = 0x00


class PropertyType(Enum):
    DOUBLE = 0x01
    FLOAT = 0x02
    INTEGER_64 = 0x03
    INTEGER = 0x04
    INTEGER_32 = 0x06
    INTEGER_UNSIGNED = 0x07
    BOOLEAN = 0x0C
    ENUM = 0x0B
    STRING_UNICODE = 0x0D
    STRING_ASCII = 0x0E
    PACKED_UINT_32 = 0x15
    OBJECT = 0x1B


class ManifestProperty:
    index: int
    name: Union[str, None]
    type: PropertyType
    flags: int
    version: int
    integer_format: Union[None, IntegerFormat]
    string_format: Union[None, StringFormat]
    object_reference: Union[None, int]
    list_item_type: Union[None, int]
    extension: bool
    target: Union[None, int]


    TAG_INDEX = 0x08
    TAG_TYPE = 0x10
    TAG_FLAGS = 0x18
    TAG_NAME = 0x22
    TAG_OBJECT_REFERENCE = 0x28
    TAG_STRING_FORMAT = 0x30
    TAG_LIST_ITEM_TYPE = 0x38
    TAG_ENUM_INDEX = 0x40
    TAG_INTEGER_FORMAT = 0x48
    TAG_EXTENSION = 0x50
    TAG_EXTENSION_TARGET = 0x60

    SCALAR_INT_TAGS = [ TAG_INDEX, TAG_TYPE, TAG_ENUM_INDEX, TAG_EXTENSION_TARGET, TAG_FLAGS, TAG_STRING_FORMAT, TAG_INTEGER_FORMAT, TAG_OBJECT_REFERENCE, TAG_LIST_ITEM_TYPE ]
    PROPERTY_MAP = {
        TAG_INDEX: 'index',
        TAG_TYPE: 'type',
        TAG_NAME: 'name',
        TAG_FLAGS: 'flags',
        TAG_STRING_FORMAT: 'string_format',
        TAG_INTEGER_FORMAT: 'integer_format',
        TAG_OBJECT_REFERENCE: 'object_reference',
        TAG_LIST_ITEM_TYPE: 'list_item_type',
        TAG_ENUM_INDEX: 'enum',
        TAG_EXTENSION_TARGET: 'target'
    }

    def __str__(self):
        return f"<PropertyDefinition parent:{self.parent.name} name:{self.name} type:{self.type} index:{hex(self.index)} flags:{hex(self.flags)}>"

    def __init__(self, parent, content: bytes):
        self.name = None
        self.content = content
        self.parent = parent
        self.extension = False

        reader = io.BytesIO(content)
        while reader.seek(0, io.SEEK_CUR) < len(content):
            tag, tag_length = decode_variable_length_int(reader)

            if tag in ManifestProperty.SCALAR_INT_TAGS:
                value, _ = decode_variable_length_int(reader)

                self.__setattr__(ManifestProperty.PROPERTY_MAP[tag], value)

            elif tag == ManifestProperty.TAG_NAME:
                length, _ = decode_variable_length_int(reader)
                self.name = reader.read(length).decode('utf-8')

            elif tag == ManifestProperty.TAG_EXTENSION:
                extend, _ = decode_variable_length_int(reader)
                self.extension = False if extend == 0 else True

            else:
                # A bit dicey - but we assume that this tag has some value after, which is likely
                # either a primitive int, or is a length to a complex type
                value, _ = decode_variable_length_int(reader)
                print(f"Unknown tag in property definition for {self.parent.name} ({hex(tag)}, value: {value})")

        try:
            self.type = PropertyType(self.type)
        except ValueError:
            print(f"Unable to set type for property {self.name if self.name is not None else 'anonymous'} for class {self.parent.name} to type {hex(self.type)}")


class ManifestDefinition(abc.ABC):
    tag: int

    def __init__(self, tag: int):
        self.tag = tag

    @abc.abstractmethod
    def parse(self, data: bytes):
        pass


class ManifestEnumMember:
    name: str
    value: int

    TAG_NAME = 0x0A
    TAG_VALUE_INT = 0x10
    TAG_VALUE_SIGNED = 0x18

    def __init__(self, data: bytes):
        self.data = data
        remaining_bytes = len(data)
        reader = io.BytesIO(data)

        while remaining_bytes > 0:
            tag, tag_length = decode_variable_length_int(reader)
            remaining_bytes -= tag_length

            if tag == ManifestEnumMember.TAG_NAME:
                length, size_length = decode_variable_length_int(reader)
                remaining_bytes -= size_length

                self.name = reader.read(length).decode('utf-8')
                remaining_bytes -= length

            elif tag == ManifestEnumMember.TAG_VALUE_INT:
                value, size_value = decode_variable_length_int(reader)
                remaining_bytes -= size_value

                self.value = value

            elif tag == ManifestEnumMember.TAG_VALUE_SIGNED:
                value, size_value = decode_variable_length_int(reader)
                remaining_bytes -= size_value

                # TODO: this is a speical INT case - seems to be twos complement of length
                # encoded interger, value seen was '\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01'
                # implying signed int64

                self.value = value

            else:
                raise ManifestError(f"Unknown tag type in EnumMember definition {hex(tag)}")

        assert(remaining_bytes == 0)

    def __str__(self):
        return f"<ManifestEnumMember {self.name} = {hex(self.value)}>"


class ManifestEnumDefinition(ManifestDefinition):
    entries: List[ManifestEnumMember]
    name: Union[str, None]

    TAG_NAME = 0x0A
    TAG_ENUM_MEMBER = 0x12
    TAG_ENUM_MEMBER_NAME = 0x1E

    def __init__(self, tag: int):
        super().__init__(tag)
        self.entries = []
        self.name = None

    def __str__(self):
        return f"<ManifestEnumDefinition {self.name} value_count:{len(self.entries)}>"

    def parse(self, data: bytes):
        remaining_bytes = len(data)
        reader = io.BytesIO(data)

        while remaining_bytes > 0:
            tag, tag_length = decode_variable_length_int(reader)
            remaining_bytes -= tag_length

            if tag == ManifestEnumDefinition.TAG_NAME:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                self.name = reader.read(length).decode('utf-8')
                remaining_bytes -= length

            elif tag == ManifestEnumDefinition.TAG_ENUM_MEMBER:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                member = ManifestEnumMember(reader.read(length))
                self.entries.append(member)

                remaining_bytes -= length



class ManifestObjectDefinition(ManifestDefinition):
    TAG_EVENT_NAME = 0x0A
    TAG_PROPERTY_DEFINITION = 0x12
    TAG_CLASS_NAME = 0x16

    def __init__(self, tag: int):
        super().__init__(tag)

        self.class_name = None
        self.event_name = None
        self.properties = []

    def __str__(self):
        if self.class_name is not None:
            return f"<ManifestObject class_name:{self.class_name} property_count:{len(self.properties)}>"
        elif self.event_name is not None:
            return f"<ManifestObject event_name:{self.event_name} property_count:{len(self.properties)}>"
        else:
            return f"<ManifestObject anonymous property_count:{len(self.properties)}>"

    def parse(self, content: bytes):
        remaining_bytes = len(content)
        reader = io.BytesIO(content)

        while remaining_bytes > 0:
            tag, tag_length = decode_variable_length_int(reader)
            remaining_bytes -= tag_length

            if tag == ManifestObjectDefinition.TAG_PROPERTY_DEFINITION:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                self.properties.append(ManifestProperty(self, reader.read(length)))
                remaining_bytes -= length

            elif tag == ManifestObjectDefinition.TAG_CLASS_NAME or tag == ManifestObjectDefinition.TAG_EVENT_NAME:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                if tag == ManifestObjectDefinition.TAG_CLASS_NAME:
                    self.class_name = reader.read(length).decode('utf-8')

                elif tag == ManifestObjectDefinition.TAG_EVENT_NAME:
                    self.event_name = reader.read(length).decode('utf-8')

                remaining_bytes -= length

            else:
                raise ManifestError(f"Unknown tag {hex(tag)} in object {self.name}")

    @property
    def name(self):
        if self.class_name is not None:
            return self.class_name

        if self.event_name is not None:
            return self.event_name

        return "anonymous"


class ManifestTable:
    DEFINE_OBJECT_TAG = 0x0A
    DEFINE_ENUM_FLAG = 0x12
    SINGLE_BYTE_TAG_STRUCT = b'B'

    rows: List[ManifestDefinition]

    def __init__(self, tag: int, offset: int, size: int, checksum: int):
        self.tag = tag
        self.offset = offset
        self.size = size
        self.checksum = checksum
        self.rows = []

    def parse(self, reader: BinaryIO):
        reader.seek(self.offset, io.SEEK_SET)

        remaining_bytes = self.size

        while remaining_bytes > 0:
            tag = None

            try:
                tag, tag_bytes = decode_variable_length_int(reader)
                remaining_bytes -= tag_bytes

            except Exception as ex:
                offset = reader.seek(0, io.SEEK_CUR)
                raise ManifestError(f"Unable to read tag at offset {offset}", ex)

            if tag == ManifestTable.DEFINE_OBJECT_TAG or tag == ManifestTable.DEFINE_ENUM_FLAG:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                parsed_result = None
                if tag == ManifestTable.DEFINE_OBJECT_TAG:
                    parsed_result = ManifestObjectDefinition(tag)
                elif tag == ManifestTable.DEFINE_ENUM_FLAG:
                    parsed_result = ManifestEnumDefinition(tag)

                parsed_result.parse(reader.read(length))
                self.rows.append(parsed_result)

                remaining_bytes -= length

            else:
                raise ManifestError(f"Unknown tag type at root {tag}")

        assert(remaining_bytes == 0)


class Manifest:
    MANIFEST_MAGIC = b'AWDM'
    HEADER_STRUCT = b'4sHH'
    HEADER_SECTION_COUNT = b'I'
    HEADER_SECTION_AND_COUNT = b'HH'
    HEADER_TABLE_STRUCT = b'IIII'
    HEADER_FOOTER_STRUCT = b'II'

    TAG_COMPACT_TABLE = 0x02
    TAG_DISPLAY_TABLE = 0x03
    TAG_FOOTER = 0x04

    tables: Dict[int, ManifestTable]
    file: BinaryIO

    def __init__(self, path: str):
        self.path = Path(path)
        if self.path.exists() is False:
            raise ManifestError("Path does not exist")

        self.file = open(self.path.absolute(), "rb")
        magic, self.major, self.minor = struct.unpack(Manifest.HEADER_STRUCT,
                                                      self.file.read(struct.calcsize(Manifest.HEADER_STRUCT)))

        if magic != Manifest.MANIFEST_MAGIC:
            raise ManifestError(f"Incorrect MAGIC (got {magic})")

        if self.major != 1 or self.minor != 1:
            raise ManifestError(f"Unsupported version (got {self.major}.{self.minor})")

        sections, *_ = struct.unpack(Manifest.HEADER_SECTION_COUNT,
                                     self.file.read(struct.calcsize(Manifest.HEADER_SECTION_COUNT)))

        self.tables: Dict[int, ManifestTable] = {}

        for _ in range(sections):
            header_id, count = struct.unpack(Manifest.HEADER_SECTION_AND_COUNT,
                                             self.file.read(struct.calcsize(Manifest.HEADER_SECTION_AND_COUNT)))

            if header_id in [ Manifest.TAG_COMPACT_TABLE, Manifest.TAG_DISPLAY_TABLE]:
                assert(count == 0x04)
                tag, offset, size, checksum = \
                    struct.unpack(Manifest.HEADER_TABLE_STRUCT,
                                  self.file.read(struct.calcsize(Manifest.HEADER_TABLE_STRUCT)))

                self.tables[header_id] = ManifestTable(tag, offset, size, checksum)
            elif header_id == Manifest.TAG_FOOTER:
                assert(count == 0x02)
                offset, size = struct.unpack(Manifest.HEADER_FOOTER_STRUCT,
                                             self.file.read(struct.calcsize(Manifest.HEADER_FOOTER_STRUCT)))

                self.footer = ManifestFooter(offset, size)
            else:
                raise ManifestError(f"Unsupported header tag of {header_id}")

    def parse(self):
        for table_id in self.tables:
            try:
                self.tables[table_id].parse(self.file)
            except ManifestError as ex:
                raise ManifestError(f"Unable to parse table {table_id} in file {self.path.absolute()}", ex)