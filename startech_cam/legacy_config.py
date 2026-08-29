"""Translate one validated KERİM document into the canon ``LEGACY/config.py``.

KERİM deliberately edits only constants for which its document has a direct
meaning.  The generator parses the existing Python file, replaces those values,
and leaves GPIO pins, timings, helper functions and comments alone.
"""

from __future__ import annotations

import ast
from typing import Any

from arac.startech.configuration.combined import combined_config_errors


class LegacyConfigError(ValueError):
    """A KERİM document cannot be represented by the canon config file."""


def _tuple(value: list[int]) -> tuple[int, ...]:
    return tuple(value)


def _first_range(colours: dict[str, Any], name: str) -> dict[str, Any]:
    return colours[name]["araliklar"][0]


def _mapped_values(document: dict[str, Any]) -> dict[str, Any]:
    errors = combined_config_errors(document)
    if errors:
        raise LegacyConfigError("; ".join(errors))

    calibration = document["kalibrasyon"]
    settings = document["ayarlar"]
    camera = calibration["kamera"]
    perspective = calibration["perspektif"]
    lane = calibration["serit"]
    profiles = lane["beyaz_profiller"]
    motor = calibration["motor"]
    colours = calibration["renkler"]
    control = settings["kontrol"]
    speed = settings["hiz"]

    red = colours["kirmizi_isik"]
    green = colours["yesil_isik"]
    if red["min_alan"] != green["min_alan"]:
        raise LegacyConfigError(
            "LEGACY/config.py uses one SIGNAL_MIN_AREA for red and green; "
            "KERİM values must match"
        )
    if len(red["araliklar"]) != 2:
        raise LegacyConfigError("red signal needs exactly two HSV ranges")
    parking = colours["kirmizi_park"]
    if len(parking["araliklar"]) != 2:
        raise LegacyConfigError("red parking needs exactly two HSV ranges")

    orange = _first_range(colours, "turuncu_arac")
    yellow = _first_range(colours, "sari_arac")
    green_range = _first_range(colours, "yesil_isik")
    blue = _first_range(colours, "mavi_levha")

    return {
        "WIDTH": camera["genislik"],
        "HEIGHT": camera["yukseklik"],
        "CAMERA_BGR_OUTPUT": camera["bgr_cikis"],
        "CAMERA_ROTATE_180": camera["dondur_180"],
        "ROI_TOP_RATIO": perspective["roi_ust_oran"],
        "PERSP_SRC": perspective["kaynak_noktalar"],
        "MIN_LANE_SIGNAL": lane["min_sinyal"],
        "MIN_LANE_SIGNAL_QUALITY_RATIO": lane["min_sinyal_kalite_orani"],
        "ASSUMED_LANE_WIDTH": lane["varsayilan_serit_genisligi"],
        "WHITE_HSV_LOW": _tuple(profiles["varsayilan"]["alt"]),
        "WHITE_HSV_HIGH": _tuple(profiles["varsayilan"]["ust"]),
        "WHITE_HSV_LOW_DARK": _tuple(profiles["karanlik"]["alt"]),
        "WHITE_HSV_HIGH_DARK": _tuple(profiles["karanlik"]["ust"]),
        "WHITE_HSV_LOW_NORMAL": _tuple(profiles["normal"]["alt"]),
        "WHITE_HSV_HIGH_NORMAL": _tuple(profiles["normal"]["ust"]),
        "WHITE_HSV_LOW_BRIGHT": _tuple(profiles["parlak"]["alt"]),
        "WHITE_HSV_HIGH_BRIGHT": _tuple(profiles["parlak"]["ust"]),
        "CLAHE_CLIP_LIMIT": lane["clahe_sinir"],
        "CLAHE_TILE_SIZE": lane["clahe_kutucuk"],
        "LANE_CONTINUITY_RATIO": lane["sureklilik_orani"],
        "KP": control["kp"],
        "KD": control["kd"],
        "KI": control["ki"],
        "INTEGRAL_MAX": control["integral_max"],
        "DERIV_CAP": control["deriv_cap"],
        "BASE_SPEED": speed["hedef"],
        "MIN_SPEED": speed["min"],
        "MAX_SPEED": speed["max"],
        "K_SPEED": speed["k_speed"],
        "LEFT_TRIM_LOW": motor["sol_trim_dusuk"],
        "LEFT_TRIM_HIGH": motor["sol_trim_yuksek"],
        "RIGHT_TRIM_LOW": motor["sag_trim_dusuk"],
        "RIGHT_TRIM_HIGH": motor["sag_trim_yuksek"],
        "DEAD_ZONE_MIN_PWM": motor["olu_bolge_min_pwm"],
        "DEAD_ZONE_PERCENT": motor["olu_bolge_yuzde"],
        "EVENT_NEAR_ROI_RATIO": settings["olay"]["yakin_roi_orani"],
        "ORANGE_HSV_LOW": _tuple(orange["alt"]),
        "ORANGE_HSV_HIGH": _tuple(orange["ust"]),
        "ORANGE_MIN_AREA": colours["turuncu_arac"]["min_alan"],
        "YELLOW_HSV_LOW": _tuple(yellow["alt"]),
        "YELLOW_HSV_HIGH": _tuple(yellow["ust"]),
        "YELLOW_MIN_AREA": colours["sari_arac"]["min_alan"],
        "RED_HSV_LOW1": _tuple(red["araliklar"][0]["alt"]),
        "RED_HSV_HIGH1": _tuple(red["araliklar"][0]["ust"]),
        "RED_HSV_LOW2": _tuple(red["araliklar"][1]["alt"]),
        "RED_HSV_HIGH2": _tuple(red["araliklar"][1]["ust"]),
        "GREEN_HSV_LOW": _tuple(green_range["alt"]),
        "GREEN_HSV_HIGH": _tuple(green_range["ust"]),
        "SIGNAL_MIN_AREA": red["min_alan"],
        "SIGN_BLUE_HSV_LOW": _tuple(blue["alt"]),
        "SIGN_BLUE_HSV_HIGH": _tuple(blue["ust"]),
        "SIGN_MIN_AREA": colours["mavi_levha"]["min_alan"],
        "PARKING_HSV_LOW1": _tuple(parking["araliklar"][0]["alt"]),
        "PARKING_HSV_HIGH1": _tuple(parking["araliklar"][0]["ust"]),
        "PARKING_HSV_LOW2": _tuple(parking["araliklar"][1]["alt"]),
        "PARKING_HSV_HIGH2": _tuple(parking["araliklar"][1]["ust"]),
        "PARKING_MIN_AREA": parking["min_alan"],
        "PARKING_TRIGGER_AREA": parking["tetik_alan"],
    }


