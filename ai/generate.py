"""Generate adversarial test cases from a locally-running Ollama model.

    ollama serve
    ollama pull qwen2.5-coder:7b
    python ai/generate.py --prompt 2 --out ai/live_cases.json

This is optional. The demo works entirely from ai/generated_cases.json if this
script fails, which is exactly why it is a separate script and not wired into
the runner.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

OLLAMA = "http://127.0.0.1:11434/api/generate"
ROOT = Path(__file__).resolve().parent

CONTRACT = (ROOT / "prompts.md").read_text().split("```")[1]


def extract_json(text: str) -> dict:
    """Models add prose and fences no matter what you tell them. Cope."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start:end + 1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="2", help="which prompt from prompts.md")
    ap.add_argument("--model", default="qwen2.5-coder:7b")
    ap.add_argument("--out", default=str(ROOT / "live_cases.json"))
    ap.add_argument("--spec", default="http://127.0.0.1:8000/openapi.json")
    args = ap.parse_args()

    spec = httpx.get(args.spec, timeout=10).text
    section = f"Use prompt {args.prompt} from prompts.md."
    prompt = f"{section}\n\nAPI specification:\n{spec}\n\n{CONTRACT}"

    print(f"asking {args.model} ...", file=sys.stderr)
    try:
        r = httpx.post(OLLAMA, json={"model": args.model, "prompt": prompt,
                                     "stream": False, "options": {"temperature": 0.2}},
                       timeout=300)
        data = extract_json(r.json()["response"])
    except Exception as exc:
        print(f"generation failed: {exc}\nfall back to ai/generated_cases.json",
              file=sys.stderr)
        return 1

    cases = data.get("cases", [])
    for i, c in enumerate(cases, 1):
        c.setdefault("id", f"TC-{i:03d}")
        c.setdefault("severity", "medium")
        c.setdefault("expect_status", [400, 422])
    Path(args.out).write_text(json.dumps({"cases": cases}, indent=2))
    print(f"wrote {len(cases)} cases to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
