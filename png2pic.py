#!/usr/bin/env python3

from PIL import Image
import argparse
import logging
import struct
import os

from pic_headers import (
    PicV3BlockHeader,
    PicV3Image,
    PicV3Palette,
    Pic98BlockHeader,
    pic98_header_format,
    Pic98PlaneBlock,
    pic98_plane_block_format,
)
import rle
import lzw
from shared import tr2pal
from bellard_lzss4 import lzss_compress


def main():
    parser = argparse.ArgumentParser(description="Convert PNG files to PIC files")
    parser.add_argument("file", help="The PNG file to convert.")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose mode."
    )
    parser.add_argument(
        "-p", "--palette", help="The palette file to match the image to.", required=True
    )
    parser.add_argument(
        "--pic-version",
        choices=["3", "98"],
        default="3",
        help="PIC version to create: 3 for PICv3, 98 for Pic98",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    img, width, height, bytes_orig = parse_image(args.file)
    quantized_img = convert_image_to_palette(img, args.palette)
    bytes_quantized = quantized_img.tobytes()

    if args.pic_version == "3":
        pic = make_picv3(width, height, bytes_quantized)
        ext = ".pic"
    elif args.pic_version == "98":
        pic = make_pic98(width, height, bytes_quantized, args.palette)
        ext = ".pic"

    out = f"{os.path.basename(args.file)}{ext}"
    with open(out, "wb") as f:
        print(f"writing pic to {out}")
        f.write(pic)


def convert_image_to_palette(image: Image.Image, palette_filename: str) -> Image.Image:
    """Convert an image to a palette using a specified palette file."""
    # Check if it's a binary palette file (.pal) or text palette file (.tr)
    if palette_filename.endswith(".pal"):
        with open(palette_filename, "rb") as f:
            palette = f.read()
    else:
        palette = tr2pal(palette_filename)

    palette_image = Image.new("P", (16, 16))
    palette_image.putpalette(palette)

    # Convert the image to RGB mode before quantizing
    rgb_image = image.convert("RGB")

    # Convert using fixed palette
    return rgb_image.quantize(palette=palette_image, dither=Image.FLOYDSTEINBERG)


def parse_image(filename: str) -> tuple[Image.Image, int, int, bytes]:
    """Parse an image file and return image data and metadata."""
    img = Image.open(filename)
    width, height = img.size
    bytes_data = img.tobytes()
    print("len bytes:", len(bytes_data))
    return img, width, height, bytes_data


def make_picv3(width: int, height: int, bytes: bytes) -> bytearray:
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


def make_pic98(
    width: int, height: int, pixel_data: bytes, palette_file: str
) -> bytearray:
    """Create a Pic98 file from image data"""

    # Load palette and convert to RGB444 format
    if palette_file.endswith(".pal"):
        with open(palette_file, "rb") as f:
            palette_rgb888 = f.read()
    else:
        palette_rgb888 = tr2pal(palette_file)
    palette_rgb444 = convert_rgb888_to_rgb444_bytes(palette_rgb888)

    # Create pic98 header
    sig = b"\x00H8\x00"
    header = Pic98BlockHeader(sig, width, height, palette_rgb444)

    # Separate pixel data into 4 planes
    planes = separate_into_planes(width, height, pixel_data)

    # Debug: print plane sizes before compression
    for i, plane in enumerate(planes):
        print(f"Plane {i}: {len(plane)} bytes")

    # For now, use a working solution: if our plane data exactly matches the
    # decompressed data from tlogo.pic, use its compressed data directly.
    # This is a pragmatic solution while a proper LZSS implementation is developed.
    compressed_planes = []

    for i, plane in enumerate(planes):
        with open(f"plane_{i}", "wb") as f:
            f.write(plane)
        compressed_plane = lzss_compress(plane)
        compressed_planes.append(compressed_plane)
        print(
            f"Plane {i}: {len(plane)} bytes -> {len(compressed_plane)} bytes (literal LZSS)"
        )

    # Build the pic98 file
    pic98_data = bytearray()

    # Write header
    pic98_data.extend(struct.pack(pic98_header_format, *header))

    # Write compressed plane data
    for compressed_plane in compressed_planes:
        # Write plane block header (length)
        pic98_data.extend(struct.pack(pic98_plane_block_format, len(compressed_plane)))
        # Write compressed data
        pic98_data.extend(compressed_plane)

        # Align on 16-bit boundary if needed
        if len(pic98_data) % 2 == 1:
            pic98_data.append(0)

    return pic98_data


def convert_rgb888_to_rgb444_bytes(rgb888_palette: bytes) -> bytes:
    """Convert RGB888 palette to RGB444 format (16 colors * 3 bytes = 48 bytes)"""
    if len(rgb888_palette) < 48:  # Need at least 16 colors
        raise ValueError("Palette must have at least 16 colors")

    rgb444_bytes = bytearray()

    # Convert first 16 colors from 8-bit to 4-bit
    for i in range(0, 48, 3):  # 16 colors * 3 bytes each
        r8 = rgb888_palette[i]
        g8 = rgb888_palette[i + 1]
        b8 = rgb888_palette[i + 2]

        # Convert 8-bit to 4-bit by dividing by 17 (0-255 → 0-15)
        r4 = r8 // 17
        g4 = g8 // 17
        b4 = b8 // 17

        rgb444_bytes.extend([r4, g4, b4])

    return bytes(rgb444_bytes)


# TODO: I don't think this works
def separate_into_planes(width: int, height: int, pixel_data: bytes) -> list:
    """Separate 4-bit pixel data into 4 bit planes (reverse of combine_planes)"""
    planes = [bytearray(), bytearray(), bytearray(), bytearray()]

    for y in range(height):
        for x in range(width // 8):  # 8 pixels per byte
            # Initialize plane bytes for this position
            plane_bytes = [0, 0, 0, 0]

            # Process 8 pixels
            for b in range(8):
                pixel_idx = (y * width) + (x * 8) + b
                if pixel_idx < len(pixel_data):
                    pixel = pixel_data[pixel_idx] & 0x0F  # 4-bit pixel value

                    # Extract each bit and place in corresponding plane
                    # Note: bit extraction order matches the combine_planes logic
                    bit_pos = 7 - b  # MSB first
                    plane_bytes[0] |= ((pixel & 0x01) >> 0) << bit_pos  # LSB -> plane 0
                    plane_bytes[1] |= ((pixel & 0x02) >> 1) << bit_pos
                    plane_bytes[2] |= ((pixel & 0x04) >> 2) << bit_pos
                    plane_bytes[3] |= ((pixel & 0x08) >> 3) << bit_pos  # MSB -> plane 3

            # Add bytes to each plane
            for i in range(4):
                planes[i].append(plane_bytes[i])

    return [bytes(plane) for plane in planes]


if __name__ == "__main__":
    main()
