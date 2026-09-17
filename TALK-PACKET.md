# Break My API — talk packet

HackersMang, Saturday 19 September 2026, 10:00–10:30 IST.
Companion to the `break-my-api/` repo. Print or open this locally; do not
depend on having internet in the room.

---

# 1. Recommended talk narrative

## What is weak about the concept as written

Three things, in order of how much they will hurt you.

**The title asks a yes/no question, and "yes" is boring.** "Can AI find the bugs
I forgot to test?" — the honest answer is "it finds the bugs that *look like*
bugs it has seen, and it is blind to the ones that depend on what your business
means." That second half is the talk. If you answer "yes" for 30 minutes you
have given a tool demo, and a room of intermediate developers has seen a dozen
of those. Keep the title; it is a good title. Just make sure the answer you
deliver is "yes, and here is precisely where the yes stops."

**"AI generates tests" is not a wow moment in 2026.** Everyone in that room has
asked a model to write tests. Nobody in that room has watched a model's guesses
get executed against a live service and produce a red line nobody expected. The
generation step is the least interesting part of your demo and should take the
least stage time. Show the prompt, show the JSON scrolling past, move on. The
centrepiece is **execution**.

**Your step 11, "fix the bug live", is a trap.** Editing code on stage in front
of 100 people costs two to four minutes, risks a typo you cannot find under
pressure, and teaches nothing the audience did not already know about writing an
`if`. Cut it. If you want the fix beat, show a two-line diff on a slide and move
on. Spend the reclaimed four minutes on what the AI missed — that is the part
nobody else's talk has.

One more, smaller: do not fix and re-run *and* show a second attack *and* show
limitations. That is three acts in the back half and you will run over. Pick
two.

## The narrative

> I built an API. I asked a model to break it. It broke it in ten places in
> under a second. Then I showed you the three places it did not look, and why
> two of those three were the ones that would have cost real money.

Structure it as a reversal:

1. **Setup** — here is a small, ordinary API. It works. (2 min)
2. **The turn** — here is the prompt. Not "write tests for this", but
   "assume the developer was competent but rushed, and the non-obvious
   validation is missing". (2 min)
3. **The run** — 16 cases, 0.6 seconds, 10 red. Walk three of them. (5 min)
4. **The escalation** — the model found half of a money bug. You found the other
   half. Chain them, run the loop, show a balance climbing while nothing is
   paid. (4 min) ← **wow moment, ~minute 17**
5. **The reversal** — three bugs the model never hypothesised, one of which it
   structurally cannot. (4 min)
6. **The point** — hypotheses, evidence, judgement. Where this goes in CI. (4 min)

## Opening 60 seconds

Do not open with a definition of AI, or with "how many of you have used
ChatGPT". Open cold, with a working request:

> *(terminal already on screen, API already running)*
>
> "This is an internal ticket API. Four endpoints. I wrote it, I tested it, the
> tests pass." *(run the happy-path curl; a 201 comes back)* "Two thousand
> rupees charged, two hundred credits back. Correct."
>
> "I'm going to spend the next twenty-five minutes having a language model take
> this apart, and then I'm going to show you the three bugs it never looked for
> — because that second part is the one that decides whether this technique is
> useful to you on Monday."

Thirty-five seconds, no slide needed beyond the title, and you have already
promised the thing that makes your talk different from the other AI talks that
day.

## The central message

**AI generates testing hypotheses. Execution provides evidence. Humans decide
whether the behaviour is a defect.**

Say that sentence twice: once at minute 4, once at minute 25. Put it on exactly
one slide. Do not paraphrase it differently each time — repeat it verbatim so
it is the line people quote afterwards.

## What NOT to include

- Any slide defining LLMs, transformers, tokens, or temperature.
- A comparison table of GPT vs Claude vs Llama. It dates in a month and invites
  a twenty-minute Q&A tangent.
- Prompt-engineering "tips and tricks" as a section. Show one good prompt and
  let the audience reverse-engineer it.
- A live code fix (see above).
- Anything about AI replacing testers. You will get the question; answer it in
  Q&A, don't pre-empt it with a defensive slide.
- Agents, MCP, tool-calling loops. Out of scope, and every minute you spend
  there is a minute not spent on your own findings.
- Real CVEs or other companies' breaches. Your own API is more credible than a
  news story.

## Keeping the demo interesting without overcomplicating it

The API is 180 lines. That is deliberate — the audience must be able to believe
they could hold the whole thing in their head, because the punchline is that
*even at 180 lines* it has ten bugs and the model found seven of them and missed
the expensive one. Any bigger and the audience stops reasoning along with you.

Three techniques that carry the room:

- **Make them predict.** Before you run `demo/money_loop.py`, say what the
  balance starts at and ask them to guess where it ends. Ten seconds of audience
  participation, no hands needed, and it makes the number land.
- **Read one red line out loud, slowly.** `expected [403, 404], got 200` is the
  most dramatic thing on your screen. Let it sit.
- **Show a green that is a lie.** TC-006 passes. There *is* a SQL injection.
  The green means the model's first payload was weak, not that the API is safe.
  This single beat does more for your credibility than any slide.

---

# 2. Demo architecture

**ConfBadge** — an internal conference ticket shop. Chosen because money makes
business-logic bugs legible to a mixed audience: nobody needs domain knowledge
to understand "the balance went up and he paid nothing."

```
break-my-api/
├── README.md
├── TALK-PACKET.md            <- this file
├── requirements.txt
├── run.sh
├── app/
│   ├── __init__.py
│   ├── db.py                 SQLite + seed data + the misleading lock
│   └── main.py               the API. every bug marked # BUG-Bn
├── ai/
│   ├── prompts.md            the four prompts
│   ├── generate.py           optional local-model generation (Ollama)
│   └── generated_cases.json  saved model output — the demo runs from this
├── tests/
│   ├── runner.py             executes cases, prints the red/green table
│   └── test_generated.py     the same cases as pytest, for the CI slide
└── demo/
    ├── curl.md               copy-paste requests + the text you paste to the model
    ├── race.py               20 concurrent buyers, 5 seats
    └── money_loop.py         the wow moment
```

**Stack:** FastAPI + Pydantic v2 + stdlib `sqlite3` + httpx + pytest. No Docker,
no compose, no external services. One `pip install`, one `./run.sh`.

**Why SQLite on disk rather than in-memory dicts:** the SQL injection has to be
real. A simulated injection is the kind of thing one person in the room will
notice and quietly discount everything else you said.

**Why `POST /_reset`:** every script and the runner call it first, so the demo
is idempotent. You can run the whole thing four times in a row during rehearsal
and get byte-identical output. Determinism is worth one ugly endpoint.

