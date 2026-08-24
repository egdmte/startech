"""Transition tests for the pure DORA state machine."""

from __future__ import annotations

import unittest

from arac.durum import (
    EventType,
    IllegalTransition,
    InvalidStateEvent,
    StaleStateEvent,
    StateEvent,
    StateMachine,
    VehicleState,
)


def event(event_type, timestamp, **values):
    return StateEvent(event_type, occurred_at=timestamp, **values)


class StateMachineTest(unittest.TestCase):
    def test_happy_path_reaches_finished(self):
        machine = StateMachine()
        steps = (
            (EventType.BEGIN_SELF_TEST, VehicleState.SELF_TEST),
            (EventType.SELF_TEST_PASSED, VehicleState.READY),
            (EventType.PREPARE_START, VehicleState.WAITING_FOR_GREEN),
            (EventType.GREEN_DETECTED, VehicleState.DRIVING),
            (EventType.FINISH_DETECTED, VehicleState.FINISHED),
        )

        for timestamp, (event_type, expected) in enumerate(steps, start=1):
            snapshot = machine.apply(event(event_type, float(timestamp)))
            self.assertEqual(expected, snapshot.state)

        self.assertEqual(len(steps), machine.snapshot.revision)

    def test_stop_and_resume_path_is_explicit(self):
        machine = StateMachine()
        machine.apply(event(EventType.BEGIN_SELF_TEST, 1.0))
        machine.apply(event(EventType.SELF_TEST_PASSED, 2.0))
        machine.apply(event(EventType.PREPARE_START, 3.0))
        machine.apply(event(EventType.GREEN_DETECTED, 4.0, frame_id=10))
        machine.apply(
            event(
                EventType.STOP_REQUESTED,
                5.0,
                frame_id=11,
                reason="pedestrian crossing",
            )
        )
        self.assertEqual(VehicleState.STOPPING, machine.snapshot.state)
        machine.apply(event(EventType.MOTION_STOPPED, 6.0))
        self.assertEqual(VehicleState.WAITING, machine.snapshot.state)
        machine.apply(event(EventType.RESUME_REQUESTED, 7.0, frame_id=12))
        self.assertEqual(VehicleState.DRIVING, machine.snapshot.state)

    def test_illegal_transition_preserves_previous_snapshot(self):
        machine = StateMachine()
        before = machine.snapshot

        with self.assertRaises(IllegalTransition):
            machine.apply(event(EventType.GREEN_DETECTED, 1.0))

        self.assertIs(before, machine.snapshot)

    def test_fault_is_available_from_any_normal_state(self):
        machine = StateMachine()
        snapshot = machine.apply(
            event(EventType.FAULT_DETECTED, 1.0, reason="camera heartbeat lost")
        )

        self.assertEqual(VehicleState.FAULT, snapshot.state)
        self.assertIn("camera", snapshot.reason)

    def test_reset_requires_human_confirmation(self):
        with self.assertRaises(InvalidStateEvent):
            event(EventType.RESET_REQUESTED, 1.0)

        machine = StateMachine()
        machine.apply(event(EventType.FAULT_DETECTED, 1.0, reason="test fault"))
        snapshot = machine.apply(
            event(
                EventType.RESET_REQUESTED,
                2.0,
                reason="bench reset",
                human_confirmed=True,
            )
        )
        self.assertEqual(VehicleState.BOOT, snapshot.state)

    def test_stale_time_and_frame_are_rejected_without_mutation(self):
        machine = StateMachine()
        machine.apply(event(EventType.BEGIN_SELF_TEST, 2.0, frame_id=4))
        accepted = machine.snapshot

        with self.assertRaises(StaleStateEvent):
            machine.apply(event(EventType.SELF_TEST_PASSED, 1.0, frame_id=5))
        self.assertIs(accepted, machine.snapshot)

        with self.assertRaises(StaleStateEvent):
            machine.apply(event(EventType.SELF_TEST_PASSED, 3.0, frame_id=4))
        self.assertIs(accepted, machine.snapshot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
