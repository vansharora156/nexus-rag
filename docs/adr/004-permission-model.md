# ADR-004: Post-Retrieval ACL Filtering

| Field       | Value                          |
|-------------|--------------------------------|
| **Status**  | ✅ Accepted                    |
| **Date**    | 2026-06-30                     |
| **Authors** | BigCorp Engineering            |
| **Deciders**| RAG Platform Team, Security    |

---

## Context

Enterprise knowledge bases have diverse security boundaries. Users (e.g., Engineering, HR, Finance, Executive) must only be allowed to retrieve and view documents matching their specific access permissions.
- Documents are tagged with Access Control List (ACL) identifiers at ingestion.
- Users have roles/groups associated with their authentication context.
- We must guarantee that no unauthorized document context is ever passed to the LLM or exposed in the response citations.

---

## Decision

We will implement **post-retrieval, pre-reranking ACL filtering**:

1. **Document & Chunk ACL Metadata**:
   - Each ingested chunk inherits the `acl_tags` of its parent document.
   - Metadata payload tags are stored alongside vectors in Qdrant and indices in BM25.
2. **Filtering Position in Pipeline**:
   - Retrieve candidate lists from both Qdrant (dense) and BM25 (sparse).
   - Perform Reciprocal Rank Fusion (RRF) to merge the rankings.
   - **Apply ACL filtering immediately after RRF fusion**: Filter out all chunks whose `acl_tags` do not overlap with the user's roles.
   - Pass the remaining authorized candidates to the Cross-Encoder Reranker.
3. **Over-Retrieval Compensation**:
   - Increase the first-stage retrieval counts (e.g., retrieve top-50/100 candidates per path) to ensure that a sufficient number of relevant, authorized documents pass through the ACL filter and reach the reranking/generation stage.

---

## Consequences

### Positive

- **Shared Multi-Tenant Storage**: We maintain a single Qdrant collection and BM25 index rather than duplicating indices per user role or tenant.
- **Minimal Reranking Compute**: Filtering before the Cross-Encoder step ensures we do not waste GPU/CPU resources reranking documents the user cannot access anyway.
- **Strict Citation Security**: No unauthorized text reaches the LLM, preventing data leakage or halluncinated exposure in generated answers.

### Negative

- **Retrieval Inefficiency**: For highly restricted users, a large percentage of top-k retrieved candidates might be filtered out, potentially leaving fewer results than desired for the reranker. This is countered by over-retrieval.

---

## Alternatives Considered

### 1. Separate Collections Per Role
- **Description**: Maintaining a separate physical index or database collection for each role.
- **Verdict**: Rejected due to high storage multiplication, synchronization issues, and complexity of updating document tags.

### 2. Pre-Filtering (Query-Time Vector DB Filtering)
- **Description**: Passing the user roles as metadata filter expressions inside Qdrant and BM25 query requests.
- **Verdict**: Rejected for our current deployment. While Qdrant supports payload filters, doing pre-filtering across both dense (Qdrant) and sparse (bm25s) indices requires maintaining two separate filter logic implementations, which can lead to misalignment and complexity. Post-retrieval filtering provides a single, centralized point of security policy enforcement. We will reconsider pre-filtering in the vector DB if candidate counts grow beyond 100K+ documents and post-retrieval filtering suffers from recall drop.

---

## References

- OWASP Top 10 for LLM Applications (Insecure Output Handling, Data Leakage).
