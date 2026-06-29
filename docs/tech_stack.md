# Tech Stack Selection & Justification

This document details the software, frameworks, and model selections for NexusRAG, comparing them against industry alternatives to justify the architectural choices.

---

## Tech Stack Overview

| Component | Selected Technology | Main Alternatives Considered | Primary Decision Driver |
| :--- | :--- | :--- | :--- |
| **LLM Core** | **Gemini 2.5 Flash** | OpenAI GPT-4o-mini, Local Llama-3-8B | Large context window (1M tokens), cost efficiency, native multimodal abilities. |
| **Vector DB** | **Qdrant** | ChromaDB, pgvector, Pinecone | Native payload filtering, extreme speed (Rust backend), robust local & cloud deployment. |
| **OCR Tool** | **PaddleOCR** | Tesseract, EasyOCR | Superior multi-column document layout parsing and table structure recognition. |
| **Embeddings**| **BGE-M3** | all-MiniLM-L6-v2, text-embedding-3-small | Multi-function retrieval (dense, sparse, multi-vector), multi-lingual, 8192 context limit. |
| **Reranker** | **BGE-Reranker-Large** | ms-marco-MiniLM, Cohere Rerank | Outstanding benchmark results on BEIR/MTEB, local execution without API dependence. |
| **Backend API**| **FastAPI** | Flask, Django | High performance, native async support, automatic OpenAPI/Swagger generation. |
| **Frontend UI**| **Vite + Vanilla JS** | Next.js, Streamlit | Zero-overhead fast loads, simple single-page deployment without complex build systems. |

---

## Detailed Selection Analysis

### 1. Large Language Model: Gemini 2.5 Flash
*   **Selected:** Gemini 2.5 Flash
*   **Alternatives:** OpenAI GPT-4o-mini, Meta Llama-3-8B (Local)
*   **Justification:**
    *   *Context Capacity:* Gemini 2.5 Flash supports up to 1,000,000 tokens in the context window. This makes it ideal for handling large retrieval contexts (e.g., combining 10 long search blocks with tabular structures).
    *   *API Cost-Efficiency:* Flash is extremely fast and inexpensive, matching or beating GPT-4o-mini on pricing while providing native support for complex tasks like structure parsing.
    *   *Contrast with Local Llama-3:* Running Llama-3 locally requires dedicated GPU servers, adding substantial deployment complexity and infrastructure costs for BigCorp. Flash is accessible via standard REST calls with minimal latency.

---

### 2. Vector Store: Qdrant
*   **Selected:** Qdrant (Rust-based)
*   **Alternatives:** ChromaDB, pgvector (PostgreSQL), Pinecone
*   **Justification:**
    *   *Dynamic Metadata Filtering:* Qdrant is optimized for matching dynamic JSON payloads during vector search. This is critical for our ACL verification step, allowing us to enforce security limits at the index level: `Filter(group IN user_groups)`.
    *   *Performance:* Written in Rust, Qdrant is faster and consumes less RAM than Python-based ChromaDB.
    *   *Contrast with pgvector:* While pgvector is excellent if a relational database is already in place, setting up vector indexes (HNSW) in pgvector is harder to configure and optimize than in Qdrant's containerized setup.
    *   *Contrast with Pinecone:* Pinecone is a cloud-only service. BigCorp's security standards mandate that data must be capable of running entirely inside a local/on-premise environment.

---

### 3. Document OCR: PaddleOCR
*   **Selected:** PaddleOCR
*   **Alternatives:** Tesseract, EasyOCR
*   **Justification:**
    *   *Layout-Aware OCR:* Standard OCR tools output unstructured lines of text. PaddleOCR excels at identifying paragraphs, blocks, and tables, ensuring multi-column text does not get merged side-by-side.
    *   *Accuracy on Tables:* PaddleOCR provides specific models for structural table recognition (reconstructing table cells and borders), which is essential for our financial spreadsheet requirements.
    *   *Contrast with Tesseract:* Tesseract struggles with low-contrast scanned text and complex page layouts, leading to degraded extraction quality.

---

### 4. Dense Embeddings: BGE-M3 (BAAI)
*   **Selected:** BGE-M3
*   **Alternatives:** text-embedding-3-small (OpenAI), all-MiniLM-L6-v2 (HuggingFace)
*   **Justification:**
    *   *Long Context Limits:* Standard embeddings (like all-MiniLM-L6-v2) truncate text at 256 or 512 tokens. BGE-M3 supports input lengths up to 8,192 tokens.
    *   *Multi-lingual & Multi-functional:* BGE-M3 can simultaneously generate dense embeddings, lexical weights (sparse vectors), and multi-vector representations.
    *   *On-Premise:* Unlike OpenAI's `text-embedding-3-small`, BGE-M3 can be run locally via `sentence-transformers`, guaranteeing zero data egress during the indexing process.

---

### 5. Reranker: BGE-Reranker-Large
*   **Selected:** BGE-Reranker-Large
*   **Alternatives:** ms-marco-MiniLM-L-6-v2, Cohere Rerank API
*   **Justification:**
    *   *High Precision:* Rerankers assess search fragments and query compatibility in a joint attention mechanism, resulting in far better selection accuracy than cosine similarity alone.
    *   *Cost Savings:* By running a local cross-encoder model, we avoid paying external API fees (like Cohere's) for every query.
    *   *Contrast with ms-marco-MiniLM:* BGE-Reranker-Large is trained on larger datasets and offers superior classification on complex, domain-specific text patterns.

---

### 6. Backend Framework: FastAPI
*   **Selected:** FastAPI (Python)
*   **Alternatives:** Flask, Django
*   **Justification:**
    *   *Async Support:* RAG tasks involve extensive asynchronous I/O (fetching vectors from Qdrant, querying the Gemini API, writing metadata to SQLite). FastAPI natively handles async routes, reducing request blocks.
    *   *Type Safety:* Uses Pydantic for validation, integrating with our dataclass schemas and enforcing runtime contract verification.
    *   *Interactive Docs:* Out-of-the-box Swagger UI (`/docs`) reduces developer friction when building API clients.

---

### 7. Frontend UI: Vite + Vanilla JS
*   **Selected:** Vite + Vanilla JS (Single Page Application)
*   **Alternatives:** Next.js (React), Streamlit
*   **Justification:**
    *   *Zero Build Overhead:* Next.js is overly complex for a single-page search bar. Streamlit is easy but hard to customize visually, and it is notoriously slow under heavy traffic.
    *   *Vite Performance:* Vite bundles simple, raw assets instantly. The UI contains a search form, dynamic results renderer, and permission toggle buttons—easily maintained in a single clean HTML/JS file.
