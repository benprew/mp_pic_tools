#!/usr/bin/env python3

import argparse
import logging
import os
import struct

from PIL import Image
from PIL.Image import Image as PILImage

from shared import tr2pal


def main():
    parser = argparse.ArgumentParser(description="Convert SPR files to PNG")
    parser.add_argument("file", help="The SPR file to convert.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode."
    )
    parser.add_argument(
        "-p", "--palette", help="The palette file to use.", default=None
    )
    parser.add_argument("-g", "--gen", help="generator version", default=2)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    filename = args.file
    if not args.palette:
        args.palette = "TodPal.tr"

    # open file as binary
    with open(filename, "rb") as f:
        # parse pic format
        # images = parse_spr(f, os.path.basename(filename), pal)
        images = parse_spr(f, tr2pal(args.palette))
        for i, image in enumerate(images):
            out = f"{os.path.basename(filename)}_{i}.png"
            logging.debug(f"saving to {out}")
            image.save(out)


# SPR files aren't compressed or encoded, they're raw images
# A given SPR file can contain multiple images,
def parse_spr(data_stream, palette: bytes) -> list[PILImage]:
    bitmaps: list[PILImage] = []

    while True:
        start = data_stream.tell()
        logging.info(f"tell: {data_stream.tell()} img: {len(bitmaps)}")
        # Read the image data size (4 bytes, unsigned int)
        image_data_size = struct.unpack("<I", data_stream.read(4))[0]
        end = start + image_data_size
        if image_data_size == 0xFFFFFFFF:
            break  # End of image data

        if image_data_size > 10000:
            data_stream.seek(-10, 1)
            logging.error(data_stream.read(10))
            raise ValueError(f"Invalid image data size: {image_data_size}")

        # Read width and height (2 bytes each)
        width, height = struct.unpack("<HH", data_stream.read(4))

        # Skip the unknown 2-byte values
        print("unknown1/2: ", data_stream.read(4))

        # Read number of empty lines and cutoff offset (2 bytes each)
        empty_lines, cutoff_offset_y = struct.unpack("<HH", data_stream.read(4))

        logging.info(
            f"file header: w:{width} h:{height} size:{image_data_size} empty_lines:{empty_lines}"
        )

        # Fill with "blank lines above"
        pixel_data = b"\x00" * width * empty_lines

        # Process each row
        for y in range(empty_lines, height):
            # Skip transparent pixel markers (0xFF) until we encounter valid data
            while True:
                marker = data_stream.read(1)
                if not marker or marker != b"\xFF":
                    break

            # Read transparent pixel amount and unknown data
            transparent_pixels = struct.unpack("<B", marker)[0]
            unknown3 = struct.unpack("<B", data_stream.read(1))[0]
            if unknown3 not in (0xFE, 0xFF):
                print(f"tp: {transparent_pixels} u3: {unknown3}")

            # Determine number of pixels to process in this row
            if unknown3 not in (0xFE, 0xFF):
                pixels_in_data = unknown3
            else:
                pixels_in_data = struct.unpack("<B", data_stream.read(1))[0]

            if data_stream.tell() - start >= image_data_size:
                break

            if transparent_pixels > width or pixels_in_data > width:
                data_stream.seek(-10, 1)
                logging.error(data_stream.read(10))
                raise ValueError(f"Invalid pixels in data: {pixels_in_data}")

            logging.info(
                f"t: {data_stream.tell()} tp: {transparent_pixels} pd: {pixels_in_data} sz: {len(pixel_data)} y: {y}"
            )
            # Read the raw pixel data in bulk (pixels_in_data is the number of
            # non-transparent pixels in this row)
            row_data = data_stream.read(pixels_in_data)

            pixel_data += b"\x00" * transparent_pixels  # Add transparent pixels
            pixel_data += row_data  # Add the row data
            pixel_data += b"\x00" * (width - transparent_pixels - pixels_in_data)

        # fill remaining image with transparent pixels
        if len(pixel_data) < width * height:
            pixel_data += b"\x00" * ((width * height) - len(pixel_data))

        curr = data_stream.tell()
        if curr < end:
            print(f"curr: {curr} end: {end} {data_stream.read(end - curr)}")

        # move to next image
        data_stream.seek(end)

        # Now create the image using the 'P' mode and the palette
        # Create a new Image with mode 'P' (paletted)
        bitmap = Image.new("P", (width, height))

        # Put the pixel data into the image (indexed by the palette)
        logging.info(f"image - actual: {len(pixel_data)} expected: {width * height}")
        bitmap.putdata(pixel_data)
        bitmap.putpalette(palette)
        bitmap.info["transparency"] = 0

        # Append the image to the result list
        bitmaps.append(bitmap)

    return bitmaps


if __name__ == "__main__":
    main()
