import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, ClassVar

import pymupdf

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "documents"

MAX_FILE_BYTES = 50 * 1024 * 1024

EXTENSION_TO_TYPE = {
    ".pdf": "pdf",
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
    ".txt": "text",
    ".vtt": "text",
}


@dataclass
class Document:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access (doc["text"]) alongside attribute access."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key) from None


class _TextExtractingHTMLParser(HTMLParser):
    """Collects visible text, the <title>, and heading text from an HTML document."""

    SKIP_TAGS: ClassVar[set[str]] = {"script", "style"}
    HEADING_TAGS: ClassVar[set[str]] = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self.title: str | None = None
        self.headings: list[str] = []
        self._skip_depth = 0
        self._capture_title = False
        self._heading_tag: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._capture_title = True
        elif tag in self.HEADING_TAGS:
            self._heading_tag = tag

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._capture_title = False
        elif tag == self._heading_tag:
            self._heading_tag = None

    def handle_data(self, data):
        if self._skip_depth:
            return
        stripped = data.strip()
        if not stripped:
            return
        if self._capture_title and self.title is None:
            self.title = stripped
        if self._heading_tag:
            self.headings.append(f"{self._heading_tag}:{stripped}")
        self.chunks.append(stripped)


class DocumentLoader:
    """Loads PDF, Markdown, HTML, and plain-text files into Document objects."""

    def __init__(self, max_file_bytes: int = MAX_FILE_BYTES):
        self._max_file_bytes = max_file_bytes

    def load(self, path: Path | str) -> Document:
        path = Path(path)
        file_type = EXTENSION_TO_TYPE.get(path.suffix.lower())
        if file_type is None:
            raise ValueError(f"Unsupported file type: {path.suffix} ({path.name})")

        size = path.stat().st_size
        if size > self._max_file_bytes:
            raise ValueError(
                f"{path.name} is {size} bytes, over the {self._max_file_bytes} byte limit"
            )

        loader = getattr(self, f"_load_{file_type}")
        text, extra = loader(path)

        metadata: dict[str, Any] = {
            "source": path.name,
            "file_type": file_type,
            "load_timestamp": datetime.now(UTC).isoformat(),
            # Stable across reloads (content-derived, not random) so re-ingesting the
            # same file doesn't mint a new document identity, but changes if the file's
            # content changes — deliberately not a UUID, which would do neither.
            "parent_doc_id": self._doc_id(path, size),
        }
        metadata.update(extra)

        logger.info(
            "Loaded %s (%s, %d chars, %d bytes)", path.name, file_type, len(text), size
        )
        return Document(text=text, metadata=metadata)

    def load_directory(self, directory: Path | str = DOCUMENTS_DIR) -> list[Document]:
        directory = Path(directory)
        documents = []
        for path in sorted(directory.iterdir()):
            if not path.is_file() or path.suffix.lower() not in EXTENSION_TO_TYPE:
                continue
            documents.append(self.load(path))
        logger.info("Loaded %d documents from %s", len(documents), directory)
        return documents

    @staticmethod
    def _doc_id(path: Path, size: int) -> str:
        digest = hashlib.sha256(f"{path.name}:{size}".encode()).hexdigest()
        return digest[:16]

    def _load_pdf(self, path: Path) -> tuple[str, dict[str, Any]]:
        pages = []
        offsets = []
        cursor = 0
        separator = "\n\n"
        with pymupdf.open(path) as doc:
            pdf_title = (doc.metadata or {}).get("title") or None
            for page in doc:
                text = page.get_text()
                offsets.append(cursor)
                pages.append(text)
                cursor += len(text) + len(separator)
            page_count = doc.page_count

        # Character offsets let a later chunking stage map a chunk back to its page
        # without carrying a second copy of the document in metadata.
        return separator.join(pages), {
            "page_count": page_count,
            "page_offsets": offsets,
            "title": pdf_title or path.stem,
        }

    def _load_markdown(self, path: Path) -> tuple[str, dict[str, Any]]:
        text = path.read_text(encoding="utf-8")
        headings = [
            (len(hashes), title.strip())
            for hashes, title in re.findall(r"^(#{1,6})\s+(.+)$", text, re.MULTILINE)
        ]
        title = next((t for level, t in headings if level == 1), path.stem)
        return text, {
            "headings": [f"h{level}:{t}" for level, t in headings],
            "title": title,
        }

    def _load_html(self, path: Path) -> tuple[str, dict[str, Any]]:
        parser = _TextExtractingHTMLParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        return "\n".join(parser.chunks), {
            "headings": parser.headings,
            "title": parser.title or path.stem,
        }

    def _load_text(self, path: Path) -> tuple[str, dict[str, Any]]:
        return path.read_text(encoding="utf-8"), {"title": path.stem}


def main():
    logging.basicConfig(level=logging.INFO)
    for doc in DocumentLoader().load_directory():
        print(f"--- {doc.metadata['source']} ({len(doc.text)} chars) ---")
        print(doc.metadata)
        print()


if __name__ == "__main__":
    main()