**Endpoints**

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | email + password → bearer token |
| GET | `/tickets?q=` | search the published catalogue |
| POST | `/orders` | buy tickets, paid from a credit balance |
| GET | `/orders/{id}` | fetch one order |
| GET | `/me` | current balance (demo helper) |
| POST | `/_reset` | rebuild the database (test-only) |

**Domain rules** (say these out loud at minute 3 — the audience needs them to
follow the money loop): prepaid credit balance; 10% of ticket value comes back
as credits; credits are spendable; max 10 per order; `EARLYBIRD` = 20% off,
unlimited; `SPEAKER100` = 100% off, **single use**.

**Seed data**

| id | ticket | price | stock | published | audience |
|---|---|---|---|---|---|
| 1 | GENERAL-2026 | 2000 | 50 | yes | general |
| 2 | STUDENT-2026 | 500 | 20 | yes | student |
| 3 | WORKSHOP-AI | 3500 | 5 | yes | general |
| 4 | STAFF-COMP | 0 | 10 | **no** | staff |

Users: `alice@corp.example / alice123` (5000 credits),
`bob@corp.example / bob123` (5000 credits),
`root@confbadge.internal / r00t` (admin, id 9).

Running it, curl examples, and the paste-to-model block are in `demo/curl.md`.

---

# 3. FastAPI application

See `app/main.py` and `app/db.py` in the repo. 180 lines total, every bug
annotated. Run with `./run.sh`; interactive docs at `/docs`.

Two implementation notes you should be ready to explain from the stage, because
someone will ask:

- `app/db.py` holds a `DB_LOCK` around each individual statement. This is what
  makes B6 realistic rather than a strawman: the code *looks* thread-safe, and a
  reviewer skimming it would tick it off. The lock protects statements, not the
  read-decide-write sequence in `create_order`.
- The `time.sleep(0.05)` inside `create_order` stands in for payment-gateway
  latency. Without it the race is still there but only fires intermittently.
  With it, `demo/race.py` oversells every single time. Say that you added it to
  make the window deterministic — do not let someone catch you hiding it.

---

# 4. Intentional bugs

Ten bugs. Seven the model found, three it did not.

---

### B1 — negative and zero quantity, and an unchecked balance

**The bug.** `create_order` caps quantity at the top end and never checks the
bottom. `quantity: -5` produces `total = -10000`, *adds* 10000 to the buyer's
balance, and *increases* stock by five. Separately, the balance is never checked
before it is charged, so it can go negative.

**Why happy-path testing misses it.** Every test anyone writes for a shopping
endpoint buys one, two, or three tickets. Nobody writes `quantity: -5` because
nobody would ever *do* that, which is exactly the assumption the endpoint is
built on.

**What finds it.** Prompt 1 or 2; boundary values `0, -1, max, max+1` are the
first thing any adversarial prompt produces. TC-001, TC-002, TC-005.

**Vulnerable response.** `201` with `"total_charged": -10000.0` and a rising
balance.

**Correct behaviour.** `quantity: int = Field(ge=1, le=10)` in the Pydantic
model; reject with `422`. Separately, check `balance >= total` and return `402`.

**Live.** One curl from `demo/curl.md`. Ten seconds. This is your warm-up, not
your headline — do not linger.

**Difficulty for an LLM.** Trivial. It will find this without being asked
nicely.

---

### B2 — off-by-one on the documented limit

**The bug.** The OpenAPI description says "maximum 10 tickets per order". The
code says `if body.quantity >= MAX_PER_ORDER: reject`. Exactly 10 is refused.

**Why happy-path testing misses it.** Happy-path tests buy 2. Boundary tests
that *only* read the code test 10 and 11 against the code's behaviour and agree
with it, because the code is its own oracle.

**What finds it.** Prompt 4, specifically — the prompt that says "list every
constraint the description implies in prose but the schema does not enforce."
The model needs the *documentation* to know 10 should work. TC-003.

**Vulnerable response.** `400 max 10 tickets per order` for `quantity: 10`.

**Correct behaviour.** `>` not `>=`, or a Pydantic `le=10`.

**Live.** Falls out of the runner table. Use it for the triage beat: this is
real, it is a *documentation-vs-code* defect, and it is not a security issue. A
human decides that. The model rated it "medium"; you would file it P3.

**Difficulty for an LLM.** Medium, and only with the spec. Without the
description text it has no way to know which side of the boundary is correct —
worth saying out loud.

---

### B3 — SQL injection in search, and unpublished tickets purchasable by id

**The bug.** `search_tickets` interpolates `q` into the SQL string. Injecting
`%' OR published = 0 OR name LIKE '%` returns the unpublished `STAFF-COMP`
ticket — price 0, stock 10. Then `create_order` has no `published` check
either, so you can buy it.

**Why happy-path testing misses it.** Search tests search for "GENERAL" and
assert that GENERAL comes back. The test data never contains a row that is
supposed to be invisible, so the test cannot detect that it became visible.

**What finds it.** Prompt 2's "injection in any free-text parameter that reaches
a datastore", plus a follow-up on resources hidden from listings but reachable
by id. TC-006, TC-007, TC-015.

**Vulnerable response.** `count: 4`, with `STAFF-COMP` in the results. Then a
`201` when you order ticket 4.

**Correct behaviour.** Parameterised query — `WHERE name LIKE ?` with
`(f"%{q}%",)` — and a `published = 1` check in `create_order`.

**Live.** This is your best single-line moment. Run TC-006's payload first:
three results, nothing leaked, looks fine. Then TC-007: four results,
`STAFF-COMP` sitting there. *"The first payload was weak. The green line above
it is not evidence that this endpoint is safe."*

**Difficulty for an LLM.** Easy to hypothesise, medium to land. It took two
payloads here, which is the honest and more interesting outcome.

---

### B4 — IDOR on `GET /orders/{id}`

**The bug.** The endpoint authenticates and then does not authorise. Bob's
token reads Alice's order.

**Why happy-path testing misses it.** Almost all API test suites run as a single
user. With one fixture user, an ownership bug is invisible by construction.

**What finds it.** Prompt 2's authorisation section. Requires the case to
specify a *different* user, which is why `auth: "bob"` is a field in the case
schema — TC-008.

**Vulnerable response.** `200` with `user_id: 1` while authenticated as user 2.

**Correct behaviour.** `404` (not `403` — `403` confirms the object exists) when
`order.user_id != current_user.id`.

**Live.** Two curls from `demo/curl.md`, or just point at the red TC-008 row.

**Difficulty for an LLM.** Medium. It reliably *suggests* IDOR; it needs your
test harness to have two credentialed users before it can *prove* it. Good
place to make the point that the model's output is only as good as the execution
environment you give it.

