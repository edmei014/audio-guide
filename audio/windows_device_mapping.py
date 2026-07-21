"""Map Clear Audio device names to Windows MMDevice friendly names."""

from __future__ import annotations

import re
from dataclasses import dataclass

from audio.windows_types import WindowsAudioDevice

_HOSTAPI_LABELS = (
    "windows wasapi",
    "windows directsound",
    "mme",
    "directsound",
    "wdm-ks",
    "windows wdm-ks",
)

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_SPLIT_RE = re.compile(r"[\s\-_/\\()\[\],.:;]+")
_INDEX_SUFFIX_RE = re.compile(r"\s*\[\d+\]\s*$")
_MIN_MATCH_SCORE = 60


@dataclass(frozen=True)
class DeviceMapping:
    windows_device: WindowsAudioDevice
    match_score: int
    match_reason: str


def strip_backend_labels(value: str) -> str:
    """Remove PortAudio host API labels from a display or device string."""
    text = value.strip()
    if " — " in text:
        text = text.split(" — ", 1)[0].strip()
    if "," in text:
        tail = text.rsplit(",", 1)[-1].strip().lower()
        if tail.endswith("hz") or tail.isdigit():
            text = text.rsplit(",", 1)[0].strip()
    lowered = text.lower()
    for label in _HOSTAPI_LABELS:
        for separator in (" — ", " - ", ", "):
            suffix = f"{separator}{label}"
            if lowered.endswith(suffix):
                return text[: -len(suffix)].strip()
        if lowered.endswith(label):
            return text[: -len(label)].strip(" -—,")
    text = _INDEX_SUFFIX_RE.sub("", text)
    return text.strip()


def normalize_name(value: str) -> str:
    text = strip_backend_labels(value)
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.replace("(TM)", "")
    text = text.replace("(R)", "")
    text = re.sub(r"HD\+", "HD", text, flags=re.IGNORECASE)
    return text.strip()


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_SPLIT_RE.split(value.lower())
        if len(token) >= 2
    }


def score_device_names(source: str, target: str) -> tuple[int, str]:
    """Heuristic scoring ported from Tidal Audio Switcher's DeviceMappingService."""
    source_norm = normalize_name(source)
    target_norm = normalize_name(target)

    if not source_norm or not target_norm:
        return 0, "empty name"

    if source_norm.casefold() == target_norm.casefold():
        return 100, "exact normalized match"

    if (
        target_norm.casefold() in source_norm.casefold()
        or source_norm.casefold() in target_norm.casefold()
    ):
        return 80, "substring match"

    source_tokens = _tokenize(source_norm)
    target_tokens = _tokenize(target_norm)
    overlap = len(source_tokens.intersection(target_tokens))
    union = len(source_tokens.union(target_tokens))
    if overlap == 0:
        return 0, "no token overlap"

    score = int(round(60.0 * overlap / union))
    return score, f"token overlap {overlap}/{union}"


def map_to_windows_device(
    name: str,
    windows_endpoints: list[WindowsAudioDevice],
) -> DeviceMapping | None:
    best: DeviceMapping | None = None
    for endpoint in windows_endpoints:
        score, reason = score_device_names(name, endpoint.name)
        if score <= 0:
            continue
        if best is None or score > best.match_score:
            best = DeviceMapping(
                windows_device=endpoint,
                match_score=score,
                match_reason=reason,
            )
    if best is None or best.match_score < _MIN_MATCH_SCORE:
        return None
    return best


def names_refer_to_same_device(left: str, right: str) -> bool:
    score, _ = score_device_names(left, right)
    return score >= _MIN_MATCH_SCORE
