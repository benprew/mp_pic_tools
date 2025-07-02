#!/usr/bin/env python3

from PIL import Image
import argparse
import logging
import struct
import os

from pic_headers import PicV3BlockHeader, PicV3Image, PicV3Palette
import rle
import lzw
from shared import tr2pal


def main():
    parser = argparse.ArgumentParser(description="Convert PNG files to PICv3 files")
    parser.add_argument("file", help="The PIC file to convert.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode."
    )
    parser.add_argument(
        "-p", "--palette", help="The palette file to match the image to.", required=True
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    img, width, height, bytes_orig, pal = parse_image(args.file)
    quantized_img = convert_image_to_palette(img, args.palette)
    bytes_quantized = quantized_img.tobytes()
    pic = make_pic(width, height, bytes_quantized)
    out = f"{os.path.basename(args.file)}.pic"
    with open(out, "wb") as f:
        print(f"writing pic to {out}")
        f.write(pic)


def convert_image_to_palette(
    image: Image.Image, palette_filename: bytes
) -> Image.Image:
    """Convert an image to a palette using a specified palette file."""
    palette = tr2pal(palette_filename)

    palette_image = Image.new("P", (16, 16))
    palette_image.putpalette(palette)

    # Convert the image to RGB mode before quantizing
    rgb_image = image.convert("RGB")

    # Convert using fixed palette
    return rgb_image.quantize(palette=palette_image, dither=Image.FLOYDSTEINBERG)


def parse_image(filename: str) -> tuple[Image.Image, int, int, bytes, list[tuple]]:
    """Parse an image file and return image data and metadata."""
    img = Image.open(filename)
    width, height = img.size
    bytes_data = img.tobytes()
    print("len bytes:", len(bytes_data))
    pal = img.palette
    if pal is None:
        raise ValueError("Image does not have a palette")
    pal_lst = pal.getdata()[1]  # get the palette data
    rgb_palette = [
        (pal_lst[i], pal_lst[i + 1], pal_lst[i + 2]) for i in range(0, len(pal_lst), 3)
    ]
    return img, width, height, bytes_data, rgb_palette


def make_pic(width: int, height: int, bytes: bytes) -> bytearray:
    """Write a PICv3 file"""

    pic = bytearray()
    img_block = bytearray()

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
    pic_header = PicV3BlockHeader(b"X0", len(img_block) % 2**16)
    pic.extend(struct.pack("<2sH", *pic_header))
    pic.extend(img_block)

    return pic


if __name__ == "__main__":
    main()
