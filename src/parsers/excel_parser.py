"""Parser module for Excel spreadsheets (.xlsx) and CSV files.

Extracts tabular datasets, processes multi-sheet sheets, splits rows into logical chunks,
and converts records into Markdown tables.
"""

import csv
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.config import config
from .base import DocumentParser, ParsedDocument, DocumentSection, SourceType

logger = logging.getLogger(__name__)


class ExcelParser(DocumentParser):
    """Parser for Excel and CSV spreadsheets.

    Splits large grids into row segments, formatting each segment as a Markdown table
    to preserve spatial tabular logic for the LLM context.
    """

    ROWS_PER_SECTION: int = 25  # Split large tables into sections of this many rows

    def supported_extensions(self) -> List[str]:
        """Supported file extensions.

        Returns:
            List of extensions: ['.xlsx', '.xls', '.csv']
        """
        return [".xlsx", ".xls", ".csv"]

    def parse(self, file_path: Path) -> List[ParsedDocument]:
        """Parse an Excel or CSV file.

        Args:
            file_path: Absolute path to the spreadsheet.

        Returns:
            A list containing a single ParsedDocument.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Spreadsheet file not found: {file_path}")

        logger.info(f"Parsing spreadsheet file: {file_path}")

        # 1. Load data
        # Dict mapping sheet_name -> DataFrame
        sheets: Dict[str, pd.DataFrame] = {}
        suffix = file_path.suffix.lower()

        try:
            if suffix == ".csv":
                df = pd.read_csv(file_path)
                sheets["Sheet1"] = df
            else:
                # Read all sheets in Excel file
                excel_sheets = pd.read_excel(file_path, sheet_name=None)
                for sheet_name, df in excel_sheets.items():
                    sheets[sheet_name] = df
        except Exception as e:
            logger.error(f"Failed to read spreadsheet {file_path}: {e}")
            raise

        # 2. Load ACL permissions
        acl_tags = ["all"]
        permissions_path = Path(config.PERMISSIONS_FILE)
        if permissions_path.exists():
            try:
                with open(permissions_path, "r", encoding="utf-8") as pf:
                    perms = json.load(pf)
                    acl_tags = perms.get("documents", {}).get(file_path.name, ["all"])
            except Exception as e:
                logger.warning(f"Failed to load permissions file: {e}")

        # 3. Process each sheet and compile sections/tables
        sections: List[DocumentSection] = []
        tables: List[str] = []
        full_markdown_parts = []

        for sheet_name, df in sheets.items():
            # Handle empty tables
            if df.empty:
                logger.debug(f"Sheet '{sheet_name}' is empty, skipping.")
                continue

            # Fill NaN values with empty strings
            df = df.fillna("")

            # Get headers
            headers = [str(col).strip() for col in df.columns]

            # Split rows into chunks
            num_rows = len(df)
            for start_row in range(0, num_rows, self.ROWS_PER_SECTION):
                end_row = min(start_row + self.ROWS_PER_SECTION, num_rows)
                df_slice = df.iloc[start_row:end_row]

                # Convert this slice to markdown table
                md_table = self._dataframe_to_markdown(headers, df_slice)
                tables.append(md_table)
                full_markdown_parts.append(md_table)

                # Heading details
                row_desc = f"(rows {start_row + 1}-{end_row})"
                heading = f"{sheet_name} {row_desc}"
                heading_path = f"{file_path.stem} > {sheet_name} > {row_desc}"

                sections.append(
                    DocumentSection(
                        heading=heading,
                        heading_level=1,
                        heading_path=heading_path,
                        content=md_table,
                        row_range=f"{start_row + 1}-{end_row}"
                    )
                )

        full_content = "\n\n---\n\n".join(full_markdown_parts)
        doc_id = hashlib.md5(str(file_path.resolve()).encode("utf-8")).hexdigest()
        title = file_path.stem

        doc = ParsedDocument(
            doc_id=doc_id,
            content=full_content,
            source_type=SourceType.EXCEL,
            title=title,
            source_path=str(file_path.resolve()),
            metadata={"sheet_count": len(sheets), "row_chunk_size": self.ROWS_PER_SECTION},
            sections=sections,
            tables=tables,
            acl_tags=acl_tags,
            is_scanned=False
        )

        return [doc]

    @staticmethod
    def _dataframe_to_markdown(headers: List[str], df: pd.DataFrame) -> str:
        """Convert a Pandas DataFrame slice to a Markdown table string."""
        def _cell(val) -> str:
            """Sanitize cell value."""
            return str(val).replace("\n", " ").replace("|", "\\|").strip()

        # Build table header
        cleaned_headers = [_cell(h) for h in headers]
        header_line = "| " + " | ".join(cleaned_headers) + " |"
        sep_line = "| " + " | ".join("---" for _ in cleaned_headers) + " |"

        lines = [header_line, sep_line]
        
        # Build rows
        for _, row in df.iterrows():
            row_cells = [_cell(row[col]) for col in df.columns]
            lines.append("| " + " | ".join(row_cells) + " |")

        return "\n".join(lines)
