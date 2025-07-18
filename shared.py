import struct


# Convert a .tr text palette to bytes
def tr2pal(pal_file="TodPal.tr", default_color=(0, 0, 0)) -> bytes:
    """Parse .tr palette files into bytes"""
    pal = [default_color] * 256

    # Open text Palette and fill array
    # format "pal# - val1 val2 val3"
    with open(pal_file, "r") as read_pal:
        for line in read_pal:
            line = line.replace("-", " ")
            temp = line.strip().split()
            pal_num = int(temp[0])
            rgb = temp[1:4]
            pal[pal_num] = [int(x) for x in rgb]

    pal[254] = (255, 255, 255)  # Set the last color to black

    # Convert the list of lists to a bytes object
    byte_data = b"".join(struct.pack("<BBB", *pal[i]) for i in range(256))
    return byte_data


def pal2tpal(pal: bytes) -> list[tuple[int, int, int]]:
    """Convert a bytes pal to a list of tuples pal"""
    return [struct.unpack("<BBB", pal[i : i + 3]) for i in range(0, len(pal), 3)]


def pal_to_bytes(pal: list[tuple[int, int, int]]) -> bytes:
    return b"".join([struct.pack("<BBB", p) for p in pal])


def pic_version_help_message():
    return """
    The version of the PIC file (3 or 98). Defaults to 3.

    ### Version 3 -
    Darklands,
    F14 Fleet Defender,
    F-15 Strike Eagle III,
    Hyperspeed,
    Knights of the Sky,
    Lightspeed,
    Magic: The Gathering Shandalar,
    Sid Meier’s Civilization

    ### Version 98 -
    Sid Meier’s Civilization (PC-98),
    Sid Meier’s Railroad Tycoon (PC-98),
    Sid Meier’s Railroad Tycoon Deluxe

    ### Details: https://canadianavenger.io/2024/09/17/pic-as-we-know-it/
    """
