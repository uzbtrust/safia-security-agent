"""QLoRA fine-tuning of the base model on the RealVuln-dev training set, and merging the adapter.

Hyperparameters are fixed in advance (docs/EXPERIMENTS.md, "LoRA experiment") and are not tuned on any result.
Loss is computed on the answer tokens only. Needs a CUDA GPU (48 GB recommended): needs-local-verify.
  python scripts/lora_train.py train --base <hf dir> --data .cache/lora/train.jsonl --out .cache/lora/adapter [--smoke]
  python scripts/lora_train.py merge --base <hf dir> --adapter .cache/lora/adapter --out .cache/lora/merged
"""
import argparse
import hashlib
import json
import math
import random
import shutil
import sys
import time
from pathlib import Path

HP = {"r": 16, "alpha": 32, "dropout": 0.05, "lr": 1e-4, "epochs": 2, "grad_accum": 8, "warmup_steps": 10,
      "max_len": 8192, "seed": 1, "quant": "nf4, double quant, bf16 compute"}
SMOKE = {"examples": 8, "steps": 8}  # one step per example, the 8 longest at the full max length: memory and speed
PROJ = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def load_model(base: str, quant: bool):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    dtype_key = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    kw = {dtype_key: torch.bfloat16, "device_map": {"": 0}}
    if quant:
        kw["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                       bnb_4bit_use_double_quant=True,
                                                       bnb_4bit_compute_dtype=torch.bfloat16)
    try:
        return AutoModelForCausalLM.from_pretrained(base, **kw)
    except (ValueError, KeyError) as exc:  # multimodal checkpoints register under image-text-to-text
        print(f"causal-LM class not available ({type(exc).__name__}); loading as image-text-to-text", flush=True)
        from transformers import AutoModelForImageTextToText
        return AutoModelForImageTextToText.from_pretrained(base, **kw)


def text_targets(model) -> list[str]:
    """Attention and MLP projections of the language model only (vision/audio towers stay untouched)."""
    names = [n for n, _ in model.named_modules() if n.split(".")[-1] in PROJ]
    keep = [n for n in names if not any(t in n for t in ("vision", "audio", "multi_modal_projector"))]
    assert keep, "no projection layers found"
    return keep


def ids(x) -> list[int]:
    """Token ids from a list, a BatchEncoding or a plain dict (tokenizers return any of these)."""
    if hasattr(x, "keys") and "input_ids" in x:
        x = x["input_ids"]
    return list(x)


def end_of_turn(tok, rec: dict) -> str:
    """Text the chat template puts after a finished assistant answer (Gemma 4: '<turn|>\\n')."""
    msgs = rec["messages"]
    full, answer = tok.apply_chat_template(msgs, tokenize=False), msgs[1]["content"]
    at = full.rfind(answer)
    assert at >= 0, "chat template: the answer text is not in the rendered conversation"
    return full[at + len(answer):]


def encode(tok, rec: dict, max_len: int, eot: str):
    """Inference-aligned sequence: the generation prompt exactly as the model gets it at inference (Gemma 4 ends it
    with an empty thinking channel when thinking is off), then the answer and the end-of-turn marker. A rendered
    finished conversation would drop that channel, so it is not used (gate attempt 2, 2026-10-09)."""
    msgs = rec["messages"]
    prompt = ids(tok.apply_chat_template(msgs[:1], add_generation_prompt=True, tokenize=True))
    answer = ids(tok(msgs[1]["content"] + eot, add_special_tokens=False))
    if len(prompt) + len(answer) > max_len:
        return None
    return prompt + answer, [-100] * len(prompt) + answer


