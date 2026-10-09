import json, statistics
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("/workspace/safia/.cache/lora/base")
ids = lambda x: list(getattr(x, "input_ids", x))
rows = [json.loads(l) for l in open("/workspace/safia/.cache/lora/train.jsonl")]
MAX = 8192
L, P = [], []
for r in rows:
    m = r["messages"]
    p = ids(tok.apply_chat_template(m[:1], add_generation_prompt=True, tokenize=True))
    a = ids(tok(m[1]["content"] + "<turn|>\n", add_special_tokens=False))
    L.append(len(p) + len(a)); P.append(len(p))
print("records:", len(rows), "| max_len", MAX)
print("sequence = generation prompt + answer + <turn|>: tokens total", sum(L), "| mean", round(statistics.mean(L)), "| median", round(statistics.median(L)), "| min", min(L), "| max", max(L))
print("longer than max_len (would be dropped):", sum(1 for x in L if x > MAX), "| kept:", sum(1 for x in L if x <= MAX), "| tokens kept:", sum(x for x in L if x <= MAX))
kept = sorted((x for x in L if x <= MAX), reverse=True)
print("the 8 longest kept (the gate's smoke set):", kept[:8])
print("answer tokens (loss targets) total:", sum(l - p for l, p in zip(L, P)))
