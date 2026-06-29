# ADR-003: Choosing PaddleOCR over EasyOCR and Tesseract

| Field       | Value                          |
|-------------|--------------------------------|
| **Status**  | ✅ Accepted                    |
| **Date**    | 2026-06-30                     |
| **Authors** | BigCorp Engineering            |
| **Deciders**| RAG Platform Team              |

---

## Context

Enterprise document management involves ingesting a wide range of document types, including scanned PDFs, photographed meeting notes, policy briefs, and quarterly reports. A significant portion of these documents contains:
1. **Multi-column layouts**: Standard text block detectors fail by reading across columns, destroying structural coherence.
2. **Tables**: Financial reports and specifications contain critical tabular data that must be extracted in structural formats (e.g., Markdown tables or CSVs) rather than raw, unformatted lines of text.
3. **Multi-lingual text**: Documents may contain a mix of English and other languages.

Our previous prototype utilized Tesseract, which performs poorly on structured layouts, columns, and tabular content without extensive pre-processing and manual box-detection rules. EasyOCR was also evaluated but struggled with high-throughput table structuralization and complex layouts.

---

## Decision

We will select **PaddleOCR** as our primary OCR engine.

### Key Reasons for Choosing PaddleOCR

1. **Layout Analysis (PP-Structure)**: PaddleOCR includes PP-Structure, a lightweight, highly accurate document layout analysis system that can automatically classify layout components (text, title, table, image, etc.).
2. **Tabular Structure Extraction**: PaddleOCR has a dedicated table recognition model that reconstructs the HTML/Markdown table structure from scanned regions, preserving the relationship between rows and columns.
3. **State-of-the-Art Accuracy**: It outperforms Tesseract and EasyOCR on complex, multi-lingual, multi-column, and tabular layouts, producing clean, structured text representations.
4. **Active Ecosystem**: It is actively maintained with pre-trained models optimized for CPU deployment, making it suitable for standard cloud and local environments.

---

## Consequences

### Positive

- **High-Quality Document Parsing**: Excellent extraction of tables and structured text from scanned PDFs and images, leading to far cleaner vector representation and better LLM comprehension.
- **Table Structure Retention**: Enables our parsing pipeline to generate accurate Markdown tables from image-based formats.
- **Out-of-the-box Multi-column Handling**: Layout analysis prevents mixing text across columns.

### Negative

- **Heavy Dependencies**: PaddleOCR requires `paddlepaddle` (or `paddlepaddle-cpu` for CPU-based inference), which has a large installation size and complex dependency footprint compared to pure-python packages.
- **Resource Overhead**: Layout analysis and deep-learning OCR require more CPU/memory resources than simple heuristic parsers.

---

## Alternatives Considered

### 1. Tesseract OCR
- **Pros**: Lightweight, low footprint, widely available.
- **Cons**: Poor layout analysis, destroys tables, requires complex manual page-segmentation mode tuning.
- **Verdict**: Rejected for layout-dense documents.

### 2. EasyOCR
- **Pros**: Easy to install, clean Python package.
- **Cons**: Slower inference, lacks the advanced structural layout and table reconstruction capabilities of PaddleOCR's PP-Structure.
- **Verdict**: Rejected.

---

## References

- [PaddleOCR GitHub Repository](https://github.com/PaddlePaddle/PaddleOCR)
- [PP-Structure Layout Analysis Technical Report](https://arxiv.org/abs/2110.10126)
