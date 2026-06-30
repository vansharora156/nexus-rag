"""Parser module for Markdown/Confluence files.

Extracts text, headings, frontmatter, and tables from Markdown documents.
Preserves structural relationships through heading hierarchies and page paths.
"""

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import config
from .base import DocumentParser, ParsedDocument, DocumentSection, SourceType

logger = logging.getLogger(__name__)


class MarkdownParser(DocumentParser):
    """Parser for Confluence-style Markdown documents.

    Maintains section context by tracking heading stacks (H1-H6) and
    extracting tables into unified Markdown strings.
    """

    def supported_extensions(self) -> List[str]:
        """Supported file extensions.

        Returns:
            List of extensions: ['.md', '.markdown', '.mdx']
        """
        return [".md", ".markdown", ".mdx"]

    def parse(self, file_path: Path) -> List[ParsedDocument]:
        """Parse a Markdown file.

        Args:
            file_path: Absolute path to the document.

        Returns:
            A list containing a single ParsedDocument.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        logger.info(f"Parsing Markdown file: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # 1. Parse frontmatter if present
        metadata = {}
        content_text = raw_text
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw_text, re.DOTALL)
        if frontmatter_match:
            frontmatter_raw = frontmatter_match.group(1)
            content_text = raw_text[frontmatter_match.end() :]
            for line in frontmatter_raw.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    metadata[key.strip()] = val.strip()

        # 2. Extract tables (consecutive lines starting and ending with |)
        tables: List[str] = []
        table_pattern = r"(?:^\|[^\n]+\|\s*\n){2,}"
        table_matches = list(re.finditer(table_pattern, content_text, re.MULTILINE))
        
        # Pull out raw tables
        for match in table_matches:
            tables.append(match.group(0).strip())

        # 3. Load ACL permissions
        acl_tags = ["all"]
        permissions_path = Path(config.PERMISSIONS_FILE)
        if permissions_path.exists():
            try:
                with open(permissions_path, "r", encoding="utf-8") as pf:
                    perms = json.load(pf)
                    acl_tags = perms.get("documents", {}).get(file_path.name, ["all"])
            except Exception as e:
                logger.warning(f"Failed to load permissions file: {e}")

        # 4. Parse sections and heading paths
        sections: List[DocumentSection] = []
        lines = content_text.splitlines()
        
        heading_stack = []  # tuple of (level, text)
        current_section_lines = []
        current_heading = "Overview"
        current_level = 1
        
        # Helper to compute heading path from stack
        def get_heading_path():
            if not heading_stack:
                return current_heading
            return " > ".join(h[1] for h in heading_stack)

        for line in lines:
            # Match heading e.g., "## Heading Text" or "# Title"
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match and not line.strip().startswith("```"):
                # Save previous section if it has text
                if current_section_lines:
                    sections.append(
                        DocumentSection(
                            heading=current_heading,
                            heading_level=current_level,
                            heading_path=get_heading_path(),
                            content="\n".join(current_section_lines).strip()
                        )
                    )
                    current_section_lines = []

                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # Adjust heading stack for hierarchy
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))

                current_heading = heading_text
                current_level = level
            else:
                current_section_lines.append(line)

        # Append last section
        if current_section_lines or current_heading != "Overview":
            sections.append(
                DocumentSection(
                    heading=current_heading,
                    heading_level=current_level,
                    heading_path=get_heading_path(),
                    content="\n".join(current_section_lines).strip()
                )
            )

        title = file_path.stem
        # Extract title from H1 if present
        if heading_stack and heading_stack[0][0] == 1:
            title = heading_stack[0][1]

        doc_id = hashlib.md5(str(file_path.resolve()).encode("utf-8")).hexdigest()

        doc = ParsedDocument(
            doc_id=doc_id,
            content=content_text.strip(),
            source_type=SourceType.CONFLUENCE,
            title=title,
            source_path=str(file_path.resolve()),
            metadata=metadata,
            sections=sections,
            tables=tables,
            acl_tags=acl_tags,
            is_scanned=False
        )

        return [doc]
