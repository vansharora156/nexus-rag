"""Citation formatting module for NexusRAG.

Transforms raw retrieved chunks into numbered citation blocks with
source-type icons and a formatted context string ready for insertion
into the Gemini generation prompt.

Source-type icons
-----------------
📄  PDF
📝  Markdown / Confluence pages
📊  Excel / CSV tables
💬  Slack threads

Citation format (in-prompt)
---------------------------
[1] 📄 Q4 Financial Report (page 3)
    "...text snippet up to 300 chars..."

[2] 💬 #engineering-channel — Thread: "Deploy process"
    "...text snippet..."
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Source-type → emoji icon mapping
_SOURCE_ICONS: Dict[str, str] = {
    "pdf":      "📄",
    "markdown": "📝",
    "excel":    "📊",
    "csv":      "📊",
    "slack":    "💬",
}

_DEFAULT_ICON = "📎"

# Maximum characters of content to include per citation in the prompt
_SNIPPET_CHARS = 300


@dataclass
class Citation:
    """Structured representation of a single source citation."""
    index: int
    source_type: str
    icon: str
    title: str
    heading_path: Optional[str]
    page_number: Optional[int]
    row_range: Optional[str]
    chunk_id: str
    doc_id: str
    acls: List[str]
    score: float
    rerank_score: Optional[float]
    content_snippet: str
    is_table: bool = False

    def label(self) -> str:
        """Short human-readable source label for in-text citation tags."""
        parts = [f"[{self.index}]", self.icon, self.title]
        if self.page_number:
            parts.append(f"(page {self.page_number})")
        elif self.heading_path:
            parts.append(f"— {self.heading_path}")
        elif self.row_range:
            parts.append(f"(rows {self.row_range})")
        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "source_type": self.source_type,
            "icon": self.icon,
            "title": self.title,
            "heading_path": self.heading_path,
            "page_number": self.page_number,
            "row_range": self.row_range,
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "acls": self.acls,
            "score": self.score,
            "rerank_score": self.rerank_score,
            "content_snippet": self.content_snippet,
            "is_table": self.is_table,
            "label": self.label(),
        }


class CitationFormatter:
    """Converts retrieved chunk dicts into structured :class:`Citation` objects
    and assembles the numbered context block for the LLM prompt.
    """

    @staticmethod
    def _get_icon(source_type: str) -> str:
        return _SOURCE_ICONS.get((source_type or "").lower(), _DEFAULT_ICON)

    @staticmethod
    def _snippet(content: str, max_chars: int = _SNIPPET_CHARS) -> str:
        content = (content or "").strip()
        if len(content) <= max_chars:
            return content
        return content[:max_chars].rsplit(" ", 1)[0] + "…"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def format(self, chunks: List[Dict[str, Any]]) -> List[Citation]:
        """Build a :class:`Citation` list from retrieved chunk dicts.

        Args:
            chunks: List of chunk dicts as returned by :class:`HybridRetriever`.

        Returns:
            Ordered list of :class:`Citation` objects (1-indexed).
        """
        citations: List[Citation] = []
        for idx, chunk in enumerate(chunks, start=1):
            source_type = (chunk.get("source_type") or "").lower()
            citations.append(
                Citation(
                    index=idx,
                    source_type=source_type,
                    icon=self._get_icon(source_type),
                    title=chunk.get("title") or "Untitled",
                    heading_path=chunk.get("heading_path"),
                    page_number=chunk.get("page_number"),
                    row_range=chunk.get("row_range"),
                    chunk_id=chunk.get("chunk_id", ""),
                    doc_id=chunk.get("doc_id", ""),
                    acls=chunk.get("acls", []),
                    score=float(chunk.get("score") or chunk.get("rrf_score") or 0.0),
                    rerank_score=chunk.get("rerank_score"),
                    content_snippet=self._snippet(chunk.get("content", "")),
                    is_table=bool(chunk.get("is_table", False)),
                )
            )
        return citations

    def build_context_block(self, citations: List[Citation]) -> str:
        """Assemble the numbered context block to inject into the LLM prompt.

        Each citation is rendered as:

            [N] <icon> <title> (location hint)
            "<snippet>"

        Args:
            citations: Output from :meth:`format`.

        Returns:
            Multi-line string ready to be inserted before the question in
            the Gemini generation prompt.
        """
        lines: List[str] = []
        for c in citations:
            lines.append(c.label())
            lines.append(f'"{c.content_snippet}"')
            lines.append("")
        return "\n".join(lines).strip()
