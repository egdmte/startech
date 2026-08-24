"""STARTECH-OSMAN (MATT): lane control and the physical motor boundary.

The BCM defaults and inverted L298N direction are the wiring recorded by the
working LEGACY car.  Controller requests and the final trim/dead-zone-adjusted
values are both checked by TAWNT before a GPIO value changes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import importlib
import math
import threading
import time
from typing import Any, Protocol, runtime_checkable

import tawnt

from .goruntu import LaneObservation


class MotorOutputError(RuntimeError):
    """Base error for a motor request that cannot reach the driver."""


class InvalidMotorRequest(MotorOutputError, ValueError):
    """Raised before TAWNT when a request is malformed."""


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


@dataclass(frozen=True)
class VehicleWiring:
    """BCM pin map documented by the physical four-motor/two-channel car."""

    right_in1: int = 17
    right_in2: int = 27
    left_in1: int = 22
    left_in2: int = 23
    left_pwm: int = 12
    right_pwm: int = 13
    start_button: int = 16
    pwm_frequency_hz: int = 100

    def __post_init__(self) -> None:
        pins = (
            self.right_in1, self.right_in2, self.left_in1, self.left_in2,
            self.left_pwm, self.right_pwm, self.start_button,
        )
        if any(isinstance(pin, bool) or not isinstance(pin, int) or pin < 0 for pin in pins):
            raise ValueError("vehicle wiring pins must be non-negative BCM integers")
        if len(set(pins)) != len(pins):
            raise ValueError("vehicle wiring pins must be distinct")
        if self.pwm_frequency_hz <= 0:
            raise ValueError("PWM frequency must be positive")


LEGACY_VEHICLE_WIRING = VehicleWiring()


@dataclass(frozen=True)
class MotorRequest:
    """Untrusted normalized motor intent produced by the lane controller."""

    left: float
    right: float
    phase: str
    reason: str
    frame_id: int | None = None
    created_at: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        for name, value in (("left", self.left), ("right", self.right)):
            if not _is_finite_number(value):
                raise InvalidMotorRequest(f"{name} must be a finite number")
            if not -1 <= float(value) <= 1:
                raise InvalidMotorRequest(f"{name} must be normalized to [-1, 1]")
        if not isinstance(self.phase, str) or not self.phase.strip():
            raise InvalidMotorRequest("phase must be non-empty text")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise InvalidMotorRequest("every motor request must explain its reason")
        if self.frame_id is not None and (
            isinstance(self.frame_id, bool) or not isinstance(self.frame_id, int)
            or self.frame_id < 0
        ):
            raise InvalidMotorRequest("frame_id must be a non-negative integer or None")
        if not _is_finite_number(self.created_at) or self.created_at < 0:
            raise InvalidMotorRequest("created_at must be finite and non-negative")

    @classmethod
    def stop(
        cls, *, phase: str, reason: str, frame_id: int | None = None,
        created_at: float | None = None,
    ) -> "MotorRequest":
        values: dict[str, object] = {
            "left": 0.0, "right": 0.0, "phase": phase,
            "reason": reason, "frame_id": frame_id,
        }
        if created_at is not None:
            values["created_at"] = created_at
        return cls(**values)


@dataclass(frozen=True)
class ValidatedDriveRequest:
    """A request paired with the exact command returned by TAWNT."""

    request: MotorRequest
    command: tawnt.ValidatedMotorCommand

    def __post_init__(self) -> None:
        if not isinstance(self.request, MotorRequest):
            raise TypeError("request must be a MotorRequest")
        if not isinstance(self.command, tawnt.ValidatedMotorCommand):
            raise TypeError("command must come from tawnt.validateMotorCommand")
        if self.command.phase != self.request.phase:
            raise InvalidMotorRequest("TAWNT command phase does not match the request")
        if (
            float(self.command.left) != float(self.request.left)
            or float(self.command.right) != float(self.request.right)
        ):
            raise InvalidMotorRequest("TAWNT command values do not match the request")


def validate_request(request: MotorRequest) -> ValidatedDriveRequest:
    """Pass a structurally valid controller request through TAWNT."""

    if not isinstance(request, MotorRequest):
        raise TypeError("validate_request accepts only MotorRequest")
    command = tawnt.validateMotorCommand(request.left, request.right, phase=request.phase)
    return ValidatedDriveRequest(request=request, command=command)


@dataclass(frozen=True)
class ControllerSettings:
    kp: float
    kd: float
    ki: float
    integral_max: float
    derivative_cap: float
    target_speed: float
    minimum_speed: float
    maximum_speed: float
    speed_error_gain: float

    @classmethod
    def from_mapping(cls, settings: Mapping[str, Any]) -> "ControllerSettings":
        control = settings["kontrol"]
        speed = settings["hiz"]
        return cls(
            kp=float(control["kp"]),
            kd=float(control["kd"]),
            ki=float(control["ki"]),
            integral_max=float(control["integral_max"]),
            derivative_cap=float(control["deriv_cap"]),
            target_speed=float(speed["hedef"]),
            minimum_speed=float(speed["min"]),
            maximum_speed=float(speed["max"]),
            speed_error_gain=float(speed["k_speed"]),
        )

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if not _is_finite_number(value):
                raise ValueError(f"controller {name} must be finite")
        if not 0 <= self.minimum_speed <= self.target_speed <= self.maximum_speed <= 100:
            raise ValueError("controller speeds must satisfy 0 <= min <= target <= max <= 100")
        if self.integral_max < 0 or self.derivative_cap < 0:
            raise ValueError("controller caps cannot be negative")
        if self.speed_error_gain < 0:
            raise ValueError("controller speed_error_gain cannot be negative")


class LaneController:
    """Convert KEREM lane error to forward-only differential wheel requests.

    The stored KD is interpreted in pixels per frame, matching how the legacy
    numbers were tuned.  Lost lanes produce zero immediately; they never replay
    or reverse the previous error.
    """

    def __init__(
        self, settings: ControllerSettings, *, phase: str = "LANE_FOLLOW",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(settings, ControllerSettings):
            raise TypeError("lane controller needs ControllerSettings")
        if not isinstance(phase, str) or not phase.strip():
            raise ValueError("controller phase must be non-empty text")
        self.settings = settings
        self.phase = phase.strip()
        self._clock = clock
        self._previous_error: float | None = None
        self._previous_time: float | None = None
        self._integral = 0.0

    def reset(self) -> None:
        self._previous_error = None
        self._previous_time = None
        self._integral = 0.0

    def compute(self, observation: LaneObservation) -> MotorRequest:
        if not isinstance(observation, LaneObservation):
            raise TypeError("lane controller accepts only LaneObservation")
        now = self._clock()
        if not observation.valid:
            self.reset()
            return MotorRequest.stop(
                phase=self.phase,
                reason=f"lane unavailable: {observation.reason}",
                frame_id=observation.frame_id,
                created_at=now,
            )

        error = float(observation.error_px)
        dt = 0.0 if self._previous_time is None else max(now - self._previous_time, 0.0)
        derivative = 0.0 if self._previous_error is None else error - self._previous_error
        derivative = max(
            -self.settings.derivative_cap,
            min(self.settings.derivative_cap, derivative),
        )
        if dt > 0:
            self._integral += error * dt
            self._integral = max(
                -self.settings.integral_max,
                min(self.settings.integral_max, self._integral),
            )

        speed = self.settings.target_speed - self.settings.speed_error_gain * abs(error)
        speed = max(self.settings.minimum_speed, min(self.settings.maximum_speed, speed))
        if observation.confidence < 0.5:
            speed = self.settings.minimum_speed
        correction = (
            self.settings.kp * error
            + self.settings.kd * derivative
            + self.settings.ki * self._integral
        )
        # Lane-following must remain forward-only. A turn may stop one side but
        # may not silently become the old lost-lane pivot behaviour.
        correction = max(-speed, min(speed, correction))
        left = max(0.0, min(self.settings.maximum_speed, speed + correction))
        right = max(0.0, min(self.settings.maximum_speed, speed - correction))
        self._previous_error = error
        self._previous_time = now
        return MotorRequest(
            left=left / 100.0,
            right=right / 100.0,
            phase=self.phase,
            reason="live lane correction",
            frame_id=observation.frame_id,
            created_at=now,
        )


@runtime_checkable
class MotorDriver(Protocol):
    def apply(
        self, request: ValidatedDriveRequest
    ) -> tawnt.ValidatedMotorCommand | None:
        """Apply a TAWNT-validated request and optionally return its final command."""

    def stop(self, reason: str = "stop requested") -> None:
        """Electrically request zero output."""

    def close(self) -> None:
        """Release driver resources; repeated calls remain safe."""


class OutputWatchdog:
    """Independent electrical-stop timer for a stalled camera/control loop.

    TAWNT validates heartbeat age when code reaches it. This companion closes
    the important gap where a camera call itself hangs and the loop cannot reach
    the next validation call.
    """

    def __init__(
        self,
        driver: MotorDriver,
        *,
        timeout_seconds: float = 0.5,
        poll_seconds: float = 0.05,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(driver, MotorDriver):
            raise TypeError("output watchdog needs a MotorDriver")
        if not _is_finite_number(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("output watchdog timeout must be positive")
        if not _is_finite_number(poll_seconds) or not 0 < poll_seconds < timeout_seconds:
            raise ValueError("output watchdog poll must be between zero and timeout")
        self._driver = driver
        self._timeout = float(timeout_seconds)
        self._poll = float(poll_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._last_touch: float | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise MotorOutputError("output watchdog is already started")
        self.touch()
        self._thread = threading.Thread(
            target=self._run, name="arda-output-watchdog", daemon=True
        )
        self._thread.start()

    def touch(self) -> None:
        with self._lock:
            self._last_touch = self._clock()

    def close(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(0.2, self._poll * 2))

    def _run(self) -> None:
        while not self._stop_event.wait(self._poll):
            with self._lock:
                last_touch = self._last_touch
            if last_touch is None or self._clock() - last_touch <= self._timeout:
                continue
            try:
                self._driver.stop("output watchdog expired")
            finally:
                try:
                    tawnt.latchFault(
                        "output watchdog expired",
                        f"control loop silent for more than {self._timeout:.3f} s",
                    )
                finally:
                    self._stop_event.set()


class GpioZeroMotorDriver:
    """Real Raspberry Pi 5/gpiozero adapter for the car's L298N channels."""

    def __init__(
        self,
        motor_calibration: Mapping[str, Any],
        *,
        wiring: VehicleWiring = LEGACY_VEHICLE_WIRING,
        digital_factory: Callable[..., object] | None = None,
        pwm_factory: Callable[..., object] | None = None,
        command_validator: Callable[..., tawnt.ValidatedMotorCommand] = tawnt.validateMotorCommand,
    ) -> None:
        if not isinstance(motor_calibration, Mapping):
            raise TypeError("physical driver needs YAREN motor calibration")
        if digital_factory is None or pwm_factory is None:
            try:
                gpiozero = importlib.import_module("gpiozero")
            except ImportError as exc:
                raise MotorOutputError(
                    "gpiozero is required for the physical Raspberry Pi driver"
                ) from exc
            digital_factory = digital_factory or gpiozero.DigitalOutputDevice
            pwm_factory = pwm_factory or gpiozero.PWMOutputDevice

        self.wiring = wiring
        self._calibration = motor_calibration
        self._command_validator = command_validator
        self._closed = False
        devices: list[object] = []
        try:
            self._right_in1 = digital_factory(wiring.right_in1, initial_value=False)
            devices.append(self._right_in1)
            self._right_in2 = digital_factory(wiring.right_in2, initial_value=False)
            devices.append(self._right_in2)
            self._left_in1 = digital_factory(wiring.left_in1, initial_value=False)
            devices.append(self._left_in1)
            self._left_in2 = digital_factory(wiring.left_in2, initial_value=False)
            devices.append(self._left_in2)
            self._left_pwm = pwm_factory(
                wiring.left_pwm, initial_value=0.0, frequency=wiring.pwm_frequency_hz
            )
            devices.append(self._left_pwm)
            self._right_pwm = pwm_factory(
                wiring.right_pwm, initial_value=0.0, frequency=wiring.pwm_frequency_hz
            )
            devices.append(self._right_pwm)
        except Exception as exc:
            for device in reversed(devices):
                try:
                    device.close()
                except Exception:
                    pass
            raise MotorOutputError(f"GPIO motor driver could not open: {exc}") from exc
        self.stop("driver initialized")

    def apply(self, request: ValidatedDriveRequest) -> tawnt.ValidatedMotorCommand:
        if self._closed:
            raise MotorOutputError("physical driver is closed")
        if not isinstance(request, ValidatedDriveRequest):
            raise TypeError("driver accepts only ValidatedDriveRequest")
        left = self._final_output(float(request.command.left), side="left")
        right = self._final_output(float(request.command.right), side="right")
        # Calibration can alter PWM. Validate the exact final pair as well, so
        # no physical value exists outside TAWNT's command history/envelope.
        final = self._command_validator(left, right, phase=request.command.phase)
        self._apply_channel(self._left_in1, self._left_in2, self._left_pwm, final.left)
        self._apply_channel(self._right_in1, self._right_in2, self._right_pwm, final.right)
        return final

    def stop(self, reason: str = "stop requested") -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidMotorRequest("stop request needs a non-empty reason")
        if self._closed:
            return
        # The LEGACY car used this state as its active brake request: PWM zero,
        # both direction inputs high. Physical deceleration is verified later.
        self._left_pwm.value = 0.0
        self._right_pwm.value = 0.0
        for pin in (self._left_in1, self._left_in2, self._right_in1, self._right_in2):
            pin.on()

    def close(self) -> None:
        if self._closed:
            return
        self.stop("driver closing")
        self._closed = True
        for device in (
            self._left_pwm, self._right_pwm, self._left_in1, self._left_in2,
            self._right_in1, self._right_in2,
        ):
            try:
                device.close()
            except Exception:
                pass

    def _final_output(self, value: float, *, side: str) -> float:
        percent = value * 100.0
        magnitude = abs(percent)
        prefix = "sol" if side == "left" else "sag"
        low = float(self._calibration[f"{prefix}_trim_dusuk"])
        high = float(self._calibration[f"{prefix}_trim_yuksek"])
        if magnitude < 40:
            trim = low
        elif magnitude > 70:
            trim = high
        else:
            trim = low + ((magnitude - 40) / 30.0) * (high - low)
        adjusted = percent * trim
        minimum = float(self._calibration["olu_bolge_min_pwm"])
        if 0 < abs(adjusted) < minimum:
            adjusted = math.copysign(minimum, adjusted)
        return max(-1.0, min(1.0, adjusted / 100.0))

    @staticmethod
    def _apply_channel(in1: object, in2: object, pwm: object, speed: float) -> None:
        if speed == 0:
            pwm.value = 0.0
            in1.on()
            in2.on()
        elif speed > 0:
            # The existing car's two channels are physically inverted.
            in1.off()
            in2.on()
            pwm.value = abs(float(speed))
        else:
            in1.on()
            in2.off()
            pwm.value = abs(float(speed))


