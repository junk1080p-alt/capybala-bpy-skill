"""overlay_tools.py -- SKILL.md SS13.12 C/A pipeline helpers.

Runs OUTSIDE Blender via run_python_native (or whatever "run a script" tool your own agent
platform provides; general Python + Pillow/numpy), NOT via
blender.exe --python -- Blender's bundled Python has no Pillow (verified 2026-09-10:
`import PIL` raises ModuleNotFoundError under blender.exe --background --python-expr).
build_template.py only computes/exports data (projected label coordinates, ortho
renders); all raster image work (drawing labels, edge-detection diffing) lives here.

Two tools:
  draw_labels()       -- reads the JSON written by build_template.export_label_projections()
                          and stamps black-box/white-border/white-text OCR-friendly labels
                          onto the render, saved as a new file (original untouched).
  edge_diff_overlay()  -- only meaningful for near-orthographic, low-distortion image pairs
                          (build_template.render_ortho_views() output paired with a
                          reasonably front-on/telephoto reference photo). Autocrops both
                          images to their subject, fits them onto a shared canvas, runs
                          edge detection on each, and composites: reference edges -> red
                          channel, model edges -> green+blue channels (reads as cyan).
                          Misaligned edges show up as visible red/cyan fringing; aligned
                          edges converge toward white/gray. Wide-angle or close-up reference
                          photos with real perspective distortion will produce false
                          mismatches here -- don't use this pairing for those, and don't
                          trust the diff if the reference photo itself isn't roughly
                          front-on.
"""
from __future__ import annotations

import json
import os


def _load_font(size: int):
    from PIL import ImageFont

    for path in (
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_labels(render_path: str, labels_json_path: str, out_path: str | None = None,
                font_size: int = 22) -> str:
    """Stamp black-box/white-border/white-text component-ID labels onto a render.

    labels_json_path: the file written by build_template.export_label_projections()
    (same render, same camera state -- coordinates won't line up otherwise).
    Saves to a new file by default (out_path=None -> "<render>_labeled.png") so the
    unlabeled render used for the final deliverable is never touched.
    """
    from PIL import Image, ImageDraw

    with open(labels_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    img = Image.open(render_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)
    placed = 0
    for item in data.get("labels", []):
        text = str(item["id"])
        px, py = float(item["px"]), float(item["py"])
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad = 4
        box = [px - tw / 2 - pad, py - th / 2 - pad, px + tw / 2 + pad, py + th / 2 + pad]
        draw.rectangle(box, fill=(0, 0, 0), outline=(255, 255, 255), width=2)
        draw.text((px - tw / 2 - bbox[0], py - th / 2 - bbox[1]), text, fill=(255, 255, 255), font=font)
        placed += 1

    out_path = out_path or (os.path.splitext(render_path)[0] + "_labeled.png")
    img.save(out_path)
    print(f"[overlay_tools] draw_labels: {placed} labels -> {out_path}")
    return out_path


def _autocrop_to_content(img, bg_tol: int = 18):
    """Sample the four corners as the background color, crop out the margin that stays
    within bg_tol of it. Not real background removal -- just a rough subject bounding
    box for the next step's scale/center alignment. Falls back to the full image
    untouched when no clear boundary is found (e.g. a gradient/shadowed background)."""
    import numpy as np

    arr = np.asarray(img.convert("RGB"), dtype=np.int16)
    h, w, _ = arr.shape
    corners = [arr[0, 0], arr[0, w - 1], arr[h - 1, 0], arr[h - 1, w - 1]]
    bg = np.median(np.array(corners), axis=0)
    diff = np.abs(arr - bg).sum(axis=2)
    mask = diff > bg_tol * 3
    ys, xs = np.where(mask)
    if len(xs) < 50 or len(ys) < 50:
        return img, (0, 0, w, h)
    x0, x1 = max(0, int(xs.min()) - 4), min(w, int(xs.max()) + 4)
    y0, y1 = max(0, int(ys.min()) - 4), min(h, int(ys.max()) + 4)
    return img.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)


def edge_diff_overlay(reference_path: str, render_path: str, out_path: str | None = None,
                      canvas_size: int = 900) -> str:
    """Composite a reference-vs-render edge-alignment diff. See module docstring for when
    this pairing is valid (near-orthographic / low-distortion images only).

    This is NOT pixel-accurate registration -- no feature-point alignment or perspective
    correction, just autocrop-to-subject + uniform scale-to-fit + center. Works best on
    clean-background, near-orthographic product photos. A reference photo with real
    perspective distortion or a cluttered background can produce an offset that's purely
    an artifact of how the photo was taken, not a real modeling error -- say so explicitly
    when reporting on this diff instead of treating every red/cyan fringe as a defect.
    """
    from PIL import Image, ImageFilter
    import numpy as np

    ref = Image.open(reference_path).convert("RGB")
    mdl = Image.open(render_path).convert("RGB")
    ref_c, _ = _autocrop_to_content(ref)
    mdl_c, _ = _autocrop_to_content(mdl)

    def _fit(img):
        canvas = Image.new("RGB", (canvas_size, canvas_size), (32, 32, 32))
        scale = min(canvas_size / img.width, canvas_size / img.height) * 0.92
        nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
        resized = img.resize((nw, nh), Image.LANCZOS)
        canvas.paste(resized, ((canvas_size - nw) // 2, (canvas_size - nh) // 2))
        return canvas

    ref_fit = _fit(ref_c)
    mdl_fit = _fit(mdl_c)

    def _edges(img):
        gray = img.convert("L").filter(ImageFilter.FIND_EDGES)
        arr = np.asarray(gray, dtype=np.float32)
        peak = arr.max()
        if peak > 1e-6:
            arr = np.clip(arr / peak * 255.0, 0, 255)
        return arr.astype(np.uint8)

    ref_edge = _edges(ref_fit)
    mdl_edge = _edges(mdl_fit)

    out_arr = np.zeros((canvas_size, canvas_size, 3), dtype=np.uint8)
    out_arr[..., 0] = ref_edge   # reference edges -> red
    out_arr[..., 1] = mdl_edge   # model edges -> green+blue = cyan
    out_arr[..., 2] = mdl_edge
    out_img = Image.fromarray(out_arr, mode="RGB")

    out_path = out_path or (os.path.splitext(render_path)[0] + "_edgediff.png")
    out_img.save(out_path)
    print(f"[overlay_tools] edge_diff_overlay -> {out_path}")
    return out_path


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("labels", help="Stamp component-ID labels onto a render")
    p1.add_argument("render_path")
    p1.add_argument("labels_json_path")
    p1.add_argument("--out")

    p2 = sub.add_parser("diff", help="Composite a reference-vs-render edge-alignment diff")
    p2.add_argument("reference_path")
    p2.add_argument("render_path")
    p2.add_argument("--out")

    args = ap.parse_args()
    if args.cmd == "labels":
        draw_labels(args.render_path, args.labels_json_path, args.out)
    elif args.cmd == "diff":
        edge_diff_overlay(args.reference_path, args.render_path, args.out)
