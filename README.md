# CloudServe support router

This folder is a complete, runnable project. It reads CloudServe support tickets, classifies them, retrieves the matching documentation, and either sends a cited answer or hands the ticket to a person. A reviewer can check that on this machine without installing packages into Windows itself.

Use the Python in `.venv` in this folder. It does not need an API key. If `.venv` is missing, or `.\.venv\Scripts\python.exe` will not start, create it with the steps below before the checks. Windows must already have Python 3.11 or newer. This machine has Python 3.14, and `setup.ps1` uses the `py -3` launcher.

## Bring it to a working run

Open PowerShell in this folder.

1. Create the environment and install the packages, if `.venv` is not already here:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

`setup.ps1` creates `.venv` in this folder and installs `requirements.txt`. If `.venv` is already present and can import the packages, the script leaves it as it is.

2. Run the tests, the demo, and the 80-ticket file:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify.ps1
```

`verify.ps1` runs `setup.ps1` first when `.venv` is missing, then the three checks below.

## Check it in three commands

When `.venv` already starts, open PowerShell in this folder and run:

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

Copy `.env.example` to `.env` only if you want to change a threshold. The default run leaves `USE_LLM=false`. No key is required. A virtual environment remembers the Python that created it, so a copy of `.venv` from another computer can fail. Delete that folder and run `setup.ps1` again.

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

## What each file does

| Path | What it does |
| --- | --- |
| `src\ingest.py` | Turns an email, chat, docs comment, or forum post into one ticket shape |
| `src\classify.py` | Names the intent and urgency, with a confidence and the other intents considered |
| `src\retrieve.py` | Searches the 29 articles and returns a real passage, or nothing |
| `src\generate.py` | Copies the resolution steps from the chosen article and adds the document id |
| `src\guardrails.py` | Stops a reply that tries to override the instructions, leaks private data, or makes a forbidden claim |
| `src\route.py` | Chooses answer, escalate, or block. The same text always gets the same choice |
| `src\logging_store.py` | Writes one SQLite row for every ticket |
| `src\pipeline.py` | Runs those steps in order for one ticket |
| `src\demo.py` | Prints the three cases: a cited answer, an escalation, and a block |
| `src\api.py` | Accepts one ticket at `POST /tickets`. `GET /health` says the process is up. `GET /metrics` is a Prometheus counter, not the business table |
| `evaluation\harness.py` | Processes a whole ticket file and writes the results |
| `evaluation\metrics.py` | Calculates the rates in the table below |
| `evaluation\results\validation\metrics.md` | The place to read those rates after a run |
| `05_Datasets\` | The 500 development tickets, the 80 validation tickets, and the 29 articles |
| `prompts\` | The prompt text, used only if a hosted model is switched on |
| `tests\test_acceptance.py` | The 13 checks |
| `setup.ps1` | Creates `.venv` and installs the packages |
| `verify.ps1` | Creates `.venv` if needed, then runs the three checks |
| `docs\architecture.md` | How the seven steps fit together |
| `docs\governance.md` | Risks, the decision log, fairness, and what to do if a reply is wrong |
| `monitoring\` | A Prometheus config and a Grafana dashboard file. Nothing in this folder opens a window |
| `JaganMohanSaini_Capstone_Report.pdf` | The written account, including the same numbers |

Security incidents, compliance requests, feature requests, and unclear requests are never answered automatically. A ticket with only a few words, such as "it is not working", is treated as unclear and escalated. If retrieval finds nothing relevant, the system says it does not know.

## Why this stack

The course pins in `06_Configuration\requirements.txt` target LangChain 0.1 and Chroma 0.3. Those builds do not install on Python 3.14, which is the interpreter on this machine, and they need a model download plus an API key. This project keeps the same pipeline and the same acceptance behaviour, and it runs offline so a reviewer can verify it. `requirements.txt` in the project root is the file to install. An OpenRouter call exists behind `USE_LLM=true` and is skipped when the provider times out.

## Numbers you can quote

There is no web page for these figures. The project has no HTML screens. The numbers are written into `evaluation\results\validation\metrics.md` when the harness finishes, and the same table is copied here and in the PDF. Open that markdown file to see them. `http://127.0.0.1:8000/metrics` does not show this table. That address is a machine counter for request latency, for a monitoring tool, and it stays empty of business rates until tickets are posted to the API.

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
