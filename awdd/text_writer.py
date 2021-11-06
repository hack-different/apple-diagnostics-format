from . import WriterBase
from .object import *
from io import IOBase


class TextWriter:
    def write_to(self, value: DiagnosticObject, stream: IOBase) -> None:
        pass