import struct


# Convert a .tr text palette to bytes
def tr2pal(pal_file="TodPal.tr") -> bytes:
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

    # Convert the list of lists to a bytes object
    byte_data = b"".join(struct.pack("<BBB", *pal[i]) for i in range(256))
    return byte_data


def pal_to_bytes(pal: list[tuple[int, int, int]]) -> bytes:
    return b"".join([struct.pack("<BBB", p) for p in pal])
