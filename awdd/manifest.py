import os
from pathlib import *
from pyasn1 import *
import struct
from pyasn1.codec.ber.decoder import decode


class ManifestError(Exception):
    pass


MANIFEST_MAGIC = b'AWDM'
HEADER_MAGIC_STRUCT = b'4sHH'
HEADER_STRUCT_HEADER = b'I' * 7
HEADER_STRUCT_DISPLAY = b'I' * 6
HEADER_STRUCT_FOOTER = b'I' * 5


class ManifestRow:
    def __init__(self, row):
        pass


class ManifestDisplayRow:
    def __init__(self, row):
        pass


class Manifest:
    def __init__(self, path: str):
        self.path = Path(path)
        if self.path.exists() is False:
            raise ManifestError("Path does not exist")

        self.file = open(self.path.absolute(), "rb")
        magic, major, minor = struct.unpack(HEADER_MAGIC_STRUCT, self.file.read(struct.calcsize(HEADER_MAGIC_STRUCT)))
        if magic != MANIFEST_MAGIC:
            raise ManifestError("Incorrect magic value")
        if major != 1 or minor != 1:
            raise ManifestError("Incompatible manifest version")

        _, _, _, self.tag, self.header_size, self.table_size, self.header_checksum = struct.unpack(
            HEADER_STRUCT_HEADER, self.file.read(struct.calcsize(HEADER_STRUCT_HEADER)))

        _, _, self.tag, self.display_offset, self.display_size, self.display_checksum = struct.unpack(
            HEADER_STRUCT_DISPLAY, self.file.read(struct.calcsize(HEADER_STRUCT_DISPLAY)))

        _, _, self.footer_offset, self.footer_size, _ = struct.unpack(
            HEADER_STRUCT_FOOTER, self.file.read(struct.calcsize(HEADER_STRUCT_FOOTER)))

        def decode_rows():
            self.file.seek(self.header_size, os.SEEK_SET)
            for row in decode(self.file.read(self.header_size)):
                yield ManifestRow(row)

        self.table = list(decode_rows())

        def decode_display_row():
            self.file.seek(self.header_size + self.table_size, os.SEEK_SET)
            for display_row in decode(self.file.read(self.display_size)):
                yield ManifestDisplayRow(display_row)

        self.display_table = list(decode_display_row())