"""Loads Roam directory dump."""
from pathlib import Path
from typing import List

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader


class RoamLoader(BaseLoader):
    """Loads Roam files from disk."""

    def __init__(self, path: str):
        """Initialize with a path."""
        self.file_path = path

    def load(self) -> List[Document]:
        """Load documents."""
        ps = list(Path(self.file_path).glob("**/*.md"))
        docs = []
        for p in ps:
            text = Path(p).read_text()
            metadata = {"source": str(p)}
            docs.append(Document(page_content=text, metadata=metadata))
        return docs
