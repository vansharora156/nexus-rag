# NexusRAG Project Roadmap

This document outlines the week-by-week development plan for implementing, testing, and deploying the NexusRAG enterprise search system.

---

## Roadmap Overview

```
Week 1: [Foundations & Ingestion] =======> (Milestone: Raw parser pipeline verified)
Week 2: [Chunking, Dedup, Indexing] =====> (Milestone: Vector & Lexical indices populated)
Week 3: [Retrieval, ACL, Generation] ====> (Milestone: RRF & Reranked output functional)
Week 4: [API, UI, Evaluation] ==========> (Milestone: Production API, UI & 100% test pass)
```

---

## Detailed Weekly Schedule

### Week 1: Foundations & Ingestion Parsers
*   **Objectives:** Establish the core project repository structure, database models, and write raw document extraction modules.
*   **Tasks:**
    *   Initialize python packages with appropriate `__init__.py` files and typing structures.
    *   Create the SQLite database schema for document metadata, hash histories, and ACL mappings.
    *   Build the **Confluence (Markdown)** parser, stripping headers and extracting frontmatter.
    *   Build the **PDF parser**:
        *   Integrate `pdfplumber` for digital PDFs.
        *   Set up `PaddleOCR` layout analysis for scanned PDFs.
        *   Implement local file caching to skip unchanged files based on MD5 checksums.
    *   Build the **Slack JSON thread builder**, grouping parent and reply structures chronologically.
    *   Build the **Excel & CSV table converter**, outputting tables in markdown syntax.
*   **Deliverable:** An ingestion CLI tool that parses any of the four files and logs output to text files.

---

### Week 2: Chunking, Deduplication, & Indexing
*   **Objectives:** Segment parsed data semantically, implement near-duplicate detection, and feed the vector and keyword databases.
*   **Tasks:**
    *   Write a **Structural Chunker** that respects markdown headers, tables, and Slack thread boundaries.
    *   Implement **MinHash LSH Deduplication**:
        *   Compute shingles/n-grams from parsed text.
        *   Generate 128-integer MinHash signatures.
        *   Construct an LSH index to link duplicates (Jaccard similarity > 85%).
    *   Deploy **Qdrant** locally via Docker and establish the vector collection configuration.
    *   Integrate `sentence-transformers` with the **BGE-M3** model to generate 1024-dimensional dense vectors.
    *   Configure the **BM25s** sparse search engine, indexing tokenized text structures.
*   **Deliverable:** Indexing pipeline that processes files, filters duplicates, records entries in SQLite, and writes data to Qdrant/BM25s.

---

### Week 3: Retrieval, ACL Gating, & LLM Synthesis
*   **Objectives:** Construct search orchestration, implement dynamic permission gating, and connect the LLM generation layer.
*   **Tasks:**
    *   Build the **Hybrid Search Router**, querying BM25s and Qdrant in parallel.
    *   Implement **Dynamic ACL Gating**:
        *   Inject user roles (e.g., `Engineering`, `Finance`) directly as filter payloads in Qdrant.
        *   Filter SQLite and BM25s queries using user authorization groups.
    *   Write the **Reciprocal Rank Fusion (RRF)** combiner to merge lexical and vector search lists.
    *   Integrate the **BGE-Reranker-Large** model for cross-encoder re-scoring of fused search results.
    *   Write the Gemini 2.5 Flash API connector.
    *   Construct LLM generation templates, enforcing strict context grounding and inline citations.
*   **Deliverable:** Retrieval and query runner script that takes a user query and user role, prints the fused/reranked documents, and generates the final cited answer.

---

### Week 4: API development, Frontend UI, & Evaluation
*   **Objectives:** Wrap backend services in an API, create a web user interface, and evaluate performance against the golden test suite.
*   **Tasks:**
    *   Develop a **FastAPI backend** exposing the following endpoints:
        *   `POST /query` (takes query string and user authorization roles, returns answers and source citations).
        *   `POST /ingest` (triggers folder scans and runs ingestion pipeline).
        *   `GET /health` (monitors container connections and database sizes).
    *   Build a responsive **web frontend** (Vite + Vanilla JS) offering a search bar, user role simulation selectors, query timing logs, and structured citation views.
    *   Write the automated **Evaluation Engine**:
        *   Load the 100-question Golden Dataset.
        *   Run queries through the API and measure correctness, recall, and permission boundaries.
        *   Format final testing metrics into reports.
*   **Deliverable:** A complete, locally-runnable search application with full test coverage and performance metrics.
