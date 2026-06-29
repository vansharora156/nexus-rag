# ADR-001: Choosing Qdrant over ChromaDB

| Field       | Value                          |
|-------------|--------------------------------|
| **Status**  | ✅ Accepted                    |
| **Date**    | 2026-06-30                     |
| **Authors** | BigCorp Engineering            |
| **Deciders**| RAG Platform Team              |

---

## Context

For the AskTheCompany/NexusRAG production deployment, we need a robust, enterprise-grade vector database to handle dense vector storage and retrieval. Our initial prototype utilized ChromaDB, which is a lightweight, easy-to-configure, Python-native vector store.

However, during our scale and performance testing, several critical limitations of ChromaDB became evident:
1. **Payload & Metadata Filtering Limitations**: ChromaDB's support for complex, nested metadata filtering is limited and can result in significant query latency or scan overhead.
2. **Production Scaling**: ChromaDB does not natively support distributed operations, clustering, or high availability, which are hard requirements for our enterprise service-level agreements (SLAs).
3. **Enterprise Database Features**: It lacks advanced indexing structures (such as HNSW customization on payloads), snapshots/backups, and granular monitoring metrics.
4. **Memory Management**: ChromaDB's memory footprint grows aggressively with collection size, sometimes leading to unstable out-of-memory issues in resource-constrained container environments.

Therefore, we need to transition to a production-ready vector database that can seamlessly support local development while scaling horizontally in production environments.

---

## Decision

We will select **Qdrant** as our primary vector store, replacing ChromaDB.

### Key Reasons for Choosing Qdrant

1. **Rust Engine Performance**: Qdrant is written in Rust, offering extremely low latency, high throughput, and efficient CPU/memory utilization.
2. **Advanced Payload Filtering**: Qdrant supports complex metadata (payload) filtering (using logical operators, nested values, and array checks) directly during the vector search process, avoiding separate post-retrieval overhead.
3. **Custom Payload Indices**: We can create indices on specific payload keys (e.g., keyword, integer, geo, etc.), allowing Qdrant to speed up metadata-filtered queries dramatically.
4. **Development and Production Parity**:
   - **Local development**: Qdrant can run in-memory (`:memory:`) or write to local disk via a path (similar to SQLite/ChromaDB), meaning developers do not need a Docker container running for basic test suites.
   - **Production**: Qdrant is easily deployed as a clustered, distributed service (using Helm charts or Docker Compose) with built-in replication, failover, and snapshot capabilities.
5. **Clean API & Client Support**: The `qdrant-client` Python SDK is robust, fully typed, asynchronous-compatible, and well-maintained.

---

## Consequences

### Positive

- **Cleaner Metadata Filtering Code**: Leveraging Qdrant's payload filtering capabilities simplifies python-side code and avoids raw filter loops.
- **Faster Search & Higher Throughput**: Qdrant's HNSW implementation in Rust significantly outperforms ChromaDB's Python/C++ wrapper, especially under high concurrency.
- **Production Scalability**: Highly scalable to millions of vectors with horizontal clustering and sharding support out-of-the-box.
- **Local Run Support**: Allows `:memory:` or local directory storage modes, keeping developer onboarding simple.

### Negative

- **Slightly Larger Python Dependency**: The `qdrant-client` package and its dependencies add to the initial project setup size.
- **Infrastructure Footprint**: Production deployments require running and maintaining a Qdrant container/service (though mitigated by hosting options and simple container orchestration).

---

## Alternatives Considered

### 1. ChromaDB
- **Pros**: Zero-configuration, Python-native, easy local runs.
- **Cons**: Poor scalability, lack of robust payload indices, high memory consumption, not ready for production-grade enterprise traffic.
- **Verdict**: Rejected for production; replaced by Qdrant.

### 2. Milvus / pgvector
- **Pros**: Milvus is highly scalable; pgvector keeps data in PostgreSQL.
- **Cons**: Milvus has extremely high operational complexity (requires Pulsar, MinIO, Etcd). pgvector is great but lacks advanced out-of-the-box HNSW optimizations and features that a dedicated vector DB like Qdrant provides for hybrid RAG applications.
- **Verdict**: Rejected due to operational complexity or lack of specialized features.

---

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Vector DB Comparison Benchmarks](https://qdrant.tech/benchmarks/)
