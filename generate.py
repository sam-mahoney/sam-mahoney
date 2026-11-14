#!/usr/bin/env python3
import math
import os
import random
from datetime import date, datetime, timezone
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


def flipbook(frames: list[Grid], fps, css, under=""):
    rows, cols = len(frames[0]), len(frames[0][0])
    w, h = int(cols * CELL_W + 2 * PAD), int(rows * CELL_H + 2 * PAD)
    n, dt = len(frames), 1 / fps
    style = BASE_CSS.format(total=n * dt, pct=100 / n, font=FONT) + css
    body = "".join(f'<g class="f" style="animation-delay:{i * dt:.3f}s">{grid_to_runs(g)}</g>\n'
                   for i, g in enumerate(frames))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">\n<style>{style}</style>\n'
            f'<rect width="100%" height="100%" rx="8" fill="#0d1117"/>\n{under}{body}</svg>\n')


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


RAMP = ".,-~:;=!*#$@"
LIGHT = (0.0, 1 / math.sqrt(2), -1 / math.sqrt(2))
SHADE_CSS = """
  .s { fill: #484f58; } .m { fill: #8b949e; } .b { fill: #e6edf3; }
"""


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    n = math.sqrt(dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1, 0, 0), (0, c, -s), (0, s, c))


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0, s), (0, 1, 0), (-s, 0, c))


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def matmul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def apply(m, v):
    return (dot(m[0], v), dot(m[1], v), dot(m[2], v))


def shade_class(idx):
    return "b" if idx > 8 else "m" if idx > 4 else "s"


def fit(rmax, cols, rows):
    K2 = 2.5 * rmax
    K1 = 0.88 * K2 / rmax * min(cols / 4, rows / 2)
    return K1, K2


def render_solid(samples, specs, cols, rows, light=LIGHT, ortho=False, fill_dark=False):
    n = len(samples)
    cx = sum(p[0] for p, _, _ in samples) / n
    cy = sum(p[1] for p, _, _ in samples) / n
    cz = sum(p[2] for p, _, _ in samples) / n
    samples = [((p[0] - cx, p[1] - cy, p[2] - cz), nv, b) for p, nv, b in samples]
    rmax = max(math.sqrt(dot(p, p)) for p, _, _ in samples)
    K1, K2 = fit(rmax, cols, rows)
    flat = 0.92 * min(cols / (4 * rmax), rows / (2 * rmax))
    if ortho:
        ex = max(abs(apply(m, p)[0]) for m, _ in specs for p, _, _ in samples[::7])
        ey = max(abs(apply(m, p)[1]) for m, _ in specs for p, _, _ in samples[::7])
        flat = 0.94 * min(cols / (4 * ex), rows / (2 * ey))

    frames = []
    for m, boost_on in specs:
        zbuf = [[-1.0] * cols for _ in range(rows)]
        grid = blank(cols, rows)
        for p, nv, boost in samples:
            px, py, pz = apply(m, p)
            nx, ny, nz = apply(m, nv)
            view = (0.0, 0.0, 1.0) if ortho else (px, py, pz + K2)
            facing = nx * view[0] + ny * view[1] + nz * view[2]
            if facing > 0:
                continue
            ooz = 1 / (pz + K2)
            s = flat if ortho else K1 * ooz
            c = int(cols / 2 + 2 * s * px)
            r = int(rows / 2 - s * py)
            depth = ooz + (10 if boost and boost_on else 0)
            if not (0 <= r < rows and 0 <= c < cols) or depth <= zbuf[r][c]:
                continue
            lum = nx * light[0] + ny * light[1] + nz * light[2]
            if lum <= 0 and not fill_dark:
                continue
            zbuf[r][c] = depth
            idx = max(0, min(len(RAMP) - 1, int(lum * len(RAMP))))
            grid[r][c] = (RAMP[idx], shade_class(idx))
        frames.append(grid)
    return frames


def tube(curve, a, nu, nv):
    out, h = [], 1e-3
    for i in range(nu):
        t = 2 * math.pi * i / nu
        c, f, b = curve(t), curve(t + h), curve(t - h)
        d1 = tuple((f[k] - b[k]) / (2 * h) for k in range(3))
        d2 = tuple((f[k] - 2 * c[k] + b[k]) / (h * h) for k in range(3))
        T = unit(d1)
        N = unit(tuple(d2[k] - dot(d2, T) * T[k] for k in range(3)))
        B = cross(T, N)
        for j in range(nv):
            v = 2 * math.pi * j / nv
            nrm = tuple(math.cos(v) * N[k] + math.sin(v) * B[k] for k in range(3))
            out.append((tuple(c[k] + a * nrm[k] for k in range(3)), nrm, False))
    return out


