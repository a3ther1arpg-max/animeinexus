"""Repair the sprite defects reported after the RAR expansion review.

Usage: python3 tools/prepare_reported_sprite_fixes.py ORIGINAL_DIR CURRENT_DIR OUTPUT_DIR

ORIGINAL_DIR contains the extracted RAR images. CURRENT_DIR contains the already
normalized CDN strips for the animations that only need local cleanup/scaling.
The generated form sheets and every unrelated animation are left untouched.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

W, H, FEET, CENTER = 256, 300, 280, 128


def cells(image: Image.Image) -> list[Image.Image]:
    return [image.crop((x * W, 0, (x + 1) * W, H)) for x in range(image.width // W)]


def save(frames: list[Image.Image], output: Path, name: str) -> None:
    sheet = Image.new("RGBA", (W * len(frames), H))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, (index * W, 0))
    sheet.save(output / f"{name}.png")


def main_component(data: np.ndarray, mask: np.ndarray | None = None, threshold: int = 12) -> np.ndarray:
    alpha = data[:, :, 3] > threshold
    if mask is not None:
        alpha &= mask
    labels, count = ndimage.label(alpha)
    if not count:
        return data
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    main = labels == sizes.argmax()
    keep = ndimage.binary_dilation(main, iterations=2)
    cleaned = data.copy()
    cleaned[~keep] = 0
    return cleaned


def aura_mask(data: np.ndarray) -> np.ndarray:
    rgb = data[:, :, :3].astype(float)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    alpha = data[:, :, 3] > 8
    cyan = alpha & (b > 125) & (b > r * 1.10) & (g > r * 1.06)
    near = ndimage.binary_dilation(cyan, iterations=10)
    white_core = alpha & near & (r > 165) & (g > 190) & (b > 200)
    return cyan | white_core


def normalize_plain(crop: Image.Image, target_height: int = 180) -> Image.Image:
    data = main_component(np.array(crop.convert("RGBA")))
    ys, xs = np.where(data[:, :, 3] > 20)
    if not len(xs):
        return Image.new("RGBA", (W, H))
    top, feet = int(ys.min()), int(ys.max()) + 1
    scale = target_height / (feet - top)
    center = (int(xs.min()) + int(xs.max()) + 1) / 2
    resized = Image.fromarray(data).resize(
        (round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS
    )
    frame = Image.new("RGBA", (W, H))
    frame.alpha_composite(resized, (round(CENTER - center * scale), round(FEET - feet * scale)))
    return frame


def normalize_rasen(crop: Image.Image, scale: float, strip_released: bool = False) -> Image.Image:
    source = np.array(crop.convert("RGBA"))
    aura = aura_mask(source)
    body_data = main_component(source, ~aura)
    body_alpha = body_data[:, :, 3] > 20
    ys, xs = np.where(body_alpha)
    if not len(xs):
        return Image.new("RGBA", (W, H))
    feet = int(ys.max()) + 1
    center = (int(xs.min()) + int(xs.max()) + 1) / 2
    if strip_released:
        labels, count = ndimage.label(aura)
        for label in range(1, count + 1):
            component = labels == label
            area = int(component.sum())
            component_x = float(np.where(component)[1].mean())
            if area > 500 and component_x > center + 30:
                source[ndimage.binary_dilation(component, iterations=3)] = 0
        aura = aura_mask(source)

    # Remove neighboring-row specks while retaining the body and its cyan aura.
    body_keep = ndimage.binary_dilation(body_alpha, iterations=2)
    source[~(body_keep | aura)] = 0
    resized = Image.fromarray(source).resize(
        (round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS
    )
    data = np.array(resized)
    aura = aura_mask(data)
    body = data.copy()
    body[aura] = 0
    effect = data.copy()
    effect[~aura] = 0

    dx, dy = round(CENTER - center * scale), round(FEET - feet * scale)
    frame = Image.new("RGBA", (W, H))
    frame.alpha_composite(Image.fromarray(body), (dx, dy))

    ys, xs = np.where(effect[:, :, 3] > 8)
    if len(xs):
        x0, x1 = int(xs.min()), int(xs.max()) + 1
        y0, y1 = int(ys.min()), int(ys.max()) + 1
        aura_image = Image.fromarray(effect).crop((x0, y0, x1, y1))
        left, top, bottom = dx + x0, dy + y0, dy + y1
        factor = min(1.0, 242 / aura_image.width, 184 / aura_image.height, (bottom - 4) / aura_image.height)
        if factor < 1.0:
            aura_image = aura_image.resize(
                (max(1, round(aura_image.width * factor)), max(1, round(aura_image.height * factor))),
                Image.Resampling.LANCZOS,
            )
        aura_center = left + (x1 - x0) / 2
        new_left = round(min(max(aura_center - aura_image.width / 2, 4), W - 4 - aura_image.width))
        new_top = round(min(bottom, H - 4) - aura_image.height)
        frame.alpha_composite(aura_image, (new_left, new_top))
    return frame


def repair_sage(original: Path, output: Path) -> None:
    idle = Image.open(original / "Naruto Modo Sábio em Animação Pixel Art.png").convert("RGBA")
    edges = [0, 273, 545, 817, 1088, 1360, 1631, 1900, 2172]
    frames = [normalize_plain(idle.crop((left, 0, right, 724))) for left, right in zip(edges, edges[1:])]
    save(frames, output, "sage_idle")

    source = Image.open(original / "Sequência do Rasenshuriken de Naruto.png").convert("RGBA")
    boxes = [(left, top, right, top + 360) for top in (0, 362) for left, right in zip(edges, edges[1:])]
    first = np.array(source.crop(boxes[0]))
    body = main_component(first, ~aura_mask(first))
    ys, _ = np.where(body[:, :, 3] > 20)
    scale = 180 / (int(ys.max()) + 1 - int(ys.min()))
    normalized = [normalize_rasen(source.crop(box), scale, strip_released=index == 15) for index, box in enumerate(boxes)]
    # Top row charges; the first bottom pose is the held, fully formed shuriken.
    save(normalized[:9], output, "sage_rasen_charge")
    # The throw keeps Naruto visible in every frame. No projectile-only final cell.
    save(normalized[9:15], output, "sage_rasen_throw")


def repair_hair(original: Path, current: Path, output: Path) -> None:
    frames = cells(Image.open(current / "luffy_charge.png").convert("RGBA"))
    donor_sheet = Image.open(original / "Luffy Comendo Carne em Pixel Art.png").convert("RGBA")
    edges = [round(index * donor_sheet.width / 8) for index in range(9)]
    donors = [normalize_plain(donor_sheet.crop((left, 0, right, donor_sheet.height))) for left, right in zip(edges, edges[1:])]
    repaired = []
    for index, frame in enumerate(frames):
        data = np.array(frame)
        donor = np.array(donors[index])
        ys, _ = np.where(data[:, :, 3] > 20)
        dys, _ = np.where(donor[:, :, 3] > 20)
        top, donor_top = int(ys.min()), int(dys.min())
        yy, _ = np.indices(data.shape[:2])
        donor_rgb = donor[:, :, :3].astype(float)
        donor_max, donor_min = donor_rgb.max(axis=2), donor_rgb.min(axis=2)
        hair = (donor[:, :, 3] > 15) & (donor_max < 175) & ((donor_max - donor_min) < 88)
        hair[:donor_top] = False
        hair[donor_top + 49:] = False
        hx = np.where(hair)[1]
        current_region = (data[:, :, 3] > 20) & (yy >= top) & (yy < top + 49)
        cx = np.where(current_region)[1]
        dx = round((float(np.median(cx)) if len(cx) else CENTER) - (float(np.median(hx)) if len(hx) else CENTER))
        dy = top - donor_top
        hair_layer = np.zeros_like(data)
        source_ys, source_xs = np.where(hair)
        target_xs, target_ys = source_xs + dx, source_ys + dy
        valid = (target_xs >= 0) & (target_xs < W) & (target_ys >= 0) & (target_ys < H)
        hair_layer[target_ys[valid], target_xs[valid]] = donor[source_ys[valid], source_xs[valid]]
        base = Image.fromarray(data)
        base.alpha_composite(Image.fromarray(hair_layer))
        data = np.array(base)
        rgb = data[:, :, :3].astype(float)
        maximum, minimum = rgb.max(axis=2), rgb.min(axis=2)
        mask = (yy >= top) & (yy < top + 45) & (data[:, :, 3] > 20) & (maximum > 125) & ((maximum - minimum) < 58)
        luminance = rgb.mean(axis=2)
        shade = np.clip(18 + (255 - luminance) * 0.10, 18, 42)
        for channel in range(3):
            data[:, :, channel][mask] = shade[mask].astype(np.uint8)
        repaired.append(Image.fromarray(data))
    save(repaired, output, "luffy_charge")


def scale_at_feet(frame: Image.Image, factor: float) -> Image.Image:
    resized = frame.resize((round(W * factor), round(H * factor)), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (W, H))
    out.alpha_composite(resized, (round(CENTER - CENTER * factor), round(FEET - FEET * factor)))
    return out


def repair_gear(current: Path, output: Path) -> None:
    factors = [1, 1, 1, 0.98, 0.90, 0.82, 0.76, 0.74]
    for name in ("luffy_gear_transform_a", "luffy_gear_transform_b"):
        frames = cells(Image.open(current / f"{name}.png").convert("RGBA"))
        save([scale_at_feet(frame, 0.74 if name.endswith("_b") else factors[index]) for index, frame in enumerate(frames)], output, name)


def repair_goku(current: Path, output: Path) -> None:
    run = cells(Image.open(current / "update_ssj_run.png").convert("RGBA"))
    tops = []
    for frame in run:
        ys, _ = np.where(np.array(frame)[:, :, 3] > 20)
        tops.append(int(ys.min()))
    baseline = min(tops)
    stabilized = []
    for frame, top in zip(run, tops):
        shifted = Image.new("RGBA", (W, H))
        shifted.alpha_composite(frame, (0, baseline - top))
        stabilized.append(shifted)
    save(stabilized, output, "update_ssj_run")

    charge = cells(Image.open(current / "kaioken_charge_start.png").convert("RGBA"))
    cleaned = []
    for frame in charge:
        data = main_component(np.array(frame), threshold=48)
        # Neighboring aura columns at the crop seam caused a one-frame flash.
        data[:, :10] = 0
        data[:, -10:] = 0
        rgb = data[:, :, :3].astype(float)
        r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
        alpha = data[:, :, 3] > 20
        orange = alpha & (r > 140) & (g > 45) & (g < 190) & (b < 120) & (r > g * 1.3)
        pink = alpha & (r > 150) & (b > 100) & (r > g * 1.25)
        orange_xs = np.where(orange)[1]
        if len(orange_xs):
            left, right = int(orange_xs.min()) - 8, int(orange_xs.max()) + 8
            labels, count = ndimage.label(pink)
            for label in range(1, count + 1):
                component = labels == label
                ys, xs = np.where(component)
                if not len(xs):
                    continue
                center_x = (int(xs.min()) + int(xs.max())) / 2
                if int(xs.max()) - int(xs.min()) <= 12 and int(ys.max()) - int(ys.min()) >= 25 and (center_x < left or center_x > right):
                    data[ndimage.binary_dilation(component, iterations=2)] = 0
        cleaned.append(Image.fromarray(data))
    save(cleaned, output, "kaioken_charge_start")


def selection_goku(original: Path, output: Path) -> None:
    base = Image.open(original / "Tela de seleção Naruto e Goku.png").convert("RGBA")
    glow = Image.new("RGBA", base.size)
    draw = ImageDraw.Draw(glow)
    for box, radius in (((735, 350, 941, 555), 20), ((590, 720, 1080, 855), 45)):
        draw.rounded_rectangle(box, radius=radius, outline=(255, 174, 0, 230), width=14)
    soft = glow.filter(ImageFilter.GaussianBlur(22))
    near = glow.filter(ImageFilter.GaussianBlur(6))
    result = Image.alpha_composite(base, soft)
    result = Image.alpha_composite(result, near)
    crisp = Image.new("RGBA", base.size)
    draw = ImageDraw.Draw(crisp)
    draw.rounded_rectangle((738, 353, 938, 552), radius=18, outline=(255, 225, 92, 255), width=4)
    result = Image.alpha_composite(result, crisp)
    result.convert("RGB").save(output / "select_goku_highlight.png")


def prepare(original: Path, current: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    repair_sage(original, output)
    repair_hair(original, current, output)
    repair_gear(current, output)
    repair_goku(current, output)
    selection_goku(original, output)
    print("Prepared 8 corrected assets in", output)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
