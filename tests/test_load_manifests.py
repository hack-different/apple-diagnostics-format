import pytest
import os
from glob import glob
from awdd.manifest import Manifest


def test_load_manifests():
    metadata_path = os.path.join(os.path.dirname(__file__), "../metadata/*.bin")

    for manifest_file in glob(metadata_path):
        manifest = Manifest(manifest_file)
        assert(manifest is not None)
        assert(len(manifest.tables) >= 1)


def test_parse_manifests():
    metadata_path = os.path.join(os.path.dirname(__file__), "../metadata/*.bin")

    for manifest_file in glob(metadata_path):
        print(f"Reading in test data file {manifest_file}\n")

        manifest = Manifest(manifest_file)
        assert(manifest is not None)
        assert(len(manifest.tables) >= 1)
        manifest.parse()

        print(f"File {manifest_file} has {len(manifest.tables)} tables\n")
        for table_id in manifest.tables:
            print(f"Table ID: {table_id} has {len(manifest.tables[table_id].rows)}\n")
            assert(len(manifest.tables[table_id].rows) > 0)

