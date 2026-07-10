"""src.parsers module initialization for NexusRAG."""

from .base import DocumentParser, ParsedDocument, DocumentSection, SourceType
from .markdown_parser import MarkdownParser
from .pdf_parser import PDFParser
from .slack_parser import SlackParser
from .excel_parser import ExcelParser
from .registry import ParserRegistry

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "DocumentSection",
    "SourceType",
    "MarkdownParser",
    "PDFParser",
    "SlackParser",
    "ExcelParser",
    "ParserRegistry",
]
