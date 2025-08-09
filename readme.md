SEM Plan Builder (Search + Shopping + PMax)

Overview
- Input a YAML config and Google Keyword Planner CSV exports.
- Output an Excel workbook with grouped Search keywords, CPC guidance, negatives, and budget-based forecasts (2% CVR) for Search, Shopping, and PMax.

Requirements
- Python 3.9+
- pip install -r requirements.txt

Project files
- build_deliverable1.py
- requirements.txt
- config.yaml
- brand_keywords.csv
- competitor_keywords.csv
- deliverable1_adgroups.xlsx (output)

Quick start (Windows PowerShell)
1) Optional venv
   - py -3 -m venv .venv
   - .\.venv\Scripts\Activate.ps1
2) Install
   - python -m pip install -U pip
   - python -m pip install -r requirements.txt
3) Set config.yaml (see example below)
4) Run
   - python build_deliverable1.py --config config.yaml
5) Open deliverable1_adgroups.xlsx

Config.yaml
```yaml
brand:
  name: "HealthKart"
  brand_terms: ["healthkart","hk"]
  # url: "https://www.healthkart.com"      

competitor:
  name: "MuscleBlaze"
  competitor_terms: ["muscleblaze","mb"]
  # url: "https://www.muscleblaze.com"        

targeting:
  locations: ["Mumbai","Delhi","Bengaluru","Hyderabad","Chennai","Pune"]
  default_location_label: "India"

inputs:
  brand_csv: "brand_keywords.csv"
  competitor_csv: "competitor_keywords.csv"

filters:
  min_search_volume: 500        
  max_keywords_per_group: 80

budgets:
  shopping_monthly_inr: 80000
  search_monthly_inr: 120000
  pmax_monthly_inr: 100000
  aov_inr: 1500                

output:
  file: "deliverable1_adgroups.xlsx"
```

Exporting CSVs from Google Keyword Planner
- Use “Discover new keywords” or “Get search volume”.
- Location/language as needed (e.g., India/English).
- Download “Keyword ideas” as CSV (GKP often adds a “Keyword Stats …” banner line; the script auto-detects this).
- Typical columns (any close variant is fine; script maps headers):
  - Keyword
  - Avg. monthly searches
  - Competition
  - Top of page bid (low range)
  - Top of page bid (high range)
  - Landing page (optional)

What the script does
- Reads config + CSVs, merges, dedupes.
- Classifies intent: Brand, Category, Competitor, Location, LongTail.
- Assigns ad groups and match types (Exact/Phrase).
- Suggests CPCs: uses Top-of-page bids when present; else intent ranges.
- Filters by min_search_volume when volume exists.
- Caps keywords per ad group (max_keywords_per_group).
- Fills Location from keyword text or default (e.g., India).
- Writes Excel with all deliverables.

Workbook sheets
- AdGroups: campaign, ad_group, keyword, match_type, CPC suggestions, GKP metrics, location, source, intent, category_bucket.
- Summary: count of keywords per ad group.
- Forecast_2pc_CVR (Search): budget split, avg CPC, estimated clicks, conversions (2%), CPA, revenue (AOV), ROAS.
- Negatives: initial negative themes.
- Shopping_Structure: category-led plan with budget, clicks, conversions, CPA, ROAS.
- PMax_Asset_Groups: brand/category/location asset groups with budget, clicks, conversions, CPA, ROAS.
- Budgets: values from config.
- Config: JSON dump of the config (for audit).

Validation checklist (before sending)
- Config filters.min_search_volume = 500.
- AdGroups: source shows brand/competitor (not fallback); metrics (volume/bids/competition) populated where GKP provided them.
- Forecast_2pc_CVR: SUM(budget_inr) = search_monthly_inr.
- Shopping_Structure: SUM(budget_inr) = shopping_monthly_inr.
- PMax_Asset_Groups: SUM(budget_inr) = pmax_monthly_inr.
- If needed, hide/delete the Config sheet (it’s safe to keep).

Troubleshooting
- Empty metric columns: re-export CSV from GKP; ensure it includes the columns above. Script auto-detects UTF‑16, delimiter, and header row.
- Too few keywords: set filters.min_search_volume to 0 to inspect; then restore to 500.
- Missing locations: script fills city if found in the keyword; otherwise uses default_location_label.
License
- Internal assessment project.