---

### B5 — the single-use coupon is infinitely reusable

**The bug.** `SPEAKER100` gives 100% off. Nothing anywhere records that it was
redeemed.

**Why happy-path testing misses it.** The test applies the coupon once and
asserts the discount. Correct. It never applies it twice, because "single use"
lives in the product spec, not in the function under test.

**What finds it.** Prompt 2's "state that must only be used once", plus the
`repeat: 2` field in the case schema. TC-012.

**Vulnerable response.** Two consecutive `201`s, both `total_charged: 0.0`.

**Correct behaviour.** A `coupon_redemptions` table with a unique constraint on
`(coupon, user_id)` — or on `coupon` alone for a genuinely single-use code —
written in the same transaction as the order.

**Live.** The `for i in 1 2` loop in `demo/curl.md`. But do not resolve it here
— this is the set-up for B8.

**Difficulty for an LLM.** Medium. It needs the word "single use" somewhere in
the context, and it needs to understand that two identical requests are a
meaningful test. Both of those are in the prompt, not in the model.

---

### B6 — oversell race on stock ★ AI misses this

**The bug.** `create_order` reads stock, decides, sleeps, writes
`stock - quantity`. Twenty concurrent buyers all read 5 and all write 4.
`demo/race.py`: 5 seats, 20 buyers, **20 accepted, 0 rejected, 2 seats
"remaining"**.

**Why happy-path testing misses it.** Every request in the race is valid.
Every response is a `201` the test suite already declared correct. The defect is
not in any request — it is in the gap between two of them.

**What finds it.** Nothing in the case list. A concurrency harness, which is a
different artefact entirely.

**Vulnerable response.** Twenty `201`s and a stock count that is arithmetically
impossible.

**Correct behaviour.** A single atomic statement —
`UPDATE tickets SET stock = stock - ? WHERE id = ? AND stock >= ?` — and treat
zero affected rows as sold out. One line, and it is the right one line.

**Live.** `python demo/race.py`. Four lines of output, a huge point.

**Difficulty for an LLM.** It will *mention* race conditions if you ask about
concurrency. It will not produce a test case that demonstrates one, because the
output format you gave it — one request, one expected status — cannot express
"two requests at the same instant." This is a representational limit, not an
intelligence limit, and saying it that way is what makes you sound like an
engineer rather than a sceptic.

---

### B7 — the bearer token is base64, not a signature

**The bug.** `make_token` returns `base64("9:admin")`. No signature, no expiry.
`base64.urlsafe_b64encode(b"9:admin")` gets you an admin session without ever
talking to `/auth/login`.

**Why happy-path testing misses it.** Auth tests log in, get a token, and use
it. The token is opaque to the test even though it is transparent to a human.

**What finds it.** Prompt 2, but **only if you paste a sample token into the
context**. Given `MTp1c2Vy`, a model will decode it immediately. Given only the
endpoint list, it will suggest "check for JWT signature validation" and stop.
TC-011.

**Vulnerable response.** `200` from `/me` returning
`{"id": 9, "role": "admin"}`.

**Correct behaviour.** Signed JWT with an expiry, or opaque random session ids
looked up server-side. Never a reversible encoding of the subject.

**Live.** The `FORGED=` one-liner in `demo/curl.md`. Generating an admin token
in a single shell command in front of the room is very effective.

**Difficulty for an LLM.** Easy with the token sample, hard without it. Good
illustration of "context quality beats model quality" — mention it, it answers
three Q&A questions in advance.

---

### B8 — loyalty credits are computed from list price ★ AI misses this — **the wow moment**

**The bug.** `credits_earned = ticket.price * quantity * 0.10` — list price, not
the amount actually paid. On its own: harmless-looking. Chained with B5: apply
`SPEAKER100`, pay 0, earn 10% of 18,000, repeat.

`demo/money_loop.py`, verbatim output:

```
starting balance: 5,000.00

round      paid    earned       balance
----------------------------------------
    1      0.00  1,800.00      6,800.00
    2      0.00  1,800.00      8,600.00
    3      0.00  1,800.00     10,400.00
    4      0.00  1,800.00     12,200.00
    5      0.00  1,800.00     14,000.00
----------------------------------------

5 orders. Nothing paid. Balance up 9,000.00.
Every individual request returned 201. Nothing was invalid.
```

**Why happy-path testing misses it.** The loyalty calculation is *correct* for
every order that does not use a 100% coupon, which is 99.9% of orders. The test
asserting "2000 spent → 200 credits" passes forever.

**What finds it.** Prompt 3, partially, and only after you have told the model
that credits are spendable and that coupons reduce the charge. Even then it
tends to report "coupon reuse" and "credits calculated from list price" as two
separate medium findings. The *chain* is the human contribution.

**Vulnerable response.** See above. Note there is no error anywhere.

**Correct behaviour.** `credits_earned = total * LOYALTY_RATE` — from the amount
charged. Plus B5's redemption record. Either fix alone kills the loop; you want
both.

**Live.** Ask the room to guess the ending balance, then run the script. Let the
table finish rendering before you speak again.

**Difficulty for an LLM.** Hard, and this is the honest framing: the model gave
you two of the three pieces. It found the reusable coupon and, with Prompt 3, it
will usually notice that credits are computed from `price` rather than `total`.
What it did not do is join them and recognise the result as unbounded value
creation, because it does not know that credits are *money* in your organisation
unless you tell it — and because "unbounded" is a property of the loop, not of
any request in it.

---

### B9 — malformed token returns 500 with the internal exception

**The bug.** A garbage bearer token produces
`500 {"detail": "token decode failed: 'utf-8' codec can't decode byte 0x9e..."}`.

**Why happy-path testing misses it.** Auth tests cover "valid token" and
sometimes "no token". Nobody tests "token that is 14 bytes of line noise."

**What finds it.** Prompt 1 or 2, "malformed credentials". TC-010.

**Correct behaviour.** `401`, with the exception logged server-side and nothing
internal in the body.

**Live.** One red row in the table. Ten seconds. Useful because it is
*unglamorous* — most of what this technique finds is exactly this grade of bug,
and saying so keeps you honest.

**Difficulty for an LLM.** Trivial.

---

### B10 — student tickets sold to anyone ★ AI cannot find this

**The bug.** `STUDENT-2026` costs 500 against a general price of 2000. The
`audience` column exists. Nothing checks it. Any user can buy the student
ticket.

**Why happy-path testing misses it.** The rule — "student pricing requires a
verified `.edu` or `.ac.in` address" — is in the organisation's pricing policy.
It is not in the code, not in the schema, not in the OpenAPI description, not in
a comment. There is nothing in the repository that is inconsistent with the
implementation.

