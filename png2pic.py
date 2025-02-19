#!/usr/bin/env python3

from PIL import Image
import argparse
import logging
import struct
import os

from pic_headers import PicV3BlockHeader, PicV3Image, PicV3Palette
import rle
import lzw


def main():
    parser = argparse.ArgumentParser(description="Convert PNG files to PICv3 files")
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

    width, height, bytes, pal = parse_image(args.file)
    pic = make_pic(width, height, bytes, pal)
    out = f"{os.path.basename(args.file)}.pic"
    with open(out, "wb") as f:
        print(f"writing pic to {out}")
        f.write(pic)


def parse_image(filename: str) -> tuple[int, int, bytes, list[tuple]]:
    img = Image.open(filename)
    width, height = img.size
    bytes = img.tobytes()
    pal = img.palette
    if pal is None:
        raise ValueError("Image does not have a palette")
    pal_lst = pal.getdata()[1]  # get the palette data
    rgb_palette = [
        (pal_lst[i], pal_lst[i + 1], pal_lst[i + 2]) for i in range(0, len(pal_lst), 3)
    ]
    return width, height, bytes, rgb_palette


def make_pic(width: int, height: int, bytes: bytes, pal: list[tuple]) -> bytearray:
    """Write a PICv3 file"""

    pic = bytearray()
    pal_block = bytearray()
    img_block = bytearray()

    # write palette
    pal_header = PicV3Palette(0, len(pal) - 1)
    pal_block.extend(struct.pack("<BB", *pal_header))
    pal_block.extend(b"".join([struct.pack("<BBB", *p) for p in pal]))
    pic_header = PicV3BlockHeader(b"M0", len(pal_block))
    pic.extend(struct.pack("<2sH", *pic_header))
    pic.extend(pal_block)

    # write image
    mode = 11
    img_header = PicV3Image(width, height, mode)
    img_block.extend(struct.pack("<HHB", *img_header))
    # print(bytes, len(bytes))
    # print(width, height)
    rle_bytes = rle.encode(bytes)
    # print(rle_bytes)
    # print("rle_bytes", len(rle_bytes))
    img_compressed = lzw.compress(rle_bytes, mode)
    img_block.extend(struct.pack("<" + ("B" * len(img_compressed)), *img_compressed))
    # print(len(img_compressed))
    # Some files (0028.pic) are larger than uint8, so we write the overflowed value
    pic_header = PicV3BlockHeader(b"X1", len(img_block) % 2**16)
    pic.extend(struct.pack("<2sH", *pic_header))
    pic.extend(img_block)

    return pic


if __name__ == "__main__":
    main()
