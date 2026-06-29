# NexusRAG Evaluation & Testing Plan

This document outlines the evaluation framework, metric definitions, and testing procedures for measuring the quality, correctness, and security of the NexusRAG system.

---

## 1. Golden Dataset Structure

To ensure comprehensive testing, we will construct a **100-question Golden Dataset**. This dataset will be stored as a structured JSON file containing diverse query types and expected targets.

### 1.1 JSON Schema of the Golden Dataset

```json
[
  {
    "id": "Q001",
    "query": "What is the expected database downtime for the migration on June 30?",
    "difficulty": "factual", // 'factual' | 'multi-hop' | 'table' | 'discussion'
    "source_type": "slack", // 'confluence' | 'pdf' | 'slack' | 'spreadsheet'
    "expected_answer": "The database downtime is expected to be 15 minutes, starting at 11:00 PM EST.",
    "expected_citations": [
      {
        "doc_id": "slack_thread_1719600000",
        "chunk_index": 0
      }
    ],
    "required_acls": ["Engineering", "Exec"], // User must have at least one of these groups to see this answer
    "restricted_acls": ["HR", "Finance"] // Users with only these roles must receive a "Not Found" response
  }
]
```

### 1.2 Difficulty Categories
The 100 questions are split across four distinct challenges:
1.  **Factual (30 Questions):** Direct queries seeking a single, explicitly stated fact from a Confluence page or PDF.
2.  **Multi-Hop (30 Questions):** Queries requiring information from two or more documents to compose the final answer (e.g., matching a client ID in an invoice PDF with a contact person name in a Confluence roster).
3.  **Table Extraction (20 Questions):** Queries asking for specific cells, column averages, or intersections in Excel sheets or embedded PDF tables.
4.  **Discussion Threads (20 Questions):** Queries targetting consensus, decision history, or troubleshooting records within Slack message chains.

---

## 2. Evaluation Metrics

Every run of the evaluation engine will compute the following performance indicators.

```
       +------------------------------------------------------------+
       |                  NexusRAG Metrics Suite                    |
       +------------------------------------------------------------+
       |   Generation Metrics    |  Answer Accuracy (LLM-as-Judge)  |
       |                         |  Citation Precision & Recall     |
       +-------------------------+----------------------------------+
       |   Retrieval Metrics     |  Context Recall                  |
       |                         |  Deduplication Rate              |
       +-------------------------+----------------------------------+
       |   Security Metrics      |  Permission Compliance (100%)    |
       +------------------------------------------------------------+
```

### 2.1 Answer Accuracy (LLM-as-Judge)
*   **Definition:** Measures how faithfully the generated answer matches the semantic meaning of the `expected_answer`.
*   **Measurement:** We use Gemini 2.5 Flash as an evaluator, feeding it the query, the expected answer, and the generated answer. It outputs a score from 1 to 5:
    *   *5 (Excellent):* Generated answer contains all facts and has no hallucinations.
    *   *3 (Satisfactory):* Correct answer, but missing minor context.
    *   *1 (Incorrect):* Hallucinations, wrong values, or incorrect facts.

### 2.2 Context Recall
*   **Definition:** Measures if the retrieval pipeline succeeded in fetching the specific document chunks containing the correct information.
*   **Calculation:**
    $$\text{Context Recall} = \frac{|\text{Retrieved Ground Truth Chunks} \cap \text{Expected Citations}|}{|\text{Expected Citations}|}$$
*   **Target:** $\ge 90\%$.

### 2.3 Citation Precision & Recall
*   **Citation Precision:** The fraction of citations in the generated answer that are actually relevant to the facts they claim to support.
    $$\text{Citation Precision} = \frac{\text{Number of Accurate Citations}}{\text{Total Citations Generated}}$$
*   **Citation Recall:** The fraction of retrieved source chunks that *should* have been cited to support statements in the answer.
    $$\text{Citation Recall} = \frac{\text{Number of Cited Expected Chunks}}{\text{Total Expected Chunks Retrieved}}$$

### 2.4 Permission Compliance (Critical)
*   **Definition:** Validates that ACL filtering strictly prevents access leakage.
*   **Calculation:** For every question, the evaluator runs two user queries:
    1.  *Authorized User:* User role matches `required_acls`. Verify that the correct answer is retrieved.
    2.  *Unauthorized User:* User role only contains `restricted_acls`. Verify that the system returns "I cannot find the answer" and retrieved context contains 0 restricted chunks.
*   **Target:** **Exactly 100%**. Any leak (value > 0% failure) triggers a test failure.

### 2.5 Deduplication Rate
*   **Definition:** Measures the percentage of redundant, near-duplicate chunks successfully filtered out of the active index.
*   **Calculation:**
    $$\text{Deduplication Rate} = 1.0 - \frac{\text{Unique Indexed Chunks in System}}{\text{Total Parsed Chunks before LSH}}$$

---

## 3. Testing Procedure

The evaluation will be automated via a Python test runner script (`src/eval/run_eval.py`).

### Step 1: Ingestion & Duplicate Setup
1.  Clear the SQLite metadata database, Qdrant vector index, and BM25s binaries.
2.  Ingest the test document corpus (including several files designed to trigger the MinHash LSH deduplicator).
3.  Log the **Deduplication Rate** output to verify the MinHash logic.

### Step 2: Query Execution & Security Auditing
1.  Iterate over each test case in the Golden Dataset JSON.
2.  **Audit A (Authorized Access):**
    *   Post the query to the FastAPI `/query` route with the authorized role header.
    *   Record latency (ms).
    *   Save generated answer, retrieved context, and citation list.
3.  **Audit B (Unauthorized Access):**
    *   Post the query to `/query` using an unauthorized role header.
    *   Verify that the response returns the standard fallback message and that no forbidden chunk IDs exist in the payload response.

### Step 3: Metric Calculation & Report Generation
1.  Compute the retrieval scores (Context Recall).
2.  Format the LLM-as-judge prompts to score the accuracy and citation precision of the authorized responses.
3.  Compile the results into a markdown test run artifact (`artifacts/evaluation_run_latest.md`), mapping scores by category (factual, multi-hop, table, discussion) and listing average latencies.
