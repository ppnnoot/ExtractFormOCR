# AI Extraction Strategy: Page Handling & Optimization

This document outlines strategies for handling multi-page OCR text in the extraction pipeline, comparing different approaches to balance accuracy, performance, and cost.

## 1. Current Approach: Full Text Concatenation (Recommended)
**Method:** Combine text from all pages into a single string (`\n` separator) and send to AI in one shot.

- **Pros:**
  - ✅ **High Accuracy:** AI sees the full context (Header, Body, Footer) simultaneously.
  - ✅ **Simplicity:** No complex merging logic required.
  - ✅ **Consistency:** Header fields (e.g., HN, Name) that appear only on Page 1 are correctly associated with items on Page 2.
- **Cons:**
  - ⚠️ **Token Limit Risk:** Very long documents (>50 pages) might exceed the model's context window (though modern models handle 128k+ tokens easily).
  - ⚠️ **Cost:** Re-sending common text (like headers repeated on every page) consumes extra tokens if not cleaned.

## 2. Alternative: Page-by-Page Extraction
**Method:** Split OCR text by page markers (e.g., `Page 1`, `Page 2`), send each page to AI individually, then merge results.

- **Pros:**
  - ✅ **Scalability:** Can handle infinite pages by processing chunks.
  - ✅ **Parallelism:** Can process multiple pages simultaneously (Async).
- **Cons:**
  - ❌ **Context Loss:** Page 2 might contain only a table without the patient's name. AI will return "null" for `patient_name`, requiring complex fallback logic.
  - ❌ **Higher Cost:** System prompts and instructions are repeated for every page call.
  - ❌ **Complex Merging:** Requires logic to decide *which* page's value to trust (e.g., Page 1 has `total: 0`, Page 5 has `total: 5000`).

## 3. Advanced: Hybrid / Segmented Extraction
**Method:** Intelligently slice the document and extract specific sections.
1. **Header Extraction:** Send only Page 1 (or top 20%) to extract metadata.
2. **Body Extraction:** Send middle sections to extract line items.
3. **Footer Extraction:** Send only Page N (or bottom 20%) to extract totals.

- **Pros:**
  - ✅ **Efficiency:** Lowest token usage.
  - ✅ **Precision:** Targeted prompts for specific data types.
- **Cons:**
  - ❌ **Complexity:** High implementation effort to reliably identify sections.
  - ❌ **Layout Sensitivity:** Fails if the document layout changes (e.g., totals appearing at the top).

## Conclusion & Recommendation
For **Medical Receipts/Invoices (1-10 pages)**, the **Current Approach (Full Text)** is superior because:
1. Context preservation is critical for medical documents.
2. 10 pages of text is well within modern LLM limits (~5k-10k tokens).
3. Implementation is robust and maintainable.

**Optimization Tip:** Instead of splitting pages, implement a **Text Cleaner** to remove redundant headers/footers from pages 2+ *before* sending to AI. This reduces token usage while keeping the context intact.


