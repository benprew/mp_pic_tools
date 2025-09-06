import struct

"""
Pic98 files are compressed using Bellar's lzss algorithm. This is based off of the
lzexe reproduction https://github.com/mywave82/unlzexe.

See: https://canadianavenger.io/2024/06/26/oops-i-did-it-again/ for details of the
format
"""


class BitStream:
    def __init__(self, file):
        self.fp = file
        self.count = 0x10
        buf = self.fp.read(2)
        if len(buf) < 2:
            raise EOFError("Unexpected EOF while initializing bit buffer")
        self.buf = struct.unpack("<H", buf)[0]

    def getbit(self):
        b = self.buf & 1
        self.count -= 1
        if self.count == 0:
            buf = self.fp.read(2)
            if len(buf) < 2:
                raise EOFError("Unexpected EOF while reloading bit buffer")
            self.buf = struct.unpack("<H", buf)[0]
            self.count = 0x10
        else:
            self.buf >>= 1
        return b


def lzss_decompress(ifile, start_offset=0):
    # Seek to compressed data start
    ifile.seek(start_offset)
    bits = BitStream(ifile)
    data = bytearray(0x4500)
    p = 0
    out = bytearray()

    while True:
        if p > 0x4000:
            out.extend(data[:0x2000])
            data[:0x2500] = data[0x2000:p] + bytearray(0x500)  # Slide
            p -= 0x2000

        if bits.getbit():
            b = ifile.read(1)
            if not b:
                break
            data[p] = b[0]
            p += 1
            continue

        if not bits.getbit():
            len_ = (bits.getbit() << 1) | bits.getbit()
            len_ += 2
            b = ifile.read(1)
            if not b:
                break
            span = b[0] | 0xFF00
        else:
            b1 = ifile.read(1)
            b2 = ifile.read(1)
            if not b1 or not b2:
                break
            span = b1[0]
            len_ = b2[0]
            span |= ((len_ & ~0x07) << 5) | 0xE000
            len_ = (len_ & 0x07) + 2
            if len_ == 2:
                b = ifile.read(1)
                if not b:
                    break
                len_ = b[0]
                if len_ == 0:
                    break  # End of stream
                elif len_ == 1:
                    continue  # Segment change, ignore
                else:
                    len_ += 1

        for _ in range(len_):
            ref = p + int(struct.unpack("<h", struct.pack("<H", span))[0])
            data[p] = data[ref]
            p += 1

    out.extend(data[:p])
    return out


class BitWriter:
    """Bit writer that matches the BitStream reader format"""

    def __init__(self):
        self.data = bytearray()
        self.bit_buffer = 0
        self.bit_count = 0

    def write_bit(self, bit):
        # Pack bits to match the getbit() reader which reads LSB first
        if bit:
            self.bit_buffer |= 1 << self.bit_count
        self.bit_count += 1

        if self.bit_count == 16:
            self.data.extend(struct.pack("<H", self.bit_buffer))
            self.bit_buffer = 0
            self.bit_count = 0

    def write_byte(self, byte):
        self.data.append(byte)

    def finish(self):
        # Always write remaining bits as 16-bit buffer, even if count is 0
        self.data.extend(struct.pack("<H", self.bit_buffer))
        return bytes(self.data)


"""
https://canadianavenger.io/2024/07/02/shoving-the-toothpaste-back-into-the-tube/
https://canadianavenger.io/2024/07/04/sometimes-you-need-a-hammer/
"""


def lzss_compress(data):
    """
    LZSS compressor implementing Sega's Kosinski compression algorithm.
    Uses a greedy approach to match the original behavior.
    """
    if not data:
        return b""

    # Use Kosinski-style descriptor bit packing
    output = bytearray()
    descriptor = 0
    descriptor_bits = 0
    match_buffer = bytearray()

    def flush_descriptor():
        nonlocal descriptor, descriptor_bits
        # Shift descriptor to align bits properly
        descriptor >>= 16 - descriptor_bits
        # Write descriptor as little-endian 16-bit value
        output.extend(struct.pack("<H", descriptor))
        # Write match buffer
        output.extend(match_buffer)
        # Reset for next descriptor
        descriptor = 0
        descriptor_bits = 0
        match_buffer.clear()

    def put_bit(bit):
        nonlocal descriptor, descriptor_bits
        descriptor = (descriptor >> 1) | ((1 if bit else 0) << 15)
        descriptor_bits += 1
        if descriptor_bits == 16:
            flush_descriptor()

    def put_match_byte(byte):
        match_buffer.append(byte)

    pos = 0
    while pos < len(data):
        # Simple single-pass search: find longest match, preferring closer distances
        best_length = 0
        best_distance = 0
        max_len = min(253, len(data) - pos)
        search_end = min(pos, 8192)  # 8K sliding window

        for distance in range(1, search_end + 1):
            length = 0

            # Count matching bytes
            while (
                length < max_len
                and pos + length < len(data)
                and data[pos + length] == data[pos - distance + length]
            ):
                length += 1

            # Update if we found a longer match (closer distance wins ties)
            if length > best_length:
                best_length = length
                best_distance = distance

        # Decide literal vs match
        if best_length < 2 or (best_length == 2 and best_distance >= 256):
            # Output literal
            put_bit(True)
            put_match_byte(data[pos])
            pos += 1
        else:
            # Output match
            put_bit(False)

            if best_length <= 5 and best_distance <= 256:
                # Short form: 4 bits total - 00 + 2 length bits
                put_bit(False)

                # Length in 2 bits (0-3 for lengths 2-5)
                length_code = best_length - 2
                put_bit(bool(length_code & 2))
                put_bit(bool(length_code & 1))

                # Distance byte (negated)
                put_match_byte((-best_distance) & 0xFF)
            else:
                # Long form: 2 bits - 01
                put_bit(True)

                # Limit to 253 like MicroProse implementation
                if best_length > 253:
                    best_length = 253

                neg_distance = (-best_distance) & 0x1FFF
                put_match_byte(neg_distance & 0xFF)

                if best_length <= 9:
                    # Standard long pointer
                    length_code = best_length - 2
                    # From documentation: distance >>= 5, then & 0x00f8, then OR with length
                    high_byte = ((neg_distance >> 5) & 0x00F8) | (length_code & 0x07)
                    put_match_byte(high_byte)
                else:
                    # Long-long pointer
                    high_byte = (neg_distance >> 5) & 0x00F8
                    put_match_byte(high_byte)
                    put_match_byte(best_length - 1)

            pos += best_length

    # Termination
    put_bit(False)
    put_bit(True)
    put_match_byte(0x00)
    put_match_byte(0xF0)
    put_match_byte(0x00)

    # Flush remaining bits
    if descriptor_bits > 0:
        flush_descriptor()

    # Pad to 16-byte boundary like the original compressor
    while len(output) < 16:
        output.append(0x00)

    return bytes(output)
