import pytest

from capstone_ai.rag.loader import DocumentLoader


@pytest.fixture
def loader():
    return DocumentLoader()


def test_markdown_extracts_headings_and_title(loader, tmp_path):
    path = tmp_path / "roadmap.md"
    path.write_text("# Project Kickoff\n\nBody text.\n\n## Open Items\n\nMore.\n", encoding="utf-8")

    doc = loader.load(path)

    assert doc.metadata["file_type"] == "markdown"
    assert doc.metadata["title"] == "Project Kickoff"
    assert doc.metadata["headings"] == ["h1:Project Kickoff", "h2:Open Items"]


def test_html_strips_tags_and_skips_script_and_style(loader, tmp_path):
    path = tmp_path / "notes.html"
    path.write_text(
        "<html><head><title>Kickoff</title><style>.a{color:red}</style></head>"
        "<body><h1>Heading</h1><p>Visible.</p><script>var a=1;</script></body></html>",
        encoding="utf-8",
    )

    doc = loader.load(path)

    assert doc.metadata["title"] == "Kickoff"
    assert doc.metadata["headings"] == ["h1:Heading"]
    assert "Visible." in doc.text
    assert "var a" not in doc.text
    assert "color:red" not in doc.text


def test_plain_text_reads_directly(loader, tmp_path):
    path = tmp_path / "transcript.txt"
    path.write_text("WEBVTT\n\nSpeaker: hello.\n", encoding="utf-8")

    doc = loader.load(path)

    assert doc.metadata["file_type"] == "text"
    assert doc.text.startswith("WEBVTT")


def test_pdf_records_page_count_and_offsets(loader, tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    path = tmp_path / "sample.pdf"
    doc_out = pymupdf.open()
    for body in ("Page one text.", "Page two text."):
        page = doc_out.new_page()
        page.insert_text((72, 72), body)
    doc_out.save(path)
    doc_out.close()

    doc = loader.load(path)

    assert doc.metadata["file_type"] == "pdf"
    assert doc.metadata["page_count"] == 2
    assert len(doc.metadata["page_offsets"]) == 2
    assert doc.metadata["page_offsets"][0] == 0
    assert "Page one" in doc.text
    assert "Page two" in doc.text


def test_every_document_carries_baseline_metadata(loader, tmp_path):
    path = tmp_path / "note.md"
    path.write_text("# Title\n", encoding="utf-8")

    metadata = loader.load(path).metadata

    assert metadata["source"] == "note.md"
    assert metadata["load_timestamp"]
    assert metadata["title"]


def test_unsupported_extension_is_rejected(loader, tmp_path):
    path = tmp_path / "data.xlsx"
    path.write_bytes(b"not really a spreadsheet")

    with pytest.raises(ValueError, match="Unsupported file type"):
        loader.load(path)


def test_oversized_file_is_rejected(tmp_path):
    path = tmp_path / "big.txt"
    path.write_text("x" * 100, encoding="utf-8")

    with pytest.raises(ValueError, match="over the"):
        DocumentLoader(max_file_bytes=10).load(path)


def test_load_directory_skips_unsupported_files(loader, tmp_path):
    (tmp_path / "keep.md").write_text("# Keep\n", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "skip.xlsx").write_bytes(b"skip")

    sources = {d.metadata["source"] for d in loader.load_directory(tmp_path)}

    assert sources == {"keep.md", "keep.txt"}


def test_empty_text_file_loads_as_empty_document(loader, tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    doc = loader.load(path)

    assert doc.text == ""
    assert doc.metadata["file_type"] == "text"


def test_empty_or_corrupt_pdf_raises_clear_error(loader, tmp_path):
    path = tmp_path / "empty.pdf"
    path.write_bytes(b"")

    with pytest.raises(ValueError, match="empty or not a valid PDF"):
        loader.load(path)
