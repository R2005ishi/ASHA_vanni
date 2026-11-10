# Running Evon v3.3 for ASHA Vaani

Gnani publishes Evon as **open weights only** (no hosted chat API in their docs as of Oct 2026):
<https://huggingface.co/gnani/gnani-evon-v3.3-30B-A3B>

ASHA Vaani talks to Evon through the standard **OpenAI-compatible** `/v1/chat/completions`
endpoint, so any server that exposes that works. You set three lines in `backend/.env`:

```
EVON_BASE_URL=https://<your-server>/v1
EVON_MODEL=gnani/gnani-evon-v3.3-30B-A3B      # whatever name your server registers
MOCK_LLM=0
```

## Step 0 – before anything else (Day 1)

1. Sign in to Hugging Face, open the model page and **accept the access conditions**.
   Create a read token at huggingface.co/settings/tokens.
2. Open the model's `config.json` and note the `architectures` field and the total size of the
   weight files. That tells you which server below will work.
3. Ask in the Gnani Discord whether participants can get a **hosted Evon endpoint**. If yes, use
   it and skip the rest of this page.

"30B-A3B" means about 30B total parameters with about 3B active per token (Mixture of Experts).
It is fast once loaded, but **all 30B weights still have to fit in memory**:
roughly 60 GB in bf16, roughly 30 GB in 8-bit, roughly 17–20 GB at 4-bit.

## Option A – vLLM on one large GPU (simplest, most reliable)

Any 80 GB GPU (A100/H100) runs it in bf16; a 48 GB card (L40S/A6000) usually needs FP8.
Rent one by the hour (RunPod, Lambda, Vast.ai, E2E Networks, JarvisLabs) only while you test
and record the demo.

```bash
pip install vllm
export HF_TOKEN=hf_xxx
vllm serve gnani/gnani-evon-v3.3-30B-A3B \
  --max-model-len 8192 --gpu-memory-utilization 0.92 --port 8001
# 48 GB card: add  --quantization fp8
```

Then expose it (see "Expose the server" below).

## Option B – 4-bit with llama.cpp on free GPUs (Kaggle 2×T4 = 32 GB)

Works **only if llama.cpp supports Evon's architecture** (check step 0). If a GGUF version is
already on Hugging Face, use it; otherwise convert:

```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build -DGGML_CUDA=ON && cmake --build build -j
huggingface-cli download gnani/gnani-evon-v3.3-30B-A3B --local-dir evon
python convert_hf_to_gguf.py evon --outfile evon-f16.gguf
./build/bin/llama-quantize evon-f16.gguf evon-q4_k_m.gguf Q4_K_M
./build/bin/llama-server -m evon-q4_k_m.gguf -ngl 99 -c 8192 --port 8001
```

Kaggle sessions stop after a few hours, so start it shortly before you test or record.

## Expose the server

```bash
# free, no account needed for a quick tunnel
cloudflared tunnel --url http://localhost:8001
# prints https://something.trycloudflare.com  ->  EVON_BASE_URL=https://something.trycloudflare.com/v1
```

## Check it works

```bash
curl $EVON_BASE_URL/models
cd backend && MOCK_LLM=0 python -m uvicorn app.main:app --port 8000
python ../eval/run_eval.py --text      # extraction accuracy with Evon, no STT credits used
```

`/api/health` shows `"llm": false` under `mock` once Evon is active, and every visit records which
engine produced it (`engine: evon | fallback | mock`). If Evon is unreachable mid-demo, the app
keeps working with the fallback extractor and marks those visits `fallback`, so you never
present fallback output as Evon output.

## Notes

- Evon is a reasoning model and may print a `<think>…</think>` block before its answer.
  `app/llm.py` strips it and retries once if the JSON is invalid.
- Temperature is 0 for repeatable extraction.
- Keep the prompt short: each visit note is under 30 seconds of speech, so 8k context is plenty.
