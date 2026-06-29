# NexusRAG Supported Data Sources

This document describes the four primary data source types processed by NexusRAG, detailing their file formats, ingestion strategies, structural challenges, and the metadata extracted for retrieval and access control.

---

## 1. Confluence (Markdown Pages)

### 1.1 Source Format & Structure
Confluence pages are exported or fetched as standard Markdown files (`.md`). They feature a clear text hierarchy, with frontmatter or header text containing page metadata, followed by structured text using headers (`#` to `####`), bullet points, and inline tables.

### 1.2 Parsing & Ingestion Strategy
*   **Tooling:** Python's native file readers combined with regex-based frontmatter parsers.
*   **Pipeline:** The parser extracts metadata headers (such as `Space:`, `Author:`, `PageID:`, `Permissions:`) and strips them from the main content. The body text is passed to the Markdown chunker, which splits the content on headers (`#`, `##`, `###`) to ensure subtopics remain in separate chunks.

### 1.3 Structural Challenges & Technical Solutions
*   *Challenge:* Relative links to other pages (e.g., `[Link Text](./other-page.md)`) become broken or meaningless during chunking.
*   *Solution:* The parser extracts and resolves markdown links, converting them into absolute page titles and saving them in the chunk metadata as context.

### 1.4 Captured Metadata & ACL Mapping
```json
{
  "doc_id": "conf_12345",
  "source_type": "confluence",
  "title": "Engineering Handover 2026",
  "space": "Engineering",
  "acls": ["Engineering", "Product", "Exec"],
  "author": "john.doe@bigcorp.com",
  "last_modified": "2026-05-12T14:30:00Z"
}
```

---

## 2. PDF Documents (Native & Scanned)

### 2.1 Source Format & Structure
PDFs represent a split format:
1.  *Native PDFs:* Contain extractable text blocks and digital font metadata.
2.  *Scanned PDFs:* Contain raster images (JPEG/PNG) of pages without any selectable text.

### 2.2 Parsing & Ingestion Strategy
*   **Tooling:** `pdfplumber` for native text extraction; `PaddleOCR` for scanned page layouts and OCR transcriptions.
*   **Pipeline:**
    1.  The reader attempts to extract text from a page using `pdfplumber`.
    2.  If the text yield is below a threshold (e.g., fewer than 50 characters per page), the page is marked as a scan.
    3.  Scanned pages are converted to high-resolution images and run through the `PaddleOCR` layout analysis pipeline.
    4.  Layout analysis detects paragraphs, headers, and tables, returning them in reading order.

### 2.3 Structural Challenges & Technical Solutions
*   *Challenge:* Scanned tables are transcribed as a flat list of words, losing the spreadsheet matrix structure.
*   *Solution:* PaddleOCR’s table recognition module reconstructs cells, which are then formatted into Markdown tables (e.g., `| Col1 | Col2 |`) and appended to the text before chunking.

### 2.4 Captured Metadata & ACL Mapping
```json
{
  "doc_id": "pdf_98765",
  "source_type": "pdf",
  "title": "Q3_Financial_Audit_Report",
  "file_path": "/shared/finance/Q3_Financial_Audit_Report.pdf",
  "acls": ["Finance", "Exec"],
  "total_pages": 42,
  "is_ocr": true
}
```

---

## 3. Slack Message Threads

### 3.1 Source Format & Structure
Slack data is ingested as raw JSON exports. Each channel folder contains JSON files listing messages. Message threads consist of a parent message (with a unique timestamp `ts`) and a series of replies containing a thread timestamp (`thread_ts`).

### 3.2 Parsing & Ingestion Strategy
*   **Tooling:** Python `json` library + custom thread assembly modules.
*   **Pipeline:**
    1.  Group all messages sharing a `thread_ts`.
    2.  Sort replies chronologically.
    3.  Format the thread into a readable markdown conversation block:
        ```markdown
        ### Slack Channel: #dev-announcements
        **[UserA] (10:15 AM):** We are migrating the database tonight.
        *   **[UserB] (10:17 AM):** What is the downtime window?
        *   **[UserA] (10:18 AM):** Expected to be 15 minutes, starting at 11:00 PM EST.
        ```
    4.  Pass the entire assembled thread block as a single document/chunk so the context is preserved.

### 3.3 Structural Challenges & Technical Solutions
*   *Challenge:* Slack channels are sometimes renamed or private, and thread context is lost if a single reply is retrieved on its own.
*   *Solution:* We never index single replies. The entire thread (up to a limit of 4,000 tokens) is indexed as a single chunk. If a thread exceeds the token limit, it is split, but the parent message is prepended to the subsequent chunks to carry forward the context.

### 3.4 Captured Metadata & ACL Mapping
```json
{
  "doc_id": "slack_thread_1719600000",
  "source_type": "slack",
  "channel_name": "dev-announcements",
  "channel_type": "public",
  "acls": ["Engineering", "Product", "HR", "Finance", "Exec"],
  "participants": ["UserA", "UserB"],
  "thread_timestamp": "1719600000.000200"
}
```
> [!NOTE]
> Private Slack channel exports map their ACL list strictly to the members of that private channel, preventing external exposure.

---

## 4. Spreadsheets (Excel & CSV)

### 4.1 Source Format & Structure
Tabular records stored in Microsoft Excel (`.xlsx`) or comma-separated files (`.csv`). They represent raw rows, columns, and sheets.

### 4.2 Parsing & Ingestion Strategy
*   **Tooling:** `openpyxl` (for Excel files) and `pandas` (for CSV tables).
*   **Pipeline:**
    1.  Read sheets individually.
    2.  Convert empty/merged cells into unified representations.
    3.  Format tables into markdown blocks.
    4.  Split large sheets into chunks by row count, ensuring headers are duplicated on every chunk to maintain context.

### 4.3 Structural Challenges & Technical Solutions
*   *Challenge:* Large spreadsheets (e.g., 50 columns, 5,000 rows) exceed LLM context windows and result in useless chunks when split randomly.
*   *Solution:*
    1.  Sheets are chunked in row blocks (e.g., 50 rows per chunk).
    2.  The schema headers (row 0) are dynamically injected into the beginning of every chunk.
    3.  Users can query rows with column references preserved:
        ```markdown
        [Columns: Date | Expense | Department]
        Row 23: 2026-03-01 | $5,200 | Engineering
        Row 24: 2026-03-02 | $1,100 | Marketing
        ```

### 4.4 Captured Metadata & ACL Mapping
```json
{
  "doc_id": "sheet_44556",
  "source_type": "spreadsheet",
  "title": "Department_Budgets_2026",
  "sheet_name": "Engineering_Budget",
  "acls": ["Finance", "Engineering", "Exec"],
  "column_headers": ["Date", "Expense", "Department"]
}
```
