from .manifest import *
from abc import ABC, abstractmethod
from enum import IntEnum, IntFlag

ROOT_OBJECT = None


class PropertyFlags(IntFlag):
    NONE = 0x00
    REPEATED = 0x01


class IntegerFormat(IntEnum):
    TIMESTAMP = 0x01
    TRIGGER_ID = 0x03
    PROFILE_ID = 0x04
    AVERAGE_TIME = 0x15
    TIME_DELTA = 0x16
    TIMEZONE_OFFSET = 0x17
    ASSOCIATED_TIME = 0x18
    PERIOD_IN_HOURS = 0x19
    TIME_OF_DAY = 0x1E
    SAMPLE_TIMESTAMP = 0x1F


class StringFormat(IntEnum):
    UNKNOWN = 0x00
    UUID = 0x01


class PropertyType(IntEnum):
    UNKNOWN = 0x00
    DOUBLE = 0x01
    FLOAT = 0x02
    INTEGER_64 = 0x03
    INTEGER = 0x04
    UNKNOWN_5 = 0x05
    INTEGER_32 = 0x06
    INTEGER_UNSIGNED = 0x07
    UNKNOWN_8 = 0x08
    UNKNOWN_9 = 0x09
    UNKNOWN_10 = 0x0A
    BOOLEAN = 0x0C
    ENUM = 0x0B
    STRING = 0x0D
    BYTES = 0x0E
    PACKED_UINT_32 = 0x15
    UNKNOWN_17 = 0x11
    UNKNOWN_20 = 0x14
    OBJECT = 0x1B


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

