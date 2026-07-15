"""NexusRAG generation layer.

Exports the primary generation components for use by the query pipeline.
"""

from src.generation.generator import GeminiGenerator
from src.generation.citation_formatter import CitationFormatter, Citation

__all__ = [
    "GeminiGenerator",
    "CitationFormatter",
    "Citation",
]
