import pytest
import os
from glob import glob
from awdd.manifest import Manifest


def test_load_manifests():
    metadata_path = os.path.join(os.path.dirname(__file__), "../metadata/*.bin")

    for manifest_file in glob(metadata_path):
        manifest = Manifest(manifest_file)
        assert(manifest is not None)
        assert(len(manifest.compact_tables) >= 1)


def test_parse_root_manifest():
    manifest = Manifest('/System/Library/PrivateFrameworks/WirelessDiagnostics.framework/Support/AWDMetadata.bin')
    manifest.parse()

    assert(len(manifest.display_tables) > 1)
    assert(len(manifest.footers) > 1)
    assert(len(manifest.display_tables[0].rows) > 1)
    assert(len(manifest.compact_tables[0].rows) > 1)

    compact_tags = set(manifest.compact_tables.keys())
    display_tags = set(manifest.display_tables.keys())

    assert compact_tags == display_tags

    for tag in manifest.compact_tables:
        print(f"Tag {hex(tag)} has {len(manifest.compact_tables[tag].rows)} compact rows and {len(manifest.display_tables[tag].rows)} display rows")

    print(f"Tables has {len(manifest.footers)} footers")
    for footer_id in manifest.footers:
        print(f"Footer {footer_id} has size of {manifest.footers[footer_id].size}")


def test_extension_parse_manifests():
    metadata_path = os.path.join(os.path.dirname(__file__), "../metadata/*.bin")

    for manifest_file in glob(metadata_path):
        print(f"Reading in test data file {manifest_file}\n")

        manifest = Manifest(manifest_file)
        assert(manifest is not None)

        manifest.parse()

        assert(1 >= len(manifest.display_tables) >= 0)
        assert(len(manifest.compact_tables) == 1)


