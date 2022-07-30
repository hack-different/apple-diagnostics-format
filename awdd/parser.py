import io
from typing import *
from awdd.manifest import *
from awdd.metadata import Metadata
from awdd.object import *
from awdd import decode_variable_length_int


class LogParser:
    metadata: Metadata

    def __init__(self, metadata: Optional[Metadata] = None):
        self.metadata = metadata if metadata is not None else Metadata()
        self.metadata.resolve()

    def parse(self, data: io.RawIOBase) -> DiagnosticObject:
        root_object: ManifestObjectDefinition = self.metadata.root()
        tags = decode_tags(data)
        result_object: DiagnosticObject = DiagnosticObject(
            self.metadata, root_object, tags
        )

        return result_object
