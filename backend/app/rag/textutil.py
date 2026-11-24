"""Chunking, hashing and FTS query sanitation. Tokenizer is whitespace words, labeled as such."""

from __future__ import annotations

import hashlib
import re
import uuid

NS = uuid.UUID("6f0c1c2e-0a1b-4c3d-9e5f-7a8b9c0d1e2f")
_HEADING = re.compile(r"^(={2,})\s*(.+?)\s*\1\s*$")
_FTS_UNSAFE = re.compile(r"[^0-9A-Za-z\u0080-\uFFFF]+")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NS, "|".join(parts)))


def word_count(text: str) -> int:
    return len(text.split())


def chunk_sections(text: str, *, target_words: int = 320, overlap_words: int = 50) -> list[dict]:
    """Section-aware chunks. Offsets are into the normalized text."""
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    sections: list[tuple[str, str]] = []
    current = "Overview"
    buf: list[str] = []
    for line in normalized.split("\n"):
        m = _HEADING.match(line.strip())
        if m:
            if buf:
                sections.append((current, "\n".join(buf).strip()))
            current = m.group(2).strip()
            buf = []
        else:
            buf.append(line)
    if buf:
        sections.append((current, "\n".join(buf).strip()))

    chunks: list[dict] = []
    cursor = 0
    for section, body in sections:
        if not body:
            continue
        start_in_doc = normalized.find(body, cursor)
        if start_in_doc < 0:
            start_in_doc = cursor
        words = body.split()
        if len(words) <= target_words:
            chunks.append(
                {
                    "section_path": section,
                    "text": body,
                    "start_offset": start_in_doc,
                    "end_offset": start_in_doc + len(body),
                    "token_count": len(words),
                }
            )
            cursor = start_in_doc + len(body)
            continue
        step = max(target_words - overlap_words, 1)
        for i in range(0, len(words), step):
            piece_words = words[i : i + target_words]
            if not piece_words:
                break
            piece = " ".join(piece_words)
            rel = body.find(piece_words[0], 0 if i == 0 else 0)
            # Offsets are approximate to the section start plus a word-walk.
            prefix = " ".join(words[:i])
            local = len(prefix) + (1 if prefix else 0)
            chunks.append(
                {
                    "section_path": section,
                    "text": piece,
                    "start_offset": start_in_doc + local,
                    "end_offset": start_in_doc + local + len(piece),
                    "token_count": len(piece_words),
                }
            )
            if i + target_words >= len(words):
                break
        cursor = start_in_doc + len(body)
    return chunks


def fts_match_query(text: str, *, limit_terms: int = 16) -> str:
    """Quoted OR of tokens. Rejects raw FTS operators from user text."""
    raw = _FTS_UNSAFE.sub(" ", text.lower())
    terms = [t for t in raw.split() if len(t) > 1][:limit_terms]
    if not terms:
        return ""
    return " OR ".join(f'"{t}"' for t in terms)


def significant_terms(text: str) -> set[str]:
    stop = {
        "the", "and", "with", "from", "for", "to", "of", "in", "on", "a", "an",
        "under", "over", "trip", "plan", "days", "day", "people", "person",
        "quiet", "very", "some", "into", "near", "around", "that", "this",
    }
    raw = _FTS_UNSAFE.sub(" ", text.lower())
    return {t for t in raw.split() if len(t) > 2 and t not in stop}
