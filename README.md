# RAG System (Azure)

Retrieval-Augmented Generation pipeline with ingestion, indexing, and question answering.

## Features
- Ingest PDF/DOCX/PPTX, split into paragraphs, chunk, embed, and index
- Ask questions via API or agent streaming (SSE)
- Azure Search vector store integration
- Optional Llama Cloud OCR for workflow pages
- FastAPI service with health, ingest, and ask routes

## Project layout
- src/domain: core models, services, and exceptions
- src/application: use cases
- src/infrastructure: adapters, persistence, scripts, DI
- src/presentation: FastAPI API
- tests: unit and integration tests

## Pipeline overview
1. Load document (PDF/DOCX/PPTX)
2. Classify pages and extract text/workflow content
3. Split into paragraphs and chunk with overlap
4. Generate embeddings
5. Store in Azure AI Search
6. Retrieve chunks and generate answer

## Requirements
- Python 3.11+ (3.14 used in dev)
- Azure OpenAI, Azure Search, and Azure AI Project credentials
- Optional: Llama Cloud OCR credentials

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with required variables:
```
# Ingestion / data
DATA_DIR=data
EXCEL_PATH=extra_data/categories.xlsx

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_API_VERSION=
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=
AZURE_OPENAI_DEPLOYMENT_NAME=

# Azure AI Search
AZURE_AI_SEARCH_ENDPOINT=
AZURE_AI_SEARCH_INDEX_NAME=
AZURE_AI_SEARCH_API_KEY=
AZURE_EMBEDDING_DIMENSIONS=3072

# Azure AI Agent
AZURE_TENANT_ID=
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_PROJECT_ENDPOINT=
AZURE_AI_AGENT_ID=

# Llama Cloud OCR (optional)
LLAMA_CLOUD_API_KEY=
LLAMA_CLOUD_ENDPOINT=
```

## Run API
```bash
D:/rag_system_azure/.venv/Scripts/python.exe -m uvicorn src.presentation.api.main:app --reload
```

## Ingestion scripts
```bash
D:/rag_system_azure/.venv/Scripts/python.exe src/infrastructure/scripts/create_index_script.py
D:/rag_system_azure/.venv/Scripts/python.exe src/infrastructure/scripts/upload_files_script.py
```

## Tests
```bash
D:/rag_system_azure/.venv/Scripts/python.exe -m pytest
D:/rag_system_azure/.venv/Scripts/python.exe -m pytest tests/unit
D:/rag_system_azure/.venv/Scripts/python.exe -m pytest tests/integration
```

Current test count: 72
- Unit tests: 65
- Integration tests: 7

## Notes
- Integration tests use mocks for external services by default.
- Update `.env` values before running ingestion or API in production.