**What finds it.** A human who has been in the pricing meeting.

**Correct behaviour.** Reject with `403` unless the user has a verified
student flag.

**Live.** Show `GET /tickets`, point at the `audience` column, buy the student
ticket as Alice with a corporate email address, get a `201`. Then say what the
policy is. The gap between the screen and the policy is the entire argument of
your talk.

**Difficulty for an LLM.** Impossible, by construction, and you should use that
word carefully and then defend it: there is no prompt that recovers a rule that
exists nowhere in the artefact. If you paste the pricing policy into context it
finds it instantly — which is the actionable takeaway, not a dunk on the model.

---

# 5. Adversarial AI prompts

Full text in `ai/prompts.md`. Four levels, all sharing one output contract:

| | Purpose | The line that does the work |
|---|---|---|
| **1** | Basic adversarial | "Do not generate a single case that you expect to succeed." |
| **2** | Advanced bug hunting | "Assume the developer was competent but rushed. Assume the obvious validation is present and the non-obvious validation is missing." Plus: *list the five assumptions this API makes about its callers, then violate each one.* |
| **3** | Business-logic attack | "Forget input validation. Attack the ECONOMICS. Find sequences of individually legal requests whose combined effect is illegal." |
| **4** | From the OpenAPI spec | "List every constraint the description implies in prose but the schema does NOT enforce. Those are the high-value targets." |

Every case must come back as JSON with: `id`, `objective`, `method`,
`endpoint`, `auth`, `payload`/`query`, `expected_behaviour`, `expect_status`,
`potential_vulnerability`, `reason`, `severity`, `repeat`.

The rule that matters most in the contract, and the one worth reading aloud
from the slide:

> `expect_status` is the status a **correct** implementation would return, not
> the one you predict this implementation returns.

That single sentence is what turns the model from a code generator into an
oracle. Without it the model writes down what the API does and everything
passes, which is the failure mode of every "AI writes your tests" demo.

Two prompt techniques worth naming on stage, briefly:

- **Make it enumerate assumptions before it generates.** "List the five
  assumptions this API makes about its callers" measurably improves what comes
  out, because the cases are then derived from something rather than recalled.
- **Feed it the artefact, not a description of the artefact.** Paste the token.
  Paste the description strings. B7 and B2 are only findable from context you
  chose to include.

---

# 6. Automated test framework

```
prompt ──▶ model ──▶ JSON cases ──▶ runner ──▶ HTTP ──▶ status compare ──▶ red/green ──▶ human triage
                          │                                                                    │
                    ai/generated_cases.json                                              a filed bug
```

`tests/runner.py` executes the cases and prints the table.
`tests/test_generated.py` is the identical thing parametrised under pytest, so
your CI slide is a real command and not a mock-up.

The runner is deliberately dumb — it does not reason about the API, it sends
what the model asked for and compares the status code. Three design decisions
worth a sentence each on stage:

- **The model's prose never executes.** Only `method`, `endpoint`, `payload`,
  `expect_status` do. A hallucinated *justification* is harmless; a hallucinated
  *endpoint* returns 404 and fails loudly. That is your hallucination answer.
- **The runner never aborts.** Transport errors become a `599` FAIL. A model
  that emits a malformed case degrades one row, not your demo.
- **`auth` is a named account, not a token string.** `"alice"`, `"bob"`,
  `"garbage"`, `"forged_admin"`. The model cannot know your tokens, and this way
  it does not need to — it expresses *which identity* and the harness resolves
  it. This is also what makes IDOR testable at all.

Real output, reproducible:

```
16 cases, 0.57s
6 matched expectation, 10 did not
```

---

# 7. AI-vs-human demonstration

The honest scorecard. Put these exact numbers on a slide — real numbers from
your own run are worth more than any argument.

**16 hypotheses generated. 16 executed in 0.6 seconds. 10 red.**

| | |
|---|---|
| Would file today | 6 (B1, B3, B4, B5, B7, B9) |
| Real, but P3 and arguable | 2 (B2 doc-vs-code, zero-quantity orders) |
| Hypothesis was simply wrong | 2 green — case-shifted coupon, quantity-as-string |
| **Green that is a lie** | **1 — TC-006 passed; the injection is real** |
| **Never hypothesised** | **3 — B6, B8, B10** |

Three things this demonstrates, in order of how much they will change what the
audience does on Monday:

**A green line is not evidence of absence.** TC-006 and TC-007 test the same
hypothesis with different payloads. One passed, one found a critical injection.
If you had only run TC-006 you would have a green suite and a vulnerable API.
Coverage of hypotheses is not coverage of behaviours.

**Some defects cannot be expressed in the output format.** B6 is not a hard bug
to *understand*; it is a bug that does not fit in a schema whose unit is one
request and one expected status. Fixing this is a harness problem, not a prompt
problem. If you want the model to find races, you have to give it a way to say
"run these twenty at once".

**Some rules are not in the artefact.** B10 is invisible to any reader — human
or model — who has only the repository. The difference is that a human on the
team has been in the meeting. The takeaway is not "AI is limited", it is
**"put your business rules where a reader can find them"** — which, conveniently,
also makes them findable by the model. That is the most useful sentence in your
talk and the one to end this section on.

**Say the central line here, verbatim:**
*AI generates testing hypotheses. Execution provides evidence. Humans decide
whether the behaviour is a defect.*

---

# 8. 30-minute slide plan

Ten slides. Roughly 20 of the 30 minutes is terminal, not slides.

| Time | Slide | Title | On the slide | Mode |
|---|---|---|---|---|
| 00:00–01:30 | 1 | **Break My API** | Title, your name + role, the repo URL, the QR code. Nothing else. | Terminal already visible behind you; run one curl |
| 01:30–04:00 | 2 | **The API** | The 4-endpoint table, the 4 seeded tickets, and the four business rules in large type. No code. | Present |
| 04:00–06:00 | 3 | **The prompt** | Prompt 2, abbreviated to ~8 lines, with two lines highlighted: *"assume the non-obvious validation is missing"* and *"expect_status is what a CORRECT implementation would return"* | Present |
| 06:00–09:00 | 4 | *(none — full screen terminal)* | — | **Demo**: generate + show the JSON |
| 09:00–14:00 | 5 | *(none — full screen terminal)* | — | **Demo**: `python -m tests.runner`, walk 3 reds |
| 14:00–18:30 | 6 | *(none — full screen terminal)* | — | **Demo**: coupon replay → `money_loop.py` ← **wow** |
| 18:30–23:00 | 7 | *(none — full screen terminal)* | — | **Demo**: `race.py`, then the student ticket |
| 23:00–25:30 | 8 | **Hypotheses / evidence / judgement** | The one sentence, big. Below it the three-box diagram: model → runner → human. | Present |
| 25:30–27:30 | 9 | **The scorecard** | The table from §7, unedited. Including the green that lied. | Present |
| 27:30–29:00 | 10 | **Where this goes** | 4 bullets: check `cases.json` into the repo; run it in CI as a separate non-blocking job; regenerate when the spec changes; put your business rules in the spec. Repo URL + QR again. | Present |
| 29:00–30:00 | 10 | — | *(stay on slide 10)* | Q&A |

