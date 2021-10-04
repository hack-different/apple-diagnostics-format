import io
from typing import *
from awdd.manifest import *
from awdd import decode_variable_length_int
from awdd.root_manifest import create_root_manifest


class LogParser:
    default_manifests: ClassVar[Union[None, List[Manifest]]] = None

    root: ManifestObjectDefinition
    manifests: List[Manifest]

    @classmethod
    def load_default_manifests(cls) -> List[Manifest]:
        pass

    def __init__(self, manifests: Union[None, List[Manifest]] = None,
                 use_default_manifests: bool = True):

        self.root = create_root_manifest()
        self.manifests = []

        if use_default_manifests and LogParser.default_manifests is None:
            for manifest in LogParser.load_default_manifests():
                manifests.append(manifest)

        if manifests is not None:
            for manifest in manifests:
                self.manifests.append(manifest)

    def parse(self, data: io.RawIOBase):
        while (tag, tag_len := decode_variable_length_int(data)) is not None:
            print(hex(tag))


    def output_text(self, writer: io.BufferedWriter):
        pass
