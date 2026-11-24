"""Rebuild the reported Luffy and Sage strips without per-frame rescaling.

Usage:
  python3 tools/prepare_final_sprite_repairs.py RAR_DIR LUFFY_EATING_PNG OUTPUT_DIR

Every animation uses one scale and one source-space anchor. This preserves the
artist's spacing and prevents independently cropped frames from jumping.
"""
from pathlib import Path
import sys
from PIL import Image
import numpy as np
from scipy import ndimage

W, H, FEET_Y, AXIS_X = 256, 300, 280, 128


def grid(sheet: Image.Image, columns: int, rows: int) -> list[list[Image.Image]]:
    return [
        [
            sheet.crop((
                round(col * sheet.width / columns),
                round(row * sheet.height / rows),
                round((col + 1) * sheet.width / columns),
                round((row + 1) * sheet.height / rows),
            ))
            for col in range(columns)
        ]
        for row in range(rows)
    ]


def isolated_row(
    sheet: Image.Image,
    columns: int,
    top: int,
    bottom: int,
    *,
    padding: float = 0.75,
    separate_aura: bool = False,
) -> list[Image.Image]:
    """Crop overlapping cells, retaining the central fighter and nearby effects."""
    cells: list[Image.Image] = []
    cell_width = sheet.width / columns
    for column in range(columns):
        center = (column + 0.5) * cell_width
        left = max(0, round(center - cell_width * padding))
        right = min(sheet.width, round(center + cell_width * padding))
        cell = sheet.crop((left, top, right, bottom)).convert("RGBA")
        pixels = np.asarray(cell).copy()
        rgb = pixels[:, :, :3].astype(np.float32)
        maximum = rgb.max(axis=2)
        minimum = rgb.min(axis=2)
        saturation = (maximum - minimum) / np.maximum(maximum, 1)
        body_mask = pixels[:, :, 3] > 12
        if separate_aura:
            body_mask &= ~((saturation < 0.22) & (maximum > 140)) & (maximum > 70)
        labels, count = ndimage.label(body_mask, structure=np.ones((3, 3)))
        if not count:
            cells.append(cell)
            continue
        objects = ndimage.find_objects(labels)
        central_left = round((center - cell_width / 2 - left))
        central_right = round((center + cell_width / 2 - left))
        scores = []
        for label_id in range(1, count + 1):
            scores.append(int(np.count_nonzero(labels[:, central_left:central_right] == label_id)))
        main_id = 1 + int(np.argmax(scores))
        main_slice = objects[main_id - 1]
        if main_slice is None:
            cells.append(cell)
            continue
        main_y, main_x = main_slice
        main_area = int(np.count_nonzero(labels == main_id))
        keep = labels == main_id
        if separate_aura:
            # Restore outlines/highlights attached to the selected colored body only.
            keep = ndimage.binary_dilation(keep, iterations=10) & (pixels[:, :, 3] > 12)
            white_labels, _ = ndimage.label(
                (pixels[:, :, 3] > 12) & (saturation < 0.22) & (maximum > 140),
                structure=np.ones((3, 3)),
            )
            for white_id, bounds in enumerate(ndimage.find_objects(white_labels), start=1):
                if bounds is None:
                    continue
                ys, xs = bounds
                distance_x = max(main_x.start - xs.stop, xs.start - main_x.stop, 0)
                distance_y = max(main_y.start - ys.stop, ys.start - main_y.stop, 0)
                if distance_x <= 60 and distance_y <= 60:
                    keep |= white_labels == white_id
        else:
            for label_id, bounds in enumerate(objects, start=1):
                if label_id == main_id or bounds is None:
                    continue
                ys, xs = bounds
                area = int(np.count_nonzero(labels == label_id))
                touches_crop_edge = xs.start <= 1 or xs.stop >= cell.width - 1
                distance_x = max(main_x.start - xs.stop, xs.start - main_x.stop, 0)
                distance_y = max(main_y.start - ys.stop, ys.start - main_y.stop, 0)
                component = labels == label_id
                whitish = float(np.median(saturation[component])) < 0.22 and float(np.median(maximum[component])) > 140
                if whitish:
                    if distance_x <= 60 and distance_y <= 60 and area < main_area * 3:
                        keep |= component
                    continue
                if touches_crop_edge or area > main_area * 0.45:
                    continue
                if distance_x > 35 or distance_y > 35:
                    continue
                if area < main_area * 0.18:
                    keep |= component
        pixels[:, :, 3] = np.where(keep, pixels[:, :, 3], 0)
        cells.append(Image.fromarray(pixels, "RGBA"))
    return cells


