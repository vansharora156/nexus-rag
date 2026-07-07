"""
Parser module for Markdown/Confluence files.

Extracts text, headings, frontmatter, and tables from Markdown documents.
Preserves structural relationships through heading hierarchies and page paths.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import List

from src.config import config
from .base import (
    DocumentParser,
    ParsedDocument,
    DocumentSection,
    SourceType,
)

logger = logging.getLogger(__name__)


class MarkdownParser(DocumentParser):
    """
    Parser for Confluence-style Markdown documents.

    Maintains section context by tracking heading stacks (H1-H6)
    and extracting tables into Markdown format.
    """

    def supported_extensions(self) -> List[str]:
        return [".md", ".markdown", ".mdx"]

    def parse(self, file_path: Path) -> List[ParsedDocument]:

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Markdown file not found: {file_path}"
            )

        logger.info(f"Parsing Markdown file: {file_path}")

        logger.info(
            "File size: %.2f KB",
            file_path.stat().st_size / 1024,
        )

        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # ----------------------------------------------------
        # Parse Frontmatter
        # ----------------------------------------------------

        metadata = {}
        content_text = raw_text

        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n",
            raw_text,
            re.DOTALL,
        )

        if frontmatter_match:

            frontmatter_raw = frontmatter_match.group(1)

            content_text = raw_text[
                frontmatter_match.end():
            ]

            for line in frontmatter_raw.splitlines():

                if ":" in line:

                    key, value = line.split(":", 1)

                    metadata[key.strip()] = value.strip()

        # ----------------------------------------------------
        # Extract Markdown Tables
        # ----------------------------------------------------

        tables: List[str] = []

        table_pattern = r"(?:^\|[^\n]+\|\s*\n){2,}"

        table_matches = list(
            re.finditer(
                table_pattern,
                content_text,
                re.MULTILINE,
            )
        )

        for match in table_matches:
            tables.append(match.group(0).strip())

        # ----------------------------------------------------
        # Load ACL
        # ----------------------------------------------------

        acl_tags = ["all"]

        permissions_path = Path(config.PERMISSIONS_FILE)

        if permissions_path.exists():

            try:

                with open(
                    permissions_path,
                    "r",
                    encoding="utf-8",
                ) as pf:

                    permissions = json.load(pf)

                    acl_tags = (
                        permissions
                        .get("documents", {})
                        .get(file_path.name, ["all"])
                    )

            except Exception as e:

                logger.warning(
                    f"Failed loading ACL: {e}"
                )

        # ----------------------------------------------------
        # Parse Sections
        # ----------------------------------------------------

        sections: List[DocumentSection] = []

        lines = content_text.splitlines()

        heading_stack = []

        current_heading = "Overview"

        current_level = 1

        current_section_lines = []

        def get_heading_path():

            if not heading_stack:
                return current_heading

            return " > ".join(
                heading
                for _, heading in heading_stack
            )

        for line in lines:

            heading_match = re.match(
                r"^(#{1,6})\s+(.+)$",
                line,
            )

            if (
                heading_match
                and not line.strip().startswith("```")
            ):

                section_content = (
                    "\n".join(current_section_lines)
                    .strip()
                )

                if section_content:

                    sections.append(

                        DocumentSection(

                            heading=current_heading,

                            heading_level=current_level,

                            heading_path=get_heading_path(),

                            content=section_content,

                        )

                    )

                current_section_lines = []

                level = len(
                    heading_match.group(1)
                )

                heading_text = (
                    heading_match.group(2)
                    .strip()
                )

                while (
                    heading_stack
                    and heading_stack[-1][0] >= level
                ):
                    heading_stack.pop()

                heading_stack.append(
                    (
                        level,
                        heading_text,
                    )
                )

                current_heading = heading_text

                current_level = level

            else:

                current_section_lines.append(line)

        section_content = (
            "\n".join(current_section_lines)
            .strip()
        )

        if section_content:

            sections.append(

                DocumentSection(

                    heading=current_heading,

                    heading_level=current_level,

                    heading_path=get_heading_path(),

                    content=section_content,

                )

            )

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        title = (
            heading_stack[0][1]
            if (
                heading_stack
                and heading_stack[0][0] == 1
            )
            else file_path.stem
            .replace("-", " ")
            .title()
        )

        # ----------------------------------------------------
        # Document ID
        # ----------------------------------------------------

        doc_id = hashlib.sha256(
            content_text.encode("utf-8")
        ).hexdigest()

        logger.info(
            "Sections: %d | Tables: %d",
            len(sections),
            len(tables),
        )

        # ----------------------------------------------------
        # ParsedDocument
        # ----------------------------------------------------

        document = ParsedDocument(

            doc_id=doc_id,

            content=content_text.strip(),

            source_type=SourceType.CONFLUENCE,

            title=title,

            source_path=str(file_path.resolve()),

            metadata={
                **metadata,
                "source_file": file_path.name,
                "file_size": file_path.stat().st_size,
                "parser": "markdown",
                "section_count": len(sections),
                "table_count": len(tables),
                "extension": file_path.suffix,
            },

            sections=sections,

            tables=tables,

            acl_tags=acl_tags,

            is_scanned=False,
        )

        return [document]