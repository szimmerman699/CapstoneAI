import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

if TYPE_CHECKING:
    from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]
# No universal default exists — cosine-similarity thresholds are specific to the
# embedding model and to how topically varied a given corpus is. 0.55 was chosen by
# measuring the actual consecutive-sentence similarity distribution on this project's
# corpus with BAAI/bge-small-en-v1.5 (min ~0.41, median ~0.57, max ~0.87 on a sampled
# document) and sweeping candidate values against real chunk counts — not copied from
# a tutorial. Re-measure with Chunker._similarity_distribution() before reusing this
# default against a different embedding model or a corpus with different topic density.
DEFAULT_SEMANTIC_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_SEMANTIC_THRESHOLD = 0.55

_BARE_HEADING = re.compile(r"#{1,6}\s+\S.*")

# Splits after ., !, or ? followed by whitespace and a capital/digit/quote — a cheap
# heuristic, not a real sentence tokenizer, so it will mis-split on abbreviations
# ("e.g.") and decimals. Good enough for grouping, not for anything citation-critical.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


@dataclass
class Chunk:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access (chunk["text"]) alongside attribute access."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None


class Chunker:
    def __init__(self, semantic_model: str = DEFAULT_SEMANTIC_MODEL):
        self._semantic_model_name = semantic_model
        self._embedder: TextEmbedding | None = None  # lazy: chunk_fixed/recursive shouldn't pay for model download

    def _get_embedder(self) -> "TextEmbedding":
        if self._embedder is None:
            from fastembed import TextEmbedding

            self._embedder = TextEmbedding(self._semantic_model_name)
        return self._embedder

    @staticmethod
    def _enrich_metadata(
        doc_metadata: dict[str, Any], source_text: str, start_char: int, end_char: int
    ) -> dict[str, Any]:
        """Derive page_number/section_header for a chunk from the loader's document metadata.

        doc_metadata is whatever the caller passed as chunk_fixed/recursive/semantic's
        `metadata` argument — expected to be a loader.Document.metadata dict (or a
        superset of it) so page_offsets/headings/source/file_type/parent_doc_id are
        available to derive from. source_text is the full text the chunk was cut from
        (used to locate each heading's position, since loader.headings carries titles
        but not offsets). Both derived keys are best-effort: PDFs get page_number from
        page_offsets, Markdown/HTML get section_header from the nearest preceding
        heading (or a heading that starts inside the chunk itself, since the merge in
        _merge_bare_headings can pull one in), and everything else gets neither.
        """
        enriched = dict(doc_metadata)

        page_offsets = doc_metadata.get("page_offsets")
        if page_offsets:
            # 1-indexed page number: the page whose offset is the last one <= start_char.
            page_number = 1
            for i, offset in enumerate(page_offsets):
                if offset <= start_char:
                    page_number = i + 1
                else:
                    break
            enriched["page_number"] = page_number

        headings = doc_metadata.get("headings")
        if headings:
            # Resolve each heading's real offset by searching forward from the previous
            # match (not from 0 every time), so a repeated title doesn't collide, and
            # a heading is "current" for a chunk if it starts at or before the chunk's
            # end — covering both the nearest-preceding case and a heading that opens
            # the chunk itself.
            current_section = None
            cursor = 0
            for heading in headings:
                _, _, title = heading.partition(":")
                pos = source_text.find(title, cursor)
                if pos == -1:
                    continue
                cursor = pos + len(title)
                if pos < end_char:
                    current_section = title
                else:
                    break
            if current_section:
                enriched["section_header"] = current_section

        return enriched

    def chunk_fixed(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100,
        metadata: dict[str, Any] | None = None,
        snap_to_word_boundary: bool = True,
    ) -> list[Chunk]:
        """Split text into ~chunk_size-character chunks overlapping by ~overlap characters.

        snap_to_word_boundary (default True) nudges each cut point backward to the
        nearest whitespace within a small lookback window, so a chunk never starts or
        ends mid-word. This makes chunk length approximate rather than exact — a chunk
        may land a little under chunk_size. Pass False to get the raw fixed-offset
        behavior (useful for demonstrating what "no boundary awareness at all" looks
        like, e.g. in reports/chunking_comparison.md).
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if overlap < 0:
            raise ValueError(f"overlap must be non-negative, got {overlap}")
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be smaller than chunk_size ({chunk_size}); "
                "otherwise the window never advances"
            )

        base = metadata or {}
        chunks: list[Chunk] = []
        start = 0

        while start < len(text):
            raw_end = min(start + chunk_size, len(text))
            end = (
                self._snap_to_boundary(text, raw_end)
                if snap_to_word_boundary and raw_end < len(text)
                else raw_end
            )
            if end <= start:
                # Snapping collapsed the window to nothing (e.g. chunk_size is close to
                # a word length and the nearest whitespace behind raw_end sits at or
                # before start) — fall back to the raw offset so the chunk is never
                # empty and start always advances.
                end = raw_end

            chunks.append(
                Chunk(
                    text=text[start:end],
                    metadata={
                        **self._enrich_metadata(base, text, start, end),
                        "chunk_index": len(chunks),
                        "chunk_strategy": "fixed",
                        "start_char": start,
                        "end_char": end,
                    },
                )
            )
            if end == len(text):
                break
            next_start = end - overlap
            if snap_to_word_boundary:
                # end was already snapped to a boundary, but next_start = end - overlap
                # is an arithmetic offset from that boundary and can land back inside
                # the word end was snapped away from (e.g. end snapped past "riverbank",
                # next_start - overlap lands inside "riverbank" again). Snap it forward
                # to the next boundary at-or-after next_start, not backward, so this
                # chunk doesn't reopen the same word the previous one just closed.
                next_start = self._snap_to_boundary(text, next_start, lookback=40, forward=True)
            # Snapping can still leave next_start <= start on a short/dense chunk;
            # force forward progress rather than looping forever.
            start = next_start if next_start > start else end

        logger.info(
            "Chunked %d chars into %d fixed chunks (size=%d, overlap=%d, snapped=%s)",
            len(text), len(chunks), chunk_size, overlap, snap_to_word_boundary,
        )
        return chunks

    @staticmethod
    def _snap_to_boundary(
        text: str, pos: int, lookback: int = 40, forward: bool = False
    ) -> int:
        """Move pos to the nearest whitespace within `lookback` chars.

        Searches backward by default (used for a chunk's end, so the chunk doesn't
        run into the next word). With forward=True searches forward instead (used for
        a chunk's start, so it doesn't reopen a word the previous chunk's end just
        snapped past). Falls back to the raw position if no whitespace is found in
        range (e.g. one word longer than the lookback window) — better to allow a
        rare mid-word split than to silently produce oversized chunks or get stuck.
        """
        if forward:
            window_end = min(len(text), pos + lookback)
            window = text[pos:window_end]
            first_space = next((i for i, ch in enumerate(window) if ch.isspace()), None)
            if first_space is None:
                return pos
            return pos + first_space + 1  # cut after the whitespace, not on it

        window_start = max(0, pos - lookback)
        window = text[window_start:pos]
        last_space = window.rfind(" ")
        if last_space == -1:
            # try any whitespace, not just plain space (newlines, tabs)
            for i in range(len(window) - 1, -1, -1):
                if window[i].isspace():
                    last_space = i
                    break
        if last_space == -1:
            return pos
        return window_start + last_space + 1  # cut after the whitespace, not on it

    def chunk_recursive(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 100,
        metadata: dict[str, Any] | None = None,
        separators: list[str] | None = None,
    ) -> list[Chunk]:
        """Split text on the largest natural boundary that fits, falling back to smaller ones.

        Unlike chunk_fixed, chunk sizes vary: the splitter prefers paragraph and sentence
        breaks over hitting chunk_size exactly.
        """
        if chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {chunk_size}")
        if overlap < 0:
            raise ValueError(f"overlap must be non-negative, got {overlap}")
        if overlap >= chunk_size:
            raise ValueError(
                f"overlap ({overlap}) must be smaller than chunk_size ({chunk_size}); "
                "otherwise the window never advances"
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=separators or DEFAULT_SEPARATORS,
            add_start_index=True,
        )

        base = metadata or {}
        raw_pieces = [
            (piece.page_content, piece.metadata["start_index"])
            for piece in splitter.create_documents([text])
        ]
        merged_pieces = self._merge_bare_headings(raw_pieces)

        chunks = [
            Chunk(
                text=piece_text,
                metadata={
                    **self._enrich_metadata(base, text, start, start + len(piece_text)),
                    "chunk_index": index,
                    "chunk_strategy": "recursive",
                    "start_char": start,
                    "end_char": start + len(piece_text),
                },
            )
            for index, (piece_text, start) in enumerate(merged_pieces)
        ]

        logger.info(
            "Chunked %d chars into %d recursive chunks (size=%d, overlap=%d)",
            len(text), len(chunks), chunk_size, overlap,
        )
        return chunks

    @staticmethod
    def _merge_bare_headings(
        pieces: list[tuple[str, int]],
    ) -> list[tuple[str, int]]:
        """Fold a chunk that is only a markdown heading into the chunk after it.

        RecursiveCharacterTextSplitter splits on "\\n\\n" first, which lands a split
        immediately after "## Heading" whenever the heading is short enough to be its
        own chunk — isolating it from the body text it introduces. A retrieved
        heading-only chunk carries no answerable content.
        """
        merged: list[tuple[str, int]] = []
        i = 0
        while i < len(pieces):
            text, start = pieces[i]
            is_last = i + 1 == len(pieces)
            if _BARE_HEADING.fullmatch(text.strip()) and not is_last:
                next_text, _ = pieces[i + 1]
                merged.append((f"{text}\n\n{next_text}", start))
                i += 2
            else:
                merged.append((text, start))
                i += 1
        return merged

    def similarity_distribution(self, text: str) -> dict[str, float]:
        """Report min/p25/median/p75/max of consecutive-sentence cosine similarity.

        Run this against real corpus text before picking a threshold for
        chunk_semantic — thresholds are specific to both the embedding model and how
        topically varied the text is, so a value that worked for a tutorial's example
        or a different corpus is not a safe default here.
        """
        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            raise ValueError("need at least 2 sentences to measure similarity")

        unit_vectors = self._embed_unit_vectors([s for s, _ in sentences])
        similarities = sorted(
            float(v) for v in np.sum(unit_vectors[1:] * unit_vectors[:-1], axis=1)
        )
        n = len(similarities)
        return {
            "min": similarities[0],
            "p25": similarities[n // 4],
            "median": similarities[n // 2],
            "p75": similarities[3 * n // 4],
            "max": similarities[-1],
        }

    def _embed_unit_vectors(self, sentences: list[str]) -> np.ndarray:
        embedder = self._get_embedder()
        vectors = np.array(list(embedder.embed(sentences)))
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.clip(norms, a_min=1e-12, a_max=None)

    def chunk_semantic(
        self,
        text: str,
        threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Group consecutive sentences into chunks, splitting where topic similarity drops.

        Unlike chunk_fixed/chunk_recursive, chunk size is not directly controlled here —
        a chunk ends where consecutive-sentence cosine similarity falls BELOW threshold,
        not at a character count. A higher threshold is a stricter bar to stay in the
        same chunk, so it produces MORE, smaller chunks; a lower threshold produces
        FEWER, larger chunks. Call similarity_distribution() first to pick a threshold
        grounded in your actual text rather than a borrowed default.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"threshold must be in [0.0, 1.0], got {threshold}")

        sentences = self._split_sentences(text)
        if not sentences:
            return []
        base = metadata or {}
        if len(sentences) == 1:
            return [self._make_semantic_chunk(sentences, 0, base, text)]

        unit_vectors = self._embed_unit_vectors([s for s, _ in sentences])

        # cosine similarity between each sentence and the one before it, via unit-vector dot product
        similarities = np.sum(unit_vectors[1:] * unit_vectors[:-1], axis=1)

        group_start = 0
        groups: list[tuple[int, int]] = []
        for i, sim in enumerate(similarities, start=1):
            if sim < threshold:
                groups.append((group_start, i))
                group_start = i
        groups.append((group_start, len(sentences)))

        chunks = [
            self._make_semantic_chunk(sentences, index, base, text, group_bounds=bounds)
            for index, bounds in enumerate(groups)
        ]

        logger.info(
            "Chunked %d chars into %d semantic chunks (%d sentences, threshold=%.2f)",
            len(text), len(chunks), len(sentences), threshold,
        )
        return chunks

    def _make_semantic_chunk(
        self,
        sentences: list[tuple[str, int]],
        index: int,
        metadata: dict[str, Any],
        source_text: str,
        group_bounds: tuple[int, int] = (0, 1),
    ) -> Chunk:
        lo, hi = group_bounds
        group = sentences[lo:hi]
        chunk_text = " ".join(s for s, _ in group)
        start = group[0][1]
        return Chunk(
            text=chunk_text,
            metadata={
                **self._enrich_metadata(metadata, source_text, start, start + len(chunk_text)),
                "chunk_index": index,
                "chunk_strategy": "semantic",
                "start_char": start,
                "end_char": start + len(chunk_text),
                "sentence_count": len(group),
            },
        )

    @staticmethod
    def _split_sentences(text: str) -> list[tuple[str, int]]:
        """Split into (sentence, start_char) pairs, keeping terminal punctuation.

        Embedding a sentence without its "." or "?" throws away information the
        embedding model uses (a statement vs. a question read differently), so the
        punctuation stays attached rather than being stripped as a delimiter.
        """
        sentences = []
        cursor = 0
        for piece in _SENTENCE_BOUNDARY.split(text.strip()):
            piece = piece.strip()
            if not piece:
                continue
            start = text.index(piece, cursor)
            sentences.append((piece, start))
            cursor = start + len(piece)
        return sentences
