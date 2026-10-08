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
SMOKE = {"examples": 8, "steps": 4, "max_len": 2048}
PROJ = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def load_model(base: str, quant: bool):
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    kw = {"torch_dtype": torch.bfloat16, "device_map": {"": 0}}
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


def encode(tok, rec: dict, max_len: int):
    msgs = rec["messages"]
    prompt = tok.apply_chat_template(msgs[:1], add_generation_prompt=True, tokenize=True)
    full = tok.apply_chat_template(msgs, tokenize=True)
    prompt, full = list(getattr(prompt, "input_ids", prompt)), list(getattr(full, "input_ids", full))
    assert full[: len(prompt)] == prompt, "chat template: the prompt is not a prefix of the full conversation"
    if len(full) > max_len:
        return None
    return full, [-100] * len(prompt) + full[len(prompt):]


def train(args) -> None:
    import torch
    import peft
    import transformers
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoTokenizer, get_cosine_schedule_with_warmup

    random.seed(HP["seed"])
    torch.manual_seed(HP["seed"])
    max_len = SMOKE["max_len"] if args.smoke else HP["max_len"]
    raw = Path(args.data).read_bytes()
    rows = [json.loads(line) for line in raw.decode().splitlines()]
    if args.smoke:
        rows = rows[: SMOKE["examples"]]
    tok = AutoTokenizer.from_pretrained(args.base)
    data, dropped = [], 0
    for rec in rows:
        enc = encode(tok, rec, max_len)
        if enc is None:
            dropped += 1
        else:
            data.append(enc)
    print(f"{len(data)} examples, {dropped} longer than {max_len} tokens dropped", flush=True)

    model = load_model(args.base, quant=True)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    targets = text_targets(model)
    model = get_peft_model(model, LoraConfig(r=HP["r"], lora_alpha=HP["alpha"], lora_dropout=HP["dropout"],
                                             target_modules=targets, task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    multimodal = "ConditionalGeneration" in type(model.get_base_model()).__name__
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=HP["lr"], weight_decay=0.0)
    total = SMOKE["steps"] if args.smoke else math.ceil(len(data) * HP["epochs"] / HP["grad_accum"])
    sched = get_cosine_schedule_with_warmup(opt, min(HP["warmup_steps"], max(total // 10, 1)), total)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "loss.jsonl").open("w")
    model.train()
    step, t0, acc = 0, time.time(), []
    order = list(range(len(data)))
    for epoch in range(1 if args.smoke else HP["epochs"]):
        random.shuffle(order)
        for i, idx in enumerate(order):
            ids, labels = data[idx]
            x = torch.tensor([ids], device="cuda")
            kw = {"token_type_ids": torch.zeros_like(x)} if multimodal else {}
            loss = model(input_ids=x, labels=torch.tensor([labels], device="cuda"), **kw).loss
            (loss / HP["grad_accum"]).backward()
            acc.append(loss.item())
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
    model.save_pretrained(out)
    (out / "train_meta.json").write_text(json.dumps({
        "hyperparameters": HP, "smoke": args.smoke, "examples": len(data), "dropped_too_long": dropped,
        "steps": step, "seconds": round(time.time() - t0), "data_sha256": hashlib.sha256(raw).hexdigest(),
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
    t.add_argument("--smoke", action="store_true", help=f"{SMOKE['steps']} steps on {SMOKE['examples']} examples")
    m = sub.add_parser("merge")
    m.add_argument("--base", required=True)
    m.add_argument("--adapter", required=True)
    m.add_argument("--out", required=True)
    args = ap.parse_args()
    train(args) if args.cmd == "train" else merge(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
