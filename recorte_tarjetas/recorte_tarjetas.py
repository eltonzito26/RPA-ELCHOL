from __future__ import annotations

import csv
import math
import queue
import threading
import unicodedata
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageTk
from rapidocr import RapidOCR

CARD_MM = (85.60, 53.98)
SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DEFAULT_DPI = 300


def order_quad(points):
    """Return TL, TR, BR, BL in source-image coordinates."""
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()  # y - x
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)],
                     pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def refine_quad_edges(rgb, quad):
    """Fit the four straight card edges and extrapolate past rounded corners.

    Color masks tend to stop on the inside of the DPI border, and their four
    vertices can land at the ends of a rounded corner instead of at the virtual
    corner where the straight edges meet. Search outward from each side for a
    continuous color/brightness transition, fit a line robustly, then intersect
    adjacent lines. This specifically corrects a common top-left under-crop.
    """
    q = order_quad(quad).astype(np.float32)
    h, w = rgb.shape[:2]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    lines = []
    for i in range(4):
        a, b = q[i], q[(i + 1) % 4]
        edge = b - a
        length = float(np.linalg.norm(edge))
        if length < 20:
            lines.append(None)
            continue
        tangent = edge / length
        inward = np.array([-tangent[1], tangent[0]], dtype=np.float32)
        short_side = min(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[3] - q[0]))
        radius = min(52, max(14, int(short_side * 0.13)))
        offsets = np.arange(-radius, 1, 2, dtype=np.float32)
        samples_t = np.linspace(0.16, 0.84, 17)
        observed_offsets, observed_t = [], []

        def sample_strip(center):
            positions = center[None, :] + np.array([-4.0, 0.0, 4.0], dtype=np.float32)[:, None] * tangent
            xs = np.clip(np.rint(positions[:, 0]).astype(int), 0, w - 1)
            ys = np.clip(np.rint(positions[:, 1]).astype(int), 0, h - 1)
            return lab[ys, xs].mean(axis=0), hsv[ys, xs, 1].mean()

        for t in samples_t:
            p = a + edge * t
            contrasts = []
            for offset in offsets:
                inside = p + (offset + 6.0) * inward
                outside = p + (offset - 6.0) * inward
                in_lab, in_sat = sample_strip(inside)
                out_lab, out_sat = sample_strip(outside)
                contrasts.append(float(np.linalg.norm(in_lab - out_lab) +
                                       max(0.0, in_sat - out_sat) * 0.16))
            contrasts = np.asarray(contrasts, dtype=np.float32)
            maximum = float(contrasts.max())
            # Pick the nearest plausible outside-to-inside boundary, not a stronger
            # line farther into the background or an internal printed stripe.
            eligible = np.flatnonzero(contrasts >= max(13.0, maximum * 0.68))
            if maximum < 15.0 or not len(eligible):
                continue
            chosen = int(eligible[-1])
            observed_offsets.append(float(offsets[chosen]))
            observed_t.append(float(t))

        if len(observed_offsets) < 9:
            lines.append(None)
            continue
        observed_offsets = np.asarray(observed_offsets, dtype=np.float32)
        observed_t = np.asarray(observed_t, dtype=np.float32)
        # RANSAC-style one-dimensional line fit. A few printed lines or paper folds
        # can create strong local edges, but they do not follow the card border along
        # most of a side.
        best = None
        for slope in range(-60, 61):
            intercept = float(np.median(observed_offsets - slope * (observed_t - 0.5)))
            residual = np.abs(observed_offsets - (intercept + slope * (observed_t - 0.5)))
            inliers = residual <= 7.0
            key = (int(inliers.sum()), -float(np.median(residual[inliers])) if np.any(inliers) else -999,
                   -abs(slope))
            if best is None or key > best[0]:
                best = (key, inliers)
        if best is None or best[0][0] < 9:
            lines.append(None)
            continue
        inliers = best[1]
        slope, intercept = np.polyfit(observed_t[inliers], observed_offsets[inliers], 1)
        points = np.asarray([a + edge * t + (slope * t + intercept) * inward
                             for t in observed_t[inliers]], dtype=np.float32)
        fit = cv2.fitLine(points, cv2.DIST_HUBER, 0, 0.01, 0.01).flatten()
        lines.append((fit[:2].astype(np.float32), fit[2:].astype(np.float32)))

    def line_through_side(i):
        fit = cv2.fitLine(np.asarray([q[i], q[(i + 1) % 4]], dtype=np.float32),
                          cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        return fit[:2].astype(np.float32), fit[2:].astype(np.float32)

    lines = [line if line is not None else line_through_side(i)
             for i, line in enumerate(lines)]

    def intersection(first, second):
        v1, p1 = first
        v2, p2 = second
        matrix = np.column_stack((v1, -v2))
        if abs(float(np.linalg.det(matrix))) < 1e-5:
            return None
        return p1 + np.linalg.solve(matrix, p2 - p1)[0] * v1

    refined = []
    for i in range(4):
        point = intersection(lines[(i - 1) % 4], lines[i])
        if point is None:
            return q
        refined.append(point)
    refined = np.asarray(refined, dtype=np.float32)
    original_area = abs(cv2.contourArea(q))
    refined_area = abs(cv2.contourArea(refined))
    if (not cv2.isContourConvex(np.round(refined).astype(np.int32)) or
            refined_area < original_area * 0.80 or refined_area > original_area * 1.35 or
            np.any(refined[:, 0] < 0) or np.any(refined[:, 0] >= w) or
            np.any(refined[:, 1] < 0) or np.any(refined[:, 1] >= h)):
        return q
    return refined


def find_card_quad(rgb):
    h, w = rgb.shape[:2]
    scale = min(1.0, 1800.0 / max(h, w))
    small = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else rgb
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edge_sets = []
    for lo, hi in ((25, 85), (40, 130), (60, 180)):
        edges = cv2.Canny(gray, lo, hi)
        for k in (5, 9):
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
            edge_sets.append(cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2))
    # Adaptive threshold helps when the card border has weak contrast against paper.
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 41, 7)
    edge_sets.append(cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE,
                      cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)), iterations=2))

    image_area = h * w * scale * scale
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    candidates = []
    seen = set()
    for edges in edge_sets:
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < image_area * 0.025 or area > image_area * 0.88:
                continue
            perimeter = cv2.arcLength(contour, True)
            for epsilon in (0.012, 0.018, 0.025, 0.035, 0.05, 0.07):
                poly = cv2.approxPolyDP(contour, epsilon * perimeter, True)
                if len(poly) != 4 or not cv2.isContourConvex(poly):
                    continue
                q = order_quad(poly.reshape(4, 2))
                lens = np.array([np.linalg.norm(q[(i + 1) % 4] - q[i]) for i in range(4)])
                horizontal = (lens[0] + lens[2]) / 2
                vertical = (lens[1] + lens[3]) / 2
                long_side, short_side = max(horizontal, vertical), min(horizontal, vertical)
                ratio = long_side / max(short_side, 1)
                if not 1.30 <= ratio <= 1.92:
                    continue
                # Require roughly parallel opposite edges; perspective can still be substantial.
                parallel_error = (abs(lens[0] - lens[2]) + abs(lens[1] - lens[3])) / (long_side + short_side)
                ratio_error = abs(math.log(ratio / (CARD_MM[0] / CARD_MM[1])))
                area_fraction = area / image_area
                # Reject paper folds and page edges: a real ID has color inside its frame,
                # while the paper/fabric immediately around it is usually less saturated.
                polygon_mask = np.zeros((h if scale == 1 else small.shape[0], w if scale == 1 else small.shape[1]), dtype=np.uint8)
                cv2.fillConvexPoly(polygon_mask, np.round(q).astype(np.int32), 255)
                expanded = cv2.dilate(polygon_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
                outside_mask = cv2.subtract(expanded, polygon_mask)
                inside_sat = float(np.mean(hsv[:, :, 1][polygon_mask > 0])) if np.any(polygon_mask) else 0.0
                outside_sat = float(np.mean(hsv[:, :, 1][outside_mask > 0])) if np.any(outside_mask) else 0.0
                color_separation = inside_sat - outside_sat
                # A card can fill most of a photo, but a quad around the whole scene
                # should lose to a smaller card-shaped quad when the extra area is
                # mostly paper, tile, or fabric. Guatemalan DPI cards usually contain
                # appreciable cyan/blue/green ink; use that as supporting evidence,
                # never as the sole detector (lighting and card side vary).
                core = cv2.erode(polygon_mask, cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE, (max(3, k), max(3, k)))) > 0
                core_hsv = hsv[core]
                if len(core_hsv):
                    cyan_fraction = float(np.mean((core_hsv[:, 0] >= 45) &
                                                  (core_hsv[:, 0] <= 110) &
                                                  (core_hsv[:, 1] >= 35)))
                else:
                    cyan_fraction = 0.0
                oversized_scene_penalty = (max(0.0, area_fraction - 0.58) * 2.5
                                           * (1.0 - min(cyan_fraction / 0.30, 1.0)))
                margin_x, margin_y = 0.015 * small.shape[1], 0.015 * small.shape[0]
                touches_photo_edge = (np.min(q[:, 0]) < margin_x or np.max(q[:, 0]) > small.shape[1] - margin_x or
                                      np.min(q[:, 1]) < margin_y or np.max(q[:, 1]) > small.shape[0] - margin_y)
                edge_penalty = 0.45 if touches_photo_edge else 0.0
                score = (2.3 * ratio_error + 0.55 * parallel_error
                         - 0.18 * math.sqrt(area_fraction)
                         + max(0.0, 12.0 - color_separation) / 35.0
                         + oversized_scene_penalty + edge_penalty)
                key = tuple(np.round(q.flatten() / max(scale, 1e-6) / 8).astype(int))
                if key in seen:
                    continue
                seen.add(key)
                candidates.append((score, q / scale))
                break

    # Add a second detector that looks for the actual blue/cyan/green card body.
    # Edge-only methods often close around the notebook or sheet behind a DPI because
    # that outer edge is stronger than the card's rounded border. Color segmentation
    # supplies an independent, card-specific contour for those photographs.
    color_ranges = ((30, 115, 18, 50), (40, 108, 24, 55), (48, 105, 30, 60))
    for hue_lo, hue_hi, sat_lo, val_lo in color_ranges:
        color_mask = cv2.inRange(hsv, np.array([hue_lo, sat_lo, val_lo], np.uint8),
                                 np.array([hue_hi, 255, 255], np.uint8))
        for close_size in (11, 21):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_size, close_size))
            closed = cv2.morphologyEx(color_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < image_area * 0.025 or area > image_area * 0.88:
                    continue
                rect = cv2.minAreaRect(contour)
                rw, rh = rect[1]
                ratio = max(rw, rh) / max(min(rw, rh), 1.0)
                if not 1.30 <= ratio <= 1.92:
                    continue
                perimeter = cv2.arcLength(contour, True)
                poly = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
                quad = poly.reshape(4, 2) if len(poly) == 4 and cv2.isContourConvex(poly) else cv2.boxPoints(rect)
                q = order_quad(quad)
                lens = np.array([np.linalg.norm(q[(i + 1) % 4] - q[i]) for i in range(4)])
                long_side = max((lens[0] + lens[2]) / 2, (lens[1] + lens[3]) / 2)
                short_side = min((lens[0] + lens[2]) / 2, (lens[1] + lens[3]) / 2)
                ratio = long_side / max(short_side, 1.0)
                if not 1.30 <= ratio <= 1.92:
                    continue
                polygon_mask = np.zeros(small.shape[:2], dtype=np.uint8)
                cv2.fillConvexPoly(polygon_mask, np.round(q).astype(np.int32), 255)
                core = cv2.erode(polygon_mask, cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE, (9, 9))) > 0
                core_hsv = hsv[core]
                if len(core_hsv) == 0:
                    continue
                cyan_fraction = float(np.mean((core_hsv[:, 0] >= 35) &
                                              (core_hsv[:, 0] <= 115) &
                                              (core_hsv[:, 1] >= 18)))
                if cyan_fraction < 0.08:
                    continue
                area_fraction = abs(cv2.contourArea(q.astype(np.float32))) / image_area
                ratio_error = abs(math.log(ratio / (CARD_MM[0] / CARD_MM[1])))
                parallel_error = (abs(lens[0] - lens[2]) + abs(lens[1] - lens[3])) / max(long_side + short_side, 1)
                outside_penalty = max(0.0, area_fraction - 0.58) * 2.5 * (1.0 - min(cyan_fraction / 0.30, 1.0))
                margin_x, margin_y = 0.015 * small.shape[1], 0.015 * small.shape[0]
                touches_photo_edge = (np.min(q[:, 0]) < margin_x or np.max(q[:, 0]) > small.shape[1] - margin_x or
                                      np.min(q[:, 1]) < margin_y or np.max(q[:, 1]) > small.shape[0] - margin_y)
                edge_penalty = 0.45 if touches_photo_edge else 0.0
                score = (2.3 * ratio_error + 0.55 * parallel_error
                         - 0.12 * math.sqrt(area_fraction)
                         + max(0.0, 0.18 - cyan_fraction) * 1.5
                         + outside_penalty + edge_penalty - 0.08)
                key = tuple(np.round(q.flatten() / max(scale, 1e-6) / 8).astype(int))
                if key in seen:
                    continue
                seen.add(key)
                candidates.append((score, q / scale))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    # Keep several plausible frames. OCR in the worker chooses the candidate containing
    # DPI text, rather than trusting the largest paper/notebook rectangle.
    return [(score, refine_quad_edges(rgb, quad))
            for score, quad in candidates[:8] if score <= 0.48]


