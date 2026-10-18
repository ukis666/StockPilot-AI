# Optional local English commentary

The app works with `LLM_URL` empty and always has a deterministic English fallback. No GGUF file is included or downloaded during setup, tests, builds or startup.

The preferred model is Qwen3-0.6B, GGUF Q4_K_M. Obtain a compatible GGUF file explicitly from a source you choose and place it at `models/Qwen3-0.6B-Q4_K_M.gguf`. If using Hugging Face CLI, use `hf download <verified-repository> <exact-file.gguf> --local-dir models`, then rename the chosen file to match the configured filename. Do not use the deprecated `huggingface-cli` command. Check the model's license and provenance before downloading; no particular third-party conversion is required by the application.

## Docker CPU endpoint

```bash
mkdir -p models
# Place your explicitly obtained model at models/Qwen3-0.6B-Q4_K_M.gguf first.
LLM_URL=http://llm:8080 docker compose --profile llm up -d app llm
# Stop while preserving application records and artifacts:
docker compose --profile llm down
```

Compose uses the standard CPU `ghcr.io/ggml-org/llama.cpp:server` image and `--n-gpu-layers 0`. There are no GPU device mappings, CUDA, ROCm or Vulkan services. The GGUF mount is read-only. The LLM's port is internal to Compose.

## Native CPU server

For a local llama.cpp build, explicitly disable GPU backends:

```bash
cmake -S /path/to/llama.cpp -B /path/to/llama.cpp/build \
  -DGGML_CUDA=OFF -DGGML_HIP=OFF -DGGML_VULKAN=OFF -DGGML_SYCL=OFF
cmake --build /path/to/llama.cpp/build --target llama-server -j 4
/path/to/llama.cpp/build/bin/llama-server \
  -m "$PWD/models/Qwen3-0.6B-Q4_K_M.gguf" --n-gpu-layers 0 \
  --host 127.0.0.1 --port 8080 --threads 4 --ctx-size 2048
```

In another terminal: `LLM_URL=http://127.0.0.1:8080 flask --app app run`. The adapter allows only HTTP localhost/loopback or the internal `llm` hostname; redirects are refused. It posts to `/v1/chat/completions`, uses a five-second timeout and caps response bytes. Thinking is disabled through `chat_template_kwargs.enable_thinking=false`. Slower CPU responses safely fall back.

## Input and output boundary

Validated input contains exactly `product` (1–120 characters), `current_stock` (nonnegative integer), `estimated_days_left` (finite nonnegative number or null), `anomaly_detected` (boolean), and `recommended_order` (nonnegative integer). Extra fields and malformed types are rejected.

The app first constructs all factual English sentences from those values. The model returns a constrained JSON permutation of their indexes, arranging the sentences into a short briefing. The app verifies that every index appears exactly once and renders only the supplied sentences. This deliberately limits linguistic freedom so the model cannot invent a statistic, recommend a different quantity, or inject SQL, tools or commands. The model has no database or shell access. Malformed, repeated, missing, excessive or out-of-range output uses the same deterministic fallback.

The dashboard labels either “Local LLM commentary” or “Deterministic summary.” Unit tests cover both a valid mocked server response and endpoint failures, malformed JSON, hallucinated indexes, extra fields and invalid numerical inputs. A real GGUF run requires a separately supplied model; see the verification report for what was actually tested.

Endpoint and container reference: [official llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md), [official CPU Docker instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md).
