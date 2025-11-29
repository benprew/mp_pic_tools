#!/usr/bin/env python3

import sys
from shared import tr2pal, pal2tpal

default_rgb = (0, 0, 0)

pal1 = pal2tpal(tr2pal(sys.argv[1], default_rgb))
pal2 = pal2tpal(tr2pal(sys.argv[2], default_rgb))


def pal2tr(pal: list[tuple[int, int, int]]):
    with open("out.tr", "w") as f:
        for i, rgb in enumerate(pal):
            f.write(f"{i} - {' '.join([str(x) for x in rgb])}\n")


for i, pal in enumerate(pal1):
    if pal2[i] == default_rgb:
        print(f"pal1[{i}] = {pal}")
        pal2[i] = pal

print(len(pal2))

pal2tr(pal2)
