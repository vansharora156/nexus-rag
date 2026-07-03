"""PDF document parser with automatic OCR fallback.

Extracts text and tables from ``.pdf`` files using *pdfplumber*. When a
page contains fewer than :pyattr:`OCR_THRESHOLD` characters of
extractable text (common in scanned / image-only PDFs), the parser
transparently falls back to **PaddleOCR** for that page.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import List, Optional, Any

from src.config import config
from .base import DocumentParser, ParsedDocument, DocumentSection, SourceType

logger = logging.getLogger(__name__)


class PDFParser(DocumentParser):
    """Parser for PDF documents with automatic OCR fallback.

    Strategy
    --------
    1. Try text extraction with **pdfplumber**.
    2. If extracted text is too sparse (< :pyattr:`OCR_THRESHOLD`
       chars/page), fall back to OCR via **PaddleOCR**.
    3. Extract tables via ``pdfplumber.extract_tables()`` and convert
       them to Markdown table strings.

    Attributes:
        OCR_THRESHOLD: Minimum characters per page before OCR is
            triggered. Defaults to ``50``.
    """

    OCR_THRESHOLD: int = 50
    def __init__(self):
        """
        Initialize parser.
        OCR client is created lazily (only when first needed) because
        PaddleOCR initialization is expensive.
        """
        self.ocr_client = None

    def supported_extensions(self) -> List[str]:
        """Return extensions this parser handles.

        Returns:
            ``['.pdf']``
        """
        return [".pdf"]

    def parse(self, file_path: Path) -> List[ParsedDocument]:
        """Parse a PDF file into a list of :class:`ParsedDocument`.

        Each page is emitted as a separate :class:`DocumentSection`.
        Tables are extracted and stored as Markdown strings.

        Args:
            file_path: Absolute path to the ``.pdf`` file.

        Returns:
            A single-element list containing the parsed document.
        """
        import pdfplumber

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Parsing PDF file: {file_path}")

        sections: List[DocumentSection] = []
        tables: List[str] = []
        all_text_parts: List[str] = []
        is_scanned = False

        # Load ACL permissions
        acl_tags = ["all"]
        permissions_path = Path(config.PERMISSIONS_FILE)
        if permissions_path.exists():
            try:
                with open(permissions_path, "r", encoding="utf-8") as pf:
                    perms = json.load(pf)
                    acl_tags = perms.get("documents", {}).get(file_path.name, ["all"])
            except Exception as e:
                logger.warning(f"Failed to load permissions file: {e}")

        try:
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) == 0:
                    raise ValueError(f"PDF has no pages: {file_path}")

                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1

                    # 1. Text extraction
                    raw_text: Optional[str] = None
                    try:
                        raw_text = page.extract_text()
                    except Exception as e:
                        logger.warning(f"Text extraction failed on page {page_num}: {e}")

                    page_text = (raw_text or "").strip()

                    # 2. OCR fallback
                    if len(page_text) < self.OCR_THRESHOLD:
                        logger.debug(
                            f"Page {page_num} has {len(page_text)} chars - triggering OCR fallback"
                        )
                        ocr_text = self._extract_text_with_ocr(page, page_num)
                        if ocr_text:
                            page_text = ocr_text
                            is_scanned = True

                    all_text_parts.append(page_text)

                    # Heading heuristics
                    heading = self._detect_heading(page_text, page_num)

                    sections.append(
                        DocumentSection(
                            heading=heading,
                            heading_level=1,
                            heading_path=f"Page {page_num} > {heading}",
                            content=page_text,
                            page_number=page_num
                        )
                    )

                    # 3. Table extraction
                    try:
                        page_tables = page.extract_tables()
                        if page_tables:
                            for tbl in page_tables:
                                md_table = self._table_to_markdown(tbl)
                                if md_table:
                                    tables.append(md_table)
                    except Exception as e:
                        logger.warning(f"Table extraction failed on page {page_num}: {e}")

        except ValueError:
            raise
        except Exception as exc:
            logger.error(f"Failed to parse PDF {file_path}: {exc}")
            raise

        full_content = "\n\n".join(all_text_parts).strip()
        if not full_content:
            raise ValueError(f"No text could be extracted from PDF: {file_path}")

        title = self._extract_title(sections, file_path)
        doc_id = hashlib.sha256(full_content.encode("utf-8")).hexdigest()

        doc = ParsedDocument(
            doc_id=doc_id,
            content=full_content,
            source_type=SourceType.PDF,
            title=title,
            source_path=str(file_path.resolve()),
            metadata={
                "page_count": len(sections),
                "source_file": file_path.name,
                "file_size": file_path.stat().st_size,
                "parser": "pdfplumber",
                "ocr_enabled": is_scanned,
                },
       
            sections=sections,
            tables=tables,
            acl_tags=acl_tags,
            is_scanned=is_scanned
        )

        return [doc]

    def _extract_text_with_ocr(self, page: Any, page_num: int) -> str:
        """Run OCR on a single PDF page using PaddleOCR.

        The page is rasterised to a PIL ``Image`` via pdfplumber's
        built-in renderer, then passed to PaddleOCR.

        Args:
            page: A ``pdfplumber.Page`` object.
            page_num: 1-indexed page number (for logging).

        Returns:
            Extracted text as a single string, or ``""`` on failure.
        """
        try:
            import numpy as np  # lazy import
            from paddleocr import PaddleOCR as OCR  # lazy import  # type: ignore[import]

            pil_image = page.to_image(resolution=300).original
            image_array = np.array(pil_image)

            # Initialize PaddleOCR client (using CPU by default, English language, quiet logging)
            if self.ocr_client is None:
                self.ocr_client = OCR(
                    use_angle_cls=True,
                    lang=config.OCR_LANGUAGE,
                    show_log=False,
                    use_gpu=False,
                )
            result = self.ocr_client.ocr(image_array, cls=True)

            if not result or not result[0]:
                return ""

            # Extract text from layout lines
            text_lines = [line[1][0] for line in result[0]]
            text = "\n".join(text_lines)

            logger.debug(
                f"OCR extracted {len(text)} chars from page {page_num}"
            )
            return text
        except ImportError:
            logger.warning(
                f"paddleocr or numpy not installed – skipping OCR for page {page_num}"
            )
            return ""
        except Exception as exc:
            logger.warning(f"OCR failed for page {page_num}: {exc}")
            return ""

    @staticmethod
    def _table_to_markdown(table: List[List[Optional[str]]]) -> str:
        """Convert a pdfplumber table (list of rows) to a Markdown table."""
        if not table or len(table) < 1:
            return ""

        def _cell(value: Optional[str]) -> str:
            """Sanitise cell value."""
            if value is None:
                return ""
            return str(value).replace("\n", " ").replace("|", "\\|").strip()

        # Header row
        headers = [_cell(c) for c in table[0]]
        header_line = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join("---" for _ in headers) + " |"

        lines = [header_line, separator]
        for row in table[1:]:
            cells = [_cell(c) for c in row]
            while len(cells) < len(headers):
                cells.append("")
            cells = cells[: len(headers)]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    @staticmethod
    def _detect_heading(page_text: str, page_num: int) -> str:
        """Derive a section heading from the page text.

        Uses the first non-blank line of the page as the heading, capped
        at 120 characters. Falls back to ``"Page N"``.
        """
        for line in page_text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:120]
        return f"Page {page_num}"

    @staticmethod
    def _extract_title(sections: List[DocumentSection], file_path: Path) -> str:
        """Choose a document title.

        Prefers the heading of the first section; falls back to the
        filename stem.
        """
        if sections and sections[0].heading:
            return sections[0].heading
        return file_path.stem
