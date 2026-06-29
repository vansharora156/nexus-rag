# NexusRAG Technical Architecture

This document describes the technical specifications, schemas, storage layers, and mathematical formulations powering the NexusRAG enterprise search engine.

---

## 1. Ingestion Flow & Data Representations

During the ingestion process, files are mapped to structured Python dataclasses before being split, deduplicated, and indexed.

### 1.1 Dataclass Schemas (Python 3.10+)

```python
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class ParsedDocument:
    """Represents a document parsed from a raw file (PDF, Slack export, Excel, Confluence)."""
    doc_id: str
    title: str
    content: str  # Contains the full text, with tables rendered as markdown
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Metadata includes:
    # - file_path (str)
    # - source_type (str: 'confluence' | 'pdf' | 'slack' | 'spreadsheet')
    # - file_hash (str: MD5 hash of raw bytes)
    # - created_at (str: ISO timestamp)
    # - acls (List[str]: Access control lists, e.g., ["Engineering", "HR"])
    tables: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Chunk:
    """Represents a discrete semantic chunk of a ParsedDocument indexed in our databases."""
    chunk_id: str  # MD5/SHA256 of content + doc_id + chunk_index
    doc_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Inherits acls, source_type, file_path from ParsedDocument.
    # Adds section_header (str) and page_number (Optional[int]) if applicable.
    vector: Optional[List[float]] = None  # Populated only during embedding phase
```

---

## 2. Storage Layer Schemas

NexusRAG employs three distinct datastores to handle unstructured text, metadata, fast lexical search, and vector search.

```
                  +-----------------------------------+
                  |           Raw Documents           |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |          Metadata / ACLs          |
                  |             (SQLite)              |
                  +-----------------------------------+
                     /                             \
                    v                               v
       +-------------------------+     +-------------------------+
       |      Dense Index        |     |      Sparse Index       |
       |        (Qdrant)         |     |        (BM25s)          |
       +-------------------------+     +-------------------------+
```

### 2.1 SQLite Schema (Document Metadata & ACLs)
SQLite stores global state, version history, MinHash signatures, and document-level ACLs.

#### Table: `documents`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `doc_id` | TEXT | PRIMARY KEY | Unique ID (usually hash of source identifier) |
| `title` | TEXT | NOT NULL | Document title / filename |
| `file_path` | TEXT | NOT NULL | Path on disk / source URI |
| `file_hash` | TEXT | NOT NULL | MD5 signature of the binary contents |
| `source_type`| TEXT | NOT NULL | `confluence`, `pdf`, `slack`, or `spreadsheet` |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Ingestion timestamp |
| `acls` | TEXT | NOT NULL | JSON string representation of allowed roles (e.g. `["HR","Exec"]`) |
| `minhash_sig`| TEXT | NOT NULL | JSON array of 128 integer hashes representing the MinHash signature |
| `primary_doc_id`| TEXT | REFERENCES `documents(doc_id)` | Self-references if primary, points to master doc if near-duplicate |

#### Table: `chunks`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `chunk_id` | TEXT | PRIMARY KEY | Hash of content + index |
| `doc_id` | TEXT | REFERENCES `documents(doc_id)` | Source document reference |
| `chunk_index`| INTEGER| NOT NULL | Chunk order within document |
| `content` | TEXT | NOT NULL | Plain text/markdown slice |

---

### 2.2 Vector DB Schema (Qdrant)
The dense vector search engine (Qdrant) stores the `BGE-M3` vector representations along with payload filters to verify document-level permissions.

*   **Collection Name:** `nexusrag_chunks`
*   **Vector Configuration:**
    *   **Dimension:** 1024 (BGE-M3 base size)
    *   **Distance Metric:** Cosine similarity (`Distance.COSINE`)
*   **Payload Layout:**
    ```json
    {
      "chunk_id": "string (UUID or hash)",
      "doc_id": "string",
      "content": "string (actual chunk text)",
      "source_type": "string ('pdf' | 'slack' | 'spreadsheet' | 'confluence')",
      "acls": ["string"], // Array of security groups, e.g. ["HR", "Exec"]
      "title": "string",
      "section_header": "string"
    }
    ```
