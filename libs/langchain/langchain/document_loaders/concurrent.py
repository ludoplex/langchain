from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Iterator, Literal, Optional, Sequence, Union

from langchain.document_loaders.base import BaseBlobParser
from langchain.document_loaders.blob_loaders import BlobLoader, FileSystemBlobLoader
from langchain.document_loaders.generic import GenericLoader
from langchain.document_loaders.parsers.registry import get_parser
from langchain.schema import Document

_PathLike = Union[str, Path]

DEFAULT = Literal["default"]


class ConcurrentLoader(GenericLoader):
    """
    A generic document loader that loads and parses documents concurrently.
    """

    def __init__(
        self, blob_loader: BlobLoader, blob_parser: BaseBlobParser, num_workers: int = 4
    ) -> None:
        super().__init__(blob_loader, blob_parser)
        self.num_workers = num_workers

    def lazy_load(
        self,
    ) -> Iterator[Document]:
        """Load documents lazily with concurrent parsing."""
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.num_workers
        ) as executor:
            futures = {
                executor.submit(self.blob_parser.lazy_parse, blob)
                for blob in self.blob_loader.yield_blobs()
            }
            for future in concurrent.futures.as_completed(futures):
                yield from future.result()

    @classmethod
    def from_filesystem(
        cls,
        path: _PathLike,
        *,
        glob: str = "**/[!.]*",
        suffixes: Optional[Sequence[str]] = None,
        show_progress: bool = False,
        parser: Union[DEFAULT, BaseBlobParser] = "default",
        num_workers: int = 4,
    ) -> ConcurrentLoader:
        """
        Create a concurrent generic document loader using a
        filesystem blob loader.
        """
        blob_loader = FileSystemBlobLoader(
            path, glob=glob, suffixes=suffixes, show_progress=show_progress
        )
        blob_parser = get_parser(parser) if isinstance(parser, str) else parser
        return cls(blob_loader, blob_parser, num_workers)
