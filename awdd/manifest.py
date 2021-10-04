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


class PropertyType(Enum):
    INTEGER = 0x04
    STRING = 0x0E
    METRICS = 0x1B

class ManifestProperty:
    index: int
    name: str
    type: PropertyType
    flags: int
    format: Union[None, int]

    TAG_INDEX = 0x08
    TAG_TYPE = 0x10
    TAG_FLAGS = 0x18
    TAG_NAME = 0x22

    SCALAR_INT_TAGS = [TAG_INDEX, TAG_TYPE, TAG_FLAGS]
    PROPERTY_MAP = {
        TAG_INDEX: 'index',
        TAG_TYPE: 'type',
        TAG_NAME: 'name',
        TAG_FLAGS: 'flags'
    }

    def __init__(self, parent, content: bytes):
        self.content = content
        self.parent = parent

        reader = io.BytesIO(content)
        while reader.seek(0, io.SEEK_CUR) < len(content):
            tag, tag_length = decode_variable_length_int(reader)

            if tag in ManifestProperty.SCALAR_INT_TAGS:
                value, _ = decode_variable_length_int(reader)

                self.__setattr__(ManifestProperty.PROPERTY_MAP[tag], value)

            elif tag == ManifestProperty.TAG_NAME:
                length, _ = decode_variable_length_int(reader)
                self.name = reader.read(length).decode('utf-8')

            else:
                print(f"Unknown tag in property definition for {self.parent.name} ({hex(tag)})")

        #if self.type not in PropertyType.__members__.values():
        #    raise ManifestError(f"Type {hex(self.type)} is not in the PropertyType enum")


class ManifestObject:
    TAG_EVENT_NAME = 0x0A
    TAG_PROPERTY_DEFINITION = 0x12
    TAG_CLASS_NAME = 0x16

    def __init__(self, tag: int):
        self.tag = tag
        self.class_name = None
        self.event_name = None
        self.properties = []
        self.children = []

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

            if tag == ManifestObject.TAG_PROPERTY_DEFINITION:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                self.properties.append(ManifestProperty(self, reader.read(length)))
                remaining_bytes -= length

            elif tag == ManifestObject.TAG_CLASS_NAME or tag == ManifestObject.TAG_EVENT_NAME:
                length, length_bytes = decode_variable_length_int(reader)
                remaining_bytes -= length_bytes

                if tag == ManifestObject.TAG_CLASS_NAME:
                    self.class_name = reader.read(length)
                elif tag == ManifestObject.TAG_EVENT_NAME:
                    self.event_name = reader.read(length)

                remaining_bytes -= length

            else:
                raise ManifestError(f"Unknown tag {tag} in object {self.name}")

    @property
    def name(self):
        if self.class_name is not None:
            return self.class_name

        if self.event_name is not None:
            return self.event_name

        return "anonymous"


class ManifestTable:
    TABLE_SEQUENCE_TAG = 0x0A
    TABLE_FLAGS_TAG = 0x18
    SINGLE_BYTE_TAG_STRUCT = b'B'

    rows: List[ManifestObject]

    def __init__(self, tag: int, offset: int, size: int, checksum: int):
        self.tag = tag
        self.offset = offset
        self.size = size
        self.checksum = checksum
        self.rows = []

    def parse(self, reader: io.BufferedReader):
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

            if tag == ManifestTable.TABLE_SEQUENCE_TAG or ManifestTable.TABLE_FLAGS_TAG:
                length, length_bytes = decode_variable_length_int(reader)

                remaining_bytes -= length_bytes
                parsed_object = ManifestObject(tag)
                parsed_object.parse(reader.read(length))
                self.rows.append(parsed_object)

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

    TAG_TABLE = 0x02
    TAG_DISPLAY_TABLE = 0x03
    TAG_FOOTER = 0x04

    tables: Dict[int, ManifestTable]
    file: io.BufferedReader

    def __init__(self, path: str):
        self.path = Path(path)
        if self.path.exists() is False:
            raise ManifestError("Path does not exist")

        self.file = io.BufferedReader(open(self.path.absolute(), "rb"))
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

            if header_id in [ Manifest.TAG_TABLE, Manifest.TAG_DISPLAY_TABLE]:
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