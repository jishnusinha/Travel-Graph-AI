# Retrieval evaluation report

Snapshot: `india-v1`  
Case file: `data/knowledge/manifests/eval_cases.json` (**50** reviewed cases)  
Measured: 2026-11-24 on the local Windows machine used for Terra integration.

## Corpus at measurement

- Documents: 92 (42 Wikivoyage + 50 Wikipedia)
- Chunks: 581
- Images: 48
- Entities / relationships: 348 / 442
- Embedding: `BAAI/bge-small-en-v1.5` via fastembed
- Reranker: `Xenova/ms-marco-MiniLM-L-6-v2`

## Metric

`hit@3` on discovery grouping: the expected destination slug appears in the top three destination results. Cases whose expected slug is absent from the snapshot are skipped and are not counted as hits. All 50 expected slugs were present.

## Results

| Strategy | hit@3 | hits/n | Misses |
|---|---|---|---|
| keyword | 0.92 | 46/50 | waterfalls-hills, dawki-river, kurseong-tea, dirang-valley |
| dense | 0.90 | 45/50 | sikkim-capital, living-root-bridges, dawki-river, kurseong-tea, dirang-valley |
| hybrid | 0.92 | 46/50 | sikkim-capital, dawki-river, kurseong-tea, dirang-valley |
| hybrid_rerank | **0.96** | 48/50 | kurseong-tea, dirang-valley |
| graph_hybrid | 0.88 | 44/50 | waterfalls-hills, sikkim-capital, living-root-bridges, dawki-river, kurseong-tea, dirang-valley |

`graph_hybrid` did **not** beat `hybrid` or `hybrid_rerank` on this set. Do not claim graph improvement from this table.

## Reproduce

```powershell
.\scripts\doctor.ps1
.\scripts\evaluate-rag.ps1
```

## Limitations

- Labels are manually reviewed against this corpus; they are not an industry held-out suite.
- Visual search and live OpenAI judge scores are not applicable in the offline demo.
- Editorial cost bands and OSM gaps are documented in `docs/DATA_SOURCES.md`.