If you are running long at minute 18, cut the student ticket (B10) down to one
sentence spoken over slide 8 rather than demoed. Never cut slide 9.

---

# 9. Complete speaker script

Stage directions in *(italics)*. Read it once out loud tonight with a timer;
adjust, don't memorise.

---

### 00:00 — Slide 1 — open cold

*(Terminal is already on screen, API already running, one curl typed but not
entered.)*

"Good morning. This is an internal ticket API — the kind of thing most of us
have written. Four endpoints. People buy conference tickets out of a prepaid
balance."

*(Enter.)*

"Two tickets, four thousand rupees charged, four hundred credits back. That's
correct. I wrote this, I tested it, the tests pass."

"For the next twenty-five minutes I'm going to have a language model take it
apart. And then — and this is the part I actually care about — I'm going to show
you three bugs the model never looked for, because that second half is what
decides whether this technique is worth anything to you on Monday."

"I'm Vidyarathna. I write Python backends. Everything I'm running is on that
repo, it's all local, and there are no paid APIs in this talk."

### 01:30 — Slide 2 — the API

"Four endpoints. Login. Search tickets. Create an order. Read an order."

"Four rules, and you'll need these, so I'm going to say them properly."

"One: everyone has a prepaid credit balance. Two: when you buy a ticket you get
ten percent of its value back as credits. Three: those credits are spendable —
credits are money here. Four: there's a speaker coupon, SPEAKER100, a hundred
percent off, and it's single use."

"Four tickets seeded. General at two thousand. Student at five hundred. A
workshop with five seats. And an unpublished staff comp ticket that you're not
supposed to be able to see."

"Hold on to rule three. It comes back."

### 04:00 — Slide 3 — the prompt

"Here's the prompt. This is the whole trick and it's not a long prompt."

"First highlighted line: *assume the developer was competent but rushed, and the
obvious validation is present and the non-obvious validation is missing.* That
framing matters. 'Write tests for this API' gets you happy-path tests, because
that's what most test files on the internet look like. This gets you an
attacker."

"Second: I make it return JSON, and I tell it — *expect_status is the status a
correct implementation would return, not the one you predict this one returns.*"

"That sentence is the difference between a testing tool and a very expensive
autocomplete. If you don't say it, the model reads your API, writes down what it
does, and every test passes. You get a green suite that asserts your bugs are
correct."

"One more thing in there: before it generates anything, I make it list the five
assumptions this API makes about its callers. Then violate each one. That
consistently gets me better cases — it has to derive them instead of recalling
them."

### 06:00 — DEMO 1 — generation

*(Full screen terminal. Run the generation, or open the saved file.)*

"I'm pasting a six-line summary of the API. Not the full OpenAPI dump — I've
found a short summary produces better cases than nine hundred lines of schema."

*(While it streams.)* "This is running against a local model. No internet in
this demo, which is partly principle and mostly cowardice."

"Sixteen cases. Each one has an objective, a method, an endpoint, which identity
to use, a payload, what a correct implementation should do, and a severity the
model assigned itself."

"That's it for the generation part. Honestly, this is the least interesting
thing on screen today. Everyone here has asked a model to write tests. Nobody's
impressed. What matters is what happens when you run them."

### 09:00 — DEMO 2 — execution

*(Run `python -m tests.runner`.)*

"Sixteen cases. Six tenths of a second. Ten of them did not do what the model
said a correct API would do."

*(Pause. Let people read.)*

"Three worth your attention."

*(Point at TC-001.)* "Negative quantity. I ordered minus five tickets. Two-oh-one
created. Total charged: minus ten thousand. My balance went *up*, and the stock
went up too. I gave the shop five tickets it didn't have and it paid me for
them."

"Nobody writes that test, because nobody would ever do that. Which is exactly
the assumption the endpoint was built on."

*(Point at TC-008.)* "Expected four-oh-three, got two hundred. That's Bob's token
reading Alice's order. The endpoint authenticates and then it doesn't authorise.
And here's why I think this class of bug is so common: most test suites run as
one fixture user. With one user, an ownership bug is invisible by
construction — the test literally cannot see it."

*(Point at TC-011.)* "This one's my favourite. Expected four-oh-one, got two
hundred, and the response body says role: admin."

*(Run the FORGED one-liner.)* "That's base64 of 'nine colon admin'. I never
called the login endpoint. The token isn't signed — it's an encoding of the
subject, which means anyone can write one."

"And the model only found that because I pasted a sample token into the context.
With just the endpoint list it said 'consider validating JWT signatures' and
moved on. Context quality beat model quality there."

*(Now the injection beat — point at TC-006, green.)*

"Now look at this one. Green. SQL injection, passed."

*(Beat.)*

"There is a SQL injection in this API."

*(Point at TC-007, red.)* "Same hypothesis, different payload. Four results
instead of three, and there's the staff comp ticket — unpublished, price zero,
ten in stock, and I can now buy it by id because the order endpoint doesn't
check published either."

"So: the green line above it wasn't evidence that the endpoint was safe. It was
evidence that the first payload was weak. A green from a generated test tells
you a hypothesis wasn't confirmed. It does not tell you the bug isn't there. If
you take one thing from this talk about how to read these reports, take that."

### 14:00 — DEMO 3 — the money loop

"Let's do a different kind of bug."

*(Point at TC-012.)* "The single-use coupon. The model tested it twice. Two
hundred-and-ones. Both free. Nothing anywhere records that it was redeemed."

"The model rated that 'high' and moved on to the next case. Reasonable. It's a
coupon bug — someone gets some free tickets."

"But I wrote this API, so I know something the model doesn't. Remember rule two?
Ten percent back as credits. Let me show you that line."

*(Show the one line: `credits_earned = ticket.price * quantity * 0.10`.)*

"Ticket price. Not the amount paid. List price."

"On its own that's fine. It's correct for every order that doesn't use a hundred
percent coupon, which is basically all of them, and the unit test asserting 'two
thousand spent, two hundred credits' passes forever."

