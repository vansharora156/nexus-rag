"""Abstract base parser and core data structures for document parsing.

This module defines the canonical data model that every concrete parser
must produce.  The two key dataclasses – ``ParsedDocument`` and
``DocumentSection`` – flow through the entire downstream pipeline
(chunking → dedup → indexing), so their fields are intentionally broad
enough to capture metadata from all supported source types.

Typical usage::

    class PdfParser(DocumentParser):
        def parse(self, file_path: Path) -> List[ParsedDocument]:
            ...

        def supported_extensions(self) -> List[str]:
            return [".pdf"]
"""

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class SourceType(Enum):
    """Enumeration of supported document source types.

    Each value maps to a concrete parser implementation and controls
    source-specific behaviour in the chunking layer (e.g. page-aware
    splitting for PDFs, row-range tracking for Excel).
    """

    CONFLUENCE = "confluence"
    PDF = "pdf"
    SLACK = "slack"
    EXCEL = "excel"


@dataclass
class ParsedDocument:
    """Structured representation of a parsed enterprise document.

    Attributes:
        doc_id: Unique document identifier (typically a content hash or
            UUID).  Must be deterministic for the same input so that
            re-ingestion is idempotent.
        content: Full plain-text content of the document, used as a
            fallback when section-level splitting is not possible.
        source_type: The ``SourceType`` enum value indicating the
            original format.
        title: Human-readable document title, extracted from the file
            name or in-document metadata.
        source_path: Absolute or relative path to the original source
            file on disk.
        metadata: Free-form dictionary for source-specific metadata
            (e.g. Confluence space key, Slack channel name, author,
            creation date).
        sections: Ordered list of ``DocumentSection`` objects produced
            by heading-aware parsing.  May be empty for flat documents.
        tables: List of tables converted to Markdown table syntax.
            Tables are indexed separately to support structured-data
            queries.
        acl_tags: Access-control labels associated with this document
            (e.g. ``["engineering", "hr-confidential"]``).  Used by the
            permissions layer to filter results at query time.
        is_scanned: ``True`` when the parser had to fall back to OCR
            (e.g. image-only PDFs).  Downstream stages may apply
            additional noise-cleaning heuristics in this case.
    """

    doc_id: str
    content: str
    source_type: SourceType
    title: str
    source_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    sections: List["DocumentSection"] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    acl_tags: List[str] = field(default_factory=list)
    is_scanned: bool = False


@dataclass
class DocumentSection:
    """A single logical section extracted from a parsed document.

    Sections map to headings in Confluence / Markdown documents, page
    breaks in PDFs, or named ranges / sheets in Excel files.

    Attributes:
        heading: The section heading text (stripped of markup).
        heading_level: Numeric heading depth where H1 = 1, H2 = 2, etc.
        heading_path: Concatenated ancestor headings that provide full
            hierarchical context, e.g. ``"Onboarding > Dev Setup"``.
        content: Body text belonging to this section (excludes the
            heading itself).
        page_number: 1-indexed page number for PDF sources; ``None``
            for other source types.
        row_range: Human-readable row range for Excel sources, e.g.
            ``"rows 5-20"``; ``None`` for other source types.
    """

    heading: str
    heading_level: int
    heading_path: str
    content: str
    page_number: Optional[int] = None
    row_range: Optional[str] = None


class DocumentParser(ABC):
    """Abstract base class that every format-specific parser must implement.

    Subclasses are responsible for:

    1. Reading a file from disk.
    2. Extracting text, headings, tables, and metadata.
    3. Returning one or more ``ParsedDocument`` instances (a single file
       may yield multiple logical documents – e.g. a multi-sheet Excel
       workbook).

    The ``can_parse`` convenience method lets the pipeline registry
    auto-discover which parser to use for a given file extension.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> List[ParsedDocument]:
        """Parse a file and return structured document(s).

        Args:
            file_path: Absolute path to the source file.

        Returns:
            A list of ``ParsedDocument`` objects extracted from the file.

        Raises:
            FileNotFoundError: If *file_path* does not exist.
            ValueError: If the file content is malformed or empty.
        """

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return file extensions this parser can handle.

        Returns:
            A list of lowercase extensions **including** the leading dot,
            e.g. ``[".pdf"]``.
        """

    def can_parse(self, file_path: Path) -> bool:
        """Check whether this parser supports the given file.

        Args:
            file_path: Path to the candidate file.

        Returns:
            ``True`` if the file's extension is in
            :meth:`supported_extensions`.
        """
        return file_path.suffix.lower() in self.supported_extensions()
