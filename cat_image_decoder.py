#!/usr/bin/env python3
"""
CAT Image Decoder - Python implementation
Decodes Shandalar CAT image files to PNG format.

Usage: python cat_image_decoder.py <cat_file> [output_file]
"""

import sys
import struct
import argparse
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np
from vlc_fast import vlc_decompress


# class VLCDecoder:
#     """Variable Length Code decoder for CAT image data."""
#
#     def __init__(self):
#         self.bits_left = 0
#         self.bitstream = b""
#         self.bitstream_start = 0
#         self.bitstream_ptr = 0
#         self.bitstream_limit = 0
#         self.bits_dword = 0
#         self.bits_dword_mask = [0xFFFFFFFF >> i for i in range(32)]
#
#         # Lookup tables
#         self.tab1 = []
#         self.tab2 = [{"field_0": 0, "field_1": 0, "field_2": 0} for _ in range(256)]
#         self.saved_index_tab = []
#         self.saved_index_count = 0
#
#     def get_bits(self, bits: int) -> int:
#         """Extract specified number of bits from bitstream."""
#         if bits <= self.bits_left:
#             value = self.bits_dword & self.bits_dword_mask[32 - bits]
#             self.bits_dword >>= bits
#             self.bits_left -= bits
#             return value
#         else:
#             value = self.bits_dword
#             bits -= self.bits_left
#             bytes_left = self.bitstream_ptr - self.bitstream_start + 4
#
#             if bytes_left < self.bitstream_limit:
#                 if self.bitstream_ptr + 4 <= len(self.bitstream):
#                     self.bits_dword = struct.unpack(
#                         "<I",
#                         self.bitstream[self.bitstream_ptr : self.bitstream_ptr + 4],
#                     )[0]
#                     self.bitstream_ptr += 4
#
#                     value |= (
#                         self.bits_dword & self.bits_dword_mask[32 - bits]
#                     ) << self.bits_left
#                     self.bits_dword >>= bits
#                     self.bits_left = 32 - bits
#
#                     return value
#             return -1
#
#     def get_next_bit(self) -> int:
#         """Get next single bit from bitstream."""
#         if self.bits_left == 0:
#             if (self.bitstream_start - self.bitstream_ptr) < self.bitstream_limit:
#                 bytes_left = self.bitstream_limit - (
#                     self.bitstream_ptr - self.bitstream_start
#                 )
#                 if bytes_left < 4:
#                     self.bits_dword = 0
#                     for i in range(
#                         min(bytes_left, len(self.bitstream) - self.bitstream_ptr)
#                     ):
#                         self.bits_dword += self.bitstream[self.bitstream_ptr + i] << (
#                             i * 8
#                         )
#                     self.bitstream_ptr += bytes_left
#                 else:
#                     if self.bitstream_ptr + 4 <= len(self.bitstream):
#                         self.bits_dword = struct.unpack(
#                             "<I",
#                             self.bitstream[self.bitstream_ptr : self.bitstream_ptr + 4],
#                         )[0]
#                         self.bitstream_ptr += 4
#                 self.bits_left = 32
#             else:
#                 return -1
#
#         bit_out = 1 if (self.bits_dword & 1) != 0 else 0
#         self.bits_dword >>= 1
#         self.bits_left -= 1
#         return bit_out
#
#     def generate_tab2(self, count: int):
#         """Generate lookup table 2."""
#         powers_of_two = [1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400]
#         var_ec = [1] * 32
#         var_6c = 0
#         var_8 = count - 1
#         var_38 = [var_8] + [0] * 99
#
#         while var_ec[0] >= 0:
#             var_fc = var_6c
#             var_6c += 1
#
#             if var_ec[var_fc] != 0:
#                 var_4 = self.tab1[var_8]["field_0"]
#             else:
#                 var_4 = self.tab1[var_8]["field_1"]
#
#             var_8 = var_4 - self.saved_index_count
#             var_38[var_6c] = var_8
#
#             if var_8 >= 0:
#                 if var_6c == 8:
#                     var_c = 0
#                     for var_f8 in range(var_6c):
#                         var_c |= var_ec[var_f8] << var_f8
#
#                     self.tab2[var_c] = {
#                         "field_0": 2147483647,  # int.MaxValue
#                         "field_1": var_6c,
#                         "field_2": var_8,
#                     }
#
#                     var_ec[var_6c] = 1
#                     var_6c -= 1
#                     var_ec[var_6c] -= 1
#                     var_8 = var_38[var_6c]
#                 else:
#                     continue
#             else:
#                 var_c = 0
#                 for var_f0 in range(var_6c):
#                     var_c |= var_ec[var_f0] << var_f0
#
#                 for i in range(powers_of_two[8 - var_6c]):
#                     var_f4 = i << var_6c
#                     self.tab2[var_f4 | var_c] = {
#                         "field_0": self.saved_index_tab[var_4],
#                         "field_1": var_6c,
#                         "field_2": -1,
#                     }
#
#                 var_ec[var_6c] = 1
#                 var_6c -= 1
#                 var_ec[var_6c] -= 1
#                 var_8 = var_38[var_6c]
#
#             while var_ec[0] >= 0:
#                 if var_ec[var_6c] < 0:
#                     var_ec[var_6c] = 1
#                     var_6c -= 1
#                     var_ec[var_6c] -= 1
#                     var_8 = var_38[var_6c]
#                 else:
#                     break
#
#     def generate_tables(
#         self, data: bytes, data_offset: int, index_tab: List[int], index_count: int
#     ) -> int:
#         """Generate VLC lookup tables."""
#         self.bitstream = data
#         self.bitstream_start = self.bitstream_ptr = data_offset
#         self.bitstream_limit = 100000
#         self.bits_dword = 0
#         self.bits_left = 0
#
#         tab1_count = self.get_bits(13)
#         bits_processed = 13
#
#         self.tab1 = []
#         for i in range(tab1_count):
#             field_0 = self.get_bits(13)
#             field_1 = self.get_bits(13)
#             self.tab1.append({"field_0": field_0, "field_1": field_1})
#             bits_processed += 26
#
#         self.saved_index_count = index_count
#         self.saved_index_tab = index_tab
#
#         self.generate_tab2(tab1_count)
#
#         return (bits_processed + 7) // 8
#
#     def decompress_chunk(
#         self, data: bytes, data_offset: int, data_size: int
#     ) -> bytearray:
#         """Decompress a single chunk of VLC data."""
#         result = bytearray()
#         self.bitstream = data
#         self.bitstream_ptr = data_offset
#         self.bitstream_start = data_offset
#         self.bitstream_limit = data_size
#
#         if (data_offset & 3) != 0:
#             unaligned_bytes = 4 - (data_offset & 3)
#             self.bits_left = unaligned_bytes * 8
#             mask = 0xFFFFFFFF >> (32 - self.bits_left)
#             if data_offset + 4 <= len(data):
#                 self.bits_dword = (
#                     struct.unpack("<I", data[data_offset : data_offset + 4])[0] & mask
#                 )
#             self.bitstream_ptr += unaligned_bytes
#         else:
#             self.bits_left = 0
#             self.bits_dword = 0
#
#         var_c = self.get_bits(8)
#
#         while var_c != -1:
#             if self.tab2[var_c]["field_0"] == 2147483647:  # int.MaxValue
#                 var_14 = self.tab2[var_c]["field_2"]
#
#                 while True:
#                     var_18 = self.get_next_bit()
#                     if var_18 == -1:
#                         break
#
#                     if var_18 != 0:
#                         var_10 = self.tab1[var_14]["field_0"]
#                     else:
#                         var_10 = self.tab1[var_14]["field_1"]
#
#                     var_14 = var_10 - self.saved_index_count
#                     if var_14 < 0:
#                         break
#
#                 if var_10 != 0:
#                     # Set as SavedIndex
#                     value = self.saved_index_tab[var_10]
#                     result.extend(struct.pack("<I", value))
#                 else:
#                     # Clear
#                     zeroes = self.get_bits(10)
#                     if zeroes >= 0:
#                         result.extend(b"\x00" * (zeroes * 4))
#
#                 var_c = self.get_bits(8)
#             else:
#                 var_24 = self.tab2[var_c]["field_1"]
#
#                 if self.tab2[var_c]["field_0"] == -2147483648:  # int.MinValue
#                     var_28 = self.get_bits(var_24 + 2)
#                     if var_28 < 0:
#                         break
#
#                     var_28 = (var_28 << (8 - var_24)) | (var_c >> var_24)
#                     result.extend(b"\x00" * (var_28 * 4))
#                     var_c = self.get_bits(8)
#                 else:
#                     # Set as field_0
#                     value = self.tab2[var_c]["field_0"]
#                     result.extend(struct.pack("<I", value))
#
#                     var_c >>= var_24
#                     var_20 = self.get_bits(var_24)
#                     if var_20 == -1:
#                         break
#
#                     var_c |= var_20 << (8 - var_24)
#
#         return result
#
#     def decompress(self, src_bytes: bytes) -> bytes:
#         """Main VLC decompression function."""
#         decompressed_size = struct.unpack("<I", src_bytes[0x90:0x94])[0] + 20000
#         result = bytearray(decompressed_size)
#
#         # Block 1
#         ecx = struct.unpack("<I", src_bytes[0x28:0x2C])[0] - 1
#         ecx = 1 if ecx == 0 else 2
#
#         width = struct.unpack("<I", src_bytes[0x1C:0x20])[0]
#         var_30 = width // ecx
#         var_2c = var_30
#
#         # Block 2
#         ecx = 1 if struct.unpack("<I", src_bytes[0:4])[0] == 0 else 2
#         var_18 = var_2c // ecx
#         var_10 = var_18
#
#         data_ptr = src_bytes[0x9C:]  # Skip header
#         small_table_size = struct.unpack("<I", src_bytes[0x24:0x28])[0]
#
#         eax = var_18 * var_10
#         ecx = var_30 * var_2c
#         var_c = ecx + 2 * eax
#
#         # Step 1
#         data_offset = 0
#         big_index_count = struct.unpack("<I", data_ptr[data_offset : data_offset + 4])[
#             0
#         ]
#         data_offset += 4
#
#         big_index_tab = []
#         for i in range(big_index_count):
#             if data_offset + 4 <= len(data_ptr):
#                 val = struct.unpack("<I", data_ptr[data_offset : data_offset + 4])[0]
#                 big_index_tab.append(val)
#                 data_offset += 4
#
#         big_index_tab[0] = -2147483648  # int.MinValue
#
#         data_offset += self.generate_tables(
#             data_ptr, data_offset, big_index_tab, big_index_count
#         )
#
#         # Process pieces
#         piece_count = struct.unpack("<I", src_bytes[0x28:0x2C])[0]
#
#         for piece_num in range(piece_count):
#             table_size = small_table_size * small_table_size * 4
#             var_24_offset = (var_c + 0x40) * piece_num * 4
#             var_38_offset = var_24_offset + var_30 * var_2c * 4 + 0x80
#             var_34_offset = var_38_offset + var_18 * var_10 * 4 + 0x80
#
#             # Small index table + data 1
#             if data_offset + table_size <= len(data_ptr):
#                 result[var_24_offset : var_24_offset + table_size] = data_ptr[
#                     data_offset : data_offset + table_size
#                 ]
#                 var_24_offset += table_size
#                 data_offset += table_size
#
#             size = struct.unpack(
#                 "<I", src_bytes[piece_num * 4 + 0x5C : piece_num * 4 + 0x60]
#             )[0]
#             chunk_data = self.decompress_chunk(data_ptr, data_offset, size)
#             result[var_24_offset : var_24_offset + len(chunk_data)] = chunk_data
#             data_offset += size
#
#             # Small index table + data 2
#             if data_offset + table_size <= len(data_ptr):
#                 result[var_38_offset : var_38_offset + table_size] = data_ptr[
#                     data_offset : data_offset + table_size
#                 ]
#                 var_38_offset += table_size
#                 data_offset += table_size
#
#             size = struct.unpack(
#                 "<I", src_bytes[piece_num * 4 + 0x6C : piece_num * 4 + 0x70]
#             )[0]
#             chunk_data = self.decompress_chunk(data_ptr, data_offset, size)
#             result[var_38_offset : var_38_offset + len(chunk_data)] = chunk_data
#             data_offset += size
#
#             # Small index table + data 3
#             if data_offset + table_size <= len(data_ptr):
#                 result[var_34_offset : var_34_offset + table_size] = data_ptr[
#                     data_offset : data_offset + table_size
#                 ]
#                 var_34_offset += table_size
#                 data_offset += table_size
#
#             size = struct.unpack(
#                 "<I", src_bytes[piece_num * 4 + 0x7C : piece_num * 4 + 0x80]
#             )[0]
#             chunk_data = self.decompress_chunk(data_ptr, data_offset, size)
#             result[var_34_offset : var_34_offset + len(chunk_data)] = chunk_data
#             data_offset += size
#
#         return bytes(result)


