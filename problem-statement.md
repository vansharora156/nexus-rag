# Project Problem Statement: NexusRAG

## 1. Business Scenario
BigCorp, a global enterprise, has accumulated 15 years of internal knowledge. Unfortunately, this knowledge is heavily fragmented and scattered across a wide array of heterogeneous data repositories:
*   **Confluence:** Wiki pages containing project plans, team structures, design docs, and product requirements.
*   **Slack:** Collaborative chat histories with complex, threaded discussions, split across public and private channels.
*   **PDFs:** Architectural diagrams, scanned invoices, old printed reports, and official company policies. Many of these are scanned images without selectable text.
*   **Word & Excel/CSV:** Financial statements, tabular database dumps, marketing plans, and project schedules.
*   **Emails:** Multi-threaded communication detailing project decisions, meeting notes, and attachments.

The CEO of BigCorp has mandated the creation of an intelligent, unified internal search and Q&A tool. Standard, off-the-shelf Retrieval-Augmented Generation (RAG) tools fail in this environment due to several key enterprise-specific hurdles:
1.  **Complex Document Layouts:** Documents contain tables, diagrams, and multi-column text that basic text splitters turn into gibberish.
2.  **Scanned Documents:** A significant portion of legacy knowledge is locked in scanned PDFs, requiring high-fidelity Optical Character Recognition (OCR).
3.  **Threaded Conversations:** Slack chats have asynchronous replies, reactions, and conversational context that is lost when chunking documents blindly.
4.  **Version Duplication:** Over 15 years, many files have been duplicated with slight modifications (e.g., `Financials_2025_v1.xlsx`, `Financials_2025_v2_final.xlsx`). Standard search returns duplicate results, wasting context window space.
5.  **Permission Boundaries:** BigCorp has strict access policies. A general employee querying the system must never see answers or citations derived from restricted documents (e.g., HR files, finance records, exec memos).

---

## 2. Problem Statement
The goal is to build **NexusRAG**, an enterprise-grade, secure, and highly accurate RAG system. NexusRAG must ingest files from four primary source categories, process them using custom layout-aware and semantic parsers, deduplicate near-identical documents, index them using a hybrid search backend (sparse and dense representations), enforce document-level Access Control Lists (ACLs) dynamically at query time, and synthesize answers containing precise inline citations.

```
+---------------------------------------------------------------------------------+
|                                  NexusRAG                                       |
+---------------------------------------------------------------------------------+
|  [Source Ingestion] -> [Layout/Thread Parsing] -> [MinHash LSH Deduplication]   |
|                                                                                 |
|  [Hybrid Indexing]  -> [ACL Policy Mapping]    -> [Retrieval & Fusion]          |
|                                                                                 |
|  [Cross-Reranking]  -> [LLM Generation]        -> [ACL-Compliant Answer]        |
+---------------------------------------------------------------------------------+
```

---

## 3. Project Objectives
To address BigCorp's requirements, the NexusRAG implementation will achieve the following:
*   **Ingest and Parse Heterogeneous Sources:** Build specialized parser modules capable of handling Confluence (Markdown), raw/scanned PDFs, Slack JSON threads, and Excel/CSV spreadsheets.
*   **Develop Layout-Aware & Conversational Chunker:** Design chunking algorithms that maintain table hierarchies, group Slack threads with their starting context, and respect markdown headers.
*   **Implement Near-Duplicate Detection:** Use MinHash and Locality-Sensitive Hashing (LSH) to identify and cluster documents with high text overlap, filtering out redundant versions.
*   **Implement Secure Hybrid Retrieval:** Set up a dual search pipeline:
    *   *Sparse retrieval* using BM25.
    *   *Dense retrieval* using BGE-M3 embeddings.
    *   Fuse results using **Reciprocal Rank Fusion (RRF)**.
*   **Enforce RBAC/ACL at Retrieval Time:** Filter search results dynamically before they reach the LLM or reranker. The system must verify the querying user's security groups against the document's ACLs.
*   **Establish a 100-Question Evaluation Suite:** Run automated tests evaluating retrieval accuracy, citation correctness, duplicate handling, and security enforcement.

---

## 4. Key Challenges

> [!IMPORTANT]
> The success of NexusRAG relies on solving these engineering challenges:

| Challenge | Impact on Off-the-Shelf RAG | NexusRAG Mitigation Strategy |
| :--- | :--- | :--- |
| **OCR Latency & Accuracy** | Scan-only PDFs are ignored or poorly parsed. | Integrated **PaddleOCR** layout parser with caching to avoid re-parsing unchanged documents. |
| **Table Preservation** | Cells are flattened into a single text stream, losing horizontal/vertical relationships. | **pdfplumber** and **openpyxl** extract tables directly into Markdown/HTML table blocks before chunking. |
| **Threaded Context** | Slack messages are split into disjointed chunks, losing the original topic. | Thread assembly logic that groups child replies with parent messages, appending channel metadata. |
| **Near-Duplicate Files** | Retrieve multiple minor versions of the same document, drowning out other sources. | **MinHash LSH** signature calculation during ingestion; indexes only the latest or primary document, flagging variants. |
| **Permission Security** | General users retrieve answers containing restricted HR or executive data (leakage). | Hard metadata filtering in Qdrant/SQLite. ACL checks occur *during* the database query, not post-retrieval. |

---

## 5. Expected Outcome
The project will deliver:
1.  **Production-Ready Backend API:** A FastAPI service exposed locally or via Docker, supporting secure queries, document ingestion, and status monitoring.
2.  **High-Fidelity UI Frontend:** A clean, responsive Vite + Vanilla JS interface showing answers, expandable sources, and inline citations.
3.  **Strict Security Verification:** A system that passes 100% of ACL leakage test cases, demonstrating that unauthorized roles can never extract protected information.
4.  **Golden Dataset Evaluation:** A comprehensive evaluation report outlining retrieval recall, answer precision, and latency metrics across 100 target queries.
