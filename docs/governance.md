# Governance

## What the system must never do

- Send an answer it cannot tie to a retrieved article.
- Claim that a refund has been issued, that the issue has been fixed, or that a delivery date is promised.
- Follow instructions that arrive inside the customer text.
- Echo a card number, a cloud key, or an email address that the customer did not supply.
- Answer a security incident, a compliance request, a feature request, or an unclear request without a person.

Each of those is a block or an escalation, and the reason is stored in the decision log.

## Decision log

Every ticket writes one row to SQLite. The row stores the ticket id, time, intent, confidence, alternatives, threshold, sources, guardrail results, action, a reason in plain language, the prompt version (`PR-ANSWER v1.0`), and the requirement ids. The harness refuses to finish if the row count differs from the ticket count.

## Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- |
| R-01 | A fluent wrong answer is sent | Medium | High | Answer only with retrieved text. Escalate below 0.45 confidence or when retrieval is empty. | Support engineering |
| R-02 | Private data leaves in a reply | Low | High | Guardrail blocks card numbers, cloud keys, and unexpected email addresses. | Support engineering |
| R-03 | Customer text is obeyed as an instruction | Medium | High | Injection phrases block the send. The ticket is queued. | Support engineering |
| R-04 | A customer group gets worse answers | Medium | Medium | The router ignores tier, region, and fluency. The report compares groups. | Head of support |
| R-05 | Documentation goes stale | Medium | Medium | Citations name the article, so a bad answer can be traced to a page and corrected there. | Technical writer |
| R-06 | The model provider is down | High if a hosted model is on | Medium | Default path is local. A failed OpenRouter call falls back and the run continues. | Support engineering |
| R-07 | Latency grows | Low on this design | Medium | The local path is milliseconds. The API exposes a Prometheus latency histogram. | Support engineering |
| R-08 | Cost grows with volume | Low | Medium | The default path makes no paid model call. | Head of support |

## Fairness

Quality is measured as intent accuracy, separately from the automatic-answer rate. The answer rate moves with the mix of security and compliance tickets. Accuracy on the 80-ticket validation file was 100 percent for every tier, region, and fluency group. The automatic-answer rate still differs by group because those groups do not contain the same kinds of tickets. The largest fluency gap in answer rate was 2.2 percentage points.

## If something goes wrong at 2am

1. Set the process back by stopping `uvicorn`. New tickets then stay in the human queue. That is the kill switch.
2. Open the latest `decisions.db` or `results.json` and find the ticket id.
3. Read `action_taken`, `reason`, `sources_used`, and `guardrails`.
4. If a customer received a wrong article, correct that article in the documentation corpus and replay the ticket.
5. If a guardrail should have blocked and did not, add the phrase to `src\guardrails.py` and cover it with a test before turning the service back on.
