"""
Parser module for Excel spreadsheets (.xlsx) and CSV files.

Extracts structured tabular datasets, processes multi-sheet workbooks,
splits large sheets into logical chunks, and converts records into
Markdown tables suitable for downstream RAG pipelines.
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.config import config
from .base import (
    DocumentParser,
    ParsedDocument,
    DocumentSection,
    SourceType,
)

logger = logging.getLogger(__name__)


class ExcelParser(DocumentParser):
    """
    Parser for Excel (.xlsx/.xls) and CSV documents.

    Large sheets are divided into multiple DocumentSections so that
    retrieval remains efficient and chunk sizes stay manageable.
    """

    ROWS_PER_SECTION = 25

    def supported_extensions(self) -> List[str]:
        """
        Supported spreadsheet formats.
        """
        return [
            ".xlsx",
            ".xls",
            ".csv",
        ]

    def parse(
        self,
        file_path: Path,
    ) -> List[ParsedDocument]:

        file_path = Path(file_path)

        if not file_path.exists():

            raise FileNotFoundError(
                f"Spreadsheet file not found: {file_path}"
            )

        logger.info(
            f"Parsing spreadsheet: {file_path.name}"
        )

        logger.info(
            "File size: %.2f KB",
            file_path.stat().st_size / 1024,
        )

        sheets: Dict[str, pd.DataFrame] = {}

        suffix = file_path.suffix.lower()

        try:

            if suffix == ".csv":

                df = pd.read_csv(file_path)

                sheets["Sheet1"] = (
                    df.fillna("")
                    .astype(str)
                )

            else:

                workbook = pd.read_excel(
                    file_path,
                    sheet_name=None,
                )

                for sheet_name, df in workbook.items():

                    sheets[sheet_name] = (
                        df.fillna("")
                        .astype(str)
                    )

        except Exception as exc:

            logger.error(
                f"Unable to read spreadsheet: {exc}"
            )

            raise

        logger.info(
            "Workbook contains %d sheet(s)",
            len(sheets),
        )

        # --------------------------------------------------
        # Load ACL Permissions
        # --------------------------------------------------

        acl_tags = ["all"]

        permissions_path = Path(
            config.PERMISSIONS_FILE
        )

        if permissions_path.exists():

            try:

                with open(
                    permissions_path,
                    "r",
                    encoding="utf-8",
                ) as fp:

                    permissions = json.load(fp)

                    acl_tags = (
                        permissions
                        .get("documents", {})
                        .get(
                            file_path.name,
                            ["all"],
                        )
                    )

            except Exception as exc:

                logger.warning(
                    f"ACL loading failed: {exc}"
                )

        # --------------------------------------------------
        # Prepare Containers
        # --------------------------------------------------

        sections: List[DocumentSection] = []

        tables: List[str] = []

        full_markdown_parts: List[str] = []

                # --------------------------------------------------
        # Process Every Sheet
        # --------------------------------------------------

        for sheet_name, df in sheets.items():

            if df.empty:

                logger.debug(
                    "Skipping empty sheet: %s",
                    sheet_name,
                )

                continue

            headers = [
                str(col).strip()
                for col in df.columns
            ]

            num_rows = len(df)

            logger.info(
                "Processing sheet '%s' (%d rows)",
                sheet_name,
                num_rows,
            )

            for start_row in range(
                0,
                num_rows,
                self.ROWS_PER_SECTION,
            ):

                end_row = min(
                    start_row + self.ROWS_PER_SECTION,
                    num_rows,
                )

                df_slice = df.iloc[
                    start_row:end_row
                ]

                markdown_table = (
                    self._dataframe_to_markdown(
                        headers,
                        df_slice,
                    )
                )

                tables.append(markdown_table)

                full_markdown_parts.append(
                    markdown_table
                )

                row_description = (
                    f"Rows {start_row + 1}-{end_row}"
                )

                heading = (
                    f"{sheet_name} "
                    f"({row_description})"
                )

                heading_path = (
                    f"{file_path.stem}"
                    f" > {sheet_name}"
                    f" > {row_description}"
                )

                sections.append(

                    DocumentSection(

                        heading=heading,

                        heading_level=1,

                        heading_path=heading_path,

                        content=markdown_table,

                        row_range=row_description,

                    )

                )

        # --------------------------------------------------
        # Build Full Document
        # --------------------------------------------------

        full_content = "\n\n---\n\n".join(
            full_markdown_parts
        ).strip()

        if not full_content:

            raise ValueError(
                f"No readable spreadsheet "
                f"content found in {file_path}"
            )

        logger.info(
            "Generated %d sections and %d tables",
            len(sections),
            len(tables),
        )

        title = (
            file_path.stem
            .replace("-", " ")
            .replace("_", " ")
            .title()
        )

        doc_id = hashlib.sha256(
            full_content.encode("utf-8")
        ).hexdigest()

        document = ParsedDocument(

            doc_id=doc_id,

            content=full_content,

            source_type=SourceType.EXCEL,

            title=title,

            source_path=str(
                file_path.resolve()
            ),

            metadata={

                "source_file": file_path.name,

                "file_size": file_path.stat().st_size,

                "parser": "pandas",

                "sheet_count": len(sheets),

                "row_chunk_size": self.ROWS_PER_SECTION,

                "table_count": len(tables),

                "section_count": len(sections),

                "extension": file_path.suffix,

            },

            sections=sections,

            tables=tables,

            acl_tags=acl_tags,

            is_scanned=False,

        )

        return [document]

    @staticmethod
    def _dataframe_to_markdown(
        headers: List[str],
        df: pd.DataFrame,
    ) -> str:
        """
        Convert a DataFrame slice into a Markdown table.

        Args:
            headers:
                Column headers.

            df:
                DataFrame slice.

        Returns:
            Markdown formatted table.
        """

        def sanitize(value) -> str:
            """
            Clean individual cell values.
            """

            if pd.isna(value):
                return ""

            return (
                str(value)
                .replace("\n", " ")
                .replace("\r", " ")
                .replace("|", "\\|")
                .strip()
            )

        cleaned_headers = [
            sanitize(h)
            for h in headers
        ]

        header_line = (
            "| "
            + " | ".join(cleaned_headers)
            + " |"
        )

        separator_line = (
            "| "
            + " | ".join(
                "---"
                for _ in cleaned_headers
            )
            + " |"
        )

        lines = [
            header_line,
            separator_line,
        ]

        for _, row in df.iterrows():

            row_cells = [
                sanitize(
                    row[column]
                )
                for column in df.columns
            ]

            if len(row_cells) < len(cleaned_headers):

                row_cells.extend(
                    [""] * (
                        len(cleaned_headers)
                        - len(row_cells)
                    )
                )

            row_cells = row_cells[
                : len(cleaned_headers)
            ]

            lines.append(
                "| "
                + " | ".join(row_cells)
                + " |"
            )

        return "\n".join(lines)
    
