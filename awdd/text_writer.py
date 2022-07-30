from . import WriterBase
from .object import *
from io import IOBase


class TextWriter:
    def write_to(self, value: DiagnosticObject, stream: IOBase) -> None:
        pass

    def _write_to_internal(self, value: DiagnosticObject):
        indent_space = indent * "\t"
        for prop in value.properties:
            if prop.property.type != PropertyType.OBJECT:
                stream.write(f"{indent_space}{prop.property.name}: {prop.value}\n")
            else:
                stream.write(indent_space + prop.property.name + " {\n")
                self.write_to(prop.value, stream, indent + 1)
                stream.write(indent_space + "}\n")
