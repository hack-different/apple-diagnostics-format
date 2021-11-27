#!/usr/bin/env python
import io
import sys
import os
import inspect

currentdir = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

from awdd import decode_tag, TagType

FILE = sys.argv[1]

if not FILE:
    print("Usage awdd2tags.py FILE")
    exit(-1)


with open(FILE, "rb") as stream:
    while tag := decode_tag(stream):
        print(tag)
        if tag.tag_type & TagType.LENGTH_PREFIX:
            substream = io.BytesIO(tag.value)
            while subtag := decode_tag(substream):
                print(f"\t{subtag}")

