#!/usr/bin/env python3

import argparse
import os
import sys

from PIL import Image


def main():
    parser = argparse.ArgumentParser(
        description="Convert an image to an 8-bit paletted PNG."
    )
    parser.add_argument("input_filename", help="The input image file (e.g., JPG, PNG).")
    args = parser.parse_args()

    input_filename = args.input_filename

    img = Image.open(input_filename)
    img = img.convert("P", palette=Image.ADAPTIVE, colors=256)

    # Construct the output filename by replacing the original extension with .png
    output_filename = os.path.splitext(input_filename)[0] + ".png"
    img.save(output_filename)
    print(f"Saved paletted PNG to: {output_filename}")


if __name__ == "__main__":
    main()
