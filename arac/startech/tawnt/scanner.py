"""Development-only AST tripwire for direct motor and PWM access."""

from __future__ import annotations

import ast
from pathlib import Path

from .model import TawntHatasi


_DIRECT_MOTOR_CALL_NAMES = {
    "_writePwm",
    "write_pwm",
    "motorlara_yaz",
    "set_pwm",
    "setMotor",
    "ChangeDutyCycle",
    "PWMOutputDevice",
}
_GATED_MOTOR_CALL_NAMES = {"applyMotorCommand", "validateMotorCommand"}
_DIRECT_ASSIGN_ATTRS = {"value", "duty_cycle", "pwm"}
_MOTOR_HINTS = {"motor", "pwm", "left", "right", "sol", "sag", "surucu"}


def _call_name(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _root_name(node) -> str:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id.lower() if isinstance(node, ast.Name) else ""


def scanDirectMotorWrites(
    root,
    allowed_files=("surucu.py", "tawnt.py", "test_tawnt.py"),
):
    """Şüpheli doğrudan motor/PWM erişimlerini AST ile raporlar."""

    base = Path(root)
    if not base.exists():
        raise TawntHatasi("Tarama yolu yok: %s" % base)
    allowed = {str(name).replace("\\", "/") for name in allowed_files}
    files = [base] if base.is_file() else sorted(base.rglob("*.py"))
    violations = []

    for path in files:
        relative = path.name if base.is_file() else path.relative_to(base).as_posix()
        if relative in allowed or path.name in allowed:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            violations.append({"path": relative, "line": 0, "reason": str(exc)})
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for target in targets:
                    if not isinstance(target, ast.Attribute):
                        continue
                    root_name = _root_name(target)
                    if (
                        target.attr in _DIRECT_ASSIGN_ATTRS
                        and any(hint in root_name for hint in _MOTOR_HINTS)
                    ):
                        violations.append(
                            {
                                "path": relative,
                                "line": node.lineno,
                                "reason": "dogrudan motor/PWM alan atamasi",
                            }
                        )
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name not in _DIRECT_MOTOR_CALL_NAMES | _GATED_MOTOR_CALL_NAMES:
                    continue
                numeric = [
                    arg
                    for arg in node.args
                    if isinstance(arg, ast.Constant)
                    and isinstance(arg.value, (int, float))
                    and not isinstance(arg.value, bool)
                ]
                if name in _GATED_MOTOR_CALL_NAMES and not numeric:
                    continue
                violations.append(
                    {
                        "path": relative,
                        "line": node.lineno,
                        "reason": (
                            "dogrudan motor/PWM cagrisi; hardcoded sayi var"
                            if numeric
                            else "dogrudan motor/PWM cagrisi"
                        ),
                    }
                )
    return violations
