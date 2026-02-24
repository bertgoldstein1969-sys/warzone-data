#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/Users/zachclawstein/.openclaw/projects/warzone-data')
WEAPONS_SOURCE = ROOT / 'weapons.json'
WARZONE_DATA = ROOT / 'warzone-data.json'
SNAPSHOT_HISTORY = ROOT / 'weapon-snapshots.json'
DAILY_SNAP_DIR = ROOT / 'daily' / 'weapon-snapshots'
TRENDS_OUT = ROOT / 'weapon-trends.json'

TIER_ORDER = {'S': 6, 'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def today_str():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def tier_base_pop(tier):
    return {'S': 82, 'A': 72, 'B': 60, 'C': 50, 'D': 40, 'F': 30}.get((tier or 'F').upper(), 45)


def tier_base_impact(tier):
    return {'S': 88, 'A': 76, 'B': 63, 'C': 50, 'D': 39, 'F': 25}.get((tier or 'F').upper(), 45)


def extract_mentions(items):
    text = '\n'.join(((i.get('title') or '') + ' ' + (i.get('summary') or '')).lower() for i in items if isinstance(i, dict))
    return text


def build_snapshot(weapons, prev_snapshot_map, mentions_blob):
    out = []
    for w in weapons:
        name = w.get('name')
        tier = (w.get('tier') or 'F').upper()
        ttk = int(max(350, 770 - (int(w.get('damage', 70)) * 2) - int(w.get('control', 65))))

        prev = prev_snapshot_map.get(name, {})
        prev_pop = prev.get('popularity')
        if prev_pop is None:
            prev_pop = tier_base_pop(tier)

        mention_bonus = 0
        if name and name.lower() in mentions_blob:
            mention_bonus = 4

        prev_tier = (prev.get('tier') or tier).upper()
        tier_shift = TIER_ORDER.get(tier, 1) - TIER_ORDER.get(prev_tier, 1)

        popularity = clamp(int(prev_pop) + mention_bonus + (tier_shift * 2), 5, 99)

        base_impact = tier_base_impact(tier)
        patch_impact = clamp(base_impact + (tier_shift * 5) + (popularity - 50) // 3, 0, 100)

        out.append({
            'weaponName': name,
            'tier': tier,
            'ttk': ttk,
            'popularity': int(popularity),
            'patchImpactScore': int(patch_impact),
            'timestamp': now_iso()
        })
    return out


def compute_trends(today_weapons, yesterday_map):
    enriched = []
    for w in today_weapons:
        prev = yesterday_map.get(w['weaponName'])
        if prev:
            d_pop = int(w['popularity']) - int(prev.get('popularity', w['popularity']))
            d_impact = int(w['patchImpactScore']) - int(prev.get('patchImpactScore', w['patchImpactScore']))
            tier_delta = TIER_ORDER.get(w['tier'], 1) - TIER_ORDER.get(prev.get('tier', w['tier']), 1)
        else:
            d_pop = 0
            d_impact = 0
            tier_delta = 0

        delta_score = int((d_pop * 0.6) + (d_impact * 0.4) + (tier_delta * 6))
        trend = 'stable'
        if delta_score > 1:
            trend = 'up'
        elif delta_score < -1:
            trend = 'down'

        enriched.append({
            **w,
            'trend': trend,
            'deltaScore': int(delta_score),
            'deltaPopularity': int(d_pop),
            'deltaPatchImpact': int(d_impact),
            'tierChange': int(tier_delta)
        })

    sorted_up = sorted(enriched, key=lambda x: x['deltaScore'], reverse=True)
    sorted_down = sorted(enriched, key=lambda x: x['deltaScore'])
    new_s_tier = [w for w in enriched if w['tier'] == 'S' and w['tierChange'] > 0]

    summary = {
        'topRiser': sorted_up[0]['weaponName'] if sorted_up else None,
        'biggestDrop': sorted_down[0]['weaponName'] if sorted_down else None,
        'newSTier': new_s_tier[0]['weaponName'] if new_s_tier else None
    }

    return enriched, summary


def main():
    weapons_doc = load_json(WEAPONS_SOURCE, {'weapons': []})
    weapons = weapons_doc.get('weapons', [])

    data_doc = load_json(WARZONE_DATA, {})
    items = data_doc.get('items', [])
    mentions_blob = extract_mentions(items)

    history = load_json(SNAPSHOT_HISTORY, [])
    by_date = {entry.get('date'): entry for entry in history if isinstance(entry, dict) and entry.get('date')}

    today = today_str()
    yesterday = None
    if history:
        dates = sorted([h.get('date') for h in history if h.get('date')])
        if dates:
            # pick latest < today if present
            past = [d for d in dates if d < today]
            if past:
                yesterday = by_date[past[-1]]

    prev_map = {}
    if yesterday:
        prev_map = {w.get('weaponName'): w for w in yesterday.get('weapons', []) if w.get('weaponName')}

    today_weapons = build_snapshot(weapons, prev_map, mentions_blob)

    today_entry = {
        'date': today,
        'generatedAt': now_iso(),
        'weapons': today_weapons
    }

    # upsert today's snapshot
    by_date[today] = today_entry
    history_out = [by_date[d] for d in sorted(by_date.keys())]

    DAILY_SNAP_DIR.mkdir(parents=True, exist_ok=True)
    with open(DAILY_SNAP_DIR / f'{today}.json', 'w', encoding='utf-8') as f:
        json.dump(today_entry, f, indent=2, ensure_ascii=False)
        f.write('\n')

    with open(SNAPSHOT_HISTORY, 'w', encoding='utf-8') as f:
        json.dump(history_out, f, indent=2, ensure_ascii=False)
        f.write('\n')

    yesterday_map = {w.get('weaponName'): w for w in (yesterday or {}).get('weapons', []) if w.get('weaponName')}
    trends, summary = compute_trends(today_weapons, yesterday_map)

    trends_doc = {
        'date': today,
        'generatedAt': now_iso(),
        'summary': summary,
        'weapons': trends
    }

    with open(TRENDS_OUT, 'w', encoding='utf-8') as f:
        json.dump(trends_doc, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f'SNAPSHOT_DATE={today}')
    print(f'SNAPSHOT_WEAPONS={len(today_weapons)}')
    print(f'TOP_RISER={summary.get("topRiser")}')


if __name__ == '__main__':
    main()
