"""Data-driven SAC and MAC editor definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Field:
    path: str
    label: str
    kind: str = "text"
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    choices: tuple[tuple[str, str], ...] = ()
    help_text: str = ""


SAC_STEPS: dict[str, tuple[str, str, tuple[Field, ...]]] = {
    "camera": (
        "Camera",
        "Physical camera values written to LEGACY/config.py.",
        (
            Field("kalibrasyon.kamera.genislik", "Width", "integer", 1, 7680, 1),
            Field("kalibrasyon.kamera.yukseklik", "Height", "integer", 1, 4320, 1),
            Field("kalibrasyon.kamera.bgr_cikis", "BGR output", "checkbox"),
            Field("kalibrasyon.kamera.dondur_180", "Rotate 180°", "checkbox"),
        ),
    ),
    "perspective": (
        "Perspective",
        "Perspective points and the top edge of the lane region.",
        (
            Field("kalibrasyon.perspektif.kaynak_noktalar", "Source points", "json"),
            Field("kalibrasyon.perspektif.roi_ust_oran", "Top ROI ratio", "number", 0, 1, 0.01),
        ),
    ),
    "recognition": (
        "Recognition",
        "Lane-recognition values used by LEGACY/lane.py.",
        (
            Field("kalibrasyon.serit.beyaz_profiller", "White lane profiles", "json"),
            Field("kalibrasyon.serit.min_sinyal", "Minimum signal", "integer", 0, 100000, 1),
            Field("kalibrasyon.serit.min_sinyal_kalite_orani", "Signal quality ratio", "number", 0, 10, 0.01),
            Field("kalibrasyon.serit.varsayilan_serit_genisligi", "Default lane width", "integer", 1, 4000, 1),
            Field("kalibrasyon.serit.sureklilik_orani", "Continuity ratio", "number", 0, 1, 0.01),
            Field("kalibrasyon.serit.clahe_sinir", "CLAHE limit", "number", 0.1, 20, 0.1),
            Field("kalibrasyon.serit.clahe_kutucuk", "CLAHE tile size", "integer", 1, 64, 1),
        ),
    ),
    "colors": (
        "Colors",
        "HSV ranges and minimum valid areas used by event detection.",
        (Field("kalibrasyon.renkler", "Color definitions", "json"),),
    ),
    "motors": (
        "Motors",
        "Motor trim and dead-zone values written to LEGACY/config.py.",
        (
            Field("kalibrasyon.motor.olculdu", "Measured on", "nullable_date"),
            Field("kalibrasyon.motor.sol_trim_dusuk", "Left low trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.sol_trim_yuksek", "Left high trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.sag_trim_dusuk", "Right low trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.sag_trim_yuksek", "Right high trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.olu_bolge_min_pwm", "Dead-zone minimum PWM", "integer", 0, 100, 1),
            Field("kalibrasyon.motor.olu_bolge_yuzde", "Dead-zone %", "integer", 0, 100, 1),
        ),
    ),
    "control": (
        "Steering and speed",
        "Controller and speed values used by the active driving loop.",
        (
            Field("ayarlar.kontrol.kp", "KP", "number", 0, 10, 0.01),
            Field("ayarlar.kontrol.kd", "KD", "number", 0, 10, 0.01),
            Field("ayarlar.kontrol.ki", "KI", "number", 0, 10, 0.01),
            Field("ayarlar.kontrol.integral_max", "Integral maximum", "number", 0, 10000, 0.1),
            Field("ayarlar.kontrol.deriv_cap", "Derivative cap", "number", 0, 10000, 1),
            Field("ayarlar.hiz.min", "Minimum", "integer", 0, 100, 1),
            Field("ayarlar.hiz.hedef", "Target", "integer", 0, 100, 1),
            Field("ayarlar.hiz.max", "Maximum", "integer", 0, 100, 1),
            Field("ayarlar.hiz.k_speed", "Speed correction gain", "number", 0, 10, 0.01),
            Field("ayarlar.olay.yakin_roi_orani", "Near ROI ratio", "number", 0, 1, 0.01),
        ),
    ),
}


MAC_SECTIONS: dict[str, tuple[str, str, tuple[Field, ...]]] = {
    "overview": (
        "Overview",
        "Configuration identity and ownership.",
        (Field("profil.ad", "Configuration name"),),
    ),
    "camera": (
        "Camera",
        "Physical camera values used by the v1 calibration contract.",
        (
            Field("kalibrasyon.kamera.genislik", "Width", "integer", 1, 7680, 1),
            Field("kalibrasyon.kamera.yukseklik", "Height", "integer", 1, 4320, 1),
            Field("kalibrasyon.kamera.bgr_cikis", "BGR output", "checkbox"),
            Field("kalibrasyon.kamera.dondur_180", "Rotate 180°", "checkbox"),
        ),
    ),
    "perspective": (
        "Perspective",
        "Perspective points must match the measured resolution.",
        (
            Field("kalibrasyon.perspektif.olculen_cozunurluk", "Measured resolution [width, height]", "json"),
            Field("kalibrasyon.perspektif.kaynak_noktalar", "Source points", "json"),
            Field("kalibrasyon.perspektif.roi_ust_oran", "Top ROI ratio", "number", 0, 1, 0.01),
        ),
    ),
    "recognition": (
        "Recognition",
        "Lane-recognition thresholds and lighting profiles.",
        (
            Field("kalibrasyon.serit.beyaz_profiller", "White lane profiles", "json"),
            Field("kalibrasyon.serit.profil_esikleri", "Profile thresholds", "json"),
            Field("kalibrasyon.serit.min_sinyal", "Minimum signal", "integer", 0, 100000, 1),
            Field("kalibrasyon.serit.min_sinyal_kalite_orani", "Signal quality ratio", "number", 0, 10, 0.01),
            Field("kalibrasyon.serit.varsayilan_serit_genisligi", "Default lane width", "integer", 1, 4000, 1),
            Field("kalibrasyon.serit.sureklilik_orani", "Continuity ratio", "number", 0, 1, 0.01),
            Field("kalibrasyon.serit.clahe_sinir", "CLAHE limit", "number", 0.1, 20, 0.1),
            Field("kalibrasyon.serit.clahe_kutucuk", "CLAHE tile size", "integer", 1, 64, 1),
        ),
    ),
    "colors": (
        "Colors",
        "HSV ranges and minimum valid areas for detected objects.",
        (Field("kalibrasyon.renkler", "Color definitions", "json"),),
    ),
    "motors": (
        "Motors",
        "Motor calibration values. Use PHYSICALLY UNVERIFIED until they are measured on the car.",
        (
            Field("kalibrasyon.motor.olculdu", "Measured on", "nullable_date"),
            Field("kalibrasyon.motor.sol_trim_dusuk", "Left low trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.sol_trim_yuksek", "Left high trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.sag_trim_dusuk", "Right low trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.sag_trim_yuksek", "Right high trim", "number", 0.1, 2, 0.01),
            Field("kalibrasyon.motor.olu_bolge_min_pwm", "Dead-zone minimum PWM", "integer", 0, 100, 1),
            Field("kalibrasyon.motor.olu_bolge_yuzde", "Dead-zone %", "integer", 0, 100, 1),
        ),
    ),
    "steering": (
        "Steering",
        "PD/PID controller values.",
        (
            Field("ayarlar.kontrol.kp", "KP", "number", 0, 10, 0.01),
            Field("ayarlar.kontrol.kd", "KD", "number", 0, 10, 0.01),
            Field("ayarlar.kontrol.ki", "KI", "number", 0, 10, 0.01),
            Field("ayarlar.kontrol.integral_max", "Integral maximum", "number", 0, 10000, 0.1),
            Field("ayarlar.kontrol.deriv_cap", "Derivative cap", "number", 0, 10000, 1),
        ),
    ),
    "speed": (
        "Speed",
        "Minimum, target, and maximum PWM command percentages used by the car.",
        (
            Field("ayarlar.hiz.min", "Minimum", "integer", 0, 100, 1),
            Field("ayarlar.hiz.hedef", "Target", "integer", 0, 100, 1),
            Field("ayarlar.hiz.max", "Maximum", "integer", 0, 100, 1),
            Field("ayarlar.hiz.k_speed", "Speed correction gain", "number", 0, 10, 0.01),
        ),
    ),
    "event-response": (
        "Event response",
        "Near-region threshold used by event handling.",
        (Field("ayarlar.olay.yakin_roi_orani", "Near ROI ratio", "number", 0, 1, 0.01),),
    ),
}


__all__ = ["Field", "MAC_SECTIONS", "SAC_STEPS"]
