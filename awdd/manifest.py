from uuid import UUID
from typing import *
from abc import ABC, abstractmethod
from enum import IntEnum
import os
import io
from datetime import time, datetime
from pathlib import Path

from . import *
from .object import *

ROOT_MANIFEST_PATH = '/System/Library/PrivateFrameworks/WirelessDiagnostics.framework/Support/AWDMetadata.bin'
EXTENSION_MANIFEST_PATH = '/System/Library/AWD/Metadata/*.bin'


ROOT_OBJECT_TAG = 0x00


class ManifestRegionType(IntEnum):
    structure = 0x02    # Compact representation of the metadata
    display = 0x03      # Metadata intended for display
    identity = 0x04     # The UUID and source file which the file was generated from
    root = 0x05         # Properties on the root object definition
    extensions = 0x06   # Extended values for the root metrics object


class ManifestError(Exception):
    pass


class ManifestRegion(ABC):
    def __init__(self, manifest: 'Manifest', data: BinaryIO, kind: ManifestRegionType, offset: int, size: int):
        self.manifest = manifest
        self.kind = kind
        self.offset = offset
        self.size = size
        self.data = data

    def read_all(self) -> bytes:
        self.data.seek(self.offset, os.SEEK_SET)
        return self.data.read(self.size)


class ManifestProperty:
    index: int
    name: Optional[str]
    type: PropertyType
    flags: PropertyFlags
    version: int
    integer_format: Optional[IntegerFormat]
    string_format: Optional[StringFormat]
    object_reference: Optional[int]
    list_item_type: Optional[int]
    extension: bool
    target: Optional[int]
    content: Optional[bytes]

    TAG_INDEX = 0x01
    TAG_TYPE = 0x02
    TAG_FLAGS = 0x03
    TAG_NAME = 0x04
    TAG_OBJECT_REFERENCE = 0x05
    TAG_STRING_FORMAT = 0x06
    TAG_LIST_ITEM_TYPE = 0x07
    TAG_ENUM_INDEX = 0x08
    TAG_INTEGER_FORMAT = 0x09
    TAG_EXTENSION = 0x0A
    TAG_EXTENSION_TARGET = 0x0B

    SCALAR_INT_TAGS = [ TAG_INDEX, TAG_ENUM_INDEX, TAG_EXTENSION_TARGET, TAG_OBJECT_REFERENCE, TAG_LIST_ITEM_TYPE ]
    PROPERTY_MAP = {
        TAG_INDEX: 'index',
        TAG_NAME: 'name',
        TAG_OBJECT_REFERENCE: 'object_reference',
        TAG_LIST_ITEM_TYPE: 'list_item_type',
        TAG_ENUM_INDEX: 'enum',
        TAG_EXTENSION_TARGET: 'target'
    }

    def __str__(self):
        name = "anonymous" if self.name is None else self.name
        return f"<PropertyDefinition {name} type:{self.type} index:{hex(self.index)} flags:{self.flags}>"

    def __init__(self, parent):
        self.type = PropertyType.UNKNOWN
        self.name = None
        self.type_name = None
        self.parent = parent
        self.extension = False
        self.index = 0x00
        self.integer_format = None
        self.string_format = None
        self.flags = PropertyFlags.NONE
        self.content = None

    def parse(self, content: bytes):
        self.content = content
        reader = io.BytesIO(content)
        while tag := decode_tag(reader):
            if tag.index in ManifestProperty.SCALAR_INT_TAGS:
                self.__setattr__(ManifestProperty.PROPERTY_MAP[tag.index], tag.value)

            elif tag.index == ManifestProperty.TAG_TYPE:
                if tag.tag_type & TagType.LENGTH_PREFIX:
                    type_extended = io.BytesIO(tag.value)
                    while extend_tag := decode_tag(type_extended):
                        if extend_tag.index == 0x01:
                            self.type_name = extend_tag.value
                        else:
                            self.type = PropertyType(extend_tag.value)
                else:
                    self.type = PropertyType(tag.value)

            elif tag.index == ManifestProperty.TAG_FLAGS:
                self.flags = PropertyFlags(tag.value)

            elif tag.index == ManifestProperty.TAG_INTEGER_FORMAT:
                try:
                    self.integer_format = IntegerFormat(tag.value)
                except ValueError as ex:
                    print(f"Unable to set integer format on {self.name} to {hex(value)}", ex)

            elif tag == ManifestProperty.TAG_STRING_FORMAT:
                value, _ = decode_variable_length_int(reader)
                self.string_format = StringFormat(value)

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

        self.flags = PropertyFlags(self.flags)

        try:
            self.type = PropertyType(self.type)
        except ValueError:
            print(f"Unable to set type for property {self.name if self.name is not None else 'anonymous'} for class {self.parent.name} to type {hex(self.type)}")


