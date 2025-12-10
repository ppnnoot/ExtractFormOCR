# Update Summary: Refactoring AI Extraction System

## 1. New AI Extraction Module (`ai_extraction.py`)
- **Purpose:** Created a streamlined, efficient AI extraction logic to replace complex legacy code.
- **Key Features:**
  - **Pure API Wrapper:** Focused solely on API communication without complex internal parsing logic.
  - **Async Support:** Implemented using `httpx` for non-blocking asynchronous API calls, improving performance under load.
  - **2-Step Extraction Process:**
    1.  **Correction:** Corrects spelling, formatting, and spacing (Unicode) of OCR text.
    2.  **Extraction:** Extracts specific fields into a structured format (TSV).
  - **Optimized Output:** Returns data in **Tab-Separated Values (TSV)** format (`key:value`) to minimize token usage and simplify parsing.
  - **Robustness:** Includes retry logic with exponential backoff and strict system prompts for data validation (e.g., removing commas in numbers).

## 2. API Server Integration (`api_server.py`)
- **New Endpoint:** Added `POST /v2/extract/text` specifically for this new logic.
- **Form ID Support:** Supports 5 form types (`HL0000050`-`HL0000055`) with dynamic context-aware prompts.
- **Seamless Integration:** Initialized alongside existing pipelines within the FastAPI lifespan context.

## 3. Prompt Engineering Improvements
- **Specific Role:** Defined AI as an expert in Thai medical documents.
- **Strict Rules:** Enforced critical rules for number formatting (no commas) and date standardization (DD/MM/YYYY).
- **Clean Output:** Enforced strict TSV output without headers or explanations to ensure machine readability.

