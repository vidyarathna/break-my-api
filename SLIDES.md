# Break My API — slide outline

HackersMang, Sat 19 Sep 2026, 10:00–10:30 IST. 10 slides, about 17 of the 30
minutes in the terminal. The words to say are in `TALK-PACKET.md` §9; this file
is only what goes **on** each slide and how to move between them.

**Deck rules**
- Light background, dark text. Body text 32pt or larger, code 28pt or larger.
- One idea per slide. If a slide needs scrolling or a pointer, it's two slides.
- Nothing on a slide that you read out word for word, except the central sentence
  on slide 8.
- No stock photos, no robot images, no "AI" clip art.
- Slides 4–7 are black "TERMINAL" cards. You switch to the terminal on them, so
  you never have to remember which window is live.
- Any number marked ⟨run⟩ must come from your own `ai/generate.py` run, not from
  this file.

---

## Slide 1 — Break My API · 00:00–01:30 · present + one curl

**On the slide**
```
Break My API
Can AI find the bugs I forgot to test?

Vidyarathna B · Software Engineer, Soult Digital
github.com/vidyarathna/break-my-api      [QR code]
```

**Before you start:** API running, terminal behind the slides, the happy-path
order curl already typed but not run.

**Beat:** switch to the terminal, run the curl, get `201` with
`total_charged 4000, credits_earned 400, credit_balance 1400`. "It works. I
tested it." Then make the promise: the model takes it apart, and then three bugs
that weren't in its case set.

**Transition:** "Before it attacks anything, you need to know the rules."

---

## Slide 2 — The API · 01:30–04:00 · present

**On the slide** (two columns)

| Endpoint | Does |
|---|---|
| `POST /auth/login` | email + password → token |
| `GET /tickets?q=` | search published tickets |
| `POST /orders` | buy tickets from your balance |
| `GET /orders/{id}` | read an order |

**The rules**
1. Everyone has a prepaid credit balance
2. Every purchase returns **10%** of the ticket value as credits
3. **Credits are spendable. Credits are money.**
4. `SPEAKER100` = 100% off, **single use**
5. Max **10** tickets per order

Small footer: `GENERAL ₹2000 · STUDENT ₹500 · WORKSHOP ₹3500 (5 seats) · STAFF (unpublished)`

**Beat:** read the rules properly. Leave rule 3 visibly bold; say "hold on to
rule three."

**Pitfall:** don't list `/me` or `/_reset` here. They're helpers, and they add
noise.

---

## Slide 3 — The prompt · 04:00–06:00 · present

**On the slide:** Prompt 2, trimmed to these lines, monospace, two lines
highlighted.
```
You are a senior security engineer doing a black-box review.
▶ Assume the developer was competent but rushed. Assume the obvious
▶ validation is present and the non-obvious validation is missing.

First, list the five assumptions this API makes about its callers.
Then write test cases that violate each one.

Return ONLY JSON. For every case:
▶ expect_status = what a CORRECT implementation would return,
▶ not what you predict this one returns.
```

**Beat:** two highlighted ideas: the attacker framing, and the "correct, not
predicted" oracle. The assumptions line is one sentence, described as intent,
not as a proven improvement.

**Optional, if you're on time:** say the central sentence for the first time
here, as a preview of slide 8.

**Transition:** "Let's run it." → slide 4.

---

## Slide 4 — TERMINAL: generate · 06:00–09:00 · demo

**On the slide:** black card, `TERMINAL`, small grey `1 / 4 · generate`.

**Screen, in order**
1. Live: `python ai/generate.py --prompt 2`, only if it took under ~40 s in your
   rehearsal. Otherwise open `ai/generated_cases.json` and say "generated last
   night, same prompt."
2. Show the `A1…A5` assumptions it printed ⟨run⟩.
3. Scroll one full case: objective, auth, payload, `expect_status`, severity.

**Don't** read out every case. Under three minutes.

---

## Slide 5 — TERMINAL: execute · 09:00–14:00 · demo

**On the slide:** black card, `TERMINAL`, `2 / 4 · execute`.

