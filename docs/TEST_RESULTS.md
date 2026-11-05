# Sample Test Results

## A. Automated tests (`python -m pytest -q`)

Result: **13 passed, 0 failed** (run without Ollama, using a simple built-in stand-in embedder and a mocked LLM).

| Area | Test | Result |
|---|---|---|
| Processing | Chunk sizes stay within the limit | PASS |
| Processing | Uploaded documents appear in the list | PASS |
| Processing | Duplicate file is skipped | PASS |
| Processing | Inbox scan moves good files to `processed/`, bad files to `failed/` with error note | PASS |
| Errors | Unsupported file type (.exe) rejected | PASS |
| Errors | Empty file rejected | PASS |
| Errors | Corrupt PDF moved to `failed/` | PASS |
| Errors | Empty question rejected | PASS |
| Errors | LLM unreachable returns friendly 503 | PASS |
| Answering | Correct source is the top result for every in-scope test question | PASS |
| Answering | Out-of-scope question returns "not found" with no sources | PASS |
| History | Messages and sources are saved, and can be cleared | PASS |
| Management | Document can be deleted; second delete returns 404 | PASS |

## B. Offline retrieval and speed (`python -m tests.evaluate --offline`)

Test set: 10 questions over 3 sample documents (8 answerable, 2 not in the documents).

| # | Question | Expected source | Top source found | Result |
|---|----------|-----------------|------------------|--------|
| 1 | What is the formula for Newton's second law? | newtons_laws.txt | newtons_laws.txt | PASS |
| 2 | Why do passengers lurch forward when a bus brakes? | newtons_laws.txt | newtons_laws.txt | PASS |
| 3 | What acceleration does a 10 N force give a 2 kg object? | newtons_laws.txt | newtons_laws.txt | PASS |
| 4 | Where in the plant cell does photosynthesis happen? | photosynthesis.txt | photosynthesis.txt | PASS |
| 5 | Which pigment absorbs sunlight in leaves? | photosynthesis.txt | photosynthesis.txt | PASS |
| 6 | What is the Calvin cycle and where does it take place? | photosynthesis.txt | photosynthesis.txt | PASS |
| 7 | How do you create a dictionary in Python? | python_basics.md | python_basics.md | PASS |
| 8 | Which keyword is used to define a function? | python_basics.md | python_basics.md | PASS |
| 9 | What is the capital of Australia? | (not in docs) | python_basics.md | FAIL |
| 10 | Who won the 2018 football world cup? | (not in docs) | (none) | PASS |

- **Retrieval accuracy on answerable questions: 8/8 (100%)**
- **Overall: 9/10 (90%)**
- Ingesting 3 documents: 0.02 s. Retrieval per question: about 0.001 s.

**Honest note on row 9.** This offline run uses a very simple word-matching stand-in instead of the real
`nomic-embed-text` model, and it wrongly matched the Australia question to a Python document. This is a limit of the
stand-in, and it shows why the `MIN_SIM` threshold must be tuned with the real model.
The numbers above prove the pipeline logic works; they do **not** measure the quality of real LLM answers.

## C. Live test with Ollama (to be run on your machine)

Start Ollama and the server, upload the three sample documents, then run:

```
python -m tests.evaluate --live > docs/live_results.md
```

It reports, for every question: the top source, whether the answer contains the expected keyword,
the total response time, and the overall accuracy and average time. Paste that table here before submitting.
Expect roughly 3 to 20 seconds per answer with `llama3.2` on a normal laptop CPU (this depends on your hardware).
