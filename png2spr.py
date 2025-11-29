#!/usr/bin/env python3

import argparse
import logging
import struct
from typing import List

from PIL import Image
from PIL.Image import Image as PILImage


def main():
    parser = argparse.ArgumentParser(description="Convert PNG files to SPR")
    parser.add_argument("files", nargs="+", help="The PNG files to convert.")
    parser.add_argument("-o", "--output", help="Output SPR file name", required=True)
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode."
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    # Load all PNG images
    images = []
    for filename in args.files:
        img = Image.open(filename)
        if img.mode != "P":
            img = img.convert("P")
        images.append(img)

    # Convert and save as SPR
    with open(args.output, "wb") as f:
        make_spr(images, f)


def make_spr(images: List[PILImage], output_stream) -> None:
    """Convert a list of PNG images to SPR format and write to output stream."""

    for image in images:
        width, height = image.size
        pixel_data = list(image.getdata())

        # Calculate empty lines at the top
        empty_lines = 0
        for y in range(height):
            if any(pixel_data[y * width : (y + 1) * width]):
                break
            empty_lines += 1

        # Find cutoff offset (first non-empty line from bottom)
        cutoff_offset_y = 0
        for y in range(height - 1, -1, -1):
            if any(pixel_data[y * width : (y + 1) * width]):
                cutoff_offset_y = height - y - 1
                break

        # Pre-calculate the image data to determine size
        image_data = bytearray()

        # Write header placeholder
        image_data.extend(b"\x00" * 16)

        # Process each row after empty lines
        for y in range(empty_lines, height):
            row = pixel_data[y * width : (y + 1) * width]

            # Find first non-transparent pixel
            transparent_pixels = 0
            while transparent_pixels < width and row[transparent_pixels] == 0:
                transparent_pixels += 1

            if transparent_pixels == width:
                continue

            # Find actual pixel data in this row
            pixels_in_data = 0
            row_data = bytearray()
            for x in range(transparent_pixels, width):
                if row[x] != 0:
                    row_data.append(row[x])
                    pixels_in_data += 1
                else:
                    break

            # Write row data
            image_data.append(transparent_pixels)  # transparent pixels count
            # image_data.append(0xFF)

            logging.info(f"pixels_in_data: {pixels_in_data}")
            if pixels_in_data > 0xFF:
                image_data.append(0xFE)  # extended pixel count marker
                image_data.append(pixels_in_data & 0xFF)
            else:
                image_data.append(pixels_in_data)  # pixel count

            image_data.extend(row_data)

        # Calculate total size and update header
        total_size = len(image_data)
        header = struct.pack(
            "<IHHHHHH",
            total_size,  # total size
            width,  # width
            height,  # height
            0,  # unknown value 1
            0,  # unknown 2
            empty_lines,  # empty lines at top
            cutoff_offset_y,  # cutoff offset
        )

        # calculate padding
        curr = len(image_data) + len(header)
        padding = (4 - (curr % 4)) % 4
        print(
            f"empty: {empty_lines} cutoff: {cutoff_offset_y} curr {curr} padding {padding}"
        )

        # Write header at start of image data
        image_data[0:16] = header

        # Write the image data
        output_stream.write(image_data)

        # TODO: Write padding

    # Write end marker
    output_stream.write(
        b"\xFF\xFF\xFF\xFF\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD\xCD"
    )


if __name__ == "__main__":
    main()
