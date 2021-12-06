from .manifest import *
from typing import *
from glob import glob

from awdd import *


class Metadata:
    root_manifest: Manifest
    extension_manifests: List[Manifest]
    all_enums: Dict[int, ManifestTypeDefinition]
    all_objects: Dict[int, ManifestObjectDefinition]

    def __init__(self):
        self.root_manifest = Manifest(ROOT_MANIFEST_PATH)

        self.extension_manifests = [Manifest(path) for path in glob(EXTENSION_MANIFEST_PATH)]

        self.all_enums = {}
        self.all_objects = {}

    def resolve(self):
        self.root_manifest.parse()

        for manifest in self.extension_manifests:
            manifest.parse()

        for entry in self.root_manifest.definitions():
            if entry.type == ManifestDefinitionTag.DEFINE_TYPE:
                self.all_enums[entry.tag] = entry.definition
            elif entry.type == ManifestDefinitionTag.DEFINE_OBJECT:
                self.all_objects[entry.tag] = entry.definition
            else:
                raise ManifestError(f"Unknown deinition type")

        for extension in self.extension_manifests:
            for entry in extension.definitions():
                if entry.type == ManifestDefinitionTag.DEFINE_TYPE:
                    self.all_enums[entry.tag] = entry.definition
                elif entry.type == ManifestDefinitionTag.DEFINE_OBJECT:
                    self.all_objects[entry.tag] = entry.definition
                else:
                    raise ManifestError(f"Unknown defintion type")

        for tag in self.all_enums:
            self.all_enums[tag].bind(self.root_manifest.types, self.all_enums, self.all_objects)

        for tag in self.all_objects:
            self.all_objects[tag].bind(self.root_manifest.types, self.all_enums, self.all_objects)

        for tag in list(self.all_objects):
            self.all_objects[tag].extend()

    def root(self) -> ManifestObjectDefinition:
        return self.root_manifest.display_tables[0].objects[0]
