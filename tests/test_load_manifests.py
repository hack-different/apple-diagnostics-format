import pytest
import os
from glob import glob
from awdd.manifest import Manifest


def test_load_manifests():
    metadata_path = os.path.join(os.path.dirname(__file__), "../metadata/*.bin")

    for manifest_file in glob(metadata_path):
        manifest = Manifest(manifest_file)
        assert(manifest is not None)
        assert(len(manifest.table) > 1)