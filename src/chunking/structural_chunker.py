"""Structural chunking module for NexusRAG.

Splits documents based on structural boundaries (headings, pages, threads, tables)
to preserve layout context.
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from src.parsers.base import ParsedDocument, DocumentSection, SourceType

@dataclass
class Chunk:
    """A chunk of text ready for embedding and indexing."""
    chunk_id: str              # Unique chunk identifier
    doc_id: str                # Parent document ID
    content: str               # Chunk text content
    source_type: SourceType    # Source type (e.g. PDF, Slack, Excel, Confluence)
    title: str                 # Document title
    heading_path: str          # Section heading hierarchy path
    page_number: Optional[int] = None  # For PDFs
    row_range: Optional[str] = None    # For Excel
    acl_tags: List[str] = field(default_factory=list)
    source_path: str = ""      # Original file path
    is_table: bool = False     # Whether this chunk is a table
    is_duplicate: bool = False # Whether marked as near-duplicate
    duplicate_of: Optional[str] = None  # chunk_id of canonical version
    metadata: Dict[str, Any] = field(default_factory=dict)


class StructuralChunker:
    """Heading-aware, table-aware, thread-aware chunker.

    Maintains the integrity of tabular data and code blocks, grouping Slack threads
    as single units and appending contextual metadata to each chunk.
    """

    def __init__(self, max_tokens: int = 512, overlap_tokens: int = 50):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        # Character-to-token ratio approximation (approx 4 chars per token)
        self.char_limit = max_tokens * 4
        self.overlap_chars = overlap_tokens * 4

    def chunk_document(self, doc: ParsedDocument) -> List[Chunk]:
        """Chunk a parsed document using structural boundaries.

        Args:
            doc: The parsed document representation.

        Returns:
            A list of Chunk objects.
        """
        chunks = []
        chunk_idx = 0

        # 1. Handle sections if present
        if doc.sections:
            for section in doc.sections:
                sec_chunks = self._chunk_section(section, doc, chunk_idx)
                chunks.extend(sec_chunks)
                chunk_idx += len(sec_chunks)
        else:
            # Fallback: chunk raw content
            raw_chunks = self._chunk_text(
                text=doc.content, 
                doc=doc, 
                heading_path=doc.title, 
                start_index=chunk_idx
            )
            chunks.extend(raw_chunks)
            chunk_idx += len(raw_chunks)

        # 2. Add table chunks (tables are kept as separate atomic chunks)
        for i, table_md in enumerate(doc.tables):
            table_chunk = self._create_table_chunk(table_md, doc, i, chunk_idx)
            chunks.append(table_chunk)
            chunk_idx += 1

        return chunks

    def _chunk_section(self, section: DocumentSection, doc: ParsedDocument, start_index: int) -> List[Chunk]:
        """Chunk a single structural section, preserving code blocks."""
        content = section.content.strip()
        if not content:
            return []

        # Find fenced code blocks and isolate them from normal text chunking
        code_blocks = list(re_find_code_blocks(content))
        
        if not code_blocks:
            return self._chunk_text(
                text=content,
                doc=doc,
                heading_path=section.heading_path,
                page_number=section.page_number,
                row_range=section.row_range,
                start_index=start_index
            )

        # Re-assemble section splitting at code block indices
        chunks = []
        curr_idx = start_index
        last_pos = 0

        for start_pos, end_pos, block_text in code_blocks:
            # Chunk the normal text before the code block
            pre_text = content[last_pos:start_pos].strip()
            if pre_text:
                pre_chunks = self._chunk_text(
                    text=pre_text,
                    doc=doc,
                    heading_path=section.heading_path,
                    page_number=section.page_number,
                    row_range=section.row_range,
                    start_index=curr_idx
                )
                chunks.extend(pre_chunks)
                curr_idx += len(pre_chunks)

            # Code block becomes a single atomic chunk if it fits, otherwise splits
            block_chunks = self._chunk_text(
                text=block_text,
                doc=doc,
                heading_path=section.heading_path,
                page_number=section.page_number,
                row_range=section.row_range,
                start_index=curr_idx
            )
            chunks.extend(block_chunks)
            curr_idx += len(block_chunks)
            
            last_pos = end_pos

        # Chunk remaining text after code blocks
        post_text = content[last_pos:].strip()
        if post_text:
            post_chunks = self._chunk_text(
                text=post_text,
                doc=doc,
                heading_path=section.heading_path,
                page_number=section.page_number,
                row_range=section.row_range,
                start_index=curr_idx
            )
            chunks.extend(post_chunks)

        return chunks

    def _chunk_text(
        self, 
        text: str, 
        doc: ParsedDocument, 
        heading_path: str, 
        page_number: Optional[int] = None, 
        row_range: Optional[str] = None,
        start_index: int = 0
    ) -> List[Chunk]:
        """Split text into overlapping chunks at paragraph boundaries."""
        if not text.strip():
            return []

        # Split on double newlines (paragraphs)
        paragraphs = text.split("\n\n")
        chunks: List[Chunk] = []
        current_buffer = []
        current_len = 0
        chunk_seq = start_index

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)
            # If paragraph itself exceeds length, split it by line or sentence
            if para_len > self.char_limit:
                # Flush current buffer first
                if current_buffer:
                    chunks.append(
                        self._build_chunk(
                            content="\n\n".join(current_buffer),
                            doc=doc,
                            heading_path=heading_path,
                            page_number=page_number,
                            row_range=row_range,
                            index=chunk_seq
                        )
                    )
                    chunk_seq += 1
                    current_buffer = []
                    current_len = 0

                # Force split the large paragraph
                sentences = re_split_sentences(para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    sentence_len = len(sentence)
                    if current_len + sentence_len > self.char_limit:
                        # Flush sentence buffer
                        if current_buffer:
                            chunks.append(
                                self._build_chunk(
                                    content=" ".join(current_buffer),
                                    doc=doc,
                                    heading_path=heading_path,
                                    page_number=page_number,
                                    row_range=row_range,
                                    index=chunk_seq
                                )
                            )
                            chunk_seq += 1
                            
                            # Keep sliding window overlap
                            overlap_text = current_buffer[-1] if current_buffer else ""
                            if len(overlap_text) < self.overlap_chars:
                                current_buffer = [overlap_text, sentence] if overlap_text else [sentence]
                                current_len = len(overlap_text) + sentence_len
                            else:
                                current_buffer = [sentence]
                                current_len = sentence_len
                        else:
                            # Sentence is massive, must hard split it
                            hard_chunks = [sentence[i:i + self.char_limit] for i in range(0, len(sentence), self.char_limit)]
                            for hc in hard_chunks:
                                chunks.append(
                                    self._build_chunk(
                                        content=hc,
                                        doc=doc,
                                        heading_path=heading_path,
                                        page_number=page_number,
                                        row_range=row_range,
                                        index=chunk_seq
                                    )
                                )
                                chunk_seq += 1
                    else:
                        current_buffer.append(sentence)
                        current_len += sentence_len
            else:
                # Normal paragraph flow
                if current_len + para_len > self.char_limit:
                    chunks.append(
                        self._build_chunk(
                            content="\n\n".join(current_buffer),
                            doc=doc,
                            heading_path=heading_path,
                            page_number=page_number,
                            row_range=row_range,
                            index=chunk_seq
                        )
                    )
                    chunk_seq += 1

                    # Keep last paragraph for overlap sliding window
                    overlap_para = current_buffer[-1] if current_buffer else ""
                    if len(overlap_para) < self.overlap_chars:
                        current_buffer = [overlap_para, para] if overlap_para else [para]
                        current_len = len(overlap_para) + para_len
                    else:
                        current_buffer = [para]
                        current_len = para_len
                else:
                    current_buffer.append(para)
                    current_len += para_len

        # Flush remaining buffer
        if current_buffer:
            chunks.append(
                self._build_chunk(
                    content="\n\n".join(current_buffer),
                    doc=doc,
                    heading_path=heading_path,
                    page_number=page_number,
                    row_range=row_range,
                    index=chunk_seq
                )
            )

        return chunks

    def _create_table_chunk(self, table_md: str, doc: ParsedDocument, table_idx: int, seq_idx: int) -> Chunk:
        """Create a dedicated Chunk object for a table, marking it as is_table."""
        chunk_id = f"{doc.doc_id}_table_{table_idx:04d}"
        
        # Prepend context to help the LLM match the table values
        context_content = f"Table {table_idx + 1} from '{doc.title}':\n\n{table_md}"

        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc.doc_id,
            content=context_content,
            source_type=doc.source_type,
            title=doc.title,
            heading_path=f"{doc.title} > Table {table_idx + 1}",
            page_number=None,
            row_range=None,
            acl_tags=doc.acl_tags,
            source_path=doc.source_path,
            is_table=True,
            metadata={"table_index": table_idx}
        )

    def _build_chunk(
        self, 
        content: str, 
        doc: ParsedDocument, 
        heading_path: str, 
        page_number: Optional[int], 
        row_range: Optional[str],
        index: int
    ) -> Chunk:
        """Helper to create a standard Chunk object."""
        chunk_id = f"{doc.doc_id}_chunk_{index:04d}"
        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc.doc_id,
            content=content,
            source_type=doc.source_type,
            title=doc.title,
            heading_path=heading_path,
            page_number=page_number,
            row_range=row_range,
            acl_tags=doc.acl_tags,
            source_path=doc.source_path,
            is_table=False,
            metadata={}
        )


def re_find_code_blocks(text: str) -> List[tuple]:
    """Find start and end indices of fenced code blocks (```...```)."""
    import re
    blocks = []
    pattern = r"```[\s\S]*?```"
    for match in re.finditer(pattern, text):
        blocks.append((match.start(), match.end(), match.group(0)))
    return blocks


def re_split_sentences(text: str) -> List[str]:
    """Helper to split a paragraph into approximate sentences."""
    import re
    # Split on period, question, exclamation marks followed by whitespace and capitalized word
    sentence_end = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
    return sentence_end.split(text)
