import sys, json, urllib.request
from huggingface_hub import hf_hub_download
tag = sys.argv[1]
files = [s["rfilename"] for s in json.load(urllib.request.urlopen("https://huggingface.co/api/models/google/gemma-4-12B-it"))["siblings"]]
bad = []
for f in files:
    if f in ("model.safetensors", "tokenizer.json"):
        continue  # the two large files already downloaded fine in the gate run
    try:
        hf_hub_download("google/gemma-4-12B-it", f, local_dir=f"/tmp/probe_{tag}", force_download=True, token=__import__("os").environ.get("HF_TOKEN"))
        print("  ok  ", f)
    except Exception as e:
        bad.append(f); print("  FAIL", f, "|", type(e).__name__, str(e)[:70])
print(tag, "failures:", bad)
