#!/usr/bin/env python3
import math
from html import escape

CELL_W, CELL_H = 7.2, 14
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
PAD = 8

BASE_CSS = """
  .f {{ visibility: hidden; animation: flip {total:.3f}s steps(1) infinite; }}
  @keyframes flip {{ 0% {{ visibility: visible; }} {pct:.4f}%, 100% {{ visibility: hidden; }} }}
  text {{ font-family: {font}; font-size: 12px; white-space: pre; }}
"""

Grid = list[list[tuple[str, str] | None]]


def blank(cols, rows) -> Grid:
    return [[None] * cols for _ in range(rows)]


def grid_to_runs(grid: Grid):
    out = []
    for r, row in enumerate(grid):
        c = 0
        while c < len(row):
            cell = row[c]
            if cell is None:
                c += 1
                continue
            cls, start, buf = cell[1], c, []
            while c < len(row) and (cell := row[c]) is not None and cell[1] == cls:
                buf.append(cell[0])
                c += 1
            x, y = PAD + start * CELL_W, PAD + (r + 1) * CELL_H - 3
            out.append(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" '
                       f'textLength="{len(buf) * CELL_W:.1f}">{escape("".join(buf))}</text>')
    return "".join(out)


def flipbook(frames: list[Grid], fps, css):
    rows, cols = len(frames[0]), len(frames[0][0])
    w, h = int(cols * CELL_W + 2 * PAD), int(rows * CELL_H + 2 * PAD)
    n, dt = len(frames), 1 / fps
    style = BASE_CSS.format(total=n * dt, pct=100 / n, font=FONT) + css
    body = "".join(f'<g class="f" style="animation-delay:{i * dt:.3f}s">{grid_to_runs(g)}</g>\n'
                   for i, g in enumerate(frames))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">\n<style>{style}</style>\n'
            f'<rect width="100%" height="100%" rx="8" fill="#0d1117"/>\n{body}</svg>\n')


def donut_svg(cols=46, rows=24, n_frames=90, fps=15):
    R1, R2, K2 = 0.65, 2.35, 5.0
    K1 = cols * K2 * 3 / (9 * (R1 + R2)) / 2
    ramp = ".,-~:;=!*#$@"
    light = (0.0, 1 / math.sqrt(2), -1 / math.sqrt(2))

    frames = []
    for f in range(n_frames):
        A = 2 * math.pi * f / n_frames
        B = 2 * math.pi * f / n_frames
        cA, sA, cB, sB = math.cos(A), math.sin(A), math.cos(B), math.sin(B)
        zbuf = [[0.0] * cols for _ in range(rows)]
        grid = blank(cols, rows)

        for i in range(90):
            th = 2 * math.pi * i / 90
            ct, st = math.cos(th), math.sin(th)
            for j in range(240):
                ph = 2 * math.pi * j / 240
                cp, sp = math.cos(ph), math.sin(ph)
                px, py, pz = (R2 + R1 * ct) * cp, R1 * st, -(R2 + R1 * ct) * sp
                nx, ny, nz = ct * cp, st, -ct * sp
                py, pz = py * cA - pz * sA, py * sA + pz * cA
                ny, nz = ny * cA - nz * sA, ny * sA + nz * cA
                px, py = px * cB - py * sB, px * sB + py * cB
                nx, ny = nx * cB - ny * sB, nx * sB + ny * cB

                ooz = 1 / (pz + K2)
                c = int(cols / 2 + 2 * K1 * ooz * px)
                r = int(rows / 2 - K1 * ooz * py)
                lum = nx * light[0] + ny * light[1] + nz * light[2]
                if 0 <= r < rows and 0 <= c < cols and ooz > zbuf[r][c] and lum > 0:
                    zbuf[r][c] = ooz
                    idx = min(len(ramp) - 1, int(lum * len(ramp)))
                    grid[r][c] = (ramp[idx], "b" if idx > 8 else "m" if idx > 4 else "s")
        frames.append(grid)

    css = """
  .s { fill: #484f58; } .m { fill: #8b949e; } .b { fill: #e6edf3; }
"""
    return flipbook(frames, fps, css)


if __name__ == "__main__":
    svg = donut_svg()
    with open("donut.svg", "w") as fh:
        fh.write(svg)
    print(f"wrote donut.svg ({len(svg) / 1024:.0f} KB)")
