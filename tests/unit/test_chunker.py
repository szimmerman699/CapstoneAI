from typing import ClassVar

import pytest

from capstone_ai.rag.chunker import Chunker


@pytest.fixture
def chunker():
    return Chunker()


def test_chunk_boundaries_and_metadata(chunker):
    text = "abcdefghij"

    chunks = chunker.chunk_fixed(text, chunk_size=4, overlap=1)

    assert [c.text for c in chunks] == ["abcd", "defg", "ghij"]
    assert [(c["metadata"]["start_char"], c["metadata"]["end_char"]) for c in chunks] == [
        (0, 4),
        (3, 7),
        (6, 10),
    ]
    assert [c["metadata"]["chunk_index"] for c in chunks] == [0, 1, 2]
    assert {c["metadata"]["chunk_strategy"] for c in chunks} == {"fixed"}


def test_offsets_map_back_to_source_text(chunker):
    text = "x" * 250 + "FINDME" + "y" * 250

    for chunk in chunker.chunk_fixed(text, chunk_size=100, overlap=20):
        start, end = chunk["metadata"]["start_char"], chunk["metadata"]["end_char"]
        assert text[start:end] == chunk.text


def test_overlap_repeats_trailing_characters(chunker):
    chunks = chunker.chunk_fixed("abcdefghij", chunk_size=5, overlap=2)

    assert chunks[0].text[-2:] == chunks[1].text[:2]


def test_final_chunk_is_truncated_not_padded(chunker):
    chunks = chunker.chunk_fixed("abcdefg", chunk_size=4, overlap=1)

    assert chunks[-1]["metadata"]["end_char"] == 7
    assert chunks[-1].text == "defg"


def test_text_shorter_than_chunk_size_yields_one_chunk(chunker):
    chunks = chunker.chunk_fixed("short", chunk_size=500, overlap=100)

    assert len(chunks) == 1
    assert chunks[0].text == "short"
    assert chunks[0]["metadata"]["end_char"] == 5


def test_empty_text_yields_no_chunks(chunker):
    assert chunker.chunk_fixed("") == []


def test_zero_overlap_is_allowed(chunker):
    chunks = chunker.chunk_fixed("abcdef", chunk_size=2, overlap=0)

    assert [c.text for c in chunks] == ["ab", "cd", "ef"]


def test_source_metadata_is_carried_through(chunker):
    chunks = chunker.chunk_fixed(
        "abcdef", chunk_size=3, overlap=0, metadata={"source": "notes.md", "client": "acme"}
    )

    assert all(c["metadata"]["source"] == "notes.md" for c in chunks)
    assert all(c["metadata"]["client"] == "acme" for c in chunks)


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (100, -1), (100, 100), (100, 150)],
)
def test_invalid_parameters_are_rejected(chunker, chunk_size, overlap):
    with pytest.raises(ValueError):
        chunker.chunk_fixed("some text", chunk_size=chunk_size, overlap=overlap)


PARAGRAPHS = (
    "First paragraph about pricing tiers and order minimums.\n\n"
    "Second paragraph covering the imprint colour options.\n\n"
    "Third paragraph on artwork upload and checkout flow."
)


def test_recursive_offsets_map_back_to_source_text(chunker):
    for chunk in chunker.chunk_recursive(PARAGRAPHS, chunk_size=60, overlap=10):
        start, end = chunk["metadata"]["start_char"], chunk["metadata"]["end_char"]
        assert PARAGRAPHS[start:end] == chunk.text


def test_recursive_labels_strategy_and_indexes_sequentially(chunker):
    chunks = chunker.chunk_recursive(PARAGRAPHS, chunk_size=60, overlap=10)

    assert {c["metadata"]["chunk_strategy"] for c in chunks} == {"recursive"}
    assert [c["metadata"]["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_recursive_prefers_paragraph_boundaries(chunker):
    chunks = chunker.chunk_recursive(PARAGRAPHS, chunk_size=60, overlap=0)

    # Each paragraph fits within chunk_size, so none should be split mid-sentence.
    assert [c.text for c in chunks] == PARAGRAPHS.split("\n\n")


def test_recursive_respects_chunk_size_ceiling(chunker):
    text = "word " * 400

    for chunk in chunker.chunk_recursive(text, chunk_size=100, overlap=20):
        assert len(chunk.text) <= 100


def test_recursive_carries_source_metadata(chunker):
    chunks = chunker.chunk_recursive(
        PARAGRAPHS, chunk_size=60, overlap=0, metadata={"source": "notes.md"}
    )

    assert all(c["metadata"]["source"] == "notes.md" for c in chunks)


def test_recursive_empty_text_yields_no_chunks(chunker):
    assert chunker.chunk_recursive("") == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (100, -1), (100, 100), (100, 150)],
)
def test_recursive_invalid_parameters_are_rejected(chunker, chunk_size, overlap):
    with pytest.raises(ValueError):
        chunker.chunk_recursive("some text", chunk_size=chunk_size, overlap=overlap)


