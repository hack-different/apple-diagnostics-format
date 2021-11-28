import io

import pytest
import os
from glob import glob
from awdd.metadata import *
from awdd.parser import LogParser


def test_resolve_manifests():
    metadata = Metadata()
    metadata.resolve()