def generate_legacy_config(
    template: str,
    document: dict[str, Any],
    *,
    profile_tag: str | None = None,
) -> str:
    """Return ``template`` with KERİM-backed constants replaced deterministically."""

    try:
        tree = ast.parse(template, filename="LEGACY/config.py")
    except SyntaxError as exc:
        raise LegacyConfigError(f"LEGACY/config.py is not valid Python: {exc}") from exc
    values = _mapped_values(document)
    assignments: dict[str, ast.Assign] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in values
        ):
            assignments[node.targets[0].id] = node
    missing = sorted(set(values) - set(assignments))
    if missing:
        raise LegacyConfigError(
            "LEGACY/config.py is missing KERİM constants: " + ", ".join(missing)
        )

    lines = template.splitlines(keepends=True)
    replacements: dict[int, list[tuple[int, int, str]]] = {}
    for name, node in assignments.items():
        value_node = node.value
        if value_node.lineno != value_node.end_lineno:
            raise LegacyConfigError(f"{name} must remain a one-line assignment")
        replacements.setdefault(value_node.lineno - 1, []).append(
            (value_node.col_offset, value_node.end_col_offset, repr(values[name]))
        )
    for line_index, spans in replacements.items():
        line = lines[line_index]
        for start, end, replacement in sorted(spans, reverse=True):
            line = line[:start] + replacement + line[end:]
        lines[line_index] = line

    tag = profile_tag or str(document["profil"]["kimlik"])
    header = (
        f"# KERİM profile {tag}: generated values; GPIO and other canon logic preserved.\n"
    )
    generated = header + "".join(lines)
    try:
        ast.parse(generated, filename="LEGACY/config.py")
    except SyntaxError as exc:
        raise LegacyConfigError(f"generated LEGACY/config.py is invalid: {exc}") from exc
    return generated


__all__ = ["LegacyConfigError", "generate_legacy_config"]
