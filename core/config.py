"""User configuration and target catalogue.

Targets are loaded from CSV files in two locations: a read-only seed
directory bundled with the app, and a user-writable directory under the
app data folder. User files override seeds with the same key, so a
shooter can tweak a built-in target without losing the original.

The runtime config is a plain JSON dict persisted to the user data dir.
"""

from __future__ import annotations

import json
import logging
import math
import re
import tempfile
import os
import shutil
from typing import Iterable, Optional, Tuple

from core.paths import config_path, resource_path, user_targets_dir

VERSION = "1.3"

CONFIG_FILE = str(config_path())


def _migrate_legacy_config() -> None:
    """Copy any pre-1.2 config beside ``main.py`` into the user data dir."""
    if os.path.exists(CONFIG_FILE):
        return
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    legacy = os.path.join(project_root, "splatt2_config.json")
    if not os.path.isfile(legacy):
        return
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        shutil.copy2(legacy, CONFIG_FILE)
        print(f"[Config] Migrated legacy config -> {CONFIG_FILE}")
    except OSError as e:
        print(f"[Config] Could not migrate legacy config: {e}")


_migrate_legacy_config()


# Target CSV layout
# -----------------
# Header rows in ``key=value`` form, then a separator header, then data
# rows. Two header forms are accepted::
#
#     score,ring_diameter_mm
#     score_integer,score_decimal,ring_diameter_mm
#
# Ring diameters are visual only; scoring geometry is computed at runtime
# from ``card_diameter_mm`` and the configured pellet calibre.

_DATA_HEADERS = (
    "score,ring_diameter_mm",
    "score_integer,score_decimal,ring_diameter_mm",
)


def bundled_targets_dir() -> str:
    """Read-only directory of bundled target CSVs."""
    return str(resource_path("targets"))


def writable_targets_dir() -> str:
    """User-writable directory of target CSVs."""
    return str(user_targets_dir())


# Backwards-compatible aliases used by the UI module.
_targets_dir = bundled_targets_dir
_user_targets_dir = writable_targets_dir


def _parse_csv_row(parts: list) -> Optional[Tuple[float, float]]:
    """Return ``(score, diameter_mm)`` for a CSV data row, or ``None``."""
    if len(parts) == 2:
        return float(parts[0]), float(parts[1])
    if len(parts) == 3:
        # Legacy three-column format: score_integer, score_decimal, diameter.
        return float(parts[0]), float(parts[2])
    return None


def _quincunx_offsets(spacing_mm: float) -> list:
    """Five mark centres in a quincunx pattern at the given spacing."""
    h = spacing_mm / 2
    return [
        (-h, -h), (+h, -h),
        (0.0, 0.0),
        (-h, +h), (+h, +h),
    ]


def _resolve_mark_offsets(meta: dict) -> Optional[list]:
    """Build mark centres for a multi-mark target, or ``None``."""
    mark_count = int(meta.get("mark_count", 1))
    if mark_count <= 1:
        return None
    spacing = float(meta.get("mark_spacing_mm", 75.0))
    if mark_count == 5:
        return _quincunx_offsets(spacing)
    return None


