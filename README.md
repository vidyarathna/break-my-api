# Break My API

Demo repo for *Break My API: Can AI Find the Bugs I Forgot to Test?*
HackersMang, 19 September 2026.

`app/` is a small, deliberately broken FastAPI service. `ai/` holds the
adversarial prompts and the test cases a model produced from them. `tests/`
executes those cases. `demo/` holds the two scripts that show what the model
did not produce.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run.sh                      # http://127.0.0.1:8000  (docs at /docs)
```

In a second terminal:

```bash
python -m tests.runner        # execute the AI-generated cases
python -m tests.runner TC-008 # one case; same verdict as in the full run
python ai/generate.py --prompt 2 && python -m tests.runner --cases ai/live_cases.json
pytest tests/ -q              # the same cases, CI-shaped
python demo/race.py           # what a list of test cases cannot express
python demo/money_loop.py     # the chained bug: coupon replay + list-price credits
curl -X POST localhost:8000/_reset   # clean slate between runs
```

## The API

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | email + password to bearer token |
| GET | `/tickets?q=` | search the published catalogue |
| POST | `/orders` | buy tickets, paid from a credit balance |
| GET | `/orders/{id}` | fetch one order |
| GET | `/me` | current balance (helper for the demo) |
| POST | `/_reset` | rebuild the database (test-only) |

Attendees hold prepaid credits, spend them on tickets, and earn 10% of the
ticket value back as credits. Maximum 10 tickets per order. `SPEAKER100` is a
single-use 100% coupon.

## Bug map

Every bug is marked `# BUG-Bn` in `app/main.py`. Do not put this file on screen
before the demo.

| ID | Class | Exposed by `ai/generated_cases.json`? |
|---|---|---|
| B1 | negative / zero quantity, unchecked balance | yes (TC-001, TC-002, TC-005) |
| B2 | off-by-one on the documented 10-per-order limit | yes (TC-003) |
| B3 | SQL injection in ticket search, plus buying unpublished tickets by id | yes (TC-006 stays green, TC-007 and TC-015 go red) |
| B4 | IDOR on `GET /orders/{id}` | yes (TC-008) |
| B5 | single-use coupon can be replayed | yes (TC-012) |
| B6 | oversell race on stock | **no** — one request per case cannot express it |
| B7 | unsigned, forgeable bearer token | yes (TC-011) |
| B8 | loyalty credits computed from list price, not amount paid | **no** |
| B9 | malformed token returns 500 with internal detail | yes (TC-010) |
| B10 | student tickets sold to anyone | **no** — and no reader can confirm it without the pricing policy |

This table describes the saved case set, not models in general. Update it from
a real `ai/generate.py` run before quoting it.

B8 chained to B5 is the money loop. B10 is a rule that exists only in the
organisation's pricing policy and appears nowhere in this repository.

## Warning

Nothing here is safe to deploy. The SQL injection is real, against a local
throwaway SQLite file. Do not point any of this at anything you care about.
