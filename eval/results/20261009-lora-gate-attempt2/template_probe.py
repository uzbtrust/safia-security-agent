import json
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("/workspace/safia/.cache/lora/base")
rec = json.loads(open("/workspace/safia/.cache/lora/train.jsonl").readline())
msgs = rec["messages"]
ids = lambda x: list(getattr(x, "input_ids", x))          # same handling as scripts/lora_train.py::encode
p = ids(tok.apply_chat_template(msgs[:1], add_generation_prompt=True, tokenize=True))
f = ids(tok.apply_chat_template(msgs, tokenize=True))
n = next((i for i, (a, b) in enumerate(zip(p, f)) if a != b), min(len(p), len(f)))
print("prompt tokens:", len(p), "| full tokens:", len(f), "| first differing token index:", n, "(prompt is a prefix: %s)" % (f[:len(p)] == p))
print("prompt tail  :", repr(tok.decode(p[-9:])))
print("full at that point:", repr(tok.decode(f[n - 2: n + 10])))
print("tokens after the user turn, prompt side:", [tok.decode([t]) for t in p[n - 1:]])
print("tokens after the user turn, full side  :", [tok.decode([t]) for t in f[n - 1: n + 9]])
# what the training sequence would look like if built as prompt + answer + end of turn (inference-style)
ans = msgs[1]["content"]
alt = p + ids(tok(ans + "<turn|>\n", add_special_tokens=False))
print("alternative sequence (generation prompt + answer + <turn|>): tokens", len(alt), "| ends with", repr(tok.decode(alt[-6:])))
print("the full-conversation rendering ends with", repr(tok.decode(f[-6:])))