def test_recursive_merges_bare_heading_into_following_chunk(chunker):
    # A short heading followed by enough body text that the splitter's "\n\n"
    # pass isolates the heading into its own chunk before this fix.
    text = "## Key Functional Issues to Fix\n\n" + ("Body detail sentence. " * 15)

    chunks = chunker.chunk_recursive(text, chunk_size=120, overlap=0)

    assert not any(c.text.strip() == "## Key Functional Issues to Fix" for c in chunks)
    assert chunks[0].text.startswith("## Key Functional Issues to Fix\n\nBody detail")


def test_recursive_merged_chunk_offsets_still_round_trip(chunker):
    text = "## Heading One\n\n" + ("Filler sentence. " * 10) + "\n\n## Heading Two\n\nMore text."

    for chunk in chunker.chunk_recursive(text, chunk_size=80, overlap=0):
        start, end = chunk["metadata"]["start_char"], chunk["metadata"]["end_char"]
        assert text[start:end] == chunk.text


def test_recursive_trailing_bare_heading_is_kept_as_is(chunker):
    # No following chunk to merge into — must not raise or drop content.
    text = ("Filler sentence. " * 20) + "\n\n## Trailing Heading"

    chunks = chunker.chunk_recursive(text, chunk_size=80, overlap=0)

    assert chunks[-1].text.strip() == "## Trailing Heading"


class _FakeEmbedder:
    """Deterministic stand-in for fastembed.TextEmbedding.

    Maps each sentence to a fixed unit vector by which fake "topic" keyword it
    contains, so tests don't need to download a real model or depend on a real
    model's similarity judgments.
    """

    TOPIC_VECTORS: ClassVar[dict[str, list[float]]] = {
        "weather": [1.0, 0.0],
        "market": [0.0, 1.0],
    }

    def embed(self, documents):
        import numpy as np

        for doc in documents:
            for keyword, vec in self.TOPIC_VECTORS.items():
                if keyword in doc.lower():
                    yield np.array(vec)
                    break
            else:
                yield np.array([1.0, 0.0])  # default to "weather" topic


@pytest.fixture
def semantic_chunker(monkeypatch):
    chunker = Chunker()
    monkeypatch.setattr(chunker, "_get_embedder", lambda: _FakeEmbedder())
    return chunker


def test_semantic_splits_on_topic_change(semantic_chunker):
    text = "Weather is sunny today. Weather stays warm tomorrow. Market fell sharply. Market stays volatile."

    chunks = semantic_chunker.chunk_semantic(text, threshold=0.5)

    assert len(chunks) == 2
    assert chunks[0].text == "Weather is sunny today. Weather stays warm tomorrow."
    assert chunks[1].text == "Market fell sharply. Market stays volatile."
    assert chunks[0]["metadata"]["sentence_count"] == 2
    assert chunks[1]["metadata"]["sentence_count"] == 2


def test_semantic_keeps_similar_sentences_together(semantic_chunker):
    text = "Weather is sunny. Weather is warm. Weather is clear."

    chunks = semantic_chunker.chunk_semantic(text, threshold=0.5)

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["sentence_count"] == 3


def test_semantic_labels_strategy_and_indexes_sequentially(semantic_chunker):
    text = "Weather is sunny. Market fell today."

    chunks = semantic_chunker.chunk_semantic(text, threshold=0.5)

    assert {c["metadata"]["chunk_strategy"] for c in chunks} == {"semantic"}
    assert [c["metadata"]["chunk_index"] for c in chunks] == list(range(len(chunks)))


