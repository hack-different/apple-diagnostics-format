from . import WriterBase
from .object import *
from io import IOBase


class JsonWriter(WriterBase):
    def write_to(self, value: DiagnosticObject, stream: IOBase) -> None:
        pass
