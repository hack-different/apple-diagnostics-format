#!/usr/bin/env python
import io
import os.path
import glob
from enum import IntEnum
from typing import *
import struct
import sys

# Primal metadata parser that simply shreds into regions for analysis
# this likely wont be useful beyond the reverse engineering of this format or
# when new variations occur, you probably want the higher level APIs

ROOT_MANIFEST_PATH = '/System/Library/PrivateFrameworks/WirelessDiagnostics.framework/Support/AWDMetadata.bin'
EXTENSION_MANIFEST_PATH = '/System/Library/AWD/Metadata/*.bin'


def copy_io(io_from: BinaryIO, io_to: BinaryIO, count: int, buf_size=16384):
    remaining = count
    while remaining > 0:
        chunk_size = min(remaining, buf_size)
        buf = io_from.read(chunk_size)
        if not buf:
            break
        io_to.write(buf)
        remaining -= chunk_size


class ManifestRegionType(IntEnum):
    structure = 0x02
    display = 0x03
    identity = 0x04
    root = 0x05
    linkage = 0x06


class ManifestRegion:
    parser: 'ManifestParser'
    type: ManifestRegionType
    offset: int
    size: int

    def __init__(self, parser: 'ManifestParser', region_type: ManifestRegionType, offset: int, size: int):
        self.parser = parser
        self.type = region_type
        self.offset = offset
        self.size = size

    def file_name(self):
        return f"{self.parser.file_name}_region_{self.type}.bin"

    def write_out_to(self, output_dir: str):
        with open(os.path.join(output_dir, os.path.basename(self.file_name())), "wb") as output:
            self.parser.data.seek(self.offset, io.SEEK_SET)
            copy_io(self.parser.data, output, self.size)


class ManifestTable(ManifestRegion):
    tag: int
    checksum: int

    def __init__(self, parser: 'ManifestParser', region_type: ManifestRegionType, offset: int, size: int, tag: int, checksum: int):
        super().__init__(parser, region_type, offset, size)
        self.tag = tag
        self.checksum = checksum

    def file_name(self):
        return f"{self.parser.file_name}_region_{self.type}_tag_{self.tag}.bin"


class ManifestParser:
    MANIFEST_MAGIC = b'AWDM'
    HEADER_STRUCT = b'4sHH'
    HEADER_SECTION_COUNT = b'I'
    HEADER_SECTION_AND_COUNT = b'HH'
    HEADER_TABLE_STRUCT = b'IIII'
    HEADER_FOOTER_STRUCT = b'II'

    file_name: str
    major: int
    minor: int
    data: BinaryIO
    regions: List[ManifestRegion]

    def __init__(self, path: str):
        if not os.path.isfile(path):
            raise Exception("Path does not exist")

        self.file_name = path
        self.data = open(self.file_name, "rb")
        self.regions = []

    def parse(self):
        magic, self.major, self.minor = struct.unpack(ManifestParser.HEADER_STRUCT,
                                                      self.data.read(struct.calcsize(ManifestParser.HEADER_STRUCT)))

        if magic != ManifestParser.MANIFEST_MAGIC:
            raise Exception(f"Incorrect MAGIC (got {magic})")

        if self.major != 1 or self.minor != 1:
            raise Exception(f"Unsupported version (got {self.major}.{self.minor})")

        sections, *_ = struct.unpack(ManifestParser.HEADER_SECTION_COUNT,
                                     self.data.read(struct.calcsize(ManifestParser.HEADER_SECTION_COUNT)))

        def parse_region() -> Optional[ManifestRegion]:
            header_tag, field_count = struct.unpack(ManifestParser.HEADER_SECTION_AND_COUNT,
                                                    self.data.read(
                                                        struct.calcsize(ManifestParser.HEADER_SECTION_AND_COUNT)))

            if header_tag == 0 and field_count == 0:
                return None

            parsed_tag = ManifestRegionType(header_tag)

            if field_count == 0x04:
                tag, offset, size, checksum = \
                    struct.unpack(ManifestParser.HEADER_TABLE_STRUCT,
                                  self.data.read(struct.calcsize(ManifestParser.HEADER_TABLE_STRUCT)))

                return ManifestTable(self, parsed_tag, offset, size, tag, checksum)

            elif field_count == 0x02:
                offset, size = struct.unpack(ManifestParser.HEADER_FOOTER_STRUCT,
                                             self.data.read(struct.calcsize(ManifestParser.HEADER_FOOTER_STRUCT)))

                return ManifestRegion(self, parsed_tag, offset, size)

            else:
                raise Exception(f"Unsupported header tag at {header_tag} count {field_count}")

        while single_region := parse_region():
            if single_region is None:
                break

            self.regions.append(single_region)


# If we are called with no arguments, substitute root and all extension manifests
files = [ROOT_MANIFEST_PATH] + glob.glob(EXTENSION_MANIFEST_PATH)
for file in files:
    manifest = ManifestParser(file)
    manifest.parse()

    for region in manifest.regions:
        region.write_out_to(sys.argv[1])
