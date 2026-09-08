"""Prompt loader and template filler for harness prompts."""

from pathlib import Path
from typing import Dict, Any, List

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_raw_prompt(filename: str) -> str:
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template {filename} not found in {_PROMPTS_DIR}")
    return path.read_text(encoding="utf-8")


def render_template(template: str, slots: Dict[str, Any]) -> str:
    result = template
    for key, val in slots.items():
        placeholder = f"{{{{{key}}}}}"
        result = result.replace(placeholder, str(val))
    return result


def get_harness_prompt() -> str:
    return load_raw_prompt("00-harness.md")


def get_plan_prompt(slots: Dict[str, Any]) -> str:
    template = load_raw_prompt("10-plan.md")
    return render_template(template, slots)


def get_compose_prompt(slots: Dict[str, Any]) -> str:
    template = load_raw_prompt("20-compose.md")
    return render_template(template, slots)


def get_repair_prompt(slots: Dict[str, Any]) -> str:
    template = load_raw_prompt("30-repair.md")
    return render_template(template, slots)
