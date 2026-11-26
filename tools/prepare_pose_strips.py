"""Rebuild fighter strips from the original sheets with one scale per animation.

Usage: python3 tools/prepare_pose_strips.py ORIGINAL_DIR CURRENT_DIR OUTPUT_DIR

Each pose is found by its coloured body (smoke, chakra and outlines are
attached to the nearest body), scaled once per animation and placed so the
centre of the feet sits on the shared anchor (x = frame centre, y = 280).
CURRENT_DIR holds the strips already in the game; the eating strips are only
re-anchored because their art is already correct.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

H, FEET = 300, 280
WIDE = 448


def masks(data: np.ndarray):
    rgb = data[:, :, :3].astype(float)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(2), rgb.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    alpha = data[:, :, 3]
    white = (sat < 0.2) & (mx > 150)
    cyan = (b > 125) & (b > r * 1.10) & (g > r * 1.06)
    body = (alpha > 128) & ~white & ~cyan
    return body, cyan & (alpha > 8)


def feet_center(body: np.ndarray) -> tuple[float, int]:
    ys, xs = np.where(body)
    bottom = int(ys.max())
    return float(xs[ys > bottom - 14].mean()), bottom + 1


def poses(sheet: Image.Image, band: tuple[int, int], min_area: int = 4000, alpha_floor: int = 20):
    data = np.array(sheet.convert("RGBA"))[band[0]:band[1]].copy()
    data[data[:, :, 3] < alpha_floor] = 0
    body, cyan = masks(data)
    body = ndimage.binary_opening(body, iterations=1)
    labels, count = ndimage.label(ndimage.binary_dilation(body, iterations=2))
    sizes = ndimage.sum(body, labels, range(1, count + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s >= min_area]
    order = sorted(keep, key=lambda l: np.where(labels == l)[1].mean())
    owner = np.zeros(labels.shape, int)
    for index, label in enumerate(order, start=1):
        owner[(labels == label) & body] = index
    dist, (iy, ix) = ndimage.distance_transform_edt(owner == 0, return_indices=True)
    nearest = owner[iy, ix]
    out = []
    for index in range(1, len(order) + 1):
        part = data.copy()
        part[(nearest != index) | (dist > 110)] = 0
        own_body = owner == index
        out.append((part, own_body))
    return out


def clean_small(frame: np.ndarray, min_px: int = 40) -> np.ndarray:
    alpha = frame[:, :, 3] > 20
    labels, count = ndimage.label(alpha)
    if count:
        sizes = ndimage.sum(alpha, labels, range(1, count + 1))
        for i, s in enumerate(sizes):
            if s < min_px:
                frame[labels == i + 1] = 0
    return frame


def place(part: np.ndarray, body: np.ndarray, scale: float, width: int) -> np.ndarray:
    fx, feet = feet_center(body)
    img = Image.fromarray(part)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (width, H))
    frame.alpha_composite(resized, (0, 0), (0, 0)) if False else None
    dx, dy = round(width / 2 - fx * scale), round(FEET - feet * scale)
    canvas = Image.new("RGBA", (width + 2000, H + 2000))
    canvas.alpha_composite(resized, (dx + 1000, dy + 1000))
    out = np.array(canvas.crop((1000, 1000, 1000 + width, 1000 + H)))
    return clean_small(out)


def lift_overflow(frame_src: np.ndarray, body: np.ndarray, scale: float, width: int) -> np.ndarray:
    """Place a pose; if a chakra effect would leave the top, move only the effect down."""
    _, cyan = masks(frame_src)
    effect = frame_src.copy(); effect[~cyan] = 0
    rest = frame_src.copy(); rest[cyan] = 0
    base = place(rest, body, scale, width)
    fx, feet = feet_center(body)
    ys = np.where(effect[:, :, 3] > 8)[0]
    if not len(ys):
        return base
    top = FEET - (feet - ys.min()) * scale
    shift = max(0, round(4 - top))
    fx_img = Image.fromarray(effect)
    resized = fx_img.resize((round(fx_img.width * scale), round(fx_img.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (width + 2000, H + 2000))
    canvas.alpha_composite(resized, (round(width / 2 - fx * scale) + 1000, round(FEET - feet * scale) + shift + 1000))
    eff = Image.fromarray(np.array(canvas.crop((1000, 1000, 1000 + width, 1000 + H))))
    out = Image.fromarray(base)
    out.alpha_composite(eff)
    return clean_small(np.array(out))


def body_height(body: np.ndarray) -> int:
    ys = np.where(body)[0]
    return int(ys.max() - ys.min() + 1)


def save(frames: list[np.ndarray], output: Path, name: str) -> None:
    w = frames[0].shape[1]
    sheet = Image.new("RGBA", (w * len(frames), H))
    for i, f in enumerate(frames):
        sheet.alpha_composite(Image.fromarray(f), (i * w, 0))
    sheet.save(output / f"{name}.png")
    edge = [i for i, f in enumerate(frames) if (f[:, :2, 3] > 30).any() or (f[:, -2:, 3] > 30).any() or (f[:2, :, 3] > 30).any()]
    print(name, len(frames), "frames", w, "wide", "edge-touch:", edge)


def build(sheet_path: Path, bands, names, output: Path, width: int, target: int = 180, rasen=False, alpha_floor=20, drop_released=False):
    sheet = Image.open(sheet_path)
    rows = [poses(sheet, band, alpha_floor=alpha_floor) for band in bands]
    scale = target / body_height(rows[0][0][1])
    for (name, row) in zip(names, rows):
        frames = []
        for index, (part, body) in enumerate(row):
            if drop_released and index >= 1:
                _, cyan = masks(part)
                labels, count = ndimage.label(ndimage.binary_dilation(cyan, iterations=3))
                for l in range(1, count + 1):
                    comp = labels == l
                    if comp.sum() > 2500:
                        part[comp] = 0
            frames.append(lift_overflow(part, body, scale, width) if rasen else place(part, body, scale, width))
        if isinstance(name, tuple):
            name, take = name
            frames = [frames[i] for i in take]
        save(frames, output, name)


def reanchor(current: Path, output: Path, name: str) -> None:
    strip = np.array(Image.open(current / f"{name}.png").convert("RGBA"))
    frames = []
    for i in range(strip.shape[1] // 256):
        cell = strip[:, i * 256:(i + 1) * 256].copy()
        body, _ = masks(cell)
        labels, count = ndimage.label(ndimage.binary_dilation(body, iterations=2))
        sizes = ndimage.sum(body, labels, range(1, count + 1))
        main = (labels == (int(np.argmax(sizes)) + 1)) & body
        frames.append(place(cell, main, 1.0, 256))
    save(frames, output, name)


def main() -> None:
    original, current, output = (Path(p) for p in sys.argv[1:4])
    output.mkdir(parents=True, exist_ok=True)
    for name in ("luffy_charge", "luffy_haki_charge", "luffy_gear_charge"):
        reanchor(current, output, name)
    build(original / "Naruto Modo Sábio em Animação Pixel Art.png", [(150, 560)], ["sage_idle"], output, 256)
    rasen = original / "Sequência do Rasenshuriken de Naruto.png"
    build(rasen, [(0, 380), (380, 724)], ["sage_rasen_charge", "sage_rasen_throw"], output, WIDE, rasen=True, drop_released=False)
    build(original / "luffy_gear_second_transformacao_corrigida_transparente_1672x941.png", [(140, 470), (505, 835)],
          ["luffy_gear_transform_a", "luffy_gear_transform_b"], output, 256)
    sheet = original / "luffy_haki_pulo_soco_1672x941_transparente.png"
    build(sheet, [(520, 830), (520, 830)], ["luffy_haki_punch", ("_unused", [0])], output, WIDE)
    build(original / "Sprite de Luffy Gear Second em Ação.png", [(60, 440), (440, 840)], [("_unused2", [0]), "luffy_gear_punch"], output, WIDE)
    build(original / "Sprite Sheet do Golpe Elástico do Luffy.png", [(100, 450), (480, 850)], ["luffy_gear_elastic_a", "luffy_gear_elastic_b"], output, WIDE)


if __name__ == "__main__":
    main()