def box(lo, hi, step, boost=None):
    out = []
    for k in range(3):
        a, b = [i for i in range(3) if i != k]
        na = max(2, int((hi[a] - lo[a]) / step) + 1)
        nb = max(2, int((hi[b] - lo[b]) / step) + 1)
        for side, sign in ((lo[k], -1), (hi[k], 1)):
            nrm = [0.0, 0.0, 0.0]
            nrm[k] = sign
            for i in range(na):
                for j in range(nb):
                    p = [0.0, 0.0, 0.0]
                    p[k] = side
                    p[a] = lo[a] + (hi[a] - lo[a]) * i / (na - 1)
                    p[b] = lo[b] + (hi[b] - lo[b]) * j / (nb - 1)
                    out.append((tuple(p), tuple(nrm), bool(boost and boost(p))))
    return out


def tumble(n_frames):
    return [(matmul(rot_z(2 * math.pi * f / n_frames), rot_x(2 * math.pi * f / n_frames)), False)
            for f in range(n_frames)]


def trefoil_svg(cols=46, rows=24, n_frames=90, fps=15):
    def knot(t):
        return (math.sin(t) + 2 * math.sin(2 * t), math.cos(t) - 2 * math.cos(2 * t), -math.sin(3 * t))
    frames = render_solid(tube(knot, 0.5, 420, 48), tumble(n_frames), cols, rows)
    return flipbook(frames, fps, SHADE_CSS)


def penrose_svg(cols=52, rows=28, n_frames=120, fps=15, hold=0.3):
    L, w, step = 4.0, 0.45, 0.03
    samples = (box((0, 0, 0), (L, w, w), step, boost=lambda p: p[0] < 2 * w)
               + box((L - w, 0, 0), (L, L, w), step)
               + box((L - w, L - w, 0), (L, L, L), step))
    up = unit((-1, -1, 2))
    toward = unit((-1, -1, -1))
    base = (cross(up, toward), up, toward)
    specs = []
    for f in range(n_frames):
        t = f / n_frames
        u = max(0.0, (t - hold) / (1 - hold))
        theta = 2 * math.pi * u * u * (3 - 2 * u)
        aligned = min(theta, 2 * math.pi - theta) < 0.35
        specs.append((matmul(rot_y(theta), base), aligned))
    light = unit((-0.3, 0.45, -0.85))
    frames = render_solid(samples, specs, cols, rows, light=light, ortho=True, fill_dark=True)
    return flipbook(frames, fps, SHADE_CSS)