def eight_outline_points(quad):
    q = np.asarray(quad, dtype=np.float32)
    mids = [(q[i] + q[(i + 1) % 4]) / 2 for i in range(4)]
    points = []
    for i in range(4):
        points.extend([q[i], mids[i]])
    return np.array(points, dtype=np.float32)


def orientation_score(ocr, rgb):
    """Score OCR and whether card landmarks occupy their expected upright zones."""
    result = ocr(rgb)
    raw_words = result.txts if result.txts is not None else []
    raw_scores = result.scores if result.scores is not None else []
    boxes = result.boxes if result.boxes is not None else []
    words = [str(x).strip() for x in raw_words if str(x).strip()]
    confs = [float(x) for x in raw_scores]
    text = " ".join(words).upper()
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    hints = ("GUATEMALA", "RENAP", "PERSONAS", "IDENTIFICACION", "IDGT", "CUI")
    hits = [hint for hint in hints if hint in normalized]
    char_count = sum(ch.isalnum() for ch in text)
    # OCR confidence/readable text picks up the card, but cannot decide orientation
    # on its own. A label's vertical location and the MRZ's bottom position are much
    # stronger signals for a Guatemalan DPI.
    landmarks = []
    h = rgb.shape[0]
    for word, box, confidence in zip(raw_words, boxes, raw_scores):
        normalized_word = unicodedata.normalize("NFKD", str(word).upper())
        normalized_word = "".join(ch for ch in normalized_word if not unicodedata.combining(ch))
        compact = "".join(ch for ch in normalized_word if ch.isalnum() or ch == "<")
        y = float(np.mean(np.asarray(box, dtype=np.float32)[:, 1])) / max(1, h)
        landmarks.append((normalized_word, compact, y, float(confidence)))

    direction_score = 0.0
    evidence = []
    for word, compact, y, confidence in landmarks:
        if any(token in word for token in ("REPUBLICA", "GUATEMALA", "CENTROAMERICA")):
            direction_score += (22 if y < 0.32 else -22 if y > 0.68 else 0) * confidence
            evidence.append("encabezado")
        if ("IDGTM" in compact or "GTM<<" in compact or
                (compact.count("<") >= 5 and len(compact) >= 18)):
            direction_score += (34 if y > 0.66 else -34 if y < 0.34 else 0) * confidence
            evidence.append("MRZ")
        if "FIRMA" in word:
            direction_score += (12 if y > 0.64 else -12 if y < 0.36 else 0) * confidence
            evidence.append("firma")
        if any(token in word for token in ("LUGAR", "NACIMIENTO", "APELLIDO", "NOMBRE",
                                           "VECINDAD", "ESTADO CIVIL", "VENCIMIENTO")):
            direction_score += (4 if 0.08 <= y <= 0.72 else -5 if y > 0.82 else 0) * confidence

    # Normalize quality to avoid a high word count in a background-heavy crop winning
    # simply because it exposes more characters.
    mean_conf = sum(confs) / max(1, len(confs))
    score = min(len(hits), 4) * 8 + min(char_count, 90) * 0.12 + mean_conf * 8
    return score, text, hits, direction_score, sorted(set(evidence))


