from __future__ import annotations

import math
import re
import threading
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


WORD_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_'-]*")
SKIP_DIRS = {
    ".git", ".obsidian", ".rag", "__pycache__", "rag", "static", "tests",
    "Templates", "Inbox",
}


@dataclass(frozen=True)
class Chunk:
    path: str
    title: str
    section: str
    text: str
    line: int


def _terms(text: str) -> list[str]:
    return [word.lower() for word in WORD_RE.findall(text)]


def _title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def chunk_markdown(path: Path, root: Path, max_chars: int = 1_500) -> list[Chunk]:
    text = path.read_text(encoding="utf-8")
    title = _title(text, path.stem.replace("-", " "))
    lines = text.splitlines()
    chunks: list[Chunk] = []
    section = title
    heading_path: dict[int, str] = {}
    buffer: list[str] = []
    start_line = 1

    def flush() -> None:
        nonlocal buffer, start_line
        content = "\n".join(buffer).strip()
        if content:
            chunks.append(Chunk(str(path.relative_to(root)), title, section, content, start_line))
        buffer = []

    for number, line in enumerate(lines, 1):
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading and buffer:
            flush()
        if heading:
            level = len(heading.group(1))
            heading_text = heading.group(2).strip()
            heading_path[level] = heading_text
            heading_path = {key: value for key, value in heading_path.items() if key <= level}
            breadcrumbs = [heading_path[key] for key in sorted(heading_path) if key >= 2]
            section = " › ".join(breadcrumbs) if breadcrumbs else heading_text
            start_line = number
        elif not buffer:
            start_line = number
        buffer.append(line)
        if sum(len(item) + 1 for item in buffer) >= max_chars:
            flush()
            start_line = number + 1
    flush()
    return chunks


class SearchIndex:
    """A small in-memory BM25 index over Markdown headings and content."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self._lock = threading.Lock()
        self._fingerprint: tuple[tuple[str, int, int], ...] = ()
        self.indexed_at = ""
        self.chunks: list[Chunk] = []
        self.term_counts: list[Counter] = []
        self.lengths: list[int] = []
        self.avg_length = 0.0
        self.document_frequency: Counter = Counter()
        self.refresh(force=True)

    def _paths(self) -> list[Path]:
        return sorted(
            path for path in self.root.rglob("*.md")
            if not any(
                part in SKIP_DIRS or part.startswith(".")
                for part in path.relative_to(self.root).parts
            )
        )

    def _snapshot(self, paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
        return tuple(
            (str(path.relative_to(self.root)), stat.st_mtime_ns, stat.st_size)
            for path in paths
            for stat in (path.stat(),)
        )

    def refresh(self, force: bool = False) -> bool:
        """Rebuild when a Markdown document is added, removed, or changed."""
        paths = self._paths()
        fingerprint = self._snapshot(paths)
        if not force and fingerprint == self._fingerprint:
            return False
        with self._lock:
            paths = self._paths()
            fingerprint = self._snapshot(paths)
            if not force and fingerprint == self._fingerprint:
                return False
            chunks = [chunk for path in paths for chunk in chunk_markdown(path, self.root)]
            term_counts = [Counter(_terms(f"{c.title} {c.section} {c.text}")) for c in chunks]
            lengths = [sum(counts.values()) for counts in term_counts]

            self.chunks = chunks
            self.term_counts = term_counts
            self.lengths = lengths
            self.avg_length = sum(lengths) / max(len(lengths), 1)
            self.document_frequency = Counter(term for counts in term_counts for term in counts)
            self._fingerprint = fingerprint
            self.indexed_at = datetime.now(timezone.utc).isoformat()
            return True

    def search(self, query: str, limit: int = 5) -> list[dict]:
        self.refresh()
        query_terms = _terms(query)
        if not query_terms:
            return []
        with self._lock:
            chunks = self.chunks
            term_counts = self.term_counts
            lengths = self.lengths
            avg_length = self.avg_length
            document_frequency = self.document_frequency
        scored: list[tuple[float, int]] = []
        total = len(chunks)
        for index, counts in enumerate(term_counts):
            score = 0.0
            for term in query_terms:
                frequency = counts.get(term, 0)
                if not frequency:
                    continue
                df = document_frequency[term]
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                denominator = frequency + 1.2 * (0.25 + 0.75 * lengths[index] / max(avg_length, 1))
                score += idf * frequency * 2.2 / denominator
            if score:
                scored.append((score, index))
        results = []
        for score, index in sorted(scored, reverse=True)[: max(1, min(limit, 10))]:
            chunk = chunks[index]
            results.append({
                "path": chunk.path, "title": chunk.title, "section": chunk.section,
                "line": chunk.line, "text": chunk.text, "score": round(score, 4),
            })
        return results
