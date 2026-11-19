"""Central factory for Anthropic chat models.

Newer Claude models (the 5-family: Opus 5/5.5, Sonnet 5/5.5, Haiku 5.5,
Fable 5.x, ...) removed the `temperature` / `top_p` / `top_k` sampling
parameters — sending `temperature` to them returns a 400:

    `temperature` is deprecated for this model.

Older 4-family models (Sonnet 4.6, Haiku 4.5, ...) still accept it, where it
is useful for deterministic extraction (temperature=0). This factory lets call
sites keep expressing their intent with `temperature=` while silently dropping
it for models that no longer support it, so the same code works across model
generations.
"""

import re

from langchain_anthropic import ChatAnthropic


def _model_version(model: str) -> tuple[int, int] | None:
    """Return (major, minor) version of a Claude model id.

    e.g. "claude-opus-5-5" -> (5, 5), "claude-haiku-4-5-20251001" -> (4, 5),
    "claude-opus-5" -> (5, 0). Returns None if it can't be determined
    (then we assume a modern model and omit temperature to be safe).
    """
    nums: list[int] = []
    for token in model.split("-"):
        if token.isdigit():
            # A date snapshot (e.g. 20251001) is 8 digits — never a version number.
            if len(token) >= 5:
                continue
            nums.append(int(token))
    if not nums:
        return None
    major = nums[0]
    minor = nums[1] if len(nums) > 1 else 0
    return (major, minor)


def _supports_temperature(model: str) -> bool:
    """Whether a model still accepts the `temperature` sampling parameter.

    Sampling params (temperature/top_p/top_k) were removed starting with the
    Claude 4.7 generation and are gone across the entire 5-family. They remain
    on 4.6 and older (Opus/Sonnet 4.6, Haiku 4.5, Sonnet 4.5, ...).
    """
    ver = _model_version(model)
    if ver is None:
        return False  # unknown -> assume modern, omit temperature
    major, minor = ver
    if major >= 5:
        return False
    if major == 4 and minor >= 7:  # 4.7 / 4.8 removed sampling params
        return False
    return True


def make_chat(model: str, *, temperature: float | None = None, **kwargs) -> ChatAnthropic:
    """Build a ChatAnthropic, passing `temperature` only when the model supports it."""
    if temperature is not None and _supports_temperature(model):
        kwargs["temperature"] = temperature
    return ChatAnthropic(model=model, **kwargs)
