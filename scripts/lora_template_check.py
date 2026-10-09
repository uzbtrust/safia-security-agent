"""Gate check: does the training prompt match what Ollama feeds the model at inference?

Counts the tokens of the first training record's prompt in two renderings of the base tokenizer's chat template:
  channel: the generation prompt (Gemma 4 ends it with an empty thinking channel when thinking is off);
  plain  : the rendered conversation up to where the answer starts (no channel).
Then sends that prompt once to the official Ollama model (think off, 1 output token) and reads Ollama's
prompt_eval_count. Passes when Ollama's count is within 1 token of the 'channel' rendering (which training uses) and
closer to it than to 'plain'. Run it before anything else has queried the model: a warm KV cache lowers the count.
  python scripts/lora_template_check.py --base .cache/lora/base --data .cache/lora/train.jsonl --out <json>
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gemma4:12b")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    args = ap.parse_args()
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.base)
    ids = lambda x: list(x["input_ids"] if hasattr(x, "keys") and "input_ids" in x else x)
    msgs = json.loads(Path(args.data).read_text().splitlines()[0])["messages"]
    channel = len(ids(tok.apply_chat_template(msgs[:1], add_generation_prompt=True, tokenize=True)))
    full = tok.apply_chat_template(msgs, tokenize=False)
    plain = len(ids(tok(full[: full.rfind(msgs[1]["content"])], add_special_tokens=False)))
    body = {"model": args.model, "stream": False, "think": False, "messages": msgs[:1],
            "options": {"num_predict": 1, "num_ctx": 8192, "temperature": 0, "seed": 1}}
    req = urllib.request.Request(f"{args.host}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as resp:
        ollama = json.load(resp).get("prompt_eval_count")
    ok = ollama is not None and abs(ollama - channel) <= 1 and abs(ollama - channel) < abs(ollama - plain)
    result = {"ollama_prompt_tokens": ollama, "hf_generation_prompt_tokens": channel,
              "hf_plain_prefix_tokens": plain, "training_uses": "generation prompt (channel)", "pass": ok}
    Path(args.out).write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