*   **Indexing Fields:**
    *   Payload index on `acls` (keyword index for instantaneous dynamic permission filtering).
    *   Payload index on `source_type` (keyword index for filtering by repository).

---

### 2.3 BM25s Indexing Model
We use `bm25s` for lexical retrieval.
*   **Tokenization Pipeline:**
    *   Lowercases all text.
    *   Splits text using a regular expression: `\b\w+\b`.
    *   Filters out standard NLTK/Scikit-learn English stopwords.
    *   *No stemming* is applied by default to ensure precise keyword matches for code variables and technical terms.
*   **BM25 Hyperparameters:**
    *   $k_1 = 1.5$ (controls term frequency scaling).
    *   $b = 0.75$ (controls document length normalization).

---

## 3. Retrieval Pipeline & Fusion Math

When a query is processed, dense and sparse retrieval engines calculate candidate matches. These lists are combined and reordered.

```
       Query -> [ Dense Search ]  ===> Ranks: [R_dense]
             -> [ Sparse Search ] ===> Ranks: [R_sparse]
                          \                 /
                           v               v
                     [ Reciprocal Rank Fusion (RRF) ]
                                   |
                                   v
                      [ BGE-Reranker-Large ]
                                   |
                                   v
                             [ Final Context ]
```

### 3.1 Reciprocal Rank Fusion (RRF)
RRF combines ranked results from multiple search systems. Rather than using raw scores (which have different distributions), it uses document ranks.

Given a document $d$, its RRF score is:

$$RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
*   $M$ represents the set of retrieval methods (in our case, $M = \{\text{dense}, \text{sparse}\}$).
*   $r_m(d)$ is the 1-based rank of document $d$ in the output of retrieval method $m$. If document $d$ is not found in the top retrieved results for a method, $r_m(d) \to \infty$ (effectively contributing 0).
*   $k$ is a constant hyperparameter (default value: $60$), which dampens the impact of high-ranking documents to prevent single-system outliers from dominating.

---

### 3.2 BGE Cross-Encoder Reranking
Following RRF, the top $N$ (default: 20) candidate chunks are submitted to the **BGE-Reranker-Large** model alongside the original query.
*   The model calculates a cross-entropy loss score representing the direct similarity:
    $$Score = \sigma(\text{CrossEncoder}(Query, Chunk\_Content))$$
*   Only the top $K$ (default: 5) chunks with $Score \ge 0.35$ are output to the LLM context.

---

## 4. LLM Generation & Query Expansion Templates

### 4.1 Query Expansion & HyDE Prompt
This template is used with Gemini 2.5 Flash to generate hypothetical document chunks (HyDE) to improve retrieval of documents with low lexical overlap.

```
You are an expert search assistant for BigCorp's internal knowledge base. 
The user is asking a question. Your goal is to write a single hypothetical paragraph or wiki entry that would perfectly answer the user's question. Do not include introductory text, meta-commentary, or formatting other than plain text and basic markdown.

Query: {query}

Hypothetical Answer Segment:
```

### 4.2 LLM Generation Prompt (with Citation Constraints)
This prompt enforces strict, cited answers from Gemini 2.5 Flash.

```
You are NexusRAG, the secure enterprise assistant for BigCorp.
Answer the user's query based ONLY on the provided context fragments. 

CRITICAL INSTRUCTIONS:
1. Ground your answer completely in the context. If the context does not contain the answer, state "I cannot find the answer in the provided documents." Do not assume or extrapolate.
2. Every factual claim must be backed by an inline citation to its source chunk.
3. Citations MUST follow this format: [Doc: <Title>, Chunk: <Index>].
4. Put the citation at the end of the sentence or clause it supports.

---
CONTEXT FRAGMENTS:
{context}
---

USER QUERY: {query}

ANSWER:
```
