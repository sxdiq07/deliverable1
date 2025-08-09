import argparse, csv, os
from typing import Dict, List, Tuple
try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML not installed. Run: pip install PyYAML")

FACTORS: Dict[str, float] = {"low": 0.85, "medium": 1.00, "high": 1.30}

def read_yaml(path: str) -> Dict:
    if not os.path.exists(path): raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f: return yaml.safe_load(f) or {}

def clamp(x: float, lo: float, hi: float) -> float: return max(lo, min(hi, x))
def fmt(x: float) -> str: return f"{x:.2f}"

def compute_rows(cfg: Dict) -> List[Tuple]:
    g = cfg.get("global", {}) or {}
    cvr = float(g.get("cvr", 0.02)); aov = float(g.get("aov", 45.0)); troas = float(g.get("target_roas", 3.0))
    tcpa = float(g.get("target_cpa", aov / troas)); tcpc = tcpa * cvr
    rows: List[Tuple] = []
    for it in cfg.get("shopping_bids", []) or []:
        name = str(it.get("product_group","")).strip(); low = float(it.get("top_of_page_low",0)); high = float(it.get("top_of_page_high",0))
        comp = str(it.get("competition","Medium")).strip().lower(); budget = float(it.get("daily_budget",0))
        cf = FACTORS.get(comp,1.0); prelim = tcpc*cf; sugg = clamp(prelim,low,high)
        clicks = (budget/sugg) if sugg>0 else 0.0
        if clicks<30 and sugg<high: sugg = clamp(prelim*1.15, low, high); clicks = (budget/sugg) if sugg>0 else 0.0
        conv = clicks*cvr; spend = clicks*sugg; rev = conv*aov; roas = (rev/spend) if spend>0 else 0.0
        note = "Increase budget" if roas>=troas and clicks>=30 else ("Constrained" if clicks<30 else "Monitor")
        rows.append((name,low,high,comp.capitalize(),budget,cvr,aov,troas,tcpa,tcpc,cf,prelim,sugg,clicks,conv,roas,note))
    rows.sort(key=lambda r: (r[15], r[13]), reverse=True); return rows

def write_csv(rows: List[Tuple], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True); dest = os.path.join(out_dir, "bids.csv")
    hdr = ["product_group","top_of_page_low","top_of_page_high","competition","daily_budget","cvr","aov","target_roas","target_cpa","target_cpc","comp_factor","prelim_cpc","suggested_cpc","clicks_per_day","expected_conversions","expected_roas","notes"]
    with open(dest, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(hdr)
        for r in rows: w.writerow([r[0],fmt(r[1]),fmt(r[2]),r[3],fmt(r[4]),fmt(r[5]),fmt(r[6]),fmt(r[7]),fmt(r[8]),fmt(r[9]),fmt(r[10]),fmt(r[11]),fmt(r[12]),fmt(r[13]),fmt(r[14]),fmt(r[15]),r[16]])
    return dest

def main() -> None:
    ap = argparse.ArgumentParser("Deliverable 3 – Suggested CPC Bids")
    ap.add_argument("--config", default="configs/d3.yaml"); ap.add_argument("--out", default="deliverables/3")
    args = ap.parse_args(); rows = compute_rows(read_yaml(args.config)); print("Wrote:", write_csv(rows, args.out))
if __name__ == "__main__": main()
