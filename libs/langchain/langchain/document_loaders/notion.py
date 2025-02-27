"""Loads Notion directory dump."""
from pathlib import Path
from typing import List

from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader


class NotionDirectoryLoader(BaseLoader):
    """Loads Notion directory dump."""

    def __init__(self, path: str):
        """Initialize with a file path."""
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
