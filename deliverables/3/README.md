# Deliverable 3 – Suggested CPC Bids (Manual Shopping)

Run:
python build_deliverable3.py --config configs/d3.yaml --out deliverables/3

Inputs (configs/d3.yaml):
- global: cvr=0.02, aov, target_roas
- shopping_bids: product_group, top_of_page_low, top_of_page_high, competition, daily_budget

Logic:
- Target CPA = aov / target_roas
- Target CPC = Target CPA × cvr (2%)
- Competition factor: Low 0.85, Medium 1.00, High 1.30
- suggested_cpc = clamp(target_cpc × comp_factor, low, high)
- Learning check: if clicks/day < 30, nudge toward band (≤ high)
- Output includes clicks/day, expected conversions, expected ROAS, notes

Output:
- deliverables/3/bids.csv
