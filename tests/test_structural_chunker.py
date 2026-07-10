from src.chunking.structural_chunker import StructuralChunker
from src.parsers.base import DocumentSection, ParsedDocument, SourceType


def test_chunk_section_preserves_fenced_code_blocks():
    doc = ParsedDocument(
        doc_id="doc-1",
        content="Intro paragraph before the code block.\n\n```python\nprint('hello')\n```\n\nOutro paragraph after the code block.",
        source_type=SourceType.PDF,
        title="Sample",
        source_path="sample.md",
    )
    section = DocumentSection(
        heading="Example",
        heading_level=1,
        heading_path="Example",
        content="Intro paragraph before the code block.\n\n```python\nprint('hello')\n```\n\nOutro paragraph after the code block.",
    )

    chunker = StructuralChunker(max_tokens=8, overlap_tokens=0)
    chunks = chunker._chunk_section(section=section, doc=doc, start_index=0)

    assert len(chunks) >= 3
    assert any("print('hello')" in chunk.content for chunk in chunks)
    assert any("Intro paragraph" in chunk.content for chunk in chunks)
    assert any("Outro paragraph" in chunk.content for chunk in chunks)
