#!/usr/bin/env python3

from collections import namedtuple
from io import BufferedReader
from typing import Optional
import argparse
import logging
import os
import struct

from PIL import Image
from PIL.Image import Image as PILImage

import rle
import lzw

PicV3BlockHeader = namedtuple("PicV3BlockHeader", ["block_id", "length"])
PicV3Palette = namedtuple("PicV3Palette", ["first", "last"])
PicV3Image = namedtuple("PicV3Image", ["width", "height", "max_bits"])


def main():
    parser = argparse.ArgumentParser(description="Convert PIC files to PNG")
    parser.add_argument("file", help="The PIC file to convert.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode."
    )
    parser.add_argument(
        "-p", "--palette", help="The palette file to use.", default=None
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    filename = args.file
    pal = None
    if args.palette:
        pal = parse_text_palette(args.palette)

    # open file as binary
    with open(filename, "rb") as f:
        # parse pic format
        image = parse_pic_v3(f, os.path.basename(filename), pal)
        out = f"{os.path.basename(filename)}.png"
        logging.debug(f"saving to {out}")
        image.save(out)


# The PICv3 files consist of one or more tagged blocks of data. Each block
# begins with the same common header identifying the block type via the tag,
# and its length. A valid PIC file must contain one of the image types but can
# optionally contain any one, or more, of the other defined block types
def parse_pic_v3(
    f: BufferedReader, fn: str, palette: Optional[bytes] = None
) -> PILImage:
    """Convert .pic file to .png"""
    # typedef struct {  // PicV3 General Block Header
    #     char block_id[2];  // block tag
    #     uint16_t length;   // length of the block
    #     uint8_t data[];    // remaining block data
    # } mp_picV3_block_t;

    pal = palette if palette is not None else parse_text_palette()
    def_pal = True

    while f:
        # read block header
        hdr = f.read(4)
        if not hdr:
            break
        block_header = PicV3BlockHeader._make(struct.unpack("<2sH", hdr))
        logging.info(block_header)

        try:
            header_str = block_header.block_id.decode("ascii")
        except UnicodeDecodeError:
            logging.error("invalid block header")
            break

        if header_str not in ("C0", "E0", "M0", "M1", "X0", "X1"):
            raise ValueError(f"Invalid block id: {header_str}")

        if header_str in ("M0", "M1"):  # Block Type M0 – Palette data
            pal = parse_palette(f)
            def_pal = False
        elif header_str in ("X0", "X1"):
            pic, width, height = parse_image(f, block_header.length)
        elif header_str in ("C0", "E0"):
            raise ValueError(f"header {header_str} not implemented")

    # make png from palette and pic data
    logging.info(f"pic: {fn}, def_pal: {def_pal}, w: {width}, h: {height}")
    print(f"pic {pic[0:10].hex()}")

    i = 0
    while i < len(pal):
        print(f"pal {i // 3}: {pal[i:i+3].hex()}")
        i += 3

    image = Image.frombytes("P", (width, height), pic)
    image.putpalette(pal)

    return image


# The format identifier is an 8bit signed value, with its absolute value
# representing the maximum code width for the LZW compressed stream that
# follows. The sign of the value indicates if the data is a 4bit packed pixel
# format or linear pixel format. Positive indicates pixels are packed two per
# byte (4bit packed), while a negative value indicates a linear arrangement
# (8bits per pixel). The pixel packing arrangement is discussed in the
# “Compression” section below.
# (In subsequent versions of PIC the format identifier is always positive,
# and does not indicate the pixel packing arrangement, only the maximum
# LZW code width) The most common identifier values we have seen are:
# 9-11
def parse_image(f, length: int) -> tuple[bytes, int, int]:
    # typedef struct { // PicV3 Image Block
    #     uint16_t width;    // image width in pixels
    #     uint16_t height;   // image height in pixels
    #     uint8_t max_bits;  // maximum code width for LZW data
    #     uint8_t lz_data[]; // RLE+LZW compressed stream
    # } mp_picV3_image_t;

    header = PicV3Image._make(struct.unpack("<HHB", f.read(5)))
    logging.debug(f"Image header: {header}")
    data = f.read(length - 5)

    # lzw decompress
    data = lzw.decompress(data, abs(header.max_bits))
    logging.info(f"len after LZW {len(data)}")

    # rle decompress
    data = rle.decode(data)
    logging.info(f"len after RLE {len(data)}, exp {header.width * header.height}")

    # unpack bits
    # data = unpack_data(data)
    # logging.info(f"len after UNPACK {len(data)}, exp {header.width * header.height}")
    # data += [0] * (header.width * header.height - len(data))

    return bytes(data), header.width, header.height


def unpack_data(data: list) -> list:
    unpacked_data = []
    for i in range(len(data)):
        unpacked_data.append(data[i] & 0x0F)
        unpacked_data.append(data[i] & 0xF0)
    return unpacked_data


def parse_palette(f: BufferedReader) -> bytes:
    # typedef struct { // PicV3 Palette Block
    #     uint8_t first;          // index of first palette entry
    #     uint8_t last;           // index of last palette entry
    #     pal_t palette_data[];   // last-first+1 RGB entries
    # } mp_picV3_palette_t;

    pal_header = PicV3Palette._make(struct.unpack("<BB", f.read(2)))

    logging.info(pal_header)
    palette = []

    # read palette data
    pos = 0
    while pos < pal_header.last + 1 - pal_header.first:
        palette.append(struct.unpack("<BBB", f.read(3)))
        pos += 1

    if len(palette) != pal_header.last + 1:
        raise ValueError(
            f"Invalid palette data pal:{len(palette)}, "
            f"pal_header:{pal_header.last + 1}"
        )
    format_string = "BBB"
    # Create a bytes object by packing each tuple
    byte_data = b"".join(struct.pack(format_string, *t) for t in palette)
    return byte_data


def parse_text_palette(pal_file="TodPal.tr") -> bytes:
    """Parse .tr palette files into bytes"""
    pal = [[255, 255, 255]] * 256

    # Open text Palette and fill array
    # format "pal# - val1 val2 val3"
    with open(pal_file, "r") as read_pal:
        for line in read_pal:
            temp = line.strip().split()
            pal_num = int(temp[0])
            rgb = temp[2:5]
            pal[pal_num] = [int(x) for x in rgb]

    print(pal)

    # Convert the list of lists to a bytes object
    byte_data = b"".join(struct.pack("<BBB", *pal[i]) for i in range(256))
    return byte_data


if __name__ == "__main__":
    main()
