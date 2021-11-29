from .manifest import *
from typing import *
from glob import glob


class Metadata:
    root_manifest: Manifest
    extension_manifests: List[Manifest]
    all_definitions: Dict[int, ManifestDefinition]

    def __init__(self):
        self.root_manifest = Manifest(ROOT_MANIFEST_PATH)

        self.extension_manifests = [Manifest(path) for path in glob(EXTENSION_MANIFEST_PATH)]

    def resolve(self):
        self.root_manifest.parse()

        for manifest in self.extension_manifests:
            manifest.parse()

        self.all_definitions = {}

        for entry in self.root_manifest.definitions():
            self.all_definitions[entry.tag] = entry.definition

        for extension in self.extension_manifests:
            for entry in extension.definitions():
                self.all_definitions[entry.tag] = entry.definition

        for tag in self.all_definitions:
            self.all_definitions[tag].bind(self.all_definitions)

        print(self.all_definitions)