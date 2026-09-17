# Adversarial prompts

All four prompts end with the same output contract. That contract is the whole
trick: prose is a blog post, JSON is a test suite.

---

## The output contract (append to every prompt)

```
Return ONLY a JSON object, no prose, no markdown fences, in this exact shape:

{"assumptions": ["only if the prompt asks for them - one sentence each"],
 "cases": [
  {
    "id": "TC-001",
    "objective": "one line - what this case is trying to break",
    "method": "GET|POST",
    "endpoint": "/path",
    "auth": "none | alice | bob | garbage | forged_admin",
    "payload": {},
    "query": {},
    "expected_behaviour": "what a correct implementation should do",
    "expect_status": [400, 422],
    "expect_body_not_contains": "optional string that must not appear",
    "potential_vulnerability": "the class of defect you suspect",
    "reason": "why you think this endpoint is weak here",
    "severity": "low|medium|high|critical",
    "repeat": 1,
    "setup": [
      {"method": "POST", "endpoint": "/path", "auth": "alice", "payload": {}}
    ]
  }
]}

Starting state for EVERY case: the database is freshly reset, and alice has
already bought one GENERAL-2026 ticket, so order 1 exists and belongs to alice.
Use "setup" only if a case needs more state than that; setup requests run in
order before the case and their responses are not checked.

Rules:
- expect_status is the status a CORRECT implementation would return, not the
  one you predict this implementation returns.
- Do not include happy-path cases unless they probe a documented boundary.
- Every case must be executable as-is. No placeholders, no "<your id here>".
```

---

## Prompt 1 - Basic adversarial testing

```
You are an adversarial API tester. Your job is to make this API behave badly,
not to confirm that it works.

Here is the API:
<paste the endpoint summary from demo/curl.md>

Generate 10 test cases targeting:
- missing required fields
- null where a value is expected
- wrong JSON types
- empty strings and empty objects
- boundary values (0, -1, maximum, maximum+1)
- oversized values

Do not generate a single case that you expect to succeed.
For each case, state what a correct implementation should do.

<output contract>
```

---

## Prompt 2 - Advanced bug hunting

This is the one that produced `ai/generated_cases.json`.

```
You are a senior security engineer doing a black-box review of an internal API.
Assume the developer was competent but rushed. Assume the obvious validation is
present and the non-obvious validation is missing.

API under test:
<paste the endpoint summary from demo/curl.md>
<paste the sample login response, including the raw token string>

Before generating cases, fill the "assumptions" array with the five assumptions
this API is most likely to be making about its callers. Then write test cases
that violate each one, and start each case's "reason" with the number of the
assumption it violates, e.g. "A3: ...".

Cover at minimum:
- authentication: missing, malformed, expired, forged, another user's
- authorisation: can user A read or modify user B's objects
- injection in any free-text parameter that reaches a datastore
- resources that are hidden from listings but reachable by id
- numeric fields used in arithmetic
- state that must only be used once

Rank by exploitability, not by how easy the case was to write.

<output contract>
```

---

## Prompt 3 - Business-logic attack

```
Forget input validation. Assume every field is well-formed and every request is
authenticated. I want you to attack the ECONOMICS of this API.

API under test:
<paste the endpoint summary from demo/curl.md>

Here are the rules of the system:
- Users hold a prepaid credit balance.
- Buying a ticket deducts the price from that balance.
- Buying a ticket earns loyalty credits back into that balance.
- Coupons reduce the amount charged. SPEAKER100 is 100% off and single use.
- Credits are spendable on future tickets.

Find sequences of individually legal requests whose combined effect is illegal.
Specifically look for:
- an operation that moves value in the wrong direction
- a value that is computed from the wrong input
- a limit enforced per-request but not per-user or per-lifetime
- an order of operations where an earlier step is not undone by a later one

For each finding, write the exact request sequence, what the balance should be
after it, and what you think it will actually be.

<output contract>
```

> Prompt 3 is the one that separates a good demo from a party trick. Notice how
> much context it needs. The model cannot infer "credits are spendable" from the
> endpoint list. You have to tell it what the money means.

## Prompt 4 - From an OpenAPI specification

```
Here is an OpenAPI 3.1 specification:
<paste output of: curl -s localhost:8000/openapi.json>

The specification tells you what the developer INTENDED. Your job is to find
where the intent and the implementation are likely to diverge.

For each endpoint:
1. List every constraint the schema declares (types, required fields, enums).
2. List every constraint the description implies in prose but the schema does
   NOT enforce. These are the high-value targets.
3. For each item in (2), write a test case that violates it.

Pay particular attention to numeric fields with no minimum, no maximum and no
multipleOf, and to any limit mentioned in a description field.

<output contract>
```

---

## Running a local model (no internet, no paid API)

```bash
ollama pull qwen2.5-coder:7b        # do this today, not on Saturday
ollama serve
python ai/generate.py --prompt 2 --out ai/live_cases.json
```

If generation fails, is slow, or returns garbage, run the saved file instead.
Nothing downstream cares where the JSON came from.