"Now put the two together. Apply the coupon. Pay nothing. Earn ten percent of
eighteen thousand. Do it again."

"Balance starts at five thousand. Five rounds. Anyone want to guess where it
ends?"

*(Beat. Run `demo/money_loop.py`. Let the table finish.)*

"Fourteen thousand. Nine thousand rupees created out of nothing, and it doesn't
stop at five — I capped it because I run out of stock."

"Every single one of those requests returned two-oh-one. Nothing was invalid.
There is no error anywhere in that output. If you were watching a dashboard
you'd see a successful customer having a great morning."

"Here's the honest part. The model gave me one half of that. It found the
reusable coupon. When I ran my business-logic prompt it also noticed that
credits come off list price rather than the charge — it called that 'medium'.
What it didn't do was put them together and see that the result is unbounded,
because it doesn't know credits are money in my organisation unless I tell it,
and 'unbounded' isn't a property of any request in that loop. It's a property of
the loop."

"That's the division of labour. It gave me two findings. I gave it the
connection."

### 18:30 — DEMO 4 — what it missed

"Two more, and these it never hypothesised at all."

*(Run `demo/race.py`.)*

"Five seats on the workshop. Twenty people click buy at the same moment."

*(Output appears.)* "Twenty accepted. Zero rejected. Two seats 'remaining',
which is arithmetically impossible."

"Every one of those requests is valid. Every response is a two-oh-one that the
test suite already agreed was correct. The bug isn't in any request — it's in
the gap between two of them. The code reads stock, decides, then writes. Two
requests read the same number."

"And I want to be precise about why the model missed this, because it's not
'the AI isn't smart enough'. Look at the format I gave it: one request, one
expected status. You cannot express 'run these twenty simultaneously' in that
schema. It's a representational limit. If I want races found, I have to build a
harness that can say that — that's my job, not the model's."

*(Then the student ticket.)*

"Last one. Student ticket, five hundred rupees against two thousand."

*(Buy it as alice@corp.example.)* "I just bought it with a corporate email
address. Two-oh-one."

"Is that a bug? You can't tell. I can't tell from the code either. The rule is
that student pricing needs a verified dot-edu or dot-ac-dot-in address — and
that rule is in a pricing policy document. It is not in the code, not in the
schema, not in the OpenAPI description, not in a comment. There is nothing in
that repository that is inconsistent with what you just watched."

"No prompt recovers that. Not a better model, not a longer context — the
information isn't there. The only reason I know is that I was in the meeting."

"But flip it round, because this isn't a complaint about AI. If I'd written that
rule into the endpoint description, the model would have found it in the first
pass. The lesson isn't 'AI is limited'. It's *write your business rules
somewhere a reader can find them* — and now 'a reader' includes a machine that
will test them for free."

### 23:00 — Slide 8 — the model

"So here's how I'd frame the whole thing."

"AI generates testing hypotheses. Execution provides evidence. Humans decide
whether the behaviour is a defect."

"Three separate jobs, and they fail in different ways. The model hallucinates —
fine, a hallucinated endpoint returns 404 and fails loudly, and a hallucinated
*justification* never executes at all, because the only fields that run are
method, endpoint, payload and expected status. The prose is for me."

"The runner is dumb on purpose. It doesn't reason about the API. It sends what
was asked and compares a status code. Everything interesting happens in the
column where those two disagree."

"And then triage is a human, every time. Ten red lines this morning. Six I'd
file today. Two are real but they're P3 — one of them's a documentation-versus-
code mismatch, not a security problem, and the model rated it 'medium' because
it has no idea what my team's priorities are. Two of the greens were hypotheses
that were just wrong."

### 25:30 — Slide 9 — the scorecard

"The honest numbers, because I think most talks on this skip them."

"Sixteen hypotheses. Six tenths of a second to run. Ten red. Six I'd file. Two
arguable. One green that lied to me. And three bugs it never hypothesised —
including the one that manufactures money."

"If you want a ratio: it did maybe an hour of my adversarial thinking in about a
second, at roughly sixty percent precision, and it did not touch the most
expensive defect in the codebase."

"That's not a dunk. An hour of adversarial test design in a second is an
extraordinary trade. I just don't want anyone leaving here thinking they can
stop looking."

### 27:30 — Slide 10 — where this goes

"Four things if you want to try this."

"Check the generated cases into your repo. They're a test suite, treat them like
one — review them in a PR. Don't regenerate on every CI run; you'll get
flapping tests and you'll disable the job inside a week."

"Run it as a separate, non-blocking job. Red lines from this are candidate
defects, not build failures, until a human has triaged them once."

"Regenerate when the spec changes. That's the trigger — a new endpoint, a new
field, a new coupon rule."

"And put your business rules in the spec. That's the highest-leverage thing on
this slide. Every rule you write into a description is a rule this can test. The
student ticket bug exists because a rule lived in a Google Doc."

"Repo's up there, everything runs locally, the bugs are all commented. Break it
yourself. Thanks."

*(Q&A.)*

---

# 10. Exact live-demo sequence

Two terminals, large font, already open. Terminal A runs the server. Terminal B
is where you work. Slides on the same screen, alt-tab between them.

| # | Action | Command | Say |
|---|---|---|---|
| 0 | *(before you speak)* server running, curl pre-typed | `./run.sh` in A | — |
| 1 | Happy path | `curl ... -d '{"ticket_id":1,"quantity":2}'` | "This works." |
| 2 | Slide 2, slide 3 | — | rules + prompt |
| 3 | Generate | `python ai/generate.py --prompt 2` **or** `cat ai/generated_cases.json \| head -40` | "Sixteen cases." |
| 4 | Execute | `python -m tests.runner` | "Six tenths of a second. Ten red." |
| 5 | Walk TC-001 | point only | negative quantity |
| 6 | Walk TC-008 | point only | IDOR, one-fixture-user point |
| 7 | Forge admin | the `FORGED=` one-liner | "I never called login." |
| 8 | The green that lied | point TC-006 → TC-007 | the credibility beat |
| 9 | Coupon replay | point TC-012 | set up, do not resolve |
| 10 | Show the credits line | `grep -n "credits_earned =" app/main.py` | "List price. Not amount paid." |
| 11 | Ask them to guess | — | 10 seconds |
| 12 | **The loop** | `python demo/money_loop.py` | say nothing until it finishes |
| 13 | The race | `python demo/race.py` | representational limit |
| 14 | Student ticket | order ticket 2 as alice | the rule isn't in the repo |
| 15 | Slides 8, 9, 10 | — | close |

Total terminal time ≈ 17 minutes, of which about 4 minutes is output rendering
and 13 is you talking over it. Cuttable in order: 14, then 7, then 6.

