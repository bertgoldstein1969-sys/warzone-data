# Warzone Data Automation (Snapshots + Trends)

## Snapshot structure
`weapon-snapshots.json` contains daily entries:

```json
{
  "date": "2026-02-24",
  "generatedAt": "2026-02-24T01:23:45Z",
  "weapons": [
    {
      "weaponName": "M8A1",
      "tier": "S",
      "ttk": 486,
      "popularity": 84,
      "patchImpactScore": 91,
      "timestamp": "2026-02-24T01:23:45Z"
    }
  ]
}
```

## Change detection output
`weapon-trends.json` includes computed fields from today vs yesterday:
- `trend` (`up|down|stable`)
- `deltaScore`
- `deltaPopularity`
- `deltaPatchImpact`
- `tierChange`

Plus summary fields:
- `summary.topRiser`
- `summary.biggestDrop`
- `summary.newSTier`

## Automation hook
`warzone-scrape.sh` now runs:
1. non-LLM scrape (`warzone_nonllm_scrape.py`)
2. snapshot engine (`tools/snapshot_engine.py`)
3. commit/push if any data file changed.