def test_semantic_keeps_terminal_punctuation(semantic_chunker):
    text = "Is the weather sunny? Weather stays warm."

    chunks = semantic_chunker.chunk_semantic(text, threshold=0.9)

    assert all(c.text.rstrip().endswith((".", "?", "!")) for c in chunks)


def test_semantic_single_sentence_yields_one_chunk(semantic_chunker):
    chunks = semantic_chunker.chunk_semantic("Just one weather sentence.", threshold=0.5)

    assert len(chunks) == 1
    assert chunks[0].text == "Just one weather sentence."


def test_semantic_empty_text_yields_no_chunks(semantic_chunker):
    assert semantic_chunker.chunk_semantic("") == []


def test_semantic_carries_source_metadata(semantic_chunker):
    text = "Weather is sunny. Market fell today."

    chunks = semantic_chunker.chunk_semantic(text, threshold=0.5, metadata={"source": "notes.md"})

    assert all(c["metadata"]["source"] == "notes.md" for c in chunks)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, 2.0])
def test_semantic_invalid_threshold_is_rejected(semantic_chunker, threshold):
    with pytest.raises(ValueError):
        semantic_chunker.chunk_semantic("Weather is sunny. Market fell.", threshold=threshold)


def test_semantic_start_offsets_point_at_source_sentences(semantic_chunker):
    text = "Weather is sunny today. Weather stays warm tomorrow. Market fell sharply."

    for chunk in semantic_chunker.chunk_semantic(text, threshold=0.5):
        start = chunk["metadata"]["start_char"]
        first_word = chunk.text.split()[0]
        assert text[start:].startswith(first_word)


# --- Unified metadata: parent_doc_id passthrough, page_number, section_header ---


def test_parent_doc_id_and_loader_fields_pass_through_every_strategy(chunker, semantic_chunker):
    doc_metadata = {
        "source": "roadmap.md",
        "file_type": "markdown",
        "parent_doc_id": "abc123",
    }
    text = "First sentence here. Second sentence here."

    fixed = chunker.chunk_fixed(text, chunk_size=20, overlap=5, metadata=doc_metadata)
    recursive = chunker.chunk_recursive(text, chunk_size=20, overlap=5, metadata=doc_metadata)
    semantic = semantic_chunker.chunk_semantic(text, threshold=0.5, metadata=doc_metadata)

    for chunks in (fixed, recursive, semantic):
        for c in chunks:
            assert c["metadata"]["parent_doc_id"] == "abc123"
            assert c["metadata"]["source"] == "roadmap.md"
            assert c["metadata"]["file_type"] == "markdown"


def test_page_number_derived_from_page_offsets(chunker):
    # Simulates loader.Document.metadata for a 3-page PDF.
    text = "Page one content here. " + "Page two content here. " + "Page three content here."
    doc_metadata = {"page_offsets": [0, 24, 48], "parent_doc_id": "pdf1"}

    chunks = chunker.chunk_fixed(text, chunk_size=24, overlap=0, metadata=doc_metadata)

    # chunk 0 starts at char 0 -> page 1; chunk 1 starts at char 24 -> page 2; etc.
    assert [c["metadata"]["page_number"] for c in chunks] == [1, 2, 3]


def test_page_number_absent_when_document_has_no_page_offsets(chunker):
    chunks = chunker.chunk_fixed("plain text, no pdf pages", chunk_size=10, overlap=0)

    assert all("page_number" not in c["metadata"] for c in chunks)


def test_section_header_derived_from_preceding_heading(chunker):
    text = "## Intro\n\nIntro body text goes here and continues on.\n\n## Details\n\nDetails body text."
    doc_metadata = {
        "headings": ["h2:Intro", "h2:Details"],
        "parent_doc_id": "md1",
    }

    chunks = chunker.chunk_recursive(text, chunk_size=40, overlap=0, metadata=doc_metadata)

    sections = [c["metadata"].get("section_header") for c in chunks]
    assert "Intro" in sections
    assert "Details" in sections
    # a chunk under "## Details" must not be attributed to "Intro"
    details_chunk = next(c for c in chunks if "Details body" in c.text)
    assert details_chunk["metadata"]["section_header"] == "Details"


def test_section_header_absent_when_document_has_no_headings(chunker):
    chunks = chunker.chunk_fixed("plain text, no headings at all", chunk_size=10, overlap=0)

    assert all("section_header" not in c["metadata"] for c in chunks)