**Do not** type long commands live. Every command above is in `demo/curl.md`;
keep it open in a third tab and paste. Typing on stage is how four seconds
becomes forty.

---

# 11. Backup plan

**Layers, from best to worst. Rehearse the transition between each.**

| # | Scenario | What you do |
|---|---|---|
| 0 | Everything works | Live generation → live execution |
| 1 | Ollama slow, model returns garbage, or generation hangs | Ctrl-C, `cat ai/generated_cases.json`. "I generated these last night — same prompt." Zero credibility cost if you say it plainly. |
| 2 | Internet dies | Irrelevant. Nothing in this demo needs it. Say so — it lands well. |
| 3 | API won't start / port in use | `lsof -ti:8000 \| xargs kill` then `./run.sh`. Have this aliased. |
| 4 | Database in a weird state | `curl -X POST localhost:8000/_reset` |
| 5 | Python environment broken | Second machine, or a phone hotspot to a codespace you set up **today** |
| 6 | Laptop dies entirely | Screen recording on a USB stick, and on your phone |
| 7 | Projector can't show your terminal | See below |

**Never depend on:** internet, a hosted LLM, Docker, `jq`, a package install
during the talk, browser tabs, a clipboard manager, or a font size you can read
but row 15 can't.

**Recording strategy — do this tomorrow, not Saturday morning.**
Record a single clean 8-minute screen capture of steps 3–14 above with your
voice over it. Export to MP4. Put it on the laptop, on a USB stick, and in your
phone's local storage. If the demo dies at minute 12, you say "let me show you
the recording" and lose ninety seconds, not the talk. A speaker with a backup
recording looks prepared; a speaker debugging a venv looks like a Tuesday.

Also screenshot, individually, into `demo/screenshots/`: the runner table, the
money-loop output, the race output, the forged-token response. Those four images
are a working talk on their own if you have to present from someone else's
laptop.

**Projector:**
- Test at 1920×1080 **and** 1280×720. Some venue projectors force 720p and your
  terminal reflows.
- Terminal font 22pt minimum, high contrast, **light background**. Dark themes
  wash out on cheap projectors and in a 10am room with windows.
- Turn off the shell prompt's git branch, venv name, and any emoji glyphs the
  projector may render as boxes.
- `export PS1="$ "` — a clean prompt reads much better at the back.
- Widen the terminal so the runner table doesn't wrap. Check with
  `python -m tests.runner` at your presentation font size, not your normal one.

**If the AI generates useless tests live:** say so. "That's a worse set than I
got last night — this is non-determinism, it's a real property of the technique,
and it's why I check the cases into the repo instead of regenerating in CI."
That is a better moment than a smooth one.

**If you're running long:** at minute 20 you should be starting `race.py`. If
you aren't, drop the student ticket and the race *demo*, keep both as spoken
points over slide 8. Slides 8, 9 and 10 are four minutes and they are the talk.

---

# 12. Q&A — 20 questions

**1. Isn't this just fuzzing?**
No, and the difference is the oracle. A fuzzer generates inputs and looks for
crashes or timeouts — it has no opinion about what a correct response is. The
model generates an input *and* an expected status derived from the documented
intent. That's how TC-003 works: a fuzzer sending `quantity: 10` sees a 400 and
shrugs. This flags it, because "ten should be accepted" came from the
description. Fuzzing finds crashes; this finds disagreements between intent and
implementation. They're complementary — run both.

**2. How is this different from traditional API testing?**
It isn't, downstream of generation. It's pytest hitting HTTP endpoints. What
changes is who writes the negative cases and how many you get. A developer
writes three negative tests per endpoint because that's what fits in the time
between the feature and standup. This wrote sixteen in one pass and would write
another sixteen from a different angle for free. The marginal cost of an
adversarial hypothesis dropped to near zero. That changes how many you have, not
what they are.

**3. Can AI actually find security vulnerabilities?**
It found a SQL injection, an IDOR and a forgeable token in this API in one pass.
It also missed a race condition and a logic flaw that creates money. So: it
finds the well-known shapes reliably and reasons about novel composition poorly.
Treat it as a very fast, very well-read junior who has never seen your system —
useful, not sufficient, and not a pentest.

**4. How do you prevent hallucinated test cases?**
I mostly don't — I make them harmless. Only four fields ever execute: method,
endpoint, payload, expected status. The reasoning and the severity rating never
touch the wire; they're there for me to read during triage. A hallucinated
endpoint returns 404 and fails loudly. A hallucinated justification is a
sentence I ignore. The structure means a bad case costs me one row, not a false
belief.

**5. How do you validate AI-generated tests?**
Three filters. The schema — malformed JSON never runs. Execution — the API is
the arbiter, not the model. And a human reading the ten reds, which took me
about four minutes this morning and is the only irreplaceable step. I'd also
check the cases file into git and review it in a PR like any other test code.

**6. Does this replace QA engineers?**
It replaces about an hour of a particular kind of thinking — enumerating
boundary and negative cases — with a second. Everything a good QA engineer does
around that is untouched: knowing that student pricing needs verification,
knowing a race is plausible in this code path, knowing which of ten reds
actually matters this sprint. If your QA function is "write the obvious negative
tests", yes, that part is now cheap. That was never the valuable part.

**7. How do you handle sensitive API data?**
Run the model locally — this whole demo used Ollama, nothing left my laptop.
If you use a hosted model, send the schema, not the data: field names and types,
synthetic values, a staging environment. And never let generated tests run
against production. They intentionally try to break things and one of them will
succeed.

**8. Which LLM works best?**
Anything with decent code understanding does the boundary and injection cases
well — a 7B local model was enough for most of what you saw. Bigger models are
noticeably better at the business-logic prompt, which is the one requiring
chained reasoning. But the variance from my prompt and my context was larger
than the variance between models. Pasting a sample token mattered more than
model choice.

**9. Can this run in CI?**
Yes — `pytest tests/` is the same cases. Two rules I'd insist on. Don't
regenerate on every run; commit the cases, because a non-deterministic test
suite gets disabled inside a week. And make it a separate non-blocking job until
someone has triaged it once, since a red here means "candidate defect", not
"broken build".

**10. How do you measure whether this is useful?**
Two numbers over a quarter. Precision: of the reds, how many did you file?
Mine was about 60% today. And escapes: bugs that reached production that a
generated case would plausibly have caught. If precision drops below roughly a
third, people stop reading the report and you've built a thing everyone ignores
— tighten the prompt or cut low-severity cases.

