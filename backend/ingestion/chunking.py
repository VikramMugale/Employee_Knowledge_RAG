"""
Section-aware, token-budget chunking with overlap.

Heading splits stay first so section metadata is preserved, then oversized
sections are split on paragraph boundaries with a small overlapping tail.
"""

from typing import List, Tuple


def approximate_token_count(text: str) -> int:
    words = text.split()
    return max(1, int(len(words) * 1.3) if words else 0)


def split_with_overlap(
    text: str,
    max_tokens: int = 550,
    overlap_tokens: int = 80,
) -> List[str]:
    if approximate_token_count(text) <= max_tokens:
        return [text.strip()] if text.strip() else []

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        words = text.split()
        step = max(1, max_tokens - overlap_tokens)
        windows = []
        for start in range(0, len(words), step):
            windows.append(" ".join(words[start:start + max_tokens]))
        return [window for window in windows if window.strip()]

    windows: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        tokens = approximate_token_count(paragraph)
        if current and current_tokens + tokens > max_tokens:
            windows.append("\n\n".join(current))
            overlap: List[str] = []
            overlap_count = 0
            for previous in reversed(current):
                overlap.insert(0, previous)
                overlap_count += approximate_token_count(previous)
                if overlap_count >= overlap_tokens:
                    break
            current = overlap
            current_tokens = overlap_count
        current.append(paragraph)
        current_tokens += tokens

    if current:
        windows.append("\n\n".join(current))
    return windows


def window_section(section_title: str, section_body: str, max_tokens: int, overlap_tokens: int) -> List[Tuple[str, str]]:
    pieces = split_with_overlap(section_body, max_tokens=max_tokens, overlap_tokens=overlap_tokens)
    return [(section_title, piece) for piece in pieces]
