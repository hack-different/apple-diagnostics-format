import os
from abc import *
from pathlib import Path

from .definition import *

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
        tags = decode_tags(self.read_all())

        for tag in tags:
            if tag.index == ManifestTable.DEFINE_OBJECT_TAG:
                self.rows.append(ManifestObjectDefinition.from_tag(tag))
            elif tag.index == ManifestTable.DEFINE_ENUM_TAG:
                self.rows.append(ManifestEnumDefinition.from_tag(tag))
            else:
                raise ManifestError(f"Unknown tag type at root {tag}")


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
        tags = decode_tags(self.read_all())
        for tag in tags:
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

    def parse(self):
        for index in self.structure_tables:
            self.structure_tables[index].parse()

        for index in self.display_tables:
            self.display_tables[index].parse()

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