def reference_anchor(frame: Image.Image, mode: str = "plain") -> tuple[float, float, float]:
    """Return body center-x, feet-y and body height in source-cell coordinates."""
    pixels = np.asarray(frame.convert("RGBA"), dtype=np.float32)
    r, g, b, alpha = (pixels[:, :, index] for index in range(4))
    maximum = np.maximum(np.maximum(r, g), b)
    minimum = np.minimum(np.minimum(r, g), b)
    saturation = (maximum - minimum) / np.maximum(maximum, 1)
    if mode == "plain":
        mask = alpha > 35
    elif mode == "colored":
        # Exclude white steam while retaining dark outlines and colored clothing.
        mask = (alpha > 35) & ((saturation > 0.20) | (maximum < 125))
    elif mode == "warm-dark":
        # Exclude the purple Sage aura; dark hair/body outlines remain included.
        warm = (r > g * 1.04) & (g > b * 1.08) & (r > 75)
        mask = (alpha > 45) & (warm | (maximum < 105))
    else:
        raise ValueError(mode)
    ys, xs = np.where(mask)
    if not len(ys):
        raise ValueError("Reference frame has no visible body")
    top, bottom = int(ys.min()), int(ys.max())
    center_y0 = top + int((bottom - top) * 0.30)
    center_y1 = top + int((bottom - top) * 0.78)
    center_xs = xs[(ys >= center_y0) & (ys <= center_y1)]
    center_x = float(np.median(center_xs if len(center_xs) else xs))
    return center_x, float(bottom), float(bottom - top + 1)


def build_strip(
    cells: list[Image.Image],
    output: Path,
    *,
    scale: float | None = None,
    reference_index: int = 0,
    reference_mode: str = "plain",
    target_body_height: float = 180,
) -> None:
    reference = cells[reference_index]
    anchor_x, feet_y, body_height = reference_anchor(reference, reference_mode)
    if scale is None:
        scale = target_body_height / body_height
    strip = Image.new("RGBA", (W * len(cells), H))
    for index, cell in enumerate(cells):
        resized = cell.resize(
            (max(1, round(cell.width * scale)), max(1, round(cell.height * scale))),
            Image.Resampling.LANCZOS,
        )
        left = round(AXIS_X - anchor_x * scale)
        top = round(FEET_Y - feet_y * scale)
        strip.alpha_composite(resized, (index * W + left, top))
    strip.save(output)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: prepare_final_sprite_repairs.py RAR_DIR LUFFY_EATING_PNG OUTPUT_DIR")
    source, eating_path, destination = map(Path, sys.argv[1:])
    destination.mkdir(parents=True, exist_ok=True)

    def open_source(name: str) -> Image.Image:
        return Image.open(source / name).convert("RGBA")

    # The supplied replacement has twelve frames in three compact, irregular rows.
    eating = Image.open(eating_path).convert("RGBA")
    eating_rows = [
        isolated_row(eating, 12, 170, 375),
        isolated_row(eating, 12, 375, 565),
        isolated_row(eating, 12, 565, 770),
    ]
    eating_scale = 180 / reference_anchor(eating_rows[0][0])[2]
    for index, (row, name) in enumerate(zip(eating_rows, ["luffy_charge", "luffy_haki_charge", "luffy_gear_charge"])):
        build_strip(
            row,
            destination / f"{name}.png",
            scale=eating_scale,
            reference_mode="colored" if index == 2 else "plain",
        )

    # Haki Gatling: two original rows, one shared scale and fixed source anchors.
    gatling_sheet = open_source("luffy_haki_gatling_gun_1672x941.png")
    gatling = [
        isolated_row(gatling_sheet, 8, 0, 471, padding=0.65),
        isolated_row(gatling_sheet, 8, 471, 941, padding=0.65),
    ]
    gatling_scale = 180 / reference_anchor(gatling[0][0])[2]
    build_strip(gatling[0], destination / "luffy_haki_gatling_a.png", scale=gatling_scale)
    build_strip(gatling[1], destination / "luffy_haki_gatling_b.png", scale=gatling_scale)

    # The ordinary Haki punch is the lower row of the activation sheet.
    punch_sheet = open_source("Sprite de Luffy Ativando Haki nos Braços.png")
    haki_punch = isolated_row(punch_sheet, 8, 471, 941, padding=0.65)
    build_strip(haki_punch, destination / "luffy_haki_punch.png")

    # Gear Second's elastic attack is the lower row; steam is not used as body height.
    elastic_sheet = open_source("Sprite Sheet do Golpe Elástico do Luffy.png")
    elastic = isolated_row(elastic_sheet, 8, 444, 887, padding=0.75, separate_aura=True)
    build_strip(elastic, destination / "luffy_gear_elastic.png", reference_mode="colored")

    # This is the actual eight-pose idle sheet, not the jump/charge sheet.
    sage_idle = isolated_row(open_source("Naruto Modo Sábio em Animação Pixel Art.png"), 8, 0, 724, padding=0.65)
    sage_scale = 180 / reference_anchor(sage_idle[0])[2]
    build_strip(sage_idle, destination / "sage_idle.png", scale=sage_scale)

    # Both transformation rows retain all eight poses, including smoke-only frames.
    sage_transform = grid(open_source("Transformação de Naruto para o Modo Sábio.png"), 8, 2)
    build_strip(sage_transform[0], destination / "sage_transform_a.png", scale=sage_scale)
    build_strip(
        sage_transform[1],
        destination / "sage_transform_b.png",
        scale=sage_scale,
        reference_index=7,
        reference_mode="warm-dark",
    )

    print(f"Prepared 10 fixed strips in {destination}")


if __name__ == "__main__":
    main()
