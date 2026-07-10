import io
import logging
import unittest
from pathlib import Path

from src.config import config
from src.parsers.pdf_parser import PDFParser


class TestPDFParser(unittest.TestCase):
    def test_skips_scanned_pdf_when_ocr_unavailable(self):
        parser = PDFParser()
        parser.OCR_THRESHOLD = 1

        original_engine = config.OCR_ENGINE
        config.OCR_ENGINE = "unsupported-engine"

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("src.parsers.pdf_parser")
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)

        try:
            docs = parser.parse(Path("data/pdf/scanned-policy-doc.pdf"))
            self.assertEqual(docs, [])
            self.assertIn(
                "Skipping scanned PDF 'scanned-policy-doc.pdf': OCR unavailable",
                log_stream.getvalue(),
            )
        finally:
            config.OCR_ENGINE = original_engine
            logger.removeHandler(handler)