class ManifestDefinition(ABC):
    index: int

    def __init__(self, index: int):
        self.index = index

    @abstractmethod
    def parse(self, data: bytes):
        pass


class ManifestEnumMember:
    name: str
    value: int

    TAG_NAME = 0x01
    TAG_VALUE_INT = 0x02
    TAG_VALUE_SIGNED = 0x03

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

                # TODO: this is a special INT case - seems to be twos complement of length
                # encoded integer, value seen was '\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01'
                # implying signed int64

                self.value = value

            else:
                raise ManifestError(f"Unknown tag type in EnumMember definition {hex(tag)}")

        assert(remaining_bytes == 0)

    def __str__(self):
        return f"<ManifestEnumMember {self.name} = {hex(self.value)}>"


class ManifestEnumDefinition(ManifestDefinition):
    entries: List[ManifestEnumMember]
    name: Optional[str]
    content: Optional[bytes]
    extend: int

    TAG_NAME = 0x01
    TAG_ENUM_MEMBER = 0x02
    TAG_ENUM_MEMBER_NAME = 0x1E

    def __init__(self, index: int):
        super().__init__(index)
        self.entries = []
        self.name = None
        self.content = None

    def __str__(self):
        return f"<ManifestEnumDefinition {self.name} value_count:{len(self.entries)}>"

    def parse(self, data: bytes):
        self.content = data
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
    content: Optional[bytes]
    name: str
    properties: List[ManifestProperty]

    TAG_NAME = 0x01
    TAG_PROPERTY_DEFINITION = 0x02
    TAG_EXTEND = 0x0A

    def __init__(self, index: int):
        super().__init__(index)

        self.name = '__anonymous__'
        self.properties = []
        self.content = None

    def __str__(self):
        if self.name is not None:
            return f"<ManifestObject name:{self.name} property_count:{len(self.properties)}>"
        else:
            return f"<ManifestObject __anonymous__ property_count:{len(self.properties)}>"

    def parse(self, content: bytes):
        reader = io.BytesIO(content)

        while tag := decode_tag(reader):
            if tag.index == ManifestObjectDefinition.TAG_PROPERTY_DEFINITION:
                prop = ManifestProperty(self)
                prop.parse(tag.value)
                self.properties.append(prop)

            elif tag.index == ManifestObjectDefinition.TAG_NAME:
                self.name = tag.value

            else:
                raise ManifestError(f"Unknown tag {hex(tag)} in object {self.name}")


class ManifestTable(ManifestRegion):
    DEFINE_OBJECT_TAG = 0x01
    DEFINE_ENUM_TAG = 0x02
    SINGLE_BYTE_TAG_STRUCT = b'B'

    objects: List[ManifestDefinition]
    enums: List[ManifestEnumDefinition]
    is_root: bool

    def __init__(self, manifest: 'Manifest', data: BinaryIO, kind: ManifestRegionType, tag: int, offset: int, size: int, checksum: int):
        super().__init__(manifest, data, kind, offset, size)
        self.tag = tag
        self.checksum = checksum
        self.rows = []

    def __str__(self):
        return f"<ManifestTable tag:{hex(self.tag)} definitions:{len(self.rows)}>"

    def parse(self):
        self.data.seek(self.offset, io.SEEK_SET)

        remaining_bytes = self.size

        while remaining_bytes > 0:
            tag = None

            try:
                tag, tag_bytes = decode_variable_length_int(self.data)
                remaining_bytes -= tag_bytes

            except Exception as ex:
                offset = self.data.seek(0, io.SEEK_CUR)
                raise ManifestError(f"Unable to read tag at offset {offset}", ex)

            if tag == ManifestTable.DEFINE_OBJECT_TAG or tag == ManifestTable.DEFINE_ENUM_TAG:
                length, length_bytes = decode_variable_length_int(self.data)
                remaining_bytes -= length_bytes

                parsed_result = None
                if tag == ManifestTable.DEFINE_OBJECT_TAG:
                    parsed_result = ManifestObjectDefinition(tag)
                elif tag == ManifestTable.DEFINE_ENUM_TAG:
                    parsed_result = ManifestEnumDefinition(tag)

                parsed_result.parse(self.data.read(length))
                self.rows.append(parsed_result)

                remaining_bytes -= length

            else:
                raise ManifestError(f"Unknown tag type at root {tag}")

        assert(remaining_bytes == 0)


