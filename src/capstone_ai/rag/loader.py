import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "documents"
SUPPORTED_EXTENSIONS = {".txt", ".md"}


def load_documents(directory: Path | str = DOCUMENTS_DIR) -> list[tuple[Path, str]]:
    """Read every .txt/.md file in directory and return (path, raw_text) pairs."""
    directory = Path(directory)
    documents = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        text = path.read_text(encoding="utf-8")
        documents.append((path, text))
    logger.info("Loaded %d documents from %s", len(documents), directory)
    return documents


def main():
    for path, text in load_documents():
        print(f"--- {path.name} ({len(text)} chars) ---")
        print(text)
        print()


if __name__ == "__main__":
    main()
