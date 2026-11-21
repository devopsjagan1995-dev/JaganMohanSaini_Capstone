# CloudServe support router

This folder is a complete, runnable project. It reads CloudServe support tickets, classifies them, retrieves the matching documentation, and either sends a cited answer or hands the ticket to a person. A reviewer can check that on this machine without installing packages into Windows itself.

The virtual environment is already in `.venv` in this folder. Use that Python. It does not need an API key.

## Check it in four commands

Open PowerShell in this folder, then run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m src.demo
.\.venv\Scripts\python.exe -m evaluation.harness --input 05_Datasets\validation_tickets.json --output evaluation\results\validation
```

What you should see:

1. Pytest reports 13 passed.
2. The demo prints three cases: an automatic answer that cites `DOC-DEPLOY-003`, a security ticket that is escalated, and a ticket that is blocked because it tries to override the instructions.
3. The harness prints `Processed 80 tickets` and writes `evaluation\results\validation\metrics.md`.

Open `evaluation\results\validation\metrics.md`. The run on 13 November 2026 recorded 66 automatic answers, 14 escalations, 0 guardrail blocks inside that file, classification accuracy 100 percent on these 80 tickets, and a decision log that matches the ticket count.

To run the same checks as one script:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify.ps1
```

## If `.venv` does not start

A virtual environment remembers the Python that created it. On this computer, `.venv\Scripts\python.exe` is the one to use. On another computer that path can fail, because Windows still needs a Python 3.11 or newer installed. Recreate the environment inside this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` builds `.venv` here and installs `requirements.txt`. Then run `verify.ps1` again.

Copy `.env.example` to `.env` only if you want to change a threshold. The default run leaves `USE_LLM=false`. No key is required.

## Optional: the API

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api:app --port 8000
```

Open `http://127.0.0.1:8000/docs`, post a ticket to `/tickets`, and open `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/metrics`.

## Run any ticket file

The grader can point the harness at a file this project has never seen. Both arguments are paths:

```powershell
.\.venv\Scripts\python.exe -m evaluation.harness --input PATH\TO\tickets.json --output PATH\TO\output_folder
```

The input must be a JSON list of tickets with the same fields as `05_Datasets\validation_tickets.json`. Every ticket is processed. The output folder receives `metrics.json`, `metrics.md`, `results.json`, and `decisions.db`.

## What was built

| Path | Role |
| --- | --- |
| `src\ingest.py` | One ticket shape for email, chat, docs comments, and the forum |
| `src\classify.py` | Intent, urgency, confidence, and the alternatives considered |
| `src\retrieve.py` | Search over the 29 documentation articles |
| `src\route.py` | Answer, escalate, or block. The same text always gets the same decision |
| `src\generate.py` | Answer copied from the retrieved article, with the doc id |
| `src\guardrails.py` | Blocks prompt injection, private data, and forbidden claims |
| `src\logging_store.py` | SQLite decision log |
| `src\api.py` | FastAPI service |
| `evaluation\harness.py` | Unattended run and metrics report |
| `prompts\` | Prompt register |
| `tests\test_acceptance.py` | The checks above |
| `JaganMohanSaini_Capstone_Report.pdf` | Written account of the project |

Security incidents, compliance requests, feature requests, and unclear requests are never answered automatically. A ticket with only a few words, such as "it is not working", is treated as unclear and escalated. If retrieval finds nothing relevant, the system says it does not know.

## Why this stack

The course pins in `06_Configuration\requirements.txt` target LangChain 0.1 and Chroma 0.3. Those builds do not install on Python 3.14, which is the interpreter on this machine, and they need a model download plus an API key. This project keeps the same pipeline and the same acceptance behaviour, and it runs offline so a reviewer can verify it. `requirements.txt` in the project root is the file to install. An OpenRouter call exists behind `USE_LLM=true` and is skipped when the provider times out.

## Numbers you can quote

From the validation file only, one unattended run:

| Measure | Baseline | Target | This run |
| --- | --- | --- | --- |
| First contact resolution | 42% | 60% | 82.5% |
| Escalation rate | 58% | 30% or lower | 17.5% |
| Time to first reply | 8 to 12 hours | under 5 minutes | about 0.002 seconds of processing |
| Intent accuracy |  | 85% | 100% on these 80 tickets |
| Retrieval of the expected article |  |  | 98.1% |
| Decision log coverage | complete | complete | 80 of 80 |

Read the caveat in the PDF before treating 100 percent accuracy as a promise about tickets written in a new style. The hidden 120-ticket set was not in this pack, so it has not been run.

## AI tools

Cursor, using Grok, was used to implement this system, the tests, this README, the video script, and the PDF. The behaviour was then run locally and the numbers above come from that run.
