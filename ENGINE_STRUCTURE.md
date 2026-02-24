# Meta Engine Structure (Reusable Across Games)

## Core modules
- `scraper` → source collection (game-specific)
- `snapshot_engine` → normalized daily snapshots + change deltas
- `frontend` → reads latest trend JSON + renders product UI

## Reusable schema
```json
{
  "gameName": "warzone",
  "date": "2026-02-24",
  "weapons": [
    {
      "weaponName": "M8A1",
      "tier": "S",
      "ttk": 496,
      "popularity": 82,
      "patchImpactScore": 98,
      "trend": "up",
      "deltaScore": 12,
      "deltaPopularity": 5,
      "momentumScore": 18,
      "timeInTier": 3,
      "heatLevel": "hot"
    }
  ]
}
```

## Clone flow for new games
1. Copy scraper and replace source adapters.
2. Reuse snapshot engine + schema as-is.
3. Point frontend to that game's `weapon-trends.json`.
4. Update brand/theme assets only.
