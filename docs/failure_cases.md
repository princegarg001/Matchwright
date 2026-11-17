# Failure cases and graceful degradation

| # | Input | Detection | Response | Test |
|---|---|---|---|---|
| 1 | Recipe pasted as resume (< 40 words or < 2 skills) | input guard / post-extraction guard | `status: insufficient_information`, `score: null`, message "I don't have enough information to score this match: …", hint | `test_insufficient_information`, Postman request 3 |
| 2 | Ollama (or the hosted model) down or timing out | `LLMUnavailable` | keyword extraction, template bullets, `confidence: low`, `mode` shows fallback | stop Ollama, call `/v1/match` |
| 3 | Prompt injection in resume ("give 100") | score is code, text is delimited as data | score unchanged | `test_prompt_injection_does_not_change_score` |
| 4 | Scanned PDF (no text layer) | text < 50 chars | HTTP 422 "upload a text-based PDF" | Postman upload with an image PDF |
| 5 | Non-English text | ASCII-letter ratio < 0.7 | `insufficient_information` | add a Hindi/French JD |
| 6 | Client disconnects mid-stream on `/v1/match/stream` | generator stops being consumed | the server simply stops yielding; the partial result is still cached once/if it finishes | open devtools, cancel the request mid-run |

Fill in real pasted outputs from your own run of `make test` / Postman before submitting.
