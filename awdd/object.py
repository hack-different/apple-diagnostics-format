from .manifest import *
from abc import ABC, abstractmethod
from enum import IntEnum, IntFlag
from typing import *

ROOT_OBJECT = None


class DiagnosticValue:
    property: 'ManifestProperty'


class DiagnosticObject:
    object_class: 'ManifestObjectDefinition'
    properties: List[DiagnosticValue]


class WriterBase(ABC):
    def write(self, value: DiagnosticObject) -> bytes:
        output = io.BytesIO()
        self.write_to(value, output)
        return output.getvalue()

    @abstractmethod
    def write_to(self, value: DiagnosticObject, stream: io.IOBase) -> None:
        pass

