import os
from pathlib import *
import struct
from typing import *
from awdd import *


class ManifestError(Exception):
    pass


class ManifestFooter:
    def __init__(self, offset: int, size: int):
        self.offset = offset
        self.size = size


class ManifestRow:
    def __init__(self, row):
        pass


class ManifestTable:
    rows: List[ManifestRow]

    def __init__(self, tag: int, offset: int, size: int, checksum: int):
        self.tag = tag
        self.offset = offset
        self.size = size
        self.checksum = checksum
        self.rows = []


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
            else:
                raise ManifestError(f"Unsupported header tag of {header_id}")
