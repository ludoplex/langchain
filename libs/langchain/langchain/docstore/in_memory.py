"""Simple in memory docstore in the form of a dict."""
from typing import Dict, Optional, Union

from langchain.docstore.base import AddableMixin, Docstore
from langchain.docstore.document import Document


class InMemoryDocstore(Docstore, AddableMixin):
    """Simple in memory docstore in the form of a dict."""

    def __init__(self, _dict: Optional[Dict[str, Document]] = None):
        """Initialize with dict."""
        self._dict = _dict if _dict is not None else {}

    def add(self, texts: Dict[str, Document]) -> None:
        """Add texts to in memory dictionary.

        Args:
            texts: dictionary of id -> document.

        Returns:
            None
        """
        if overlapping := set(texts).intersection(self._dict):
            raise ValueError(f"Tried to add ids that already exist: {overlapping}")
        self._dict = {**self._dict, **texts}

    def search(self, search: str) -> Union[str, Document]:
        """Search via direct lookup.

        Args:
            search: id of a document to search for.

        Returns:
            Document if found, else error message.
        """
        if search not in self._dict:
            return f"ID {search} not found."
        else:
            return self._dict[search]
