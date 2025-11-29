#!/usr/bin/env python3

from io import BufferedReader, BytesIO
from typing import Optional
import argparse
import logging
import os
import struct

from PIL import Image
from PIL.Image import Image as PILImage

import rle
import lzw
from pic_headers import (
    PicV3BlockHeader,
    PicV3Image,
    PicV3Palette,
    Pic98BlockHeader,
    pic98_header_format,
    Pic98PlaneBlock,
    pic98_plane_block_format,
)
from bellard_lzss4 import lzss_decompress
from shared import tr2pal, pic_version_help_message


def main():
    parser = argparse.ArgumentParser(description="Convert PIC files to PNG")
    parser.add_argument("file", help="The PIC file to convert.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode."
    )
    parser.add_argument(
        "-p", "--palette", help="The palette file to use.", default=None
    )
    parser.add_argument(
        "--pic-version",
        choices=["3", "98"],
        default="3",
        help=pic_version_help_message(),
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    filename = args.file
    pal = None
    if args.palette:
        if args.palette.endswith(".pal"):
            with open(args.palette, "rb") as f:
                pal = f.read()
        else:
            pal = tr2pal(args.palette)

    # open file as binary
    with open(filename, "rb") as f:
        # parse pic format based on version
        if args.pic_version == "3":
            image = parse_pic_v3(f, os.path.basename(filename), pal)
        elif args.pic_version == "98":
            image = parse_pic98(f, os.path.basename(filename), pal)
        else:
            # This case should not be reached due to 'choices' in add_argument
            raise ValueError(f"Unsupported PIC version: {args.pic_version}")

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

    pal = palette
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

    if pal is None:
        raise ValueError(
            "ERROR: No palette available. Not found in .pic and not specified as args"
        )
    # make png from palette and pic data
    logging.info(f"pic: {fn}, def_pal: {def_pal}, w: {width}, h: {height}")
    # print(f"pic {pic[0:10].hex()}")

    logging.info(f"Size: {len(pic)}")

    i = 0
    while i < len(pal):
        # print(f"pal {i // 3}: {pal[i:i+3].hex()}")
        i += 3

    image = Image.frombytes("P", (width, height), pic)
    image.putpalette(pal)
    image.info["transparency"] = 255

    return image


# The format identifier is an 8bit signed value, with its absolute value
# representing the maximum code width for the LZW compressed stream that
# follows. The sign of the value indicates if the data is a 4bit packed pixel
# format or linear pixel format. Positive indicates pixels are packed two per
# byte (4bit packed), while a negative value indicates a linear arrangement
# (8bits per pixel). The pixel packing arrangement is discussed in the
# "Compression" section below.
# (In subsequent versions of PIC the format identifier is always positive,
# and does not indicate the pixel packing arrangement, only the maximum
# LZW code width) The most common identifier values we have seen are:
# 9-11
def parse_image(f, length: int) -> tuple[bytes, int, int]:
    header = PicV3Image._make(struct.unpack("<HHB", f.read(5)))
    logging.debug(f"Image header: {header}")
    # data = f.read(length - 5)
    # sometimes length is an overflowed value (see 0028.pic in Shandalar)
    # in all the mtg picv3 files, the last block is the image data
    # so we read until the end of the file
    data = f.read(-1)

    # lzw decompress
    data = lzw.decompress(data, abs(header.max_bits))
    logging.info(f"len after LZW {len(data)}")

    # rle decompress
    data = rle.decode(data)
    logging.info(f"len after RLE {len(data)}, exp {header.width * header.height}")

    # unpack bits
    # data = unpack_data(data)
    # logging.info(f"len after UNPACK {len(data)}, exp {header.width * header.height}")

    # Pad image data to width*height
    # This happens in mtg Cstline1.pic, Dungeon.pic, and Magic.pic
    data += [255] * (header.width * header.height - len(data))

    return bytes(data), header.width, header.height


def unpack_data(data: list) -> list:
    unpacked_data = []
    for i in range(len(data)):
        unpacked_data.append(data[i] & 0x0F)
        unpacked_data.append(data[i] & 0xF0)
    return unpacked_data


def parse_palette(f: BufferedReader) -> bytes:
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


# see https://canadianavenger.io/2024/09/17/pic-as-we-know-it/
# and https://canadianavenger.io/2024/06/26/oops-i-did-it-again/
def parse_pic98(
    f: BufferedReader, fn: str, palette: Optional[bytes] = None
) -> PILImage:
    header = Pic98BlockHeader._make(struct.unpack(pic98_header_format, f.read(56)))

    if header.sig != b"\x00H8\x00":
        raise ValueError(f"Invalid pic98 file: {header.sig}")
    logging.info(f"Image header: {header}")
    logging.info(f"Width: {header.width}, Height: {header.height}")

    # Pic98 files have 4 "planes" that are overlayed to form a single image
    image_planes = []

    for i in range(4):
        # read 4 blocks of data
        block = Pic98PlaneBlock._make(
            struct.unpack(pic98_plane_block_format, f.read(2))
        )
        logging.info(f"Block {i}: len: {block.length}: curr: {f.tell()}")
        image_planes.append(lzss_decompress(BytesIO(f.read(block.length))))
        logging.info(
            f"Block {i}: len: {block.length}: curr: {f.tell()} date: {len(block)}"
        )

        # align on 16 bit boundary
        logging.info(f.tell() % 2)
        f.read(f.tell() % 2)

    pixels = combine_planes(header, image_planes)
    palette = convert_rgb444_palette_to_rgb888_bytes(header.pal)

    expected = header.width * header.height
    if len(pixels) != expected:
        raise ValueError(f"Size is: {len(pixels)} but should be {expected}")

    image = Image.frombytes("P", (header.width, header.height), pixels)
    image.putpalette(palette)
    image.info["transparency"] = 255

    return image


def combine_planes(hdr, planes):
    fo = bytearray()

    for y in range(hdr.height):
        for x in range(hdr.width // 8):  # 8 pixels per byte
            pos = (y * (hdr.width // 8)) + x
            p0 = planes[0][pos]
            p1 = planes[1][pos]
            p2 = planes[2][pos]
            p3 = planes[3][pos]

            for b in range(8):
                px = 0

                px |= p0 & 0x80
                px >>= 1
                px |= p1 & 0x80
                px >>= 1
                px |= p2 & 0x80
                px >>= 1
                px |= p3 & 0x80
                px >>= 4  # move final value to lower 4 bits

                p0 = (p0 << 1) & 0xFF
                p1 = (p1 << 1) & 0xFF
                p2 = (p2 << 1) & 0xFF
                p3 = (p3 << 1) & 0xFF

                fo.append(px)
    return fo


def convert_rgb444_palette_to_rgb888_bytes(rgb444_bytes):
    if len(rgb444_bytes) != 48:
        raise ValueError(
            "Expected 48 bytes for 16-color RGB444 palette (3 bytes per color)."
        )

    palette_bytes = bytearray()

    for i in range(0, len(rgb444_bytes), 3):
        r4 = rgb444_bytes[i]
        g4 = rgb444_bytes[i + 1]
        b4 = rgb444_bytes[i + 2]

        # Convert 4-bit to 8-bit using * 17 (0–15 → 0–255)
        palette_bytes.extend([r4 * 17, g4 * 17, b4 * 17])

    return bytes(palette_bytes)


if __name__ == "__main__":
    main()
