"""
Parser registry module for NexusRAG.

Maintains the mapping of supported file extensions to document parser
instances, providing automatic parser discovery for the ingestion pipeline.
"""

import logging
from pathlib import Path
from typing import Dict, List

from .base import DocumentParser
from .pdf_parser import PDFParser
from .markdown_parser import MarkdownParser
from .excel_parser import ExcelParser
from .slack_parser import SlackParser

logger = logging.getLogger(__name__)


class ParserRegistry:
    """
    Registry for all document parsers.

    The registry creates one instance of each parser and automatically
    maps supported file extensions to the correct parser.

    Example
    -------
    >>> registry = ParserRegistry()
    >>> parser = registry.get_parser(Path("policy.pdf"))
    >>> documents = parser.parse(Path("policy.pdf"))
    """

    def __init__(self):
        """Initialize all available parsers."""

        logger.info("Initializing Parser Registry")

        self._parsers: List[DocumentParser] = [
            PDFParser(),
            MarkdownParser(),
            ExcelParser(),
            SlackParser(),
        ]

        self._extension_map: Dict[str, DocumentParser] = {}

        for parser in self._parsers:

            for extension in parser.supported_extensions():

                extension = extension.lower()

                if extension in self._extension_map:

                    logger.warning(
                        "Extension '%s' already registered. Overwriting with %s.",
                        extension,
                        parser.__class__.__name__,
                    )

                self._extension_map[extension] = parser

        logger.info(
            "Registered %d parsers supporting %d extensions.",
            len(self._parsers),
            len(self._extension_map),
        )

    def get_parser(
        self,
        file_path: Path,
    ) -> DocumentParser:
        """
        Return the appropriate parser for a file.

        Args:
            file_path:
                Path to the document.

        Returns:
            DocumentParser instance.

        Raises:
            ValueError:
                If no parser supports the file extension.
        """

        extension = file_path.suffix.lower()

        parser = self._extension_map.get(extension)

        if parser is None:

            supported = ", ".join(
                self.supported_extensions
            )

            raise ValueError(
                f"No parser registered for '{extension}'. "
                f"Supported extensions: {supported}"
            )

        logger.debug(
            "Selected %s for %s",
            parser.__class__.__name__,
            file_path.name,
        )

        return parser

    def can_parse(
        self,
        file_path: Path,
    ) -> bool:
        """
        Check whether the registry supports a file.

        Args:
            file_path:
                File path.

        Returns:
            True if supported.
        """

        return (
            file_path.suffix.lower()
            in self._extension_map
        )

    @property
    def supported_extensions(self) -> List[str]:
        """
        Return all supported extensions.

        Returns:
            Alphabetically sorted extensions.
        """

        return sorted(
            self._extension_map.keys()
        )

    def available_parsers(self) -> List[str]:
        """
        Return all registered parser class names.

        Returns:
            List of parser names.
        """

        return sorted(
            parser.__class__.__name__
            for parser in self._parsers
        )

    def __len__(self) -> int:
        """
        Return number of registered parsers.
        """

        return len(self._parsers)

    def __repr__(self) -> str:
        """
        String representation.
        """

        return (
            f"ParserRegistry("
            f"parsers={len(self)}, "
            f"extensions={len(self._extension_map)})"
        )