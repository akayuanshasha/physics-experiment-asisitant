# Online RAG retrieval core

This package is the sole `/api/chat` and `/api/knowledge-chat` pipeline. It loads the formal experiment
guides and the current browser user's private uploads, rewrites context-dependent
questions, retrieves with BM25 plus optional remote or local embeddings,
optionally reranks with a local cross-encoder, and builds cited
parent/adjacent context.

## Configuration

```dotenv
# Chat model (GLM/OpenAI-compatible Chat Completions API).
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=...
LLM_MODEL=glm-5.2-107

# direct / system / custom. Direct avoids inherited Windows/Linux proxies.
CHAT_PROXY_MODE=direct
# CHAT_PROXY_URL=http://proxy.example:8080
CHAT_TIMEOUT_SECONDS=90
CHAT_MAX_ATTEMPTS=2

# auto / remote / local / bm25. Use bm25 when no embedding service/model exists.
RAG_EMBEDDING_BACKEND=bm25

# Remote embeddings may reuse the endpoint and key when both APIs are provided.
EMBEDDING_BASE_URL=https://example.com/v1
EMBEDDING_API_KEY=...

# Must be an embedding model, not glm-5.2 or another chat model.
EMBEDDING_MODEL=your-embedding-model
# Inherits CHAT_PROXY_MODE/CHAT_PROXY_URL unless explicitly overridden.
# EMBEDDING_PROXY_MODE=direct
# EMBEDDING_PROXY_URL=http://proxy.example:8080

# Local mode is offline by default and requires sentence-transformers.
# RAG_EMBEDDING_BACKEND=local
# LOCAL_EMBEDDING_MODEL=D:/models/text2vec-base-chinese
# LOCAL_EMBEDDING_DEVICE=cpu
# LOCAL_EMBEDDING_BATCH_SIZE=32
# LOCAL_EMBEDDING_ALLOW_DOWNLOAD=0

# Calibrated relevance thresholds; use `off` to disable either one.
# The same thresholds also decide whether primary sources are sufficient.
RAG_MIN_RRF_SCORE=0.03
RAG_MIN_BM25_SCORE=50.0

# Optional local cross-encoder (no model is loaded when this is empty).
# RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# SQLite is the default session store. REDIS_URL switches to Redis.
RAG_SESSION_DB=.cache/online_rag/sessions.sqlite3
# REDIS_URL=redis://127.0.0.1:6379/0
```

Source authority is enforced before context construction: sufficient primary
evidence excludes all secondary material; secondary material is admitted only
when primary evidence is below the configured threshold. CSV example data is
admitted only when the question explicitly requests an example, template or
calculation demonstration.

In `auto` mode a configured local model wins, then a configured remote model;
otherwise retrieval is BM25-only. `EMBEDDING_BASE_URL` falls back to
`LLM_BASE_URL`, and `EMBEDDING_API_KEY` falls back to `LLM_API_KEY`.
Local loading never downloads unless `LOCAL_EMBEDDING_ALLOW_DOWNLOAD=1`.

The chat adapter uses `LLM_*` by default. `CHAT_BASE_URL`, `CHAT_API_KEY` and
`CHAT_MODEL` can override those values when generation is hosted separately.
`CHAT_PROXY_MODE=direct` bypasses Windows Internet Settings and Linux proxy
environment variables. Use `system` only when the host's configured proxy is
required and reliable, or `custom` together with `CHAT_PROXY_URL` for an
explicit proxy. Do not copy a Windows loopback proxy such as `127.0.0.1:7877`
into a Linux VM unless that proxy actually runs inside the VM.
Remote embeddings inherit the chat proxy mode and URL by default. Set
`EMBEDDING_PROXY_MODE` and `EMBEDDING_PROXY_URL` only when the embedding
endpoint needs a different route.

## Python API

```python
from online_rag import (
    EmbeddingConfig,
    HybridRetriever,
    RemoteEmbeddingBackend,
)

backend = RemoteEmbeddingBackend(EmbeddingConfig.from_env())
retriever = HybridRetriever.from_corpus(backend)
result = retriever.retrieve("开尔文电桥为什么适合测低电阻？", top_k=6)

for hit in result.hits:
    print(hit.chunk.experiment_name, hit.chunk.section, hit.score)
```

The first construction embeds uncached chunks. Later constructions reuse
`.cache/online_rag/embeddings.json`; changing the embedding model or chunk text
invalidates the relevant cache entries.

## Grounded answer pipeline

The included remote adapter calls a GLM/OpenAI-compatible
`/chat/completions` endpoint. The complete environment-configured pipeline is:

```python
from online_rag import create_assistant_from_env

assistant = create_assistant_from_env()
answer = assistant.ask("示波器触发同步应该怎样调节？")

print(answer.answer)
print(answer.to_dict()["citations"])
```

Constructing the assistant may call the selected embedding backend to fill
missing document vectors. If local loading, document embedding or query
embedding fails, retrieval automatically
falls back to BM25 and reports `bm25_fallback`; later requests do not repeatedly
wait on the failed embedding service. When no usable evidence passes the
relevance gate, the assistant calls the chat model for a general-knowledge
answer and prepends an upload suggestion only after generation succeeds.

Before generation, the pipeline deduplicates and limits evidence, assigns stable
labels such as `[E1]`, and builds a strict evidence-only prompt. After generation,
it removes internal evidence labels and returns the selected items as related
sources for display. The web API exposes `evidence_available` instead of claiming
that the model produced verifiable citations. The internal `citations` and
`grounded` fields remain compatibility fields for the existing evaluation tools.
Empty questions never call the chat model. Streaming
generation retries before the first visible token and then falls back to one
non-streaming request; it never restarts generation after visible text has been
sent to the browser.

The web UI uses `/api/chat/stream` and consumes real SSE `status`, `meta`,
`token`, `done`, and `error` events. Conversation history persists in SQLite or
Redis. A server-generated browser cookie scopes both sessions and uploads under
`knowledge_base/users/<user_id>/`; uploading a document invalidates only that
user's cached assistant. Structured timings and retrieval counts are returned in
the response and appended to `.cache/online_rag/rag_events.jsonl` without storing
question text or raw user/session identifiers.

## PDF ingestion and release gate

`tools/rebuild_guide_texts.py` normalizes all parser outputs into
`ParsedDocument`. PyPDF2, PyMuPDF and pdfplumber are supported directly; Docling
and MinerU are registered when installed. Docling is read through its v2
`DocumentConverter`, while MinerU uses its local CLI in auto text/OCR mode.

```bash
python -B tools/rebuild_guide_texts.py gate
python -B tools/rebuild_guide_texts.py publish
```

`gate` rejects empty/malformed documents, missing source/page metadata, residual
PUA/replacement characters, and unresolved review markers. `publish` runs the
gate first and then writes reviewed Markdown directly to the formal experiment
directories without creating backups. Reports are stored in
`rag_extraction_review/quality_gate.json` and `publish_manifest.json`.

## Release regression gate

The versioned benchmark currently contains 71 questions: the 56 previously
reviewed questions are development data and 15 new questions form the untouched
acceptance split. This fully offline run
uses BM25 only, never calls the school API, and exits nonzero when any threshold
in `evaluation/rag_v1/regression_thresholds.json` is missed:

```bash
python -B -m rag_eval run --split dev --mode blind \
  --retrieval-only --lexical-only --run-id release_gate
```

## Reproducible retrieval benchmark

Run the real BM25 + embedding + weighted-RRF benchmark and preserve a baseline:

```bash
set -a
source .env
set +a
python -m online_rag.benchmark run --label before-corpus-expansion
```

Reports are timestamped under `evaluation_reports/online_rag/`. Each report
contains the corpus fingerprint, per-experiment fingerprints, evaluation-set
hash, embedding model, retrieval settings, cache coverage, aggregate metrics,
every query's ranked hits, and exact duplicate chunks found across experiments.
It never stores API keys or document text.

Evaluation query vectors are prewarmed in batches and saved under
`.cache/online_rag/benchmark_query_embeddings.json`. This prevents per-question
request bursts, resumes after a rate limit interruption, and avoids paying for
the same evaluation query again. Batch size, pacing and 429 retries are
configurable through `--query-batch-size`, `--query-batch-delay` and
`--rate-limit-retries`.

After adding or editing experiment material, run the same benchmark with a new
label. Unchanged chunks reuse cached embeddings; only new or changed chunks are
sent to the embedding service. Compare the two reports with:

```bash
python -m online_rag.benchmark compare \
  evaluation_reports/online_rag/BEFORE.json \
  evaluation_reports/online_rag/AFTER.json
```

The comparison verifies that the evaluation set, embedding model and retrieval
configuration match, then reports corpus changes, metric deltas, improved cases
and regressions.

### Adding corpus material

Editing an existing `实验指导_RAG文本.md` or `实验指导_提取文本.txt` is detected
automatically. To add a separate reference without replacing the formal guide,
place UTF-8 Markdown or text files under:

```text
b_static/experiment/expXX/RAG补充资料/
```

Recommended Markdown metadata is:

```markdown
<!-- 实验名称: 单摆法测重力加速度 -->
<!-- 源文件: 单摆补充资料.pdf -->
<!-- 页码: 8 -->

## 数据处理
补充资料正文……
```

Nested directories are supported. Other files such as PDFs and CSVs are not
silently ingested; first convert them to UTF-8 `.md` or `.txt` so extraction
quality can be inspected. The next assistant or benchmark construction embeds
only new or changed chunks. The benchmark report records stale cache entries,
which are harmless and ignored by retrieval.
