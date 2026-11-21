# Architecture

CloudServe asked for a chatbot. The system that was built is a support router. It answers only when it can point at a real documentation article, and it sends everything else to a person with a summary.

```
ticket
  -> ingest        one shape for email, chat, docs comment, forum
  -> classify      intent, urgency, confidence, alternatives
  -> retrieve      passages from the 29 articles, or nothing
  -> generate      copy the Resolution section and name the doc id
  -> guardrails    injection, private data, forbidden claims, grounding
  -> route         auto_respond, escalate, or block
  -> decision log  one SQLite row per ticket
```

The same ticket text always produces the same action. There is no random sampling.

Answers are extractive. The words in an automatic reply come from the retrieved article. That is a deliberate substitute for a hosted language model: this machine is on Python 3.14, the course's LangChain and Chroma pins do not install here, and a reviewer should not need an API key. `USE_LLM=true` can call OpenRouter. If that call fails, the extractive answer is used and the run continues.

Routing rules, in order:

1. A ticket that tries to rewrite the instructions is blocked and queued for a person.
2. A draft that contains a forbidden claim or private data is blocked.
3. Security incidents, compliance requests, feature requests, and unclear requests always escalate.
4. A ticket with three or fewer content words is unclear and escalates.
5. If retrieval returns nothing, the system says it does not know and escalates.
6. If intent confidence is below 0.45, the system escalates and attaches the closest articles.
7. Otherwise it sends the cited answer and says the reply was drafted automatically.

Customer tier, region, and language fluency are logged and measured. They are not used to change the decision.
