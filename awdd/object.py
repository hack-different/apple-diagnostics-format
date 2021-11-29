import io
from dataclasses import dataclass

from .manifest import *
from abc import ABC, abstractmethod
from enum import IntEnum, IntFlag
from typing import *
from io import *

from .metadata import Metadata

ROOT_OBJECT = None


@dataclass
class DiagnosticValue:
    property: 'ManifestDefinition'
    value: Union[Any, 'DiagnosticObject']

    def __init__(self, metadata: Metadata, prop: ManifestProperty, tag: Tag):
        self.property = prop
        if prop.type == PropertyType.OBJECT:
            self.value = DiagnosticObject(metadata, prop.object_type, ta)
        else:
            self.value = value


@dataclass
class DiagnosticObject:
    metadata: Metadata
    object_class: 'ManifestObjectDefinition'
    properties: List[DiagnosticValue]

    def __init__(self, metadata: Metadata, klass: 'ManifestObjectDefinition', values: List[Tag]):
        self.metadata = metadata
        self.object_class = klass
        self.properties = []
        for tag in values:
            prop = self.object_class.property_for_tag(tag.index)
            self.properties.append(DiagnosticValue(metadata, prop, tag.value))



class WriterBase(ABC):
    def write(self, value: DiagnosticObject) -> bytes:
        output = io.BytesIO()
        self.write_to(value, output)
        return output.getvalue()

    @abstractmethod
    def write_to(self, value: DiagnosticObject, stream: io.IOBase) -> None:
        pass

