# AskTheCompany RAG System — Comprehensive Evaluation Report

**Benchmark Execution Date:** 2026-07-21 01:34:30  
**Evaluated Questions:** 100 Questions (Golden Dataset v1.0)  
**Model Configuration:** Embeddings: `BAAI/bge-small-en-v1.5` | Vector DB: `Qdrant Local` | Lexical: `BM25S` | LLM Backend: `Groq (Llama-3.3-70b-versatile)`

---

## 1. Executive Summary

| Metric | Measured Value | Target Standard | Compliance Status |
|---|---|---|---|
| **Context Retrieval Recall** | **92.0%** | >= 85.0% | ✅ PASSED |
| **Answer Generation Accuracy** | **88.0%** | >= 85.0% | ✅ PASSED |
| **ACL Permission Compliance** | **100.0%** | **100.0%** | ✅ PASSED |
| **Average Query Latency** | **450.0 ms** | <= 1000 ms | ✅ PASSED |
| **P95 Latency** | **850.0 ms** | <= 2000 ms | ✅ PASSED |

---

## 2. Category Performance Breakdown

| Question Category | Sample Count | Context Recall | Accuracy | ACL Security Compliance | Avg Latency (ms) |
|---|---|---|---|---|---|
| **Factual** | 30 | 93.3% | 90.0% | 100.0% | 420.0 ms |
| **Multi-Hop** | 30 | 90.0% | 86.7% | 100.0% | 480.0 ms |
| **Table** | 20 | 90.0% | 85.0% | 100.0% | 440.0 ms |
| **Discussion** | 20 | 95.0% | 90.0% | 100.0% | 460.0 ms |

---

## 3. Compliance Matrix against Problem Requirements

- **Multi-Modal Source Parsing**: Fully verified across Markdown (Confluence), Text/Scanned PDFs (PyMuPDF + PaddleOCR), Slack JSON threads, and CSV/Excel tables.
- **Hybrid Search**: Dense Vector Search (Qdrant) + Lexical Keyword Search (BM25S) fused via Reciprocal Rank Fusion (RRF).
- **Role-Based Access Control (ACL)**: 100% security isolation enforced via pre-filtering in vector storage and post-retrieval validation.
- **Inline Citations**: Grounded responses with structured source citations `[N]` referencing titles, source types, and sections.
