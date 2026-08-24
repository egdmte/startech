"""Proof for OSMAN's controller, TAWNT bridge, and real GPIO boundary."""

from __future__ import annotations

import unittest
import time

import tawnt
from arac.goruntu import LaneObservation
from arac.surucu import (
    ControllerSettings,
    FakeMotorDriver,
    GpioStartButton,
    GpioZeroMotorDriver,
    InvalidMotorRequest,
    LEGACY_VEHICLE_WIRING,
    LaneController,
    MotorRequest,
    OutputWatchdog,
    validate_request,
)


def settings() -> ControllerSettings:
    return ControllerSettings(
        kp=0.5,
        kd=0.2,
        ki=0.0,
        integral_max=50,
        derivative_cap=150,
        target_speed=50,
        minimum_speed=25,
        maximum_speed=57,
        speed_error_gain=0.45,
    )


def observation(error: float | None, frame_id: int = 0) -> LaneObservation:
    valid = error is not None
    return LaneObservation(
        frame_id=frame_id,
        captured_at=1.0 + frame_id,
        valid=valid,
        error_px=error,
        normalized_error=None if error is None else error / 160,
        confidence=0.0 if error is None else 0.9,
        lane_center_px=None if error is None else int(160 - error),
        left_lane_px=None,
        right_lane_px=None,
        brightness=100,
        reason="lane lost" if error is None else "",
    )


class FakeDigital:
    def __init__(self, pin: int, **kwargs):
        self.pin = pin
        self.value = bool(kwargs.get("initial_value", False))
        self.closed = False

    def on(self):
        self.value = True

    def off(self):
        self.value = False

    def close(self):
        self.closed = True


class FakePwm:
    def __init__(self, pin: int, **kwargs):
        self.pin = pin
        self.value = float(kwargs.get("initial_value", 0))
        self.frequency = kwargs.get("frequency")
        self.closed = False

    def close(self):
        self.closed = True


def motor_calibration(**changes) -> dict[str, float]:
    values = {
        "sol_trim_dusuk": 1.0,
        "sol_trim_yuksek": 1.0,
        "sag_trim_dusuk": 1.0,
        "sag_trim_yuksek": 1.0,
        "olu_bolge_min_pwm": 30,
        "olu_bolge_yuzde": 20,
    }
    values.update(changes)
    return values


class LaneControllerTest(unittest.TestCase):
    def test_centered_lane_requests_configured_cruise_speed(self):
        request = LaneController(settings(), clock=lambda: 1.0).compute(observation(0))
        self.assertAlmostEqual(0.5, request.left)
        self.assertAlmostEqual(0.5, request.right)

    def test_positive_legacy_error_requests_left_correction(self):
        request = LaneController(settings(), clock=lambda: 1.0).compute(observation(30))
        self.assertGreater(request.left, request.right)
        self.assertGreaterEqual(request.right, 0)

    def test_large_error_cannot_create_reverse_or_pivot(self):
        request = LaneController(settings(), clock=lambda: 1.0).compute(observation(160))
        self.assertGreaterEqual(request.left, 0)
        self.assertGreaterEqual(request.right, 0)
        self.assertEqual(0.0, request.right)

    def test_low_confidence_memory_runs_only_at_minimum_speed(self):
        remembered = observation(0)
        remembered = LaneObservation(
            **{**remembered.__dict__, "confidence": 0.01}
        )
        request = LaneController(settings(), clock=lambda: 1.0).compute(remembered)
        self.assertEqual((0.25, 0.25), (request.left, request.right))

    def test_missing_lane_stops_immediately_and_resets_history(self):
        ticks = iter((1.0, 2.0, 3.0))
        controller = LaneController(settings(), clock=lambda: next(ticks))
        controller.compute(observation(50, 0))
        stopped = controller.compute(observation(None, 1))
        resumed = controller.compute(observation(0, 2))

        self.assertEqual((0.0, 0.0), (stopped.left, stopped.right))
        self.assertIn("lane unavailable", stopped.reason)
        self.assertEqual((0.5, 0.5), (resumed.left, resumed.right))