class WaveletDecoder:
    """Wavelet decoder for CAT image data."""

    def __init__(self):
        self.wavelet_buffer_1 = None
        self.wavelet_buffer_2 = None
        self.saved_data = None

    def wavelet_decode_sub7(
        self,
        tab1: int,
        tab2: int,
        tmp: np.ndarray,
        tmp_index: int,
        arg_c: int,
        arg_10: int,
        arg_18: int,
    ):
        """Wavelet decode subroutine 7."""
        for i in range(arg_10):
            var_c = tab1
            var_10 = tab1 + arg_c
            var_8 = tmp_index + arg_18 * 2
            tab1 += 1

            while tab1 < var_10:
                tmp[var_8] = self.saved_data[tab1] + self.saved_data[tab2]
                tmp[var_8 + arg_18] = self.saved_data[tab1] - self.saved_data[tab2]
                tab1 += 1
                tab2 += 1
                var_8 += arg_18 * 2

            tmp[tmp_index] = self.saved_data[var_c] + self.saved_data[tab2]
            tmp[tmp_index + arg_18] = self.saved_data[var_c] - self.saved_data[tab2]

            tmp_index += 1
            tab2 += 1

    def wavelet_decode_sub8(
        self,
        buf1: np.ndarray,
        buf2: np.ndarray,
        buf1_index: int,
        buf2_index: int,
        out_tab: int,
        arg_c: int,
        arg_10: int,
        arg_18: int,
    ):
        """Wavelet decode subroutine 8."""
        temp_buf1_index = buf1_index
        temp_buf2_index = buf2_index

        for i in range(arg_10):
            var_c = temp_buf1_index
            var_10 = temp_buf1_index + arg_c
            var_8 = out_tab + arg_18 * 2
            temp_buf1_index += 1

            while temp_buf1_index < var_10:
                self.saved_data[var_8] = (
                    buf1[temp_buf1_index] + buf2[temp_buf2_index]
                ) // 2
                self.saved_data[var_8 + arg_18] = (
                    buf1[temp_buf1_index] - buf2[temp_buf2_index]
                ) // 2

                temp_buf1_index += 1
                temp_buf2_index += 1
                var_8 += arg_18 * 2

            self.saved_data[out_tab] = (buf1[var_c] + buf2[temp_buf2_index]) // 2
            self.saved_data[out_tab + arg_18] = (
                buf1[var_c] - buf2[temp_buf2_index]
            ) // 2

            out_tab += 1
            temp_buf2_index += 1

    def wavelet_decode(self, data: np.ndarray, ctab: int, width: int, tab_size: int):
        """Main wavelet decode function."""
        self.saved_data = data

        if self.wavelet_buffer_1 is None:
            self.wavelet_buffer_1 = np.zeros(0x10000, dtype=np.int32)
            self.wavelet_buffer_2 = np.zeros(0x10000, dtype=np.int32)

        size = tab_size

        while size < width:
            self.wavelet_decode_sub7(
                ctab, size * size + ctab, self.wavelet_buffer_1, 0, size, size, size
            )

            self.wavelet_decode_sub7(
                size * size * 2 + ctab,
                size * size * 3 + ctab,
                self.wavelet_buffer_2,
                0,
                size,
                size,
                size,
            )

            self.wavelet_decode_sub8(
                self.wavelet_buffer_1,
                self.wavelet_buffer_2,
                0,
                0,
                ctab,
                size,
                2 * size,
                2 * size,
            )

            size *= 2


