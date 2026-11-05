# Educational Document Assistant (RAG Chatbot)

A standalone AI assistant that answers questions from your own PDF, TXT and Markdown files.
It runs fully on your own computer using Ollama, so no cloud account or API key is needed.

## 1. What it does

| Requirement | How it is done |
|---|---|
| Conversational interface | Web chat page at `http://localhost:8000` |
| Document question answering | PDF / TXT / MD files are read, split into chunks and searched |
| RAG | Top matching chunks are sent to the local LLM, which answers only from them |
| Automated document workflow | n8n workflow scans the `data/inbox` folder every 5 minutes |
| Conversation history and references | Saved in SQLite; every answer lists file name, page and match score |
| Testing | 13 automated tests plus an accuracy and speed report script |

## 2. How it works (in simple words)

```
 Upload file ──> Read text ──> Cut into small chunks ──> Turn chunks into numbers ──> Save in ChromaDB
                                                                                           │
 Your question ──> Turn into numbers ──> Find 4 closest chunks ◄───────────────────────────┘
                                                │
                       Chunks + question + last few messages ──> Ollama LLM ──> Answer + sources
```

Example: you ask "Which pigment absorbs sunlight?". The system finds the photosynthesis chunk that
mentions chlorophyll, gives only that text to the LLM, and shows `photosynthesis.txt, page 1` under the answer.
If nothing in your files matches, it says *"I could not find this in the uploaded documents"* instead of guessing.

## 3. Setup

**Step 1. Install Ollama** from https://ollama.com and pull two models:
```
ollama pull llama3.2
ollama pull nomic-embed-text
```
(`llama3.2` writes answers, `nomic-embed-text` turns text into searchable numbers. If your laptop is slow, use `llama3.2:1b`.)

**Step 2. Install Python packages** (Python 3.10 or newer):
```
python -m venv venv
venv\Scripts\activate          # Windows      (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

**Step 3. Start the app:**
```
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000, upload the files from `sample_docs/`, and start asking questions.

**Step 4. (Optional) Start n8n for the automatic workflow:**
```
docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
```
Open http://localhost:5678, choose *Import from file*, select `n8n/document_workflow.json` and activate it.
From now on, any PDF/TXT/MD file you drop into `data/inbox/` is processed within 5 minutes:
success moves it to `data/processed/`, failure moves it to `data/failed/` with a `.error.txt` explanation.
The "Notify" node is a placeholder; replace it with an Email or Telegram node to receive failure alerts.
If n8n is not running in Docker, change the URL in the HTTP node to `http://localhost:8000/ingest/scan`.

## 4. Project structure

| Path | Purpose |
|---|---|
| `app/main.py` | FastAPI server and all API endpoints |
| `app/ingest.py` | Reading, chunking, embedding and storing documents; inbox scanning |
| `app/rag.py` | Retrieval, prompt building, LLM call, "not found" rule |
| `app/embeddings.py` | Ollama embedding client |
| `app/store.py` | ChromaDB access |
| `app/history.py` | Chat history in SQLite |
| `app/static/index.html` | Chat web page |
| `n8n/document_workflow.json` | Importable n8n workflow |
| `sample_docs/` | Three sample educational documents |
| `tests/` | Automated tests, test questions, evaluation script |
| `docs/TEST_RESULTS.md` | Test results and how to reproduce them |

## 5. API endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/chat` | `{"question": "...", "session_id": "optional"}` returns answer, sources, seconds |
| GET / DELETE | `/history/{session_id}` | Read or clear a conversation |
| POST | `/documents/upload` | Upload and process one file |
| POST | `/ingest/scan` | Process everything in the inbox (used by n8n) |
| GET | `/documents` | List documents and chunk counts |
| DELETE | `/documents/{name}` | Remove a document |
| GET | `/health` | Quick status check |

Interactive API page: http://localhost:8000/docs

## 6. Settings (environment variables)

| Name | Default | Meaning |
|---|---|---|
| `LLM_MODEL` | llama3.2 | Model that writes answers |
| `EMBED_MODEL` | nomic-embed-text | Model that makes searchable vectors |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | 800 / 150 | Characters per chunk / shared between neighbours |
| `TOP_K` | 4 | Chunks given to the LLM |
| `MIN_SIM` | 0.30 | Minimum match score; lower than this means "not found". Raise it if the bot answers off-topic questions, lower it if it says "not found" too often |

## 7. Error handling

| Situation | Behaviour |
|---|---|
| Ollama not running | Friendly message with HTTP 503, server keeps running |
| Wrong file type, empty file, oversized file | Rejected (415 / 400 / 413) |
| Corrupt, encrypted or scanned PDF | Moved to `data/failed/` with the reason |
| Same file uploaded twice | Detected by content hash and skipped |
| Same name, new content | Old version replaced |
| Question not covered by documents | "I could not find this..." with no sources |

## 8. Testing

```
python -m pytest -q                  # 13 tests, no Ollama needed
python -m tests.evaluate --offline   # retrieval check without Ollama
python -m tests.evaluate --live      # full accuracy + time report (Ollama must be running)
```

## 9. Known limits

- Scanned (image-only) PDFs have no text and are rejected; they would need OCR.
- Answer quality depends on the local model size. Small models can occasionally ignore the "use only the context" rule.
- The chat is a prototype for one user; there is no login.

## 10. Tools used

Python, FastAPI, Ollama, ChromaDB and n8n. LangChain / LlamaIndex were not used on purpose:
the pipeline is only about 300 lines, so writing it directly makes each RAG step visible and easy to explain in a viva.