class GpioStartButton:
    """Physical start control on the existing BCM 16 wiring."""

    def __init__(
        self, pin: int = LEGACY_VEHICLE_WIRING.start_button,
        *, button_factory: Callable[..., object] | None = None,
    ) -> None:
        if button_factory is None:
            try:
                button_factory = importlib.import_module("gpiozero").Button
            except ImportError as exc:
                raise MotorOutputError("gpiozero is required for the start button") from exc
        try:
            self._button = button_factory(pin, pull_up=True, bounce_time=0.05)
        except Exception as exc:
            raise MotorOutputError(f"start button could not open on BCM {pin}: {exc}") from exc

    def wait(self) -> None:
        wait_for_press = getattr(self._button, "wait_for_press", None)
        if not callable(wait_for_press):
            raise MotorOutputError("start button has no wait_for_press method")
        wait_for_press()

    def close(self) -> None:
        close = getattr(self._button, "close", None)
        if callable(close):
            close()


__all__ = [
    "ControllerSettings", "GpioStartButton", "GpioZeroMotorDriver",
    "InvalidMotorRequest", "LEGACY_VEHICLE_WIRING", "LaneController",
    "MotorDriver", "MotorOutputError", "MotorRequest",
    "OutputWatchdog", "ValidatedDriveRequest", "VehicleWiring", "validate_request",
]
