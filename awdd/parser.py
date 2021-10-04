import io
from typing import *
from awdd.manifest import *
from awdd import decode_variable_length_int


class LogParser:
    default_manifests: ClassVar[Union[None, List[Manifest]]] = None

    manifests: List[Manifest]

    @classmethod
    def load_default_manifests(cls) -> List[Manifest]:
        pass

    @classmethod
    def load_root_manifest(cls) -> Manifest:
        return Manifest('/System/Library/PrivateFrameworks/WirelessDiagnostics.framework/Support/AWDMetadata.bin')


    def __init__(self, manifests: Union[None, List[Manifest]] = None,
                 use_default_manifests: bool = True):

        self.manifests = [LogParser.load_root_manifest()]

        if use_default_manifests and LogParser.default_manifests is None:
            for manifest in LogParser.load_default_manifests():
                manifests.append(manifest)

        if manifests is not None:
            for manifest in manifests:
                self.manifests.append(manifest)

    def parse(self, data: io.RawIOBase):
        while (tag, tag_len := decode_variable_length_int(data)) is not None:
            if tag & 0x01:
                size, size_length = decode_variable_length_int(data)
                data = data.read(size)
            else:
                pass


    def output_text(self, writer: io.BufferedWriter):
        pass