class ManifestIdentity(ManifestRegion):
    TAG_HASH = 0x01
    TAG_NAME = 0x02
    TAG_TIMESTAMP = 0x03

    hash: bytes  # SHA1 Hash
    name: str
    timestamp: datetime

    def __init__(self, manifest: 'Manifest', data: BinaryIO, kind: ManifestRegionType, offset: int, size: int):
        super().__init__(manifest, data, kind, offset, size)

    def parse(self):
        reader = io.BytesIO(self.read_all())
        while (tag := decode_tag(reader)) is not None:
            if tag.index == ManifestIdentity.TAG_HASH:
                self.hash = bytes.fromhex(tag.value.decode('ascii'))
            elif tag.index == ManifestIdentity.TAG_NAME:
                self.name = tag.value.decode('utf-8')
            elif tag.index == ManifestIdentity.TAG_TIMESTAMP:
                self.timestamp = apple_time_to_datetime(tag.value)
            else:
                raise ManifestError(f'Tag index {tag.index} not known in the context of a manifest identity')


class Manifest:
    MANIFEST_MAGIC = b'AWDM'
    HEADER_STRUCT = b'4sHH'
    HEADER_SECTION_COUNT = b'I'
    HEADER_SECTION_AND_COUNT = b'HH'
    HEADER_TABLE_STRUCT = b'IIII'
    HEADER_FOOTER_STRUCT = b'II'

    TABLE_TAGS = [ManifestRegionType.structure, ManifestRegionType.display]

    structure_tables: Dict[int, ManifestTable]
    display_tables: Dict[int, ManifestTable]
    identity: ManifestIdentity
    root: Optional[ManifestObjectDefinition]
    root_region: Optional[ManifestRegion]
    extensions: Optional[Dict[str, int]]
    extension_region: Optional[ManifestRegion]
    file: BinaryIO

    def __str__(self):
        return f"<Manifest path:{self.path} tag_count:{len(self.tags)}>"

    def __init__(self, path: str):
        self.is_root = False
        self.structure_tables = {}
        self.display_tables = {}
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

        if sections == 0:
            self.is_root = True

        while self._parse_manifest_header() is not False:
            pass

        if self.identity:
            self.identity.parse()

        if self.root_region:
            self.root = ManifestObjectDefinition(0)
            self.root.parse(self.root_region.read_all())

        if self.extension_region:
            self._parse_extension_points()

        # Meh, we could have checked the number of sections but both root and non root end with 0x00000000

    # If we get a tag of 0 return false so that we know to stop a root manifest parse
    def _parse_manifest_header(self) -> bool:
        tag_bytes = self.file.read(struct.calcsize(Manifest.HEADER_SECTION_AND_COUNT))
        if not tag_bytes or len(tag_bytes) != struct.calcsize(Manifest.HEADER_SECTION_AND_COUNT):
            return False

        header_tag, field_count = struct.unpack(Manifest.HEADER_SECTION_AND_COUNT, tag_bytes)

        if header_tag is 0 and field_count is 0:
            return False

        parsed_tag = ManifestRegionType(header_tag)

        if parsed_tag in Manifest.TABLE_TAGS:
            tag, offset, size, checksum = struct.unpack(Manifest.HEADER_TABLE_STRUCT,
                                                        self.file.read(struct.calcsize(Manifest.HEADER_TABLE_STRUCT)))

            table = ManifestTable(self, self.file, parsed_tag, tag, offset, size, checksum)

            if table.kind == ManifestRegionType.structure:
                self.structure_tables[tag] = table
            elif table.kind == ManifestRegionType.display:
                self.display_tables[tag] = table
            else:
                raise ManifestError("Table is not structure nor display??")

            return True

        else:
            offset, size = struct.unpack(Manifest.HEADER_FOOTER_STRUCT,
                                         self.file.read(struct.calcsize(Manifest.HEADER_FOOTER_STRUCT)))

            if parsed_tag == ManifestRegionType.identity:
                self.identity = ManifestIdentity(self, self.file, parsed_tag, offset, size)
            elif parsed_tag == ManifestRegionType.root:
                self.root_region = ManifestRegion(self, self.file, parsed_tag, offset, size)
            elif parsed_tag == ManifestRegionType.extensions:
                self.extension_region = ManifestRegion(self, self.file, parsed_tag, offset, size)

            return True

    def _parse_extension_points(self):
        if not self.extension_region:
            return

        self.extensions = {}

        extension_data = self.extension_region.read_all()
        extension_stream = io.BytesIO(extension_data)
        while extension_point := decode_tag(extension_stream):
            assert(extension_point.index == 1)  # Only known type in this region is EXTEND_POINT
            extend_stream = io.BytesIO(extension_point.value)

            name = ''
            while extend_value := decode_tag(extend_stream):
                if extend_value.index == 1:  # Name value
                    name = extend_value.value
                elif extend_value.index == 2:
                    self.extensions[name] = extend_value.value


    @property
    def tags(self):
        return set(self.structure_tables.keys()).union(self.display_tables.keys())

    @property
    def tag(self) -> Optional[int]:
        if self.is_root:
            return None
        else:
            return set(self.structure_tables.keys()).union(self.display_tables).pop()

