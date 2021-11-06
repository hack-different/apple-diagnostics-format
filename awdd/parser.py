import io
from typing import *
from awdd.manifest import *
from awdd.metadata import Metadata
from awdd.object import *
from awdd import decode_variable_length_int


class LogParser:
    metadata: Metadata

    def __init__(self, metadata: Optional[Metadata]):
        self.metadata = metadata if metadata is not None else Metadata()

    def parse(self, data: io.RawIOBase) -> DiagnosticObject:
        root_object: ManifestObjectDefinition = self.metadata.root_object
        result_object: DiagnosticObject = DiagnosticObject(self.metadata, ROOT_OBJECT)



        return result_object