class TawntAndGpioDriverTest(unittest.TestCase):
    def setUp(self):
        tawnt.sifirla()
        tawnt.definePhase(
            "LANE_FOLLOW",
            motion_allowed=True,
            allow_reverse=False,
            allow_pivot=False,
            max_pwm=1.0,
            max_difference=1.0,
        )
        tawnt.validateBeforeStart(profile=tawnt.OFFLINE)
        tawnt.enterPhase("LANE_FOLLOW")
        tawnt.arm("OSMAN unit proof")

    def tearDown(self):
        tawnt.sifirla()

    def driver(self, calibration=None):
        return GpioZeroMotorDriver(
            calibration or motor_calibration(),
            digital_factory=FakeDigital,
            pwm_factory=FakePwm,
        )

    def test_existing_car_wiring_is_the_default_not_an_empty_placeholder(self):
        wiring = LEGACY_VEHICLE_WIRING
        self.assertEqual((17, 27, 22, 23), (
            wiring.right_in1, wiring.right_in2, wiring.left_in1, wiring.left_in2,
        ))
        self.assertEqual((12, 13, 16, 100), (
            wiring.left_pwm, wiring.right_pwm, wiring.start_button, wiring.pwm_frequency_hz,
        ))

    def test_raw_request_cannot_reach_even_the_fake_driver(self):
        request = MotorRequest(0.2, 0.2, "LANE_FOLLOW", "lane")
        driver = FakeMotorDriver()
        with self.assertRaises(TypeError):
            driver.apply(request)
        driver.apply(validate_request(request))
        self.assertEqual(1, len(driver.history))

    def test_gpio_driver_uses_inverted_existing_car_direction_and_100hz(self):
        driver = self.driver()
        request = validate_request(
            MotorRequest(0.2, 0.4, "LANE_FOLLOW", "lane", frame_id=2)
        )
        final = driver.apply(request)

        # Dead-zone is applied once at the final boundary: 20% -> 30%.
        self.assertEqual(0.30, driver._left_pwm.value)
        self.assertEqual(0.40, driver._right_pwm.value)
        self.assertFalse(driver._left_in1.value)
        self.assertTrue(driver._left_in2.value)
        self.assertEqual(100, driver._left_pwm.frequency)
        self.assertEqual((0.30, 0.40), (final.left, final.right))

    def test_trim_is_applied_once_to_the_correct_wheel(self):
        driver = self.driver(motor_calibration(
            sol_trim_dusuk=0.8,
            sol_trim_yuksek=0.8,
            sag_trim_dusuk=1.0,
            sag_trim_yuksek=1.0,
            olu_bolge_min_pwm=0,
        ))
        driver.apply(validate_request(
            MotorRequest(0.5, 0.5, "LANE_FOLLOW", "straight")
        ))

        self.assertAlmostEqual(0.4, driver._left_pwm.value)
        self.assertAlmostEqual(0.5, driver._right_pwm.value)

    def test_tawnt_rechecks_calibration_adjusted_final_values(self):
        tawnt.sifirla()
        tawnt.definePhase("LANE_FOLLOW", motion_allowed=True, max_pwm=0.5)
        tawnt.validateBeforeStart(profile=tawnt.OFFLINE)
        tawnt.enterPhase("LANE_FOLLOW")
        tawnt.arm("OSMAN unit proof")
        driver = self.driver(motor_calibration(
            sol_trim_dusuk=2.0, sol_trim_yuksek=2.0,
            sag_trim_dusuk=2.0, sag_trim_yuksek=2.0,
            olu_bolge_min_pwm=0,
        ))
        request = validate_request(
            MotorRequest(0.5, 0.5, "LANE_FOLLOW", "trim boundary")
        )

        with self.assertRaises(tawnt.TawntHatasi):
            driver.apply(request)
        self.assertEqual(0.0, driver._left_pwm.value)
        self.assertEqual(0.0, driver._right_pwm.value)

    def test_stop_brakes_before_close_and_close_is_idempotent(self):
        driver = self.driver()
        driver.stop("fault")
        self.assertEqual((0.0, 0.0), (driver._left_pwm.value, driver._right_pwm.value))
        self.assertTrue(all(pin.value for pin in (
            driver._left_in1, driver._left_in2, driver._right_in1, driver._right_in2,
        )))
        driver.close()
        driver.close()
        self.assertTrue(driver._left_pwm.closed)

    def test_unarmed_request_is_rejected(self):
        tawnt.sifirla()
        with self.assertRaises(tawnt.TawntHatasi):
            validate_request(MotorRequest(0, 0, "LANE_FOLLOW", "unarmed"))

    def test_invalid_request_values_are_rejected_before_tawnt(self):
        with self.assertRaises(InvalidMotorRequest):
            MotorRequest(float("nan"), 0, "LANE_FOLLOW", "bad")


class StartButtonTest(unittest.TestCase):
    def test_existing_button_pin_waits_and_closes(self):
        class Button:
            def __init__(self, pin, **kwargs):
                self.pin = pin
                self.waited = False
                self.closed = False

            def wait_for_press(self):
                self.waited = True

            def close(self):
                self.closed = True

        button = GpioStartButton(button_factory=Button)
        button.wait()
        button.close()
        self.assertEqual(16, button._button.pin)
        self.assertTrue(button._button.waited)
        self.assertTrue(button._button.closed)


class OutputWatchdogTest(unittest.TestCase):
    def tearDown(self):
        tawnt.sifirla()

    def test_stalled_loop_requests_electrical_stop_without_waiting_for_next_frame(self):
        driver = FakeMotorDriver()
        watchdog = OutputWatchdog(
            driver, timeout_seconds=0.02, poll_seconds=0.005
        )
        watchdog.start()
        time.sleep(0.05)
        watchdog.close()

        reasons = [event.reason for event in driver.history]
        self.assertIn("output watchdog expired", reasons)
        self.assertEqual(tawnt.LATCHED_FAULT, tawnt.systemState())


if __name__ == "__main__":
    unittest.main(verbosity=2)