**Screen**
1. `python -m tests.runner` → ⟨run⟩ matched / did not match (saved set: 6 / 10).
2. Walk three reds:
   - **TC-001** negative quantity: `201`, `total_charged: -10000`
   - **TC-011** forged admin token: `200`, `role: admin`
   - **TC-006 green vs TC-007 red**: same hypothesis, one payload lied
3. Point at the "Candidate defects — a human still has to triage these" footer.

**Pitfall:** if you re-run one case, it's `python -m tests.runner TC-008`. It
resets the database first, so the verdict matches the full run.

---

## Slide 6 — TERMINAL: the money loop · 14:00–18:30 · demo ★ wow moment

**On the slide:** black card, `TERMINAL`, `3 / 4 · the money loop`.

**Screen**
1. Point at red **TC-012**: `SPEAKER100` accepted twice.
2. Show the single line from `app/main.py`:
   `credits_earned = round(ticket["price"] * body.quantity * LOYALTY_RATE, 2)`
   Say: list price, not amount paid.
3. Ask the room to guess, then `python demo/money_loop.py` → balance 5,000 →
   14,000, `paid 0.00` on every row.
4. Say the version from `TALK-PACKET.md` §9 Demo 3 that matches your real
   Prompt 3 run ⟨run⟩.

**Pitfall:** zoom the terminal *before* running. The table has to be readable
from the back row the moment it prints.

---

## Slide 7 — TERMINAL: not in the case set · 18:30–23:00 · demo

**On the slide:** black card, `TERMINAL`, `4 / 4 · not in the case set`.

**Screen**
1. `python demo/race.py` → 20 accepted, 0 rejected, a couple of seats
   "remaining". Point: one request, one status can't express "twenty at once."
2. Student ticket: buy `ticket_id: 2` as alice with a corporate email address →
   `201`. Then state the pricing policy. Point: the model might try it; nobody
   can confirm it's a bug from the repository alone.

**If you're behind at 18:00:** skip step 2 and say it in one sentence over slide 8.

---

## Slide 8 — The model · 23:00–25:30 · present

**On the slide**
```
AI generates testing hypotheses.
Execution provides evidence.
Humans decide whether the behaviour is a defect.
```
Below it, three boxes left to right:
```
[ model ]  ──JSON──▶  [ runner ]  ──red/green──▶  [ human ]
 guesses              sends, compares              triages
 can hallucinate      dumb on purpose              knows priorities
```

**Beat:** say the sentence verbatim. Only method, endpoint, payload and expected
status ever execute; the prose is for triage.

---

## Slide 9 — The scorecard · 25:30–27:30 · present

**On the slide** — replace every number with your real run ⟨run⟩:

| | Saved set |
|---|---|
| Hypotheses | 16 |
| Red | 10 |
| Would file today | 6 |
| Real but arguable | 2 |
| Wrong hypothesis (green) | 2 |
| **Green that lied** | **1** (TC-006) |
| **Not in the case set** | **3** (race · money chain · student rule) |

Footer, small: `one prompt · one API · local model ⟨run: model name⟩`

**Beat:** "the honest numbers." Never cut this slide.

---

## Slide 10 — Where this goes · 27:30–30:00 · present, then Q&A

**On the slide**
- Check generated cases into the repo and review them like code
- Run in CI as a **separate, non-blocking** job
- Regenerate when the spec changes, not on every run
- **Put business rules in the spec**, where a reader (or a model) can find them

`github.com/vidyarathna/break-my-api` [QR code] · Vidyarathna B

**Beat:** end on the fourth bullet. Stay on this slide for Q&A.

---

## Backup slides (after slide 10, hidden)

Only used if the terminal dies. One full-bleed screenshot each, re-taken after
the runner change:

- **B1** runner output (the 10 reds)
- **B2** `money_loop.py` table
- **B3** `race.py` oversell
- **B4** forged admin token response

## Timing checkpoints

| Clock | You should be on |
|---|---|
| 04:00 | Slide 3 |
| 09:00 | Starting `tests.runner` |
| 14:00 | Pointing at TC-012 |
| 18:30 | Starting `race.py` |
| 23:00 | Slide 8 — if not, cut the student ticket demo |
| 25:30 | Slide 9 |
