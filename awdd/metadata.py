from .manifest import *
from typing import *
from glob import glob


class Metadata:
    root_manifest: Manifest
    extension_manifests: List[Manifest]

    def __init__(self):
        self.root_manifest = Manifest(ROOT_MANIFEST_PATH)

        self.extension_manifests = [Manifest(path) for path in glob(EXTENSION_MANIFEST_PATH)]

    def resolve(self):
        pass
