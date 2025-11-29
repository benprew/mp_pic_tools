#!/usr/bin/env python3

import os
import fnmatch
import sys
import logging

from shared import tr2pal

import pic2png

dir = sys.argv[1] if len(sys.argv) > 1 else "."

# logging.basicConfig(level=logging.INFO)

duel_pal = tr2pal("out.tr")
default_pal = tr2pal("../MtG_DotP_SotA/Todpal.tr")

# Recursively find all .pic files recursively (case-insensitive)
for root, dirs, files in os.walk(dir):
    for filename in files:
        if not fnmatch.fnmatchcase(filename.lower(), "*.pic"):
            continue

        filepath = os.path.join(root, filename)
        pal = default_pal
        if os.path.join(dir, filename) != filepath:
            logging.info(f"using duel pal for {filepath}")
            pal = duel_pal
        with open(filepath, "rb") as f:
            try:
                image = pic2png.parse_pic_v3(f, filename, pal)
                out = f"{filename}.png"
                logging.debug(f"saving to {out}")
                image.save(out)
                logging.info(f"{filename}: SUCCESS")
            except Exception as e:
                logging.info(f"{filename}: FAIL {e}")