def load_target_csv(path: str) -> Optional[dict]:
    """Parse a single target CSV into a target dict, or ``None`` on error."""
    meta: dict = {}
    scores: list = []
    diameters: list = []
    in_data = False

    try:
        with open(path, newline="", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower() in _DATA_HEADERS:
                    in_data = True
                    continue
                if in_data:
                    row = _parse_csv_row([p.strip() for p in line.split(",")])
                    if row is not None:
                        scores.append(row[0])
                        diameters.append(row[1])
                else:
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        meta[parts[0].strip().lower()] = parts[1].strip()
    except Exception as e:
        print(f"[Targets] Could not load {path}: {e}")
        return None

    if not scores or "key" not in meta or "name" not in meta:
        return None

    rings_mm = [d / 2.0 for d in diameters]
    outer_dia = float(meta.get("card_diameter_mm", diameters[-1]))
    aiming_dia = float(meta.get("aiming_mark_dia_mm", diameters[0]))
    unique_dias = list(dict.fromkeys(diameters))
    ring_labels = [str(int(s)) if s == int(s) else str(s) for s in scores]
    mark_count = int(meta.get("mark_count", 1))

    # Optional explicit bull diameter for the renderer; targets that
    # don't set this fall back to the historical "outer 4 rings dark,
    # inner 6 rings light" rule applied in TargetRenderer.
    bull_dia = meta.get("bull_dia_mm")
    bull_dia = float(bull_dia) if bull_dia is not None else None

    return {
        "name": meta["name"],
        "key": meta["key"],
        "diameter_mm": outer_dia,
        "rings_mm": rings_mm,
        "ring_scores": scores,
        "gauging": meta.get("gauging", "outward"),
        "calibre_mm": float(meta.get("calibre_mm", 4.5)),
        "reference_dist_m": float(meta.get("reference_dist_m", 10.0)),
        "aiming_mark_dia_mm": aiming_dia,
        "bull_dia_mm": bull_dia,
        "outer_ring_dia_mm": outer_dia,
        "rings_dia_mm": unique_dias,
        "ring_labels": ring_labels,
        "a4_target_width_mm": float(
            meta.get("a4_target_width_mm", min(outer_dia * 1.1, 170))),
        "mark_count": mark_count,
        "mark_offsets": _resolve_mark_offsets(meta),
        "mark_spacing_mm": float(meta.get("mark_spacing_mm", 0)),
    }


# Backwards-compatible alias.
_load_target_csv = load_target_csv


def _iter_target_files(directories: Iterable[str]):
    """Yield ``(directory, filename)`` for every CSV in the given dirs."""
    for tdir in directories:
        if not os.path.isdir(tdir):
            continue
        for fname in sorted(os.listdir(tdir)):
            if fname.lower().endswith(".csv"):
                yield tdir, fname


def load_all_targets() -> dict:
    """Merge target CSVs from the bundle and the user dir into a dict."""
    targets: dict = {}
    for tdir, fname in _iter_target_files(
            (bundled_targets_dir(), writable_targets_dir())):
        target = load_target_csv(os.path.join(tdir, fname))
        if target:
            targets[target["key"]] = target
    return targets


_load_all_targets = load_all_targets

TARGETS = load_all_targets()


DEFAULT_CONFIG = {
    # Target & scoring
    "target_key": "10m_air_rifle",
    "real_range_m": 10.0,
    "shot_circle_calibre_mm": 4.5,
    "scoring_calibre_mm": 4.5,
    "decimal_scoring": False,
    "ignore_misses": False,

    # Target appearance: manual ring count controls the fill boundary.
    "target_inner_rings": 5,
    "target_score_rings": 5,
    "target_score_top": False,
    "target_score_right": True,
    "target_score_bottom": False,
    "target_score_left": False,
    "colour_target_outer": "#fbe2a9",
    "colour_target_inner": "#0f0f0f",
    "colour_target_outer_lines": "#000000",
    "colour_target_inner_lines": "#ffffff",

    # Camera
    "camera_index": 0,
    "video_width": 1920,
    "video_height": 1080,
    "video_fps": 30,
    "camera_rotation": 0,
    "flip_image": False,
    "flip_mode": -1,
    "no_video_mode": False,
    "use_clahe": True,
    "clahe_clip": 4.0,
    "brightness_target": 128.0,
    "spike_velocity_mm": 25.0,
    "spike_reversal": 0.7,
    # Unsharp-mask amount applied after CLAHE. 0 disables; 0.5 - 1.5
    # is the useful range for crisping up soft marker edges.
    "sharpen": 0.0,
    # Cap for the frame size handed to the ArUco detector. Lower is
    # faster; higher preserves more pixels per marker, which matters
    # when the camera is far from the printed sheet.
    "detection_max_width": 1920,
    "detection_max_height": 1080,
    # Digital zoom applied before detection. 1.0 disables; values up
    # to 4.0 centre-crop the frame so distant markers fill more pixels.
    "camera_zoom": 1.0,

    # ArUco tracking
    "aruco_dict": "DICT_4X4_50",
    "aruco_marker_count": "Auto",  # Or 4, 6, 8 for a fixed printed layout.
    "camera_pixel_format": "Auto",
    "aruco_marker_mm": 40.0,
    "aruco_margin_mm": 8.0,

    # Smoothing
    "smooth_mode": "ema",
    "smooth_alpha": 0.35,
    "smooth_window": 11,
    "smooth_poly": 2,

    # Audio detection
    "audio_device_index": None,
    "audio_sample_rate": 44100,
    "audio_trigger_threshold": 0.4,
    "audio_transient_ratio": 6.0,
    "audio_trigger_cooldown_ms": 800,
    "post_shot_cooldown_s": 2.0,

    # Trace and shot colours (hex; converted to BGR at render time)
    "colour_trace_approach": "#3c3c3c",
    "colour_trace_hold":     "#28be50",
    "colour_trace_preshot":  "#f0d000",
    "colour_trace_final":    "#e03020",
    "colour_shot_fill":      "#5050ff",
    "colour_acp":            "#ffc800",
    "colour_crosshair":      "#00dc64",
    "colour_mpi":            "#50b4ff",
    "colour_group":          "#6464ff",
    "colour_miss":           "#3c3cd0",

    # Trace behaviour
    "trace_width": 1,
    "trace_preshot_s": 1.0,
    "trace_final_s": 0.2,
    "fading_trace_duration_s": 2.0,
    "acp_fraction": 0.40,
    "approach_zone_factor": 2.0,

    # Persisted zero offset
    "zero_offset_x": 0.0,
    "zero_offset_y": 0.0,

    # Session & files
    "session_name": "Session",
    "shooter_name": "",
    "shots_per_series": 10,
    "save_directory": "",

    # Voice feedback
    "voice_enabled": True,  # speak scores and clock positions
    "voice_id": "",  # Empty selects the system default voice.
    "voice_rate": 175,
    "voice_volume": 1.0,
    "voice_mode": "score_direction",
}


# Limits protect the camera, renderer and audio backend from invalid input.
_LIMITS = {
    "video_width": (160, 7680), "video_height": (120, 4320), "video_fps": (1, 240),
    "detection_max_width": (160, 7680), "detection_max_height": (120, 4320),
    "camera_index": (0, 100), "camera_zoom": (1, 8),
    "aruco_marker_mm": (1, 95), "aruco_margin_mm": (0, 50),
    "real_range_m": (0.1, 1000), "shot_circle_calibre_mm": (0.1, 50),
    "scoring_calibre_mm": (0.1, 50), "shots_per_series": (1, 1000),
    "target_inner_rings": (0, 100), "target_score_rings": (0, 100),
    "audio_sample_rate": (8000, 192000), "audio_trigger_threshold": (0.005, 1),
    "audio_transient_ratio": (1.5, 20), "audio_trigger_cooldown_ms": (0, 60000),
    "post_shot_cooldown_s": (0, 60), "clahe_clip": (0.1, 40),
    "brightness_target": (1, 255), "sharpen": (0, 5),
    "smooth_alpha": (0.001, 1), "smooth_window": (3, 101), "smooth_poly": (1, 20),
    "spike_velocity_mm": (0.1, 1000), "spike_reversal": (0, 1),
    "trace_width": (1, 20), "trace_preshot_s": (0.01, 120),
    "trace_final_s": (0, 120), "fading_trace_duration_s": (0.01, 120),
    "acp_fraction": (0.01, 1), "approach_zone_factor": (1, 20),
    "voice_rate": (80, 350), "voice_volume": (0, 1),
}
_CHOICES = {
    "voice_mode": ("score", "score_direction"),
    "camera_rotation": (0, 90, 180, 270), "flip_mode": (-1, 0, 1),
    "camera_pixel_format": ("Auto", "MJPEG", "YUY2"),
    "smooth_mode": ("none", "ema", "savgol"),
}


def validate_config(cfg):
    """Return readable errors without modifying the proposed settings."""
    errors = {}
    for key, default in DEFAULT_CONFIG.items():
        value = cfg.get(key, default)
        if key == "aruco_marker_count":
            if value not in ("Auto", 4, 6, 8, "4", "6", "8"):
                errors[key] = "Choose Auto, 4, 6 or 8."
            continue
        if default is None:
            if value is not None and (type(value) is not int or value < 0):
                errors[key] = "Use a non-negative device index or the default."
            continue
        if isinstance(default, bool):
            valid = type(value) is bool
        elif isinstance(default, int):
            valid = type(value) is int
        elif isinstance(default, float):
            valid = type(value) in (int, float) and math.isfinite(value)
        else:
            valid = isinstance(value, str)
        if not valid:
            errors[key] = f"Expected {type(default).__name__}."
            continue
        if key in _LIMITS:
            lo, hi = _LIMITS[key]
            if not lo <= value <= hi:
                errors[key] = f"Must be between {lo} and {hi}."
        if key in _CHOICES and value not in _CHOICES[key]:
            errors[key] = f"Choose one of {_CHOICES[key]}."
        if key.startswith("colour_") and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
            errors[key] = "Use a colour in #RRGGBB format."
    if cfg.get("target_key", DEFAULT_CONFIG["target_key"]) not in TARGETS:
        errors["target_key"] = "Target is not available."
    if not any(k in errors for k in ("smooth_window", "smooth_poly")):
        window = cfg.get("smooth_window", 11)
        if window % 2 == 0 or cfg.get("smooth_poly", 2) >= window:
            errors["smooth_window"] = "Use an odd window larger than the polynomial order."
            errors["smooth_poly"] = "Polynomial order must be smaller than the window."
    if not any(k in errors for k in ("trace_final_s", "trace_preshot_s")):
        if cfg.get("trace_final_s", 0.2) > cfg.get("trace_preshot_s", 1.0):
            errors["trace_final_s"] = "Cannot exceed the pre-shot window."
            errors["trace_preshot_s"] = "Cannot be shorter than the final window."
    if not any(k in errors for k in ("aruco_marker_mm", "aruco_margin_mm")):
        if 2 * (cfg.get("aruco_marker_mm", 40) + cfg.get("aruco_margin_mm", 8)) >= 210:
            errors["aruco_marker_mm"] = "Markers and margins must fit on the A4 sheet."
            errors["aruco_margin_mm"] = "Markers and margins must fit on the A4 sheet."
    return errors


CONFIG_WARNINGS = []


def load_config() -> Tuple[dict, bool]:
    """Load valid settings; report invalid saved fields and use their defaults."""
    CONFIG_WARNINGS.clear()
    cfg = DEFAULT_CONFIG.copy()
    if not os.path.exists(CONFIG_FILE):
        return cfg, True
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if not isinstance(saved, dict):
            raise ValueError("Configuration must be a JSON object")
        for old, new in {
            "target_black_rings": "target_inner_rings",
            "colour_target_paper": "colour_target_outer",
            "colour_target_black": "colour_target_inner",
        }.items():
            if old in saved:
                saved.setdefault(new, saved.pop(old))
        # Older settings dialogs stored an empty directory as JSON null.
        if saved.get("save_directory") is None:
            saved["save_directory"] = ""
        cfg.update(saved)
        errors = validate_config(cfg)
        for key, reason in errors.items():
            CONFIG_WARNINGS.append(f"{key}: {reason} Default restored.")
            cfg[key] = DEFAULT_CONFIG[key]
        if CONFIG_WARNINGS:
            logging.getLogger(__name__).warning("Invalid config: %s", CONFIG_WARNINGS)
        return cfg, False
    except (OSError, ValueError, TypeError) as exc:
        CONFIG_WARNINGS.append(f"Could not load settings: {exc}. Defaults used.")
        logging.getLogger(__name__).exception("Could not load settings")
        return DEFAULT_CONFIG.copy(), True


def save_config(cfg: dict) -> None:
    """Validate and atomically replace the file; propagate failures to the UI."""
    errors = validate_config(cfg)
    if errors:
        raise ValueError("\n".join(f"{k}: {v}" for k, v in errors.items()))
    directory = os.path.dirname(CONFIG_FILE)
    os.makedirs(directory, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         prefix=".config-", suffix=".tmp", delete=False) as f:
            name = f.name
            json.dump(cfg, f, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, CONFIG_FILE)
    finally:
        if name is not None and os.path.exists(name):
            os.unlink(name)
