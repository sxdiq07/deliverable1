# Deliverable 2 – PMax Themes and Keywords

Run:
python build_deliverable2.py --config configs/d2.yaml --out deliverables/2

Inputs:
- configs/d2.yaml (themes, seeds, modifiers, negatives, priorities)
- Optional GKP CSV (auto-detected by name; or set gkp.csv_path)

Outputs:
- deliverables/2/keywords.csv  (theme_type, theme_name, keyword, match_type, landing_url, priority)
- deliverables/2/asset_groups.json  (audience_signals per theme)

Notes:
- GKP filter (min_volume=500) ranks by volume × bid × (1−competition); falls back to deterministic if no CSV.
