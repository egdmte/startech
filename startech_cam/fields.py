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
        "Choose the stable capture intent. This does not claim that a camera was physically measured.",
        (
            Field("sac_niyeti.kamera.yon_derecesi", "Frame rotation", "select", choices=(("0", "0°"), ("90", "90°"), ("180", "180°"), ("270", "270°"))),
            Field("sac_niyeti.kamera.yakalama_profili", "Capture profile", "select", choices=(("640x480", "640×480 — performance"), ("1280x720", "1280×720 — balanced"), ("1920x1080", "1920×1080 — quality"))),
            Field("sac_niyeti.kamera.tanima_hassasiyeti", "Recognition sensitivity", "select", choices=(("conservative", "Conservative"), ("balanced", "Balanced"), ("sensitive", "Sensitive"))),
            Field("sac_niyeti.kamera.raspberry_pi_oncelikli", "Try Raspberry Pi camera before USB", "checkbox"),
        ),
    ),
    "power": (
        "Power limits",
        "These are selected software limits, not measured motor voltage or proof of safe motion.",
        (
            Field("sac_niyeti.guc.minimum_hiz_yuzde", "Minimum speed %", "range", 0, 100, 1),
            Field("sac_niyeti.guc.maksimum_hiz_yuzde", "Maximum speed %", "range", 0, 100, 1),
        ),
    ),
    "compute": (
        "Compute and validation",
        "Select startup validation and module policy.",
        (
            Field("sac_niyeti.hesaplama.baslangic_onlemi", "Startup precaution", "select", choices=(("individual-buttons", "Validate each segment"), ("single-button", "Validate all segments with one button"), ("keyboard-vnc", "Validate with keyboard/VNC"))),
            Field("sac_niyeti.hesaplama.servis_durumu", "ARDA service", "select", choices=(("on", "Launch on startup"), ("off", "Manual launch"))),
            Field("sac_niyeti.hesaplama.m3th_sikiligi", "M3TH strictness", "select", choices=(("full", "Full — invalidate run"), ("semi", "Semi — pause run"), ("low", "Low — report only"))),
            Field("sac_niyeti.hesaplama.etkin_moduller", "Enabled modules", "multiselect", choices=(("yaren", "YAREN"), ("arda", "ARDA"), ("kasim", "KASIM"), ("kader", "KADER"), ("kerem", "KEREM"), ("osman", "OSMAN"), ("m3th", "M3TH"))),
        ),
    ),
    "drive": (
        "Command response",
        "Record runtime policy. Physical SAC checks are separate, short workshop commands and never start autonomous driving.",
        (
            Field("sac_niyeti.surus.komut_kaybi_eylemi", "Loss-of-command action", "select", choices=(("invalidate-request", "Invalidate request"), ("disarm-wait", "Disarm and wait"), ("refer-validated-commands", "Refer to validated commands"))),
            Field("sac_niyeti.surus.surucu_cikis_modu", "Driver output mode", "select", choices=(("off", "Off — simulations only"), ("semi", "Semi — steering only"), ("full", "Full — full car control"))),
            Field("sac_niyeti.surus.direksiyon_merkez_yuzde", "Steering center %", "range", -30, 30, 1),
            Field("sac_niyeti.surus.direksiyon_azami_hareket_yuzde", "Maximum steering movement %", "range", 10, 100, 1),
            Field("oturum_kaniti.tam_cikis_onaylandi", "I explicitly acknowledge full output", "checkbox"),
            Field("oturum_kaniti.prototip_kilidi_onaylandi", "I acknowledge that CAM does not prove hardware safety", "checkbox"),
        ),
    ),
    "wheel": (
        "Wheel intent",
        "Corrections remain unmeasured intent until supervised physical testing records evidence.",
        (
            Field("sac_niyeti.tekerlek.sol_duzeltme_yuzde", "Left correction %", "range", -20, 20, 1),
            Field("sac_niyeti.tekerlek.sag_duzeltme_yuzde", "Right correction %", "range", -20, 20, 1),
            Field("sac_niyeti.tekerlek.sol_yon", "Left direction", "select", choices=(("normal", "Normal"), ("reversed", "Reversed"))),
            Field("sac_niyeti.tekerlek.sag_yon", "Right direction", "select", choices=(("normal", "Normal"), ("reversed", "Reversed"))),
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
        "Physical camera facts used by the v1 calibration contract.",
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
        "Lane recognition thresholds and lighting profiles.",
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
        "Mechanical measurements. Do not mark measured without recorded physical evidence.",
        (
            Field("kalibrasyon.motor.olculdu", "Measured", "nullable_boolean"),
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
        "Selected minimum, target, and maximum speed policy.",
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
