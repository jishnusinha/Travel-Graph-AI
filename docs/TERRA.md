# Terra

Terra is the travel workspace. TravelGraph AI remains the agent studio.

## Modes

| AI_MODE | KNOWLEDGE_MODE | What runs |
|---|---|---|
| demo | catalog | Existing Goa fixture planner and demo cost ledger |
| demo | rag | Local retrieval and deterministic excerpts. Model cost is 0. |
| openai | rag | Local retrieval plus optional validated generation. Requires a key. |

If `KNOWLEDGE_MODE` is unset, the app stays on `catalog` so current databases keep working.

## Offline demo limits

- Keyword search works after a snapshot is imported.
- Dense and rerank search run only when the named local model is cached. Otherwise the trace says `dense_unavailable` or `rerank_unavailable`.
- Image similarity returns HTTP 503. It is not approximated.
- Maps are schematic coordinates, not driving routes.
- `ALLOW_NETWORK_TOOLS=false` by default, so weather and routing are not called.

## Commands

```powershell
.\scripts\ingest.ps1 -Limit 12
.\scripts\build-index.ps1 -Snapshot india-v1
.\scripts\evaluate-rag.ps1
```

`ingest.ps1` fetches Wikivoyage extracts into `data/knowledge/raw/` (gitignored) and builds `india-v1`. It does not download embedding weights unless you set `ALLOW_MODEL_DOWNLOAD=true` for that process.
