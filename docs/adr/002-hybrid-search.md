# ADR-002: BM25 + Dense Qdrant Hybrid Retrieval with RRF

| Field       | Value                          |
|-------------|--------------------------------|
| **Status**  | ✅ Accepted                    |
| **Date**    | 2026-06-30                     |
| **Authors** | BigCorp Engineering            |
| **Deciders**| RAG Platform Team              |

---

## Context

Enterprise knowledge bases contain a mixture of structured and unstructured information:
1. **Rare terms, product/error IDs, code snippets, and employee names**: These require exact string matching. For example, a query searching for `Error-501-A` or a specific file name like `setup.sh` needs to locate the exact match.
2. **Conceptual, semantic, or conversational queries**: These require understanding of synonyms, semantic intent, and context (e.g., "how do I onboard new hires?").

Our testing showed that:
- **Dense-only search** (using embedding models) handles semantic queries beautifully but frequently fails on exact-match queries like error codes or product SKUs because it projects them to nearby semantic concepts rather than matching exact tokens.
- **Sparse-only search** (like BM25) is fast and perfect for exact-match terms but fails when users use synonyms, different phrasing, or ask conceptual questions.

Therefore, we need a hybrid retrieval architecture that merges both dense semantic search and sparse lexical search, followed by a high-fidelity reranking step to optimize results before they are sent to the LLM.

---

## Decision

We will implement a hybrid search pipeline combining **Qdrant dense vector search** and **BM25 sparse search**, fused via **Reciprocal Rank Fusion (RRF)**, and re-ranked using a cross-encoder:

1. **Dense Retrieval Path**:
   - Embed queries and chunks using the **BAAI/bge-m3** model (which offers state-of-the-art multi-lingual, long-document representation).
   - Query the Qdrant vector database for the top dense candidates.
2. **Sparse Retrieval Path**:
   - Index document chunks lexically using **bm25s** (a highly optimized, pure-Python implementation of BM25).
   - Query the `bm25s` index for the top lexical candidates.
3. **Fusion (Reciprocal Rank Fusion)**:
   - Combine the dense and sparse rankings using Reciprocal Rank Fusion (RRF) with a constant parameter **k=60**.
   - RRF calculates scores based on the ranks rather than raw cosine/BM25 scores, preventing normalization mismatches:
     ```
     RRF_Score(d) = 1 / (60 + Rank_dense(d)) + 1 / (60 + Rank_sparse(d))
     ```
4. **Stage-2 Reranking**:
   - Pass the top candidates from RRF through **BAAI/bge-reranker-large** (a powerful Cross-Encoder model) to compute deep query-document relevance scores.
   - Select the final top-K chunks to pass to the LLM generation phase.

---

## Consequences

### Positive

- **Maximum Accuracy**: Combines the strengths of both semantic and keyword matching, ensuring exact-match queries and general conceptual queries both return highly relevant documents.
- **Code-Level and ID References**: Robustly matches rare strings, configuration variables, error codes, and scripts.
- **Improved Retrieval Performance**: RRF is rank-agnostic and robust to outlier scores, providing stable fusion without complex parameter tuning.
- **Enhanced Re-ranking Precision**: Using a high-capacity cross-encoder (`bge-reranker-large`) dramatically improves precision by evaluating token-level interactions between queries and candidates.

### Negative

- **Increased Compute**: Running both sparse index queries and dense model embeddings, followed by a local cross-encoder, increases retrieval latency.
- **Storage Overhead**: We must build, maintain, and persist both a Qdrant collection and a `bm25s` index.

---

## Alternatives Considered

### 1. Dense-Only Retrieval
- **Pros**: Lower latency, simpler indexing.
- **Cons**: Poor recall on specific product codes, variable names, and error IDs.
- **Verdict**: Rejected.

### 2. Weighted Score Fusion (Linear combination)
- **Pros**: Direct score control.
- **Cons**: Requires continuous calibration and normalization of vector similarity scores and BM25 scores, which operate on entirely different distributions.
- **Verdict**: Rejected in favor of the more robust rank-based RRF.

---

## References

- Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods.*
- BAAI/bge-m3 Model Card & Benchmarks.
