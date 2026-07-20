"""
Structural chunking module for NexusRAG.

Splits ParsedDocuments into retrieval-ready chunks while preserving
document structure such as headings, pages, tables, Slack threads,
and Excel row ranges.

The StructuralChunker performs the first stage of chunking before
semantic refinement.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.parsers.base import (
    ParsedDocument,
    DocumentSection,
    SourceType,
)

logger = logging.getLogger(__name__)


# ============================================================
# Chunk Model
# ============================================================

@dataclass
class Chunk:
    """
    Represents one retrieval chunk.

    Every downstream component (deduplication, embeddings,
    reranking, vector database, retrieval) operates on this
    object.
    """

    chunk_id: str

    doc_id: str

    content: str

    source_type: SourceType

    title: str

    heading: str

    heading_path: str

    page_number: Optional[int] = None

    row_range: Optional[str] = None

    acl_tags: List[str] = field(default_factory=list)

    source_path: str = ""

    is_table: bool = False

    is_duplicate: bool = False

    duplicate_of: Optional[str] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Structural Chunker
# ============================================================

class StructuralChunker:
    """
    Structure-aware chunker.

    Responsibilities
    ----------------

    • Preserve document hierarchy.

    • Preserve tables.

    • Preserve code blocks.

    • Preserve Slack conversations.

    • Preserve Excel row ranges.

    • Split oversized sections while keeping context.
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 50,
    ):
        """
        Initialize chunker.

        Args:
            max_tokens:
                Approximate maximum chunk size.

            overlap_tokens:
                Sliding overlap between chunks.
        """

        self.max_tokens = max_tokens

        self.overlap_tokens = overlap_tokens

        # Approximate conversion

        self.char_limit = max_tokens * 4

        self.overlap_chars = overlap_tokens * 4

        logger.info(
            "StructuralChunker initialized "
            "(max_tokens=%d overlap=%d)",
            max_tokens,
            overlap_tokens,
        )

    # ========================================================
    # Public API
    # ========================================================

    def chunk_document(
        self,
        doc: ParsedDocument,
    ) -> List[Chunk]:
        """
        Convert a ParsedDocument into retrieval chunks.

        Args:
            doc:
                Parsed enterprise document.

        Returns:
            List of Chunk objects.
        """

        logger.info(
            "Chunking document '%s'.",
            doc.title,
        )

        chunks: List[Chunk] = []

        chunk_index = 0

        # ------------------------------------
        # Structural sections
        # ------------------------------------

        if doc.sections:

            for section in doc.sections:

                section_chunks = self._chunk_section(
                    section=section,
                    doc=doc,
                    start_index=chunk_index,
                )

                chunks.extend(section_chunks)

                chunk_index += len(section_chunks)

        else:

            raw_chunks = self._chunk_text(
                text=doc.content,
                doc=doc,
                heading=doc.title,
                heading_path=doc.title,
                start_index=chunk_index,
            )

            chunks.extend(raw_chunks)

            chunk_index += len(raw_chunks)

        # ------------------------------------
        # Tables become independent chunks
        # ------------------------------------

        for table_index, table in enumerate(doc.tables):

            chunks.append(

                self._create_table_chunk(
                    table_md=table,
                    doc=doc,
                    table_index=table_index,
                )

            )

        logger.info(
            "Generated %d structural chunks for '%s'.",
            len(chunks),
            doc.title,
        )

        return chunks

    # ========================================================
    # Section Chunking
    # ========================================================

    def _chunk_section(
        self,
        section: DocumentSection,
        doc: ParsedDocument,
        start_index: int,
    ) -> List[Chunk]:
        """
        Chunk a single document section while preserving
        fenced code blocks.
        """

        content = section.content.strip()

        if not content:
            return []

        logger.debug(
            "Processing section '%s'.",
            section.heading,
        )

        code_blocks = list(re_find_code_blocks(content))

        if not code_blocks:
            return self._chunk_text(
                text=content,
                doc=doc,
                heading=section.heading,
                heading_path=section.heading_path,
                page_number=section.page_number,
                row_range=section.row_range,
                start_index=start_index,
            )

        chunks: List[Chunk] = []
        current_index = start_index
        previous_end = 0

        for start_pos, end_pos, block_text in code_blocks:
            pre_text = content[previous_end:start_pos].strip()

            if pre_text:
                pre_chunks = self._chunk_text(
                    text=pre_text,
                    doc=doc,
                    heading=section.heading,
                    heading_path=section.heading_path,
                    page_number=section.page_number,
                    row_range=section.row_range,
                    start_index=current_index,
                )
                chunks.extend(pre_chunks)
                current_index += len(pre_chunks)

            code_chunks = self._chunk_text(
                text=block_text,
                doc=doc,
                heading=section.heading,
                heading_path=section.heading_path,
                page_number=section.page_number,
                row_range=section.row_range,
                start_index=current_index,
            )
            chunks.extend(code_chunks)
            current_index += len(code_chunks)
            previous_end = end_pos

        remaining_text = content[previous_end:].strip()

        if remaining_text:
            remaining_chunks = self._chunk_text(
                text=remaining_text,
                doc=doc,
                heading=section.heading,
                heading_path=section.heading_path,
                page_number=section.page_number,
                row_range=section.row_range,
                start_index=current_index,
            )
            chunks.extend(remaining_chunks)

        return chunks

    # ========================================================
    # Text Chunking
    # ========================================================

    def _chunk_text(
        self,
        text: str,
        doc: ParsedDocument,
        heading: str,
        heading_path: str,
        page_number: Optional[int] = None,
        row_range: Optional[str] = None,
        start_index: int = 0,
    ) -> List[Chunk]:
        """
        Split text into overlapping chunks while
        preserving paragraph boundaries.
        """

        if not text.strip():
            return []

        paragraphs = text.split("\n\n")
        chunks: List[Chunk] = []
        buffer: List[str] = []
        current_length = 0
        chunk_index = start_index

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            paragraph_length = len(paragraph)

            if paragraph_length > self.char_limit:
                if buffer:
                    chunks.append(
                        self._build_chunk(
                            content="\n\n".join(buffer),
                            doc=doc,
                            heading=heading,
                            heading_path=heading_path,
                            page_number=page_number,
                            row_range=row_range,
                            index=chunk_index,
                        )
                    )
                    chunk_index += 1
                    buffer = []
                    current_length = 0

                sentences = re_split_sentences(paragraph)
                for sentence in sentences:
                    sentence = sentence.strip()

                    if not sentence:
                        continue

                    sentence_length = len(sentence)

                    if current_length + sentence_length > self.char_limit:
                        if buffer:
                            chunks.append(
                                self._build_chunk(
                                    content=" ".join(buffer),
                                    doc=doc,
                                    heading=heading,
                                    heading_path=heading_path,
                                    page_number=page_number,
                                    row_range=row_range,
                                    index=chunk_index,
                                )
                            )
                            chunk_index += 1

                            overlap = buffer[-1] if buffer else ""

                            if len(overlap) < self.overlap_chars:
                                buffer = [overlap, sentence] if overlap else [sentence]
                                current_length = len(overlap) + sentence_length
                            else:
                                buffer = [sentence]
                                current_length = sentence_length
                        else:
                            hard_chunks = [
                                sentence[i:i + self.char_limit]
                                for i in range(0, len(sentence), self.char_limit)
                            ]

                            for hard_chunk in hard_chunks:
                                chunks.append(
                                    self._build_chunk(
                                        content=hard_chunk,
                                        doc=doc,
                                        heading=heading,
                                        heading_path=heading_path,
                                        page_number=page_number,
                                        row_range=row_range,
                                        index=chunk_index,
                                    )
                                )
                                chunk_index += 1
                    else:
                        buffer.append(sentence)
                        current_length += sentence_length
            else:
                if current_length + paragraph_length > self.char_limit:
                    chunks.append(
                        self._build_chunk(
                            content="\n\n".join(buffer),
                            doc=doc,
                            heading=heading,
                            heading_path=heading_path,
                            page_number=page_number,
                            row_range=row_range,
                            index=chunk_index,
                        )
                    )
                    chunk_index += 1

                    overlap = buffer[-1] if buffer else ""

                    if len(overlap) < self.overlap_chars:
                        buffer = [overlap, paragraph] if overlap else [paragraph]
                        current_length = len(overlap) + paragraph_length
                    else:
                        buffer = [paragraph]
                        current_length = paragraph_length
                else:
                    buffer.append(paragraph)
                    current_length += paragraph_length

        if buffer:
            chunks.append(
                self._build_chunk(
                    content="\n\n".join(buffer),
                    doc=doc,
                    heading=heading,
                    heading_path=heading_path,
                    page_number=page_number,
                    row_range=row_range,
                    index=chunk_index,
                )
            )

        return chunks

    # ========================================================
    # Table Chunk
    # ========================================================

    def _create_table_chunk(
        self,
        table_md: str,
        doc: ParsedDocument,
        table_index: int,
    ) -> Chunk:
        """
        Create a dedicated chunk for a Markdown table.
        """

        heading = f"Table {table_index + 1}"
        
        # Inject metadata context directly into the text content for better retrieval matching!
        prefix = f"[{doc.title} > {heading}]\n"
        contextualized_table_md = prefix + table_md

        metadata = {
            **doc.metadata,
            "table_index": table_index,
            "source_file": doc.metadata.get("source_file"),
            "parser": doc.metadata.get("parser"),
            "character_count": len(contextualized_table_md),
            "is_table": True,
        }

        chunk_hash = hashlib.sha256(
            (doc.doc_id + heading + contextualized_table_md).encode("utf-8")
        ).hexdigest()

        return Chunk(
            chunk_id=chunk_hash,
            doc_id=doc.doc_id,
            content=contextualized_table_md,
            source_type=doc.source_type,
            title=doc.title,
            heading=heading,
            heading_path=heading,
            page_number=None,
            row_range=None,
            acl_tags=doc.acl_tags,
            source_path=doc.source_path,
            is_table=True,
            metadata=metadata,
        )

    # ========================================================
    # Chunk Builder
    # ========================================================

    def _build_chunk(
        self,
        content: str,
        doc: ParsedDocument,
        heading: str,
        heading_path: str,
        page_number: Optional[int],
        row_range: Optional[str],
        index: int,
    ) -> Chunk:
        """
        Construct a Chunk object.
        """

        content = content.strip()
        
        # Inject metadata context directly into the text content for better retrieval matching!
        prefix = f"[{doc.title} > {heading_path}]\n"
        contextualized_content = prefix + content

        chunk_hash = hashlib.sha256(
            (doc.doc_id + heading_path + contextualized_content).encode("utf-8")
        ).hexdigest()

        metadata = {
            **doc.metadata,
            "heading": heading,
            "heading_path": heading_path,
            "page_number": page_number,
            "row_range": row_range,
            "source_file": doc.metadata.get("source_file"),
            "parser": doc.metadata.get("parser"),
            "character_count": len(contextualized_content),
            "chunk_index": index,
        }

        return Chunk(
            chunk_id=chunk_hash,
            doc_id=doc.doc_id,
            content=contextualized_content,
            source_type=doc.source_type,
            title=doc.title,
            heading=heading,
            heading_path=heading_path,
            page_number=page_number,
            row_range=row_range,
            acl_tags=doc.acl_tags,
            source_path=doc.source_path,
            is_table=False,
            metadata=metadata,
        )


# ============================================================
# Helper Functions
# ============================================================

import re


_CODE_BLOCK_PATTERN = re.compile(
    r"```.*?```",
    re.DOTALL,
)


_SENTENCE_PATTERN = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])"
)


def re_find_code_blocks(text: str):
    """
    Locate fenced Markdown code blocks.

    Returns:
        Iterable of tuples:
        (start_position, end_position, block_text)
    """

    for match in _CODE_BLOCK_PATTERN.finditer(text):
        yield (
            match.start(),
            match.end(),
            match.group(),
        )


def re_split_sentences(text: str) -> List[str]:
    """
    Split text into sentences.

    Falls back to the whole text if splitting fails.
    """

    sentences = _SENTENCE_PATTERN.split(text)

    cleaned = [
        s.strip()
        for s in sentences
        if s.strip()
    ]

    return cleaned if cleaned else [text]
    