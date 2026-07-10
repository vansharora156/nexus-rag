"""PDF document parser with automatic OCR fallback.

Extracts text and tables from ``.pdf`` files using *pdfplumber*. When a
page contains fewer than :pyattr:`OCR_THRESHOLD` characters of
extractable text (common in scanned / image-only PDFs), the parser
transparently falls back to **PaddleOCR** for that page.
"""

import hashlib
import json
import logging
import traceback
from pathlib import Path
from typing import List, Optional, Any

from src.config import config
from .base import DocumentParser, ParsedDocument, DocumentSection, SourceType

logger = logging.getLogger(__name__)


class OCRUnavailableError(Exception):
    """Raised when OCR cannot be performed in the current environment."""


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
        OCR_MAX_PIXELS: Maximum pixel count for OCR images to reduce
            memory usage.
        OCR_MAX_DIMENSION: Maximum width or height for OCR images.
            Large pages are downsampled before OCR.
    """

    OCR_THRESHOLD: int = 50
    OCR_MAX_PIXELS: int = 1_200_000
    OCR_MAX_DIMENSION: int = 1200

    def __init__(self):
        """
        Initialize parser.
        OCR client is created lazily (only when first needed) because
        PaddleOCR initialization is expensive.
        """
        self.ocr_client = None
        self.ocr_enabled = True
        self._fitz_available: Optional[bool] = None

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
                        try:
                            ocr_text = self._extract_text_with_ocr(file_path, page_num)
                        except OCRUnavailableError as exc:
                            logger.warning(
                                "Skipping scanned PDF '%s': OCR unavailable (%s)",
                                file_path.name,
                                exc,
                            )
                            return []
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
            logger.warning("No text could be extracted from PDF: %s", file_path)
            return []

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

    def _extract_text_with_ocr(self, file_path: Path, page_num: int) -> str:
        """Run OCR on a single PDF page using the configured OCR engine."""
        engine = config.OCR_ENGINE.strip().lower()
        if engine == "paddleocr":
            if not self.ocr_enabled:
                logger.warning(
                    "PaddleOCR has been disabled after a previous failure. Falling back to Tesseract for page %d",
                    page_num,
                )
                return self._ocr_with_tesseract(file_path, page_num)

            try:
                text = self._ocr_with_paddleocr(file_path, page_num)
            except OCRUnavailableError:
                raise
            if text:
                return text

            logger.warning(
                "PaddleOCR failed or produced no text on page %d; falling back to Tesseract if available",
                page_num,
            )
            return self._ocr_with_tesseract(file_path, page_num)

        if engine in ("tesseract", "pytesseract"):
            return self._ocr_with_tesseract(file_path, page_num)

        raise OCRUnavailableError(
            f"Unsupported OCR engine '{config.OCR_ENGINE}' configured"
        )

    def _rasterize_pdf_page(self, file_path: Path, page_num: int, dpi: Optional[int] = None):
        """Render a PDF page to a PIL image."""
        dpi = dpi or config.OCR_RENDER_DPI
        try:
            import pdfplumber

            with pdfplumber.open(str(file_path)) as pdf:
                page = pdf.pages[page_num - 1]
                page_image = page.to_image(resolution=dpi)

            if hasattr(page_image, "original") and page_image.original is not None:
                return page_image.original
            if hasattr(page_image, "pil") and page_image.pil is not None:
                return page_image.pil
            if hasattr(page_image, "to_pil"):
                return page_image.to_pil()

            raise RuntimeError("pdfplumber failed to produce a PIL image")
        except Exception as exc:
            logger.warning(
                "pdfplumber rasterization failed for page %d at dpi %d: %s; trying PyMuPDF fallback",
                page_num,
                dpi,
                exc,
            )

        if self._fitz_available is False:
            raise RuntimeError(
                f"Unable to rasterize PDF page {page_num}: PyMuPDF fallback previously failed"
            )

        try:
            import fitz  # PyMuPDF
            from PIL import Image

            with fitz.open(str(file_path)) as doc:
                page = doc.load_page(page_num - 1)
                pix = page.get_pixmap(dpi=dpi)

            mode = "RGBA" if pix.alpha else "RGB"
            self._fitz_available = True
            return Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        except ImportError as exc:
            self._fitz_available = False
            raise RuntimeError(
                f"Unable to rasterize PDF page {page_num}: PyMuPDF is not installed: {exc}"
            ) from exc
        except MemoryError as exc:
            if dpi > 72:
                lower_dpi = max(72, dpi // 2)
                logger.warning(
                    "PyMuPDF ran out of memory at dpi %d for page %d; retrying at lower dpi %d",
                    dpi,
                    page_num,
                    lower_dpi,
                )
                return self._rasterize_pdf_page(file_path, page_num, dpi=lower_dpi)
            raise RuntimeError(
                f"Unable to rasterize PDF page {page_num}: {exc}"
            ) from exc
        except Exception as exc:
            message = str(exc).lower()
            if dpi > 72 and "malloc" in message:
                lower_dpi = max(72, dpi // 2)
                logger.warning(
                    "PyMuPDF malloc failed at dpi %d for page %d; retrying at lower dpi %d",
                    dpi,
                    page_num,
                    lower_dpi,
                )
                return self._rasterize_pdf_page(file_path, page_num, dpi=lower_dpi)

            raise RuntimeError(
                f"Unable to rasterize PDF page {page_num}: {exc}"
            ) from exc

    def _ocr_with_paddleocr(self, file_path: Path, page_num: int) -> str:
        try:
            import numpy as np  # lazy import
            from paddleocr import PaddleOCR as OCR  # lazy import  # type: ignore[import]

            image = self._rasterize_pdf_page(file_path, page_num)
            image = self._prepare_ocr_image(image, page_num)
            image_array = np.array(image.convert("RGB"))

            if self.ocr_client is None:
                try:
                    self.ocr_client = OCR(
                        use_angle_cls=True,
                        lang=config.OCR_LANGUAGE,
                    )
                except (TypeError, ValueError):
                    try:
                        self.ocr_client = OCR(
                            lang=config.OCR_LANGUAGE,
                        )
                    except (TypeError, ValueError):
                        self.ocr_client = OCR(
                            lang=config.OCR_LANGUAGE.strip().lower()
                        )
            result = self.ocr_client.ocr(image_array, cls=True)

            if not result or not result[0]:
                return ""

            text_lines = [line[1][0] for line in result[0]]
            text = "\n".join(text_lines)

            logger.debug("PaddleOCR extracted %d chars from page %d", len(text), page_num)
            return text
        except ImportError as exc:
            raise OCRUnavailableError(
                "PaddleOCR or its dependencies are not installed"
            ) from exc
        except MemoryError as exc:
            logger.warning(
                "PaddleOCR failed with MemoryError on page %d: %s",
                page_num,
                exc,
            )
            self.ocr_enabled = False
            return ""
        except Exception as exc:
            logger.warning("PaddleOCR failed on page %d: %s", page_num, exc)
            return ""

    def _prepare_ocr_image(
        self,
        image,
        page_num: int,
        max_pixels: Optional[int] = None,
        max_dimension: Optional[int] = None,
    ):
        """Downsample large images to reduce memory usage during OCR."""
        try:
            from PIL import Image
        except ImportError:
            return image

        max_pixels = max_pixels or self.OCR_MAX_PIXELS
        max_dimension = max_dimension or self.OCR_MAX_DIMENSION

        width, height = image.size
        pixel_count = width * height
        if pixel_count <= max_pixels and max(width, height) <= max_dimension:
            return image

        scale = min(
            (max_pixels / pixel_count) ** 0.5,
            max_dimension / max(width, height),
        )
        new_width = max(1, int(width * scale))
        new_height = max(1, int(height * scale))

        logger.warning(
            "Downsampling OCR image for page %d from %dx%d to %dx%d",
            page_num,
            width,
            height,
            new_width,
            new_height,
        )
        return image.resize((new_width, new_height), Image.LANCZOS)

    def _ocr_with_tesseract(self, file_path: Path, page_num: int) -> str:
        try:
            import os
            import shutil
            import pytesseract  # lazy import  # type: ignore[import]

            tesseract_cmd = shutil.which("tesseract")
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            if "TESSDATA_PREFIX" not in os.environ and tesseract_cmd:
                tessdata_dir = Path(tesseract_cmd).resolve().parent / "tessdata"
                if tessdata_dir.exists():
                    os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)
                    logger.debug("Set TESSDATA_PREFIX=%s", tessdata_dir)

            language = config.OCR_LANGUAGE.strip().lower()
            if language == "en":
                language = "eng"

            image = self._rasterize_pdf_page(file_path, page_num)
            image = self._prepare_ocr_image(image, page_num)
            try:
                text = pytesseract.image_to_string(
                    image.convert("RGB"),
                    lang=language,
                    config="--psm 1",
                )
            except Exception as exc:
                message = str(exc).lower()
                if "bad_alloc" in message or "out of memory" in message or "malloc" in message:
                    logger.warning(
                        "Tesseract failed on page %d due to memory error; retrying with smaller image",
                        page_num,
                    )
                    image = self._prepare_ocr_image(
                        image,
                        page_num,
                        max_pixels=max(300_000, self.OCR_MAX_PIXELS // 4),
                        max_dimension=max(800, self.OCR_MAX_DIMENSION // 2),
                    )
                    try:
                        text = pytesseract.image_to_string(
                            image.convert("RGB"),
                            lang=language,
                            config="--psm 1",
                        )
                    except Exception as exc2:
                        logger.warning(
                            "Tesseract retry failed on page %d: %s",
                            page_num,
                            exc2,
                        )
                        raise
                else:
                    raise
            logger.debug("Tesseract OCR extracted %d chars from page %d", len(text), page_num)
            return text.strip()
        except ImportError as exc:
            raise OCRUnavailableError(
                "pytesseract is not installed. Install pytesseract and a Tesseract binary to enable Tesseract OCR."
            ) from exc
        except pytesseract.pytesseract.TesseractError as exc:
            raise OCRUnavailableError(
                f"Tesseract OCR command failed: {exc}"
            ) from exc
        except Exception as exc:
            logger.warning("Tesseract OCR failed on page %d: %s", page_num, exc)
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
