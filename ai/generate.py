"""Generate adversarial test cases from a locally-running Ollama model.

    ollama serve
    ollama pull qwen2.5-coder:7b
    python ai/generate.py --prompt 2                 # writes ai/live_cases.json
    python -m tests.runner --cases ai/live_cases.json

    python ai/generate.py --prompt 3 --print-prompt  # show the exact text sent,
                                                     # e.g. to paste into a chat UI

The API must be running: the script reads the live OpenAPI spec and logs in as
alice to capture a real token for the prompt.

This is optional. The demo works entirely from ai/generated_cases.json if this
script fails, which is exactly why it is a separate script and not wired into
the runner.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

import httpx

OLLAMA = "http://127.0.0.1:11434/api/generate"
ROOT = Path(__file__).resolve().parent
PROMPTS = (ROOT / "prompts.md").read_text()
CURL_MD = (ROOT.parent / "demo" / "curl.md").read_text()

AUTH_VALUES = {"none", "alice", "bob", "garbage", "forged_admin"}
REQUIRED = ("objective", "method", "endpoint", "expect_status", "potential_vulnerability")


def fenced(text: str) -> str:
    """Contents of the first ``` block in text."""
    m = re.search(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)
    if not m:
        raise ValueError("no fenced block found")
    return m.group(1).strip()


def prompt_body(number: str) -> str:
    """The fenced block under '## Prompt N' in prompts.md."""
    m = re.search(rf"^## Prompt {re.escape(number)}\b.*?$(.*?)(?=^## |\Z)",
                  PROMPTS, flags=re.MULTILINE | re.DOTALL)
    if not m:
        raise ValueError(f"no '## Prompt {number}' section in prompts.md")
    return fenced(m.group(1))


def build_prompt(number: str, base: str) -> str:
    contract = fenced(PROMPTS)                      # first block = output contract
    summary = fenced(CURL_MD.split("<!-- PASTE-TO-MODEL START -->")[1])
    spec = httpx.get(f"{base}/openapi.json", timeout=10).text
    login = httpx.post(f"{base}/auth/login", timeout=10,
                       json={"email": "alice@corp.example", "password": "alice123"}).text

    text = prompt_body(number)
    text = text.replace("<paste the endpoint summary from demo/curl.md>", summary)
    text = text.replace("<paste the sample login response, including the raw token string>",
                        f"Sample login response for alice:\n{login}")
    text = text.replace("<paste output of: curl -s localhost:8000/openapi.json>", spec)
    text = text.replace("<output contract>", contract)

    leftover = re.findall(r"<paste[^>]*>|<output contract>", text)
    if leftover:
        raise ValueError(f"unfilled placeholders in prompt {number}: {leftover}")
    return text


def extract_json(text: str) -> dict:
    """Models add prose and fences no matter what you tell them. Cope."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


def problems(case: dict) -> list[str]:
    """Why a case cannot be executed as written. We reject, we never repair:
    filling in an expectation the model did not state would be putting words
    in its mouth."""
    out = [f"missing {k}" for k in REQUIRED if k not in case]
    if str(case.get("method", "")).upper() not in ("GET", "POST"):
        out.append(f"unsupported method {case.get('method')!r}")
    if case.get("auth", "none") not in AUTH_VALUES:
        out.append(f"unknown auth {case.get('auth')!r}")
    status = case.get("expect_status")
    if "expect_status" in case and not (
            isinstance(status, list) and status and all(isinstance(s, int) for s in status)):
        out.append(f"expect_status must be a list of ints, got {status!r}")
    for step in case.get("setup", []):
        if not isinstance(step, dict) or "endpoint" not in step or \
                str(step.get("method", "")).upper() not in ("GET", "POST") or \
                step.get("auth", "none") not in AUTH_VALUES:
            out.append(f"invalid setup step {step!r}")
    # "<script>" is a legitimate payload; "<your order id>" is not.
    if re.search(r"<[^<>]*\b(your|here|placeholder|insert|replace)\b[^<>]*>",
                 json.dumps(case), flags=re.IGNORECASE):
        out.append("contains a placeholder")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="2", choices=["1", "2", "3", "4"])
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default=str(ROOT / "live_cases.json"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--print-prompt", action="store_true",
                    help="print the assembled prompt and exit")
    args = ap.parse_args()

    try:
        prompt = build_prompt(args.prompt, args.base)
    except httpx.HTTPError as exc:
        print(f"cannot reach the API at {args.base}: {exc}\nstart it with ./run.sh",
              file=sys.stderr)
        return 1

    if args.print_prompt:
        print(prompt)
        return 0

    print(f"asking {args.model} with prompt {args.prompt} "
          f"({len(prompt):,} chars) ...", file=sys.stderr)
    raw_path = Path(args.out).with_suffix(".raw.txt")
    try:
        r = httpx.post(OLLAMA, timeout=300, json={
            "model": args.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            # Ollama's default context silently truncates long prompts.
            "options": {"temperature": 0.2, "seed": args.seed, "num_ctx": 8192},
        })
        r.raise_for_status()
        raw = r.json()["response"]
        raw_path.write_text(raw)               # keep the evidence, unedited
        data = extract_json(raw)
    except Exception as exc:
        print(f"generation failed: {exc}\nfall back to ai/generated_cases.json",
              file=sys.stderr)
        return 1

    kept, rejected = [], []
    for i, case in enumerate(data.get("cases", []), 1):
        case.setdefault("id", f"TC-{i:03d}")
        why = problems(case)
        if why:
            rejected.append((case["id"], why))
        else:
            case.setdefault("severity", "medium")
            kept.append(case)

    Path(args.out).write_text(json.dumps({
        "generated_by": f"{args.model} via ai/generate.py --prompt {args.prompt}",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "raw_response": raw_path.name,
        "assumptions": data.get("assumptions", []),
        "rejected": [{"id": cid, "problems": why} for cid, why in rejected],
        "cases": kept,
    }, indent=2))

    for n, assumption in enumerate(data.get("assumptions", []), 1):
        print(f"  A{n}: {assumption}", file=sys.stderr)
    print(f"wrote {len(kept)} executable cases to {args.out}", file=sys.stderr)
    for cid, why in rejected:
        print(f"  rejected {cid}: {'; '.join(why)}", file=sys.stderr)
    print(f"raw model output: {raw_path}", file=sys.stderr)
    return 0 if kept else 1


if __name__ == "__main__":
    sys.exit(main())