def lorenz_svg(cols=60, rows=26, n_frames=150, fps=15, trail=260):
    def deriv(s):
        x, y, z = s
        return (10 * (y - x), x * (28 - z) - y, x * y - 8 / 3 * z)

    def step(s, h):
        k1 = deriv(s)
        k2 = deriv(tuple(a + h / 2 * b for a, b in zip(s, k1)))
        k3 = deriv(tuple(a + h / 2 * b for a, b in zip(s, k2)))
        k4 = deriv(tuple(a + h * b for a, b in zip(s, k3)))
        return tuple(a + h / 6 * (p + 2 * q + 2 * r + t) for a, p, q, r, t in zip(s, k1, k2, k3, k4))

    s = (1.0, 1.0, 1.0)
    for _ in range(2000):
        s = step(s, 0.01)
    raw = []
    for _ in range(9000):
        s = step(s, 0.01)
        raw.append(s)
    end = min(range(len(raw) // 2, len(raw)),
              key=lambda j: sum((a - b) ** 2 for a, b in zip(raw[j], raw[0])))
    pts = [(x, z, y) for x, y, z in raw[:end]]
    cx, cy, cz = (sum(p[k] for p in pts) / len(pts) for k in range(3))
    pts = [(x - cx, y - cy, z - cz) for x, y, z in pts]
    rmax = max(math.sqrt(dot(p, p)) for p in pts)
    K1, K2 = fit(rmax, cols, rows)

    frames = []
    for f in range(n_frames):
        m = matmul(rot_x(0.3), rot_y(2 * math.pi * f / n_frames))
        scr = []
        for p in pts:
            px, py, pz = apply(m, p)
            ooz = 1 / (pz + K2)
            scr.append((int(cols / 2 + 2 * K1 * ooz * px), int(rows / 2 - K1 * ooz * py), ooz))
        dens = [[0.0] * cols for _ in range(rows)]
        for c, r, ooz in scr:
            if 0 <= r < rows and 0 <= c < cols:
                dens[r][c] += (ooz * K2) ** 2
        top = math.log1p(max(max(row) for row in dens))
        grid = blank(cols, rows)
        for r in range(rows):
            for c in range(cols):
                if dens[r][c] > 0:
                    v = math.log1p(dens[r][c]) / top
                    idx = min(len(RAMP) - 1, int(v * len(RAMP)))
                    grid[r][c] = (RAMP[idx], "m" if v > 0.45 else "s")
        head = int(f / n_frames * len(pts))
        for age in range(trail, -1, -1):
            c, r, _ = scr[(head - age) % len(pts)]
            if 0 <= r < rows and 0 <= c < cols:
                grid[r][c] = ("@" if age == 0 else "o" if age < trail / 3 else "+", "b")
        frames.append(grid)
    return flipbook(frames, fps, SHADE_CSS)


ROTATION = ["donut", "trefoil", "penrose", "lorenz"]
MEM_TOTAL = 64216.3
MEM_CACHE = 18342.7
SCENE_PID = 30482

SCENE_PROCS = {
    "donut": (24.0, 212304, 24760),
    "trefoil": (27.0, 241880, 30112),
    "penrose": (18.0, 198552, 19004),
    "lorenz": (31.0, 286412, 41236),
}

PROCS = [
    (1, "systemd", "root", "S", 0.1, 21856, 12988, "boot"),
    (2, "kthreadd", "root", "S", 0.0, 0, 0, "kernel"),
    (15, "rcu_preempt", "root", "I", 0.1, 0, 0, "kernel"),
    (412, "systemd-journald", "root", "S", 0.1, 56220, 21544, "boot"),
    (447, "systemd-udevd", "root", "S", 0.0, 33108, 9876, "boot"),
    (812, "dbus-daemon", "messagebus", "S", 0.1, 9932, 5312, "boot"),
    (820, "systemd-logind", "root", "S", 0.0, 17204, 8140, "boot"),
    (833, "nsncd", "nscd", "S", 0.0, 300472, 4980, "boot"),
    (846, "cron", "root", "S", 0.0, 6824, 2860, "boot"),
    (1021, "sshd", "root", "S", 0.0, 12544, 8812, "boot"),
    (1037, "nix-daemon", "root", "S", 0.3, 331944, 23540, "boot"),
    (1102, "containerd", "root", "S", 0.2, 1874220, 48772, "boot"),
    (30117, "zsh", "mahoney", "S", 0.0, 12460, 6012, "session"),
    (30511, "top", "mahoney", "R", 0.6, 10812, 4120, "session"),
    (31244, "kworker/0:2", "root", "I", 0.1, 0, 0, "session"),
]


def todays_scene():
    return ROTATION[datetime.now(timezone.utc).timetuple().tm_yday % len(ROTATION)]


def top_row(pid, user, pr, ni, virt, res, shr, st, cpu, mem, time, cmd):
    return f"{pid:>7} {user:<8} {pr:>3} {ni:>3} {virt:>7} {res:>6} {shr:>6} {st} {cpu:>5} {mem:>5} {time:>9} {cmd}"


def top_time(t):
    m, s = divmod(t, 60)
    return f"{int(m)}:{s:05.2f}" if m < 1000 else f"{int(m)}:{int(s):02d}"


def top_svg(cols=90, rows=23, n_frames=10, delay=3.0, seed=11, cores=4, hz=100):
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    born = date.fromisoformat(os.environ.get("BIRTH_DATE", "2000-03-26"))
    days = (now.date() - born).days
    scene = os.environ.get("SCENE") or todays_scene()
    table = [(SCENE_PID, scene, "mahoney", "R", *SCENE_PROCS[scene], "scene")] + PROCS

    cpu_time = {}
    for pid, name, _, _, cpu, _, _, kind in table:
        if kind == "boot":
            cpu_time[pid] = days * 86400 * (cpu + 0.02) / 100 * 0.3 * rng.uniform(0.2, 1.8)
        elif kind == "kernel":
            cpu_time[pid] = days * 86400 * (cpu + 0.0002) / 100 * 0.3 * rng.uniform(0.2, 1.8)
        elif kind == "scene":
            cpu_time[pid] = rng.uniform(20, 80) * 60
        else:
            cpu_time[pid] = rng.uniform(1, 200)
    base_load = SCENE_PROCS[scene][0] / 100 + 0.04
    head = top_row("PID", "USER", "PR", "NI", "VIRT", "RES", "SHR", "S", "%CPU", "%MEM", "TIME+", "COMMAND")

    frames = []
    clock = now.hour * 3600 + now.minute * 60 + now.second
    for _ in range(n_frames):
        procs, busy = [], 0
        for pid, name, user, st, cpu, virt, res, _ in table:
            expected = cpu * delay * rng.uniform(0.75, 1.25)
            ticks = int(expected) + (rng.random() < expected % 1)
            busy += ticks
            cpu_time[pid] += ticks / hz
            procs.append((ticks / delay, pid, name, user, st, virt, res))
        procs.sort(key=lambda q: (-q[0], q[1]))
        total = 100 * busy / (delay * hz * cores)
        us, sy = round(total * 0.85, 1), round(total * 0.15, 1)
        load = (base_load + rng.uniform(-0.06, 0.06), base_load + 0.03, base_load + 0.01)
        used = 4871.6 + rng.uniform(-6, 6)
        hh, mm, ss = clock // 3600 % 24, clock // 60 % 60, clock % 60
        lines = [
            (f"top - {hh:02d}:{mm:02d}:{ss:02d} up {days} day{'' if days == 1 else 's'}, {hh:2d}:{mm:02d},  1 user,  "
             f"load average: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}", "h"),
            ("Tasks: 112 total,   2 running, 110 sleeping,   0 stopped,   0 zombie", "h"),
            (f"%Cpu(s): {us:4.1f} us, {sy:4.1f} sy,  0.0 ni, {100 - us - sy - 0.1:4.1f} id,  "
             "0.0 wa,  0.0 hi,  0.1 si,  0.0 st", "h"),
            (f"MiB Mem : {MEM_TOTAL:9.1f} total, {MEM_TOTAL - used - MEM_CACHE:9.1f} free, "
             f"{used:9.1f} used, {MEM_CACHE:9.1f} buff/cache", "h"),
            (f"MiB Swap: {0.0:9.1f} total, {0.0:9.1f} free, {0.0:9.1f} used. "
             f"{MEM_TOTAL - used - 1240:9.1f} avail Mem", "h"),
            ("", "h"),
            (head.ljust(cols), "th"),
        ]
        for c, pid, name, user, st, virt, res in procs[:rows - len(lines)]:
            mem = 100 * res / (MEM_TOTAL * 1024)
            row = top_row(pid, user if len(user) <= 8 else user[:7] + "+", 20, 0, virt, res, int(res * 0.42),
                          st, f"{c:.1f}", f"{mem:.1f}", top_time(cpu_time[pid]), name)
            if len(row) > cols:
                row = row[:cols - 1] + "+"
            lines.append((row, "o"))

        grid = blank(cols, rows)
        for r, (text, cls) in enumerate(lines):
            for c, ch in enumerate(text[:cols]):
                grid[r][c] = (ch, cls)
        frames.append(grid)
        clock += int(delay)

    y = PAD + 6 * CELL_H + 1
    under = f'<rect x="{PAD}" y="{y:.1f}" width="{cols * CELL_W:.1f}" height="{CELL_H}" fill="#c9d1d9"/>\n'
    css = """
  .h { fill: #c9d1d9; } .th { fill: #0d1117; } .o { fill: #8b949e; }
"""
    return flipbook(frames, 1 / delay, css, under)


SCENES = {
    "donut": donut_svg,
    "trefoil": trefoil_svg,
    "penrose": penrose_svg,
    "lorenz": lorenz_svg,
    "top": top_svg,
}


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:] or SCENES:
        svg = SCENES[name]()
        with open(f"{name}.svg", "w") as fh:
            fh.write(svg)
        print(f"wrote {name}.svg ({len(svg) / 1024:.0f} KB)")
