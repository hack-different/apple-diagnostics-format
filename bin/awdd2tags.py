#!/usr/bin/env python
import io
import sys
import os
import inspect

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from awdd import decode_tag, TagType

FILE = sys.argv[1]

if not FILE:
    print("Usage awdd2tags.py FILE")
    exit(-1)


with open(FILE, "rb") as stream:
    while tag := decode_tag(stream):
        print(tag)
        if tag.tag_type & TagType.LENGTH_PREFIX:
            sub_stream = io.BytesIO(tag.value)
            while subtag := decode_tag(sub_stream):
                print(f"\t{subtag}")
                if subtag.index == 2:
                    subdef = io.BytesIO(subtag.value)
                    while deftag := decode_tag(subdef):
                        print(f"\t\t{deftag}")