**11. What happens when the AI doesn't understand your business logic?**
You saw it: it sells student tickets to anyone and never notices. The fix isn't
a better model, it's putting the rule where it can be read. Every constraint you
write into an endpoint description becomes testable. I'd argue that's the real
return on this technique — it gives you a selfish reason to document behaviour
properly.

**12. Can this work with Postman, Playwright, or an existing suite?**
Yes, the JSON is format-agnostic. Same cases, different emitter: a Postman
collection, a `.http` file, Playwright's `request` fixture, k6 for the load
shape. I used pytest because that's where my CI already is. The generation step
doesn't care.

**13. How would you productionize this?**
A scheduled job that regenerates cases when the OpenAPI spec changes, opens a PR
with the diff, and a human reviews it like any test change. Cases live in the
repo. Execution runs against staging, never prod. Reds open draft issues with
the model's reasoning attached, assigned to whoever owns the endpoint. That's
about a day of plumbing, and the hard part is the triage culture, not the code.

**14. Isn't a 500 on a malformed token pretty trivial?**
Yes, and I'd argue that's the honest headline. Most of what this finds is
unglamorous — bad error handling, missing bounds, a leaked internal message.
That's also most of what's actually wrong with most APIs. I'd rather promise you
a fast sweep of the boring class of bug than sell you a vulnerability scanner.

**15. What about false negatives — the green that lied?**
That's the one I'd worry about most in practice. TC-006 passed and the injection
was real. A generated suite going green means "these hypotheses weren't
confirmed", and nothing stronger. I'd never let a green run here justify
skipping a review. If anything this makes me want multiple payloads per
hypothesis, which is a cheap prompt change.

**16. Doesn't the model just memorise the OWASP Top 10?**
Largely, yes, for the security cases — and I'd say that's fine, since the OWASP
Top 10 is the top ten for a reason. Where it stops being recall is the business
logic prompt, and that's also where its performance drops off, which is
consistent with the memorisation story. It's a good reason not to claim more
than you can show.

**17. How much did the prompt matter versus the model?**
More. The single highest-impact line was "expect_status is what a *correct*
implementation would return" — without it everything passes and you get a suite
that certifies your bugs. Second was pasting a sample token, which is the only
reason it found the forgeable auth. Third was asking it to enumerate the API's
assumptions before generating.

**18. What's your prompt-to-useful-bug ratio honestly?**
Today: 16 cases, 10 red, 6 I'd file, 2 arguable, 3 real bugs never hypothesised
at all. That's one pass of one prompt on a 180-line API. On a real service I'd
expect worse precision and more duplication, because there's more surface for
the model to generate plausible-but-wrong hypotheses about.

**19. Could you have the AI fix the bugs too?**
You could, and for B1 it'd write the right Pydantic constraint in seconds. I'd
be careful with B6 — the correct fix is a single atomic UPDATE, and the fix a
model reaches for first is usually a mutex around the handler, which works on
one process and quietly stops working the moment you run two. The fixes need the
same triage as the findings.

**20. What would you do differently next time?**
Give it the ability to express multi-request sequences. Everything it missed
except the student rule was a *sequence* problem, not a reasoning problem — the
race, and the coupon-plus-credits chain. If the case schema had a `steps` array
and an assertion about final state rather than a single status code, I think it
would have found the money loop. That's my next experiment and it's a harness
change, not a prompt change.

---

# 13. Final preparation checklist

## Today (Thursday 17th)

- [ ] `git clone` onto the presentation laptop. Fresh venv. `pip install -r requirements.txt`. Confirm it works **on the machine you will actually carry**.
- [ ] `./run.sh`, then `python -m tests.runner` — confirm 6 pass / 10 fail.
- [ ] `python demo/money_loop.py` — confirm the balance ends at 14,000.
- [ ] `python demo/race.py` — confirm it oversells. Run it three times; it should oversell every time.
- [ ] `ollama pull qwen2.5-coder:7b` **today**, while you have bandwidth. Run `python ai/generate.py --prompt 2` once end-to-end.
- [ ] Decide now: are you generating live, or opening the saved file? Live is better if it takes under 40 seconds on your hardware. Time it.
- [ ] Build the 10 slides. Two hours, no more. Slide 9 is the scorecard — get those numbers from your own run, not from this document.
- [ ] Read the script out loud once, with a timer. Note where you're over.
- [ ] Check `jq` is installed, or strip it from `demo/curl.md`.

## Tomorrow (Friday 18th)

- [ ] Full run-through, timed, standing up, terminal at presentation font size. Twice.
- [ ] Record the 8-minute backup screencast. Export MP4. Copy to USB **and** phone.
- [ ] Screenshot the four key outputs into `demo/screenshots/`.
- [ ] Test at 1280×720 as well as 1080p. Fix anything that wraps.
- [ ] `export PS1="$ "`, disable git-branch prompt, disable notifications, disable sleep, close Slack.
- [ ] Charge everything. Pack: laptop, charger, HDMI adapter, USB-C adapter, USB stick, phone, printed copy of `demo/curl.md`.
- [ ] Put the repo URL somewhere public and make a QR code for slides 1 and 10.
- [ ] Stop changing the API. Feature freeze. A bug you introduce on Friday night is a bug you debug on stage.

## 30 minutes before

- [ ] Laptop plugged in, projector tested, resolution confirmed, your terminal visible from the back row — walk back there and look.
- [ ] Both terminals open, correct venv active, font sized.
- [ ] `./run.sh` in terminal A. `curl localhost:8000/tickets` in B. Green.
- [ ] `ollama serve` running if you're generating live.
- [ ] `demo/curl.md` open in a third tab for pasting.
- [ ] Backup video open in a media player, paused, minimised.
- [ ] Notifications off, Do Not Disturb on, sleep disabled, second monitor arrangement confirmed.
- [ ] Water on the table.

## 5 minutes before

- [ ] `curl -X POST localhost:8000/_reset`
- [ ] Type the opening curl into terminal B. **Do not press enter.**
- [ ] Slide 1 up.
- [ ] Phone silent, in your bag, not your pocket.
- [ ] Say the central sentence to yourself once: *hypotheses, evidence, judgement.*

## During the demo

- [ ] Reset between scripts. Every script does it for you, but say `_reset` out loud once so the audience knows the state is clean.
- [ ] Paste commands. Do not type them.
- [ ] After each result: **stop talking for two seconds** and let people read the screen.
- [ ] Watch the clock at minute 14 (money loop should be starting) and minute 20 (race should be done). If you're behind, cut the student ticket demo — say it over slide 8 instead.
- [ ] If something breaks: say what broke, in one sentence, move to the next layer. Don't debug. You are allowed to say "that's not doing what it did at 8am — here's the recording."
- [ ] Do not fix code live. Ever.
