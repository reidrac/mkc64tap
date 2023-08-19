#!/usr/bin/env python
"""
Copyright (C) 2017 by Juan J. Martinez <jjm@usebox.net>
Modified  (C) 2023 by Zibri <zibri@zibri.org>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import sys
import struct
from argparse import ArgumentParser

__version__ = "0.2"

DEF_OUTPUT = "output.tap"

# CBM ROM Loader values
PULSE_S = 0x30
PULSE_M = 0x42
PULSE_L = 0x56

def write_header(fd, data_len):
    """Write the TAP header"""
    fd.write(b"C64-TAPE-RAW")
    fd.write(b"\1") # version 1
    fd.write(b"\0\0\0") # reserved
    fd.write(struct.pack("<I", data_len))

def encbit(bit):
    """Encode a bit"""
    return [PULSE_M, PULSE_S] if bit else [PULSE_S, PULSE_M]

def encbytes(data):
    """Encode a list of bytes"""
    encoded = []
    for c in data:
        check = 1
        # data marker
        encoded.extend([PULSE_L, PULSE_M])
        for b in range(8):
            bit = (c >> b) & 1
            check ^= bit
            encoded.extend(encbit(bit))
        encoded.extend(encbit(check))

    return encoded

def petscii(text):
    """Simple conversion from ASCII to PETSCII"""
    text = map(ord, text.upper())
    for i, c in enumerate(text):
        if ord('A') <= c >= ord('Z'):
            text[i] += 32

    return text

def make_header(t, addr_start, addr_end, filename):
    """Generate a CBM block header"""
    header = [t] # type
    header.extend(bytearray(struct.pack("<H", addr_start)))
    header.extend(bytearray(struct.pack("<H", addr_end)))
    header.extend(petscii(filename[:16]))

    if len(filename) < 16:
        header.extend(map(ord, " " * (16 - len(filename))))
    # body
    header.extend(map(ord, " " * 171))

    checkbyte = 0
    for c in header:
        checkbyte ^= c
    header.append(checkbyte)

    return header

def make_end_of_tape():
    """Generate an end of tape block header and its repeat"""
    encoded = []

    # header sync
    encoded.extend(encbytes([x for x in range(0x89, 0x80, -1)]))

    # end of tape header
    header = make_header(5, 0, 0, "")
    encoded.extend(encbytes(header))

    # end of data
    encoded.extend([PULSE_L, PULSE_S])

    # gap
    for _ in range(0x4f):
        encoded.append(PULSE_S)

    # header sync (REP)
    encoded.extend(encbytes([x for x in range(9, 0, -1)]))

    # header (REP)
    encoded.extend(encbytes(header))

    # end of data
    encoded.extend([PULSE_L, PULSE_S])

    # trailer
    for _ in range(0x388):
        encoded.append(PULSE_S)

    return encoded

def read_file(filename):
    """Read a file (PRG) and return it encoded as TAP blocks"""
    with open(filename, "rb") as fd:
        data = bytearray(fd.read())

    addr_start = struct.unpack("<H", data[:2])[0]
    data = data[2:]
    addr_end = addr_start + len(data) + 1

    encoded = [0x00,0x14,0x00,0x05]

    # leader
    for _ in range(0x6a00):
        encoded.append(PULSE_S)

    # header sync
    encoded.extend(encbytes([x for x in range(0x89, 0x80, -1)]))

    # header
    header = make_header(3, addr_start, addr_end, filename[0:filename.index(".")])
    encoded.extend(encbytes(header))

    # end of data
    encoded.extend([PULSE_L, PULSE_S])

    # gap
    for _ in range(0x4f):
        encoded.append(PULSE_S)

    # header sync (REP)
    encoded.extend(encbytes([x for x in range(9, 0, -1)]))

    # header (REP)
    encoded.extend(encbytes(header))

    # end of data
    encoded.extend([PULSE_L, PULSE_S])

    # gap
    for _ in range(0x4e):
        encoded.append(PULSE_S)

    # trailer
    encoded.extend([0x00,0x14,0x00,0x05])

    for _ in range(0x1500):
        encoded.append(PULSE_S)

    # data sync
    encoded.extend(encbytes([x for x in range(0x89, 0x80, -1)]))

    # data
    checkbyte = 0
    for c in data:
        checkbyte ^= c

    encoded.extend(encbytes(data))
    encoded.extend(encbytes([checkbyte]))

    # end of data
    encoded.extend([PULSE_L, PULSE_S])

    # gap
    for _ in range(0x4f):
        encoded.append(PULSE_S)

    # data sync (REP)
    encoded.extend(encbytes([x for x in range(9, 0, -1)]))

    # data (REP)
    checkbyte = 0
    for c in data:
        checkbyte ^= c

    encoded.extend(encbytes(data))
    encoded.extend(encbytes([checkbyte]))

    # end of data
    encoded.extend([PULSE_L, PULSE_S])

    # trailer
    for _ in range(0x388):
        encoded.append(PULSE_S)

    return encoded

def main():
    parser = ArgumentParser(description="A simple tool to generate .TAP files for the C64",
                            epilog="Project page: https://github.com/reidrac/mkc64tap",
                            )

    parser.add_argument("-v", "--version", action="version", version="%(prog)s " + __version__)

    parser.add_argument("-o", "--output", dest="output",
                        default=DEF_OUTPUT,
                        help="filename for the resulting TAP file (default: %s)" % DEF_OUTPUT,
                        )

    parser.add_argument("file",
                        nargs="+",
                        type=str,
                        help="PRG file to add to the tape",
                        )

    args = parser.parse_args()

    data = []
    for filename in args.file:
        data.extend(read_file(filename))

    with open(args.output, "wb") as fd:
        write_header(fd, len(data))
        fd.write(bytearray(data))
        fd.write(bytearray(make_end_of_tape()))

    sys.exit(0)

if __name__ == "__main__":
    main()