def rectify_and_orient(rgb, quad, ocr, dpi=DEFAULT_DPI):
    q = order_quad(quad)
    widths = (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / 2
    heights = (np.linalg.norm(q[3] - q[0]) + np.linalg.norm(q[2] - q[1])) / 2
    # Put the long physical edge on the horizontal output axis. For vertical phone shots,
    # start by bringing the photographed left edge to the top; OCR will choose 0 or 180.
    if heights > widths:
        src = np.array([q[3], q[0], q[1], q[2]], dtype=np.float32)
    else:
        src = q
    out_w = round(CARD_MM[0] / 25.4 * dpi)
    out_h = round(CARD_MM[1] / 25.4 * dpi)
    dst = np.array([[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    crop = cv2.warpPerspective(rgb, matrix, (out_w, out_h), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE)
    upside_down = cv2.rotate(crop, cv2.ROTATE_180)
    score0, text0, hits0, direction0, evidence0 = orientation_score(ocr, crop)
    score180, text180, hits180, direction180, evidence180 = orientation_score(ocr, upside_down)
    # Landmark geometry is the primary decision. Text readability breaks ties only;
    # it is common for names and ID numbers to be recognized upside down as well.
    chosen_rotation = 180 if direction180 > direction0 else 0
    if abs(direction180 - direction0) < 5:
        chosen_rotation = 180 if score180 > score0 else 0
    chosen = upside_down if chosen_rotation else crop
    best_score = max(score0, score180)
    best_hits = hits180 if chosen_rotation else hits0
    best_direction = direction180 if chosen_rotation else direction0
    best_evidence = evidence180 if chosen_rotation else evidence0
    # Require actual positional evidence (header/MRZ/signature) to auto-publish.
    # Generic OCR hits alone previously allowed some upside-down cards through.
    reliable_orientation = bool(best_hits) and best_direction >= 12 and abs(direction180 - direction0) >= 18
    orientation = (f"OCR {chosen_rotation}°; pistas: {', '.join(best_hits) or 'ninguna'}; "
                   f"estructura: {', '.join(best_evidence) or 'sin señales direccionales'}")
    return (Image.fromarray(chosen, "RGB"), out_w, out_h, chosen_rotation,
            orientation, eight_outline_points(quad), best_score, reliable_orientation)


def save_rounded(image, path, dpi, brightness=1.0, contrast=1.0):
    im = ImageEnhance.Brightness(image).enhance(brightness)
    im = ImageEnhance.Contrast(im).enhance(contrast).convert("RGBA")
    w, h = im.size
    scale = 4
    radius = round(min(w, h) * 0.055)
    mask = Image.new("L", (w * scale, h * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * scale - 1, h * scale - 1),
                                           radius=radius * scale, fill=255)
    im.putalpha(mask.resize((w, h), Image.Resampling.LANCZOS))
    im.save(path, "PNG", dpi=(dpi, dpi), optimize=True)


class BatchCropper:
    def __init__(self, root):
        self.root = root
        root.title("Recorte automático de DPI por lote")
        root.geometry("760x490")
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.queue = queue.Queue()
        self.running = False
        self._build()
        self.root.after(100, self._poll)

    def _build(self):
        box = ttk.Frame(self.root, padding=18); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Procesar fotos de DPI automáticamente", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))
        ttk.Label(box, text="Carpeta con fotos:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(box, textvariable=self.input_dir, width=70).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(box, text="Elegir…", command=self.choose_input).grid(row=1, column=2)
        ttk.Label(box, text="Carpeta de salida:").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(box, textvariable=self.output_dir, width=70).grid(row=2, column=1, sticky="ew", padx=8)
        ttk.Button(box, text="Elegir…", command=self.choose_output).grid(row=2, column=2)
        ttk.Label(box, text="DPI se ajusta automáticamente a 300. Tamaño de tarjeta: 85.60 × 53.98 mm.").grid(row=3, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Label(box, text="PNG con fondo transparente y esquinas redondeadas; los originales se conservan.").grid(row=4, column=0, columnspan=3, sticky="w", pady=(0, 12))
        self.progress = ttk.Progressbar(box, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=6)
        self.status = ttk.Label(box, text="Selecciona las carpetas. Los originales se conservan.", wraplength=700)
        self.status.grid(row=6, column=0, columnspan=3, sticky="w", pady=6)
        self.start_btn = ttk.Button(box, text="Procesar carpeta", command=self.start)
        self.start_btn.grid(row=7, column=0, sticky="w", pady=12)
        ttk.Label(box, text="Marca 8 referencias, corrige perspectiva y compara 0°/180° con OCR integrado. Los casos dudosos se envían a revisión y no a la carpeta final.", wraplength=700).grid(row=8, column=0, columnspan=3, sticky="w")
        box.columnconfigure(1, weight=1)

    def choose_input(self):
        p = filedialog.askdirectory(title="Elige la carpeta que contiene las fotos")
        if p:
            self.input_dir.set(p)
            if not self.output_dir.get():
                self.output_dir.set(str(Path(p) / "recortadas"))

    def choose_output(self):
        p = filedialog.askdirectory(title="Elige dónde guardar los recortes")
        if p: self.output_dir.set(p)

    def start(self):
        src, dst = Path(self.input_dir.get()), Path(self.output_dir.get())
        if not src.is_dir() or not str(dst):
            messagebox.showwarning("Faltan carpetas", "Selecciona la carpeta de fotos y la carpeta de salida."); return
        files = [p for p in src.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED]
        if not files:
            messagebox.showinfo("No hay fotos", "La carpeta no contiene archivos de imagen compatibles."); return
        if dst.resolve() == src.resolve():
            messagebox.showwarning("Carpetas iguales", "Elige una carpeta de salida distinta a la carpeta de originales."); return
        self.running = True
        self.start_btn.config(state="disabled")
        self.progress.configure(maximum=len(files), value=0)
        threading.Thread(target=self._worker, args=(files, dst, DEFAULT_DPI), daemon=True).start()

    def _worker(self, files, dst, dpi):
        dst.mkdir(parents=True, exist_ok=True)
        report = []
        review_dir = dst / "revision"
        marks_dir = dst.parent / "marcas_8_puntos" 
        try:
            ocr = RapidOCR()
        except Exception as exc:
            self.queue.put((0, len(files), f"No se pudo iniciar OCR: {exc}. No se generarán recortes finales."))
            self.queue.put((len(files), len(files), "Instalación OCR fallida; revisa dependencias."))
            return
        for index, path in enumerate(files, 1):
            try:
                with Image.open(path) as im:
                    pil = ImageOps.exif_transpose(im).convert("RGB")
                rgb = np.asarray(pil)
                candidates = find_card_quad(rgb)
                if not candidates:
                    report.append((path.name, "revisión", "Borde poco confiable; se conserva original", ""))
                    self.queue.put((index, len(files), f"{path.name}: detección dudosa, no se guarda recorte final"))
                    continue
                options = []
                for detection_score, quad in candidates:
                    result, w, h, rotation, method, points8, ocr_score, reliable = rectify_and_orient(rgb, quad, ocr, dpi)
                    has_card_text = any(hint in method for hint in ("GUATEMALA", "RENAP", "PERSONAS", "IDENTIFICACION", "IDGT", "CUI"))
                    # Keep OCR as a card-identity signal, but stop rewarding broad
                    # background crops just because they contain more readable text.
                    # Geometry/color set by find_card_quad has a strong vote here.
                    quad_area = abs(cv2.contourArea(np.asarray(quad, dtype=np.float32)))
                    photo_area = max(1.0, rgb.shape[0] * rgb.shape[1])
                    area_fraction = quad_area / photo_area
                    area_prior = (16 if 0.06 <= area_fraction <= 0.45 else 0)
                    area_prior -= max(0.0, area_fraction - 0.45) * 80
                    quality = (area_prior
                               + min(4, len([h for h in ("GUATEMALA", "RENAP", "PERSONAS",
                                                        "IDENTIFICACION", "IDGT", "CUI")
                                             if h in method])) * 14
                               + min(ocr_score, 60) * 0.25
                               + (28 if reliable else 0)
                               - detection_score * 65)
                    options.append((quality, detection_score, result, w, h, rotation, method, points8, ocr_score, reliable, has_card_text))
                options.sort(key=lambda item: item[0], reverse=True)
                _, detection_score, result, w, h, rotation, method, points8, ocr_score, reliable, has_card_text = options[0]
                # Save a marked copy to audit exactly which eight outline references were chosen.
                marked = rgb.copy()
                poly = np.round(points8).astype(np.int32).reshape(-1, 1, 2)
                cv2.polylines(marked, [poly], True, (255, 40, 30), max(2, round(max(rgb.shape[:2]) / 450)), cv2.LINE_AA)
                radius = max(4, round(max(rgb.shape[:2]) / 180))
                for n, (x, y) in enumerate(points8, 1):
                    cv2.circle(marked, (round(x), round(y)), radius, (20, 40, 255), -1, cv2.LINE_AA)
                    cv2.putText(marked, str(n), (round(x)+radius, round(y)-radius), cv2.FONT_HERSHEY_SIMPLEX,
                                max(0.7, max(rgb.shape[:2])/1800), (255, 255, 255), 2, cv2.LINE_AA)
                marks_dir.mkdir(parents=True, exist_ok=True)
                Image.fromarray(marked).save(marks_dir / f"{path.stem}_marcas.jpg", quality=88)
                if not reliable or not has_card_text:
                    review_dir.mkdir(parents=True, exist_ok=True)
                    save_rounded(result, review_dir / f"REVISAR_{path.stem}.png", dpi)
                    report.append((path.name, "revisión", method, f"detector={detection_score:.3f}; OCR={ocr_score:.1f}"))
                    self.queue.put((index, len(files), f"{path.name}: OCR/orientación dudosa; candidato en revision"))
                    continue
                target = dst / f"{path.stem}_recortada.png"
                save_rounded(result, target, dpi)
                report.append((path.name, "procesada", method, f"giro OCR {rotation}°; 8 puntos; detector={detection_score:.3f}; OCR={ocr_score:.1f}"))
                self.queue.put((index, len(files), f"{path.name}: recortada ({method})"))
            except Exception as exc:
                report.append((path.name, "error", str(exc), ""))
                self.queue.put((index, len(files), f"{path.name}: error: {exc}"))
        try:
            with (dst / "informe_procesamiento.csv").open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f); writer.writerow(["archivo", "estado", "orientación o motivo", "detalle"]); writer.writerows(report)
        except Exception:
            pass
        self.queue.put((len(files), len(files), f"Terminado: {sum(r[1]=='procesada' for r in report)} finales, {sum(r[1]=='revisión' for r in report)} para revisar. DPI fijo: 300. Revisa informe_procesamiento.csv."))

    def _poll(self):
        try:
            while True:
                current, total, msg = self.queue.get_nowait()
                self.progress.configure(maximum=total, value=current)
                self.status.config(text=msg)
                if current >= total:
                    self.running = False
                    self.start_btn.config(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


if __name__ == "__main__":
    root = tk.Tk()
    app = BatchCropper(root)
    root.mainloop()