class CATImageDecoder:
    """Main CAT image decoder class."""

    def __init__(self):
        # self.vlc_decoder = VLCDecoder()
        self.wavelet_decoder = WaveletDecoder()
        self.ycbcr_tab = None
        self.ycbcr_tab_ptr = 0x400

    def bytes_to_int_array(self, buf: bytes, start_offset: int) -> np.ndarray:
        """Convert byte array to int32 array."""
        if start_offset >= len(buf):
            return np.array([], dtype=np.int32)

        remaining_bytes = len(buf) - start_offset
        int_count = remaining_bytes // 4

        if int_count == 0:
            return np.array([], dtype=np.int32)

        # Ensure we don't read past the buffer
        end_offset = start_offset + (int_count * 4)
        data = buf[start_offset:end_offset]

        # Convert to int32 array (little endian)
        int_array = np.frombuffer(data, dtype="<i4")
        return int_array.copy()

    def prepare_ycbcr_table(self):
        """Prepare YCbCr to RGB conversion table."""
        if self.ycbcr_tab is None:
            self.ycbcr_tab = np.zeros(0x400 + 0x1C00, dtype=np.uint8)

            for i in range(-0x400, 0x1C00):
                if i > 0:
                    eax = i >> 2
                    if eax >= 0xFF:
                        eax = 0xFF
                    self.ycbcr_tab[i + self.ycbcr_tab_ptr] = eax
                else:
                    self.ycbcr_tab[i + self.ycbcr_tab_ptr] = 0

    def ycbcr_to_rgb(
        self,
        data: np.ndarray,
        y_tab: int,
        width: int,
        height: int,
        cb_tab: int,
        cr_tab: int,
        derived_width: int,
        derived_height: int,
    ) -> Image.Image:
        """Convert YCbCr data to RGB image."""
        self.prepare_ycbcr_table()

        # Create RGB array
        rgb_array = np.zeros((height, width, 3), dtype=np.uint8)

        for y in range(height):
            if derived_height != 0:
                cb_ptr = cb_tab + (y // 2) * derived_width
                cr_ptr = cr_tab + (y // 2) * derived_width
            else:
                cb_ptr = cb_tab + y * derived_width
                cr_ptr = cr_tab + y * derived_width

            for x in range(width):
                if y_tab + y * width + x >= len(data):
                    continue

                y_val = data[y_tab + y * width + x]

                # Get Cb and Cr values
                if derived_height != 0:
                    if (x & 1) != 0:  # Interpolate
                        eax = width - x - 1
                        eax = -1 if eax == 0 else 0
                        if cb_ptr + eax + 1 < len(data) and cb_ptr < len(data):
                            cb_val = (data[cb_ptr] + data[cb_ptr + eax + 1]) // 2
                        else:
                            cb_val = data[cb_ptr] if cb_ptr < len(data) else 0

                        if cr_ptr + eax + 1 < len(data) and cr_ptr < len(data):
                            cr_val = (data[cr_ptr] + data[cr_ptr + eax + 1]) // 2
                        else:
                            cr_val = data[cr_ptr] if cr_ptr < len(data) else 0
                    else:
                        cb_val = data[cb_ptr] if cb_ptr < len(data) else 0
                        cr_val = data[cr_ptr] if cr_ptr < len(data) else 0
                else:
                    cb_val = data[cb_ptr] if cb_ptr < len(data) else 0
                    cr_val = data[cr_ptr] if cr_ptr < len(data) else 0

                # Convert to RGB
                r = y_val + cr_val + cr_val // 2 + cr_val // 8 - 0x333
                b = y_val + cb_val * 2 - 0x400
                g = y_val * 2 - y_val // 4 - r // 2 - b // 4 - b // 16

                # Clamp and apply lookup table
                r_idx = max(0, min(len(self.ycbcr_tab) - 1, r + self.ycbcr_tab_ptr))
                g_idx = max(0, min(len(self.ycbcr_tab) - 1, g + self.ycbcr_tab_ptr))
                b_idx = max(0, min(len(self.ycbcr_tab) - 1, b + self.ycbcr_tab_ptr))

                rgb_array[y, x, 0] = self.ycbcr_tab[r_idx]
                rgb_array[y, x, 1] = self.ycbcr_tab[g_idx]
                rgb_array[y, x, 2] = self.ycbcr_tab[b_idx]

                # Advance pointers
                if derived_height != 0:
                    if (x & 1) != 0:
                        cb_ptr += 1
                        cr_ptr += 1
                else:
                    cb_ptr += 1
                    cr_ptr += 1

        return Image.fromarray(rgb_array, "RGB")

    def decode_cat_image(self, asset_data: bytes) -> Image.Image:
        """Main function to decode CAT image data."""
        # Decompress data
        uncompressed_data = vlc_decompress(asset_data)
        print(f"decoded size: {len(uncompressed_data)}")

        # Extract header information
        width = struct.unpack("<I", asset_data[0x1C:0x20])[0]
        height = struct.unpack("<I", asset_data[0x20:0x24])[0]
        small_table_size = struct.unpack("<I", asset_data[0x24:0x28])[0]

        # Determine new dimensions
        if struct.unpack("<I", asset_data[0:4])[0] != 0:
            half_size = struct.unpack("<I", asset_data[0x28:0x2C])[0] == 1
            if half_size:
                new_width = width // 2
                new_height = height // 2
            else:
                new_width = width
                new_height = height
        else:
            new_width = width
            new_height = height

        # Calculate pointers
        ptr1 = 0
        ptr2 = ptr1 + width * width * 4 + 0x80
        ptr3 = ptr2 + new_width * new_width * 4 + 0x80

        # Convert to int array
        temp_array = self.bytes_to_int_array(uncompressed_data, 0)

        if len(temp_array) == 0:
            raise ValueError("Failed to convert decompressed data to int array")

        print("Wavelet decoding")

        # Wavelet decode
        self.wavelet_decoder.wavelet_decode(temp_array, ptr1, width, small_table_size)
        self.wavelet_decoder.wavelet_decode(
            temp_array, ptr2 // 4, new_width, small_table_size
        )
        self.wavelet_decoder.wavelet_decode(
            temp_array, ptr3 // 4, new_width, small_table_size
        )

        # Convert YCbCr to RGB
        output_image = self.ycbcr_to_rgb(
            temp_array, ptr1, width, height, ptr2 // 4, ptr3 // 4, new_width, new_height
        )

        return output_image


def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(
        description="Decode Shandalar CAT image files to PNG format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cat_image_decoder.py image.cat
  python cat_image_decoder.py image.cat output.png
        """,
    )

    parser.add_argument("cat_file", help="Input CAT file path")
    parser.add_argument(
        "output_file", nargs="?", help="Output PNG file path (optional)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Validate input file
    cat_path = Path(args.cat_file)
    if not cat_path.exists():
        print(f"Error: Input file '{cat_path}' does not exist", file=sys.stderr)
        return 1

    if not cat_path.is_file():
        print(f"Error: '{cat_path}' is not a file", file=sys.stderr)
        return 1

    # Determine output file
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = cat_path.with_suffix(".png")

    try:
        # Read CAT file
        if args.verbose:
            print(f"Reading CAT file: {cat_path}")

        with open(cat_path, "rb") as f:
            cat_data = f.read()

        if len(cat_data) < 0x100:
            print(
                f"Error: CAT file '{cat_path}' is too small to be valid",
                file=sys.stderr,
            )
            return 1

        # Create decoder and decode image
        if args.verbose:
            print("Decoding CAT image...")

        decoder = CATImageDecoder()
        image = decoder.decode_cat_image(cat_data)

        # Save output image
        if args.verbose:
            print(f"Saving image to: {output_path}")

        image.save(output_path, "PNG")

        if args.verbose:
            print(f"Successfully decoded CAT image to {output_path}")
            print(f"Image dimensions: {image.width}x{image.height}")

        return 0

    except Exception as e:
        print(f"Error decoding CAT file: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
