from typing import List, Tuple
import struct
from PIL import Image

import sys


def parse_spr(data: bytes, palette: List[Tuple[int, int, int]]) -> List[Image.Image]:
    """
    Parse SPR file format and return a list of PIL Images.

    Args:
        data: Bytes object containing the SPR file data
        palette: List of RGB tuples representing the color palette

    Returns:
        List of PIL Images extracted from the SPR file
    """
    offset = 0
    bitmaps = []

    while offset < len(data):
        # Read image data size (4 bytes)
        image_size = struct.unpack("<I", data[offset : offset + 4])[0]
        if image_size == 0xFFFFFFFF:
            break
        offset += 4

        # Read width and height (2 bytes each)
        width = struct.unpack("<H", data[offset : offset + 2])[0]
        height = struct.unpack("<H", data[offset + 2 : offset + 4])[0]
        offset += 4

        # Skip unknown values (2 bytes each)
        offset += 4

        # Read empty lines above and cutoff Y offset (2 bytes each)
        empty_lines_above = struct.unpack("<H", data[offset : offset + 2])[0]
        cutoff_y_offset = struct.unpack("<H", data[offset + 2 : offset + 4])[0]
        offset += 4

        # Create new RGBA image
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = image.load()

        # Process each row
        y = empty_lines_above
        while y < height:
            if y < cutoff_y_offset:
                # Skip transparent rows
                y += 1
                continue

            # Read number of transparent pixels at start of row
            transparent_pixels_amount = data[offset]
            offset += 1

            x = transparent_pixels_amount

            # Read unknown3 byte that affects pixel count
            unknown3 = data[offset]
            offset += 1

            # Determine number of pixels to read
            if unknown3 in (0xFE, 0xFF):
                pixels_to_read = data[offset]
                offset += 1
            else:
                pixels_to_read = unknown3

            # Read and set pixels for this row
            for i in range(pixels_to_read):
                if x >= width:
                    break

                color_index = data[offset]
                offset += 1

                if color_index < len(palette):
                    color = palette[color_index]
                    pixels[x, y] = (color[0], color[1], color[2], 255)  # Set RGBA

                x += 1

            y += 1

        bitmaps.append(image)

        # Move offset to end of current image data
        offset = (offset + 3) & ~3  # Align to 4-byte boundary

    return bitmaps


# Example usage:
def example_usage():
    # Example palette and data from the description
    palette = [
        (255, 0, 0),  # Red
        (0, 255, 0),  # Green
        (0, 0, 255),  # Blue
        (255, 255, 0),  # Yellow
    ]

    # Convert example data to bytes
    data = bytes(
        [
            0x24,
            0x00,
            0x00,
            0x00,  # Image size (36 bytes)
            0x04,
            0x00,
            0x04,
            0x00,  # Width = 4, Height = 4
            0x00,
            0x00,
            0x00,
            0x00,  # Unknown values
            0x00,
            0x00,  # Empty lines above = 0
            0x02,
            0x00,  # Cutoff offset = 2
            0xFF,  # Transparent pixel markers for row 1
            0x02,
            0xFF,  # Transparent pixels count for row 2
            0x01,
            0xFF,  # Transparent pixels count for row 3
            0x00,
            0xFF,  # No transparent pixels for row 4
            0x00,
            0x01,
            0x02,
            0x03,  # Palette indices for row 4
        ]
    )

    # Parse the SPR data
    images = parse_spr(data, palette)

    # Save the first image as PNG for testing
    if images:
        images[0].save("output.png")


if __name__ == "__main__":
    spr_file = sys.argv[1]
    with open(spr_file, "rb") as f:
        data = f.read()
    palette_file = sys.argv[2]
    with open(palette_file, "rb") as f:
        pal_bytes = f.read()
    palette = list(struct.iter_unpack("BBB", pal_bytes))
    images = parse_spr(data, palette)
    for i, image in enumerate(images):
        image.save(f"output_{i}.png")
