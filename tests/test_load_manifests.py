import pytest
import os
from glob import glob
from awdd.manifest import *


def test_load_manifests():
    metadata_files = glob(os.path.join(EXTENSION_MANIFEST_PATH)) + [ROOT_MANIFEST_PATH]

    for manifest_file in metadata_files:
        print(f"Reading manifest file: {manifest_file}\n")
        manifest = Manifest(manifest_file)
        assert(manifest is not None)

        manifest.parse()

        print(f"Tag: {manifest.tag}")
        print(f"Structure Tables: {len(manifest.structure_tables)}")
        print(f"Display Tables: {len(manifest.display_tables)}")
        if manifest.identity:
            print(f"Identity: {manifest.identity.name}")

        if manifest.is_root:
            # Root manifests define multiple tags
            assert(manifest.tag is None)
            assert(len(manifest.structure_tables) > 1)
            assert(len(manifest.display_tables) > 1)
        else:
            # Extension manifests define single tags
            assert(manifest.tag is not None)
            assert(len(manifest.structure_tables) in [0, 1])
            assert(len(manifest.display_tables) in [0, 1])


def test_parse_root_manifest():
    manifest = Manifest(ROOT_MANIFEST_PATH)

    manifest.parse()

    assert(len(manifest.display_tables) > 1)
    assert(len(manifest.display_tables) > 1)
    assert(len(manifest.structure_tables) > 1)

    compact_tags = set(manifest.structure_tables.keys())
    display_tags = set(manifest.display_tables.keys())

    assert compact_tags == display_tags

    for tag in manifest.structure_tables:
        print(f"Tag {hex(tag)} has {len(manifest.structure_tables[tag].rows)} compact rows and {len(manifest.display_tables[tag].rows)} display rows")


def test_extension_parse_manifests():
    for manifest_file in glob(EXTENSION_MANIFEST_PATH):
        print(f"Reading in test data file {manifest_file}\n")

        manifest = Manifest(manifest_file)
        assert(manifest is not None)

        manifest.parse()

        assert(1 >= len(manifest.display_tables) >= 0)
        assert(len(manifest.structure_tables) == 1)