def train(args) -> None:
    import torch
    import peft
    import transformers
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoTokenizer, get_cosine_schedule_with_warmup

    random.seed(HP["seed"])
    torch.manual_seed(HP["seed"])
    max_len = HP["max_len"]
    raw = Path(args.data).read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    tok = AutoTokenizer.from_pretrained(args.base)
    eot = end_of_turn(tok, rows[0])
    data, dropped = [], 0
    for rec in rows:
        enc = encode(tok, rec, max_len, eot)
        if enc is None:
            dropped += 1
        else:
            data.append(enc)
    full_tokens = sum(len(ids) for ids, _ in data)
    print(f"{len(data)} examples, {full_tokens} tokens, {dropped} longer than {max_len} tokens dropped", flush=True)
    if args.smoke:
        data = sorted(data, key=lambda d: -len(d[0]))[: SMOKE["examples"]]

    model = load_model(args.base, quant=True)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    targets = text_targets(model)
    model = get_peft_model(model, LoraConfig(r=HP["r"], lora_alpha=HP["alpha"], lora_dropout=HP["dropout"],
                                             target_modules=targets, task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    import inspect
    needs_types = "token_type_ids" in inspect.signature(model.get_base_model().forward).parameters
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=HP["lr"], weight_decay=0.0)
    total = SMOKE["steps"] if args.smoke else math.ceil(len(data) * HP["epochs"] / HP["grad_accum"])
    sched = get_cosine_schedule_with_warmup(opt, min(HP["warmup_steps"], max(total // 10, 1)), total)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "loss.jsonl").open("w")
    model.train()
    torch.cuda.reset_peak_memory_stats()
    step, t0, acc, seen_tokens = 0, time.time(), [], 0
    order = list(range(len(data)))
    for epoch in range(1 if args.smoke else HP["epochs"]):
        random.shuffle(order)
        for i, idx in enumerate(order):
            ids, labels = data[idx]
            x = torch.tensor([ids], device="cuda")
            kw = {"token_type_ids": torch.zeros_like(x)} if needs_types else {}  # text only: all zeros
            loss = model(input_ids=x, labels=torch.tensor([labels], device="cuda"), **kw).loss
            (loss / HP["grad_accum"]).backward()
            acc.append(loss.item())
            seen_tokens += len(ids)
            if (i + 1) % HP["grad_accum"] == 0 or i == len(order) - 1 or args.smoke:
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                rec = {"step": step, "epoch": epoch, "loss": round(sum(acc) / len(acc), 4),
                       "lr": sched.get_last_lr()[0], "elapsed_s": round(time.time() - t0)}
                log.write(json.dumps(rec) + "\n")
                log.flush()
                print(rec, flush=True)
                acc = []
                if step >= total:
                    break
        if step >= total:
            break
    seconds = time.time() - t0
    tps = seen_tokens / max(seconds, 1e-9)
    model.save_pretrained(out)
    (out / "train_meta.json").write_text(json.dumps({
        "hyperparameters": HP, "smoke": args.smoke, "examples": len(data), "dropped_too_long": dropped,
        "steps": step, "seconds": round(seconds), "tokens_seen": seen_tokens, "tokens_per_second": round(tps, 1),
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 2**30, 1),
        "full_set_tokens": full_tokens, "end_of_turn": eot,
        "estimated_full_training_hours": round(full_tokens * HP["epochs"] / tps / 3600, 2) if args.smoke else None,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "trainable_targets": len(targets), "torch": torch.__version__, "transformers": transformers.__version__,
        "peft": peft.__version__, "gpu": torch.cuda.get_device_name(0)}, indent=1) + "\n")
    print("adapter saved:", out, flush=True)


def merge(args) -> None:
    from peft import PeftModel
    model = load_model(args.base, quant=False)
    model = PeftModel.from_pretrained(model, args.adapter).merge_and_unload()
    out = Path(args.out)
    model.save_pretrained(out, safe_serialization=True)
    for f in Path(args.base).iterdir():  # tokenizer, chat template, processor and generation configs
        if f.is_file() and not f.name.endswith((".safetensors", ".bin", ".safetensors.index.json", ".bin.index.json")) \
                and not (out / f.name).exists():
            shutil.copy2(f, out / f.name)
    print("merged model saved:", out, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--base", required=True, help="local directory of the base checkpoint")
    t.add_argument("--data", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--smoke", action="store_true",
                   help=f"{SMOKE['steps']} steps on the {SMOKE['examples']} longest examples (memory and speed probe)")
    m = sub.add_parser("merge")
    m.add_argument("--base", required=True)
    m.add_argument("--adapter", required=True)
    m.add_argument("--out", required=True)
    args = ap.parse_args()
    train(args) if args.cmd == "train" else merge(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
