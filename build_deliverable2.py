import argparse, csv, json, math, os
from typing import Dict, List, Set, Tuple, Optional

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML not installed. Run: pip install PyYAML")

THEME_KEYS = ["product_categories", "use_cases", "demographics", "seasonal"]

def read_yaml(path: str) -> Dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def read_terms_csv(path: str) -> Set[str]:
    if not os.path.exists(path):
        return set()
    terms: Set[str] = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            for tok in raw.replace("\ufeff","").strip().split(","):
                t = tok.strip().strip('"').lower()
                if t: terms.add(t)
    return terms

def norm(s: str) -> str:
    return " ".join(str(s).lower().strip().split()).strip(".,;:-")

def expand(seeds: List[str], heads: List[str], quals: List[str], tails: List[str]) -> List[str]:
    cand: List[str] = []
    for seed in seeds:
        s = norm(seed)
        if s: cand.append(s)
        cand += [norm(f"{h} {seed}") for h in heads]
        cand += [norm(f"{seed} {q}") for q in quals]
        cand += [norm(f"{seed} {t}") for t in tails]
    out, seen = [], set()
    for kw in cand:
        if kw and kw not in seen:
            seen.add(kw); out.append(kw)
    return out

def filter_kw(kws: List[str], negatives: Set[str], banned: Set[str], brand: Set[str], comp: Set[str]) -> List[str]:
    blocked = negatives | banned | brand | comp
    return [k for k in kws if not any(b in k for b in blocked)]

# -------- GKP (optional) --------
def _san(h: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in h).strip("_")

def _num(v: Optional[str]) -> Optional[float]:
    if v is None: return None
    try: return float(str(v).replace(",","").strip())
    except: return None

def _intval(v: Optional[str]) -> Optional[int]:
    f = _num(v); return int(f) if f is not None else None

def _comp_num(s: Optional[str]) -> float:
    m = (s or "").strip().lower()
    return 0.2 if m.startswith("l") else 0.8 if m.startswith("h") else 0.5

def load_gkp(path: Optional[str]) -> Dict[str, Dict]:
    p = path if path and os.path.exists(path) else None
    if not p:
        for name in os.listdir("."):
            n = name.lower()
            if n.endswith(".csv") and ("planner" in n or "gkp" in n):
                p = name; break
    if not p or not os.path.exists(p): return {}
    data: Dict[str, Dict] = {}
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        rdr = csv.DictReader(f)
        cols = {_san(h): h for h in (rdr.fieldnames or [])}
        ck = cols.get("keyword") or cols.get("search_term") or cols.get("keyword_text") or next(iter(cols.values()), None)
        cv = cols.get("avg_monthly_searches") or cols.get("average_monthly_searches")
        cl = cols.get("top_of_page_bid_low_range") or cols.get("low_top_of_page_bid")
        ch = cols.get("top_of_page_bid_high_range") or cols.get("high_top_of_page_bid")
        cc = cols.get("competition") or cols.get("competition_indexed_value")
        if not ck or not cv: return {}
        for r in rdr:
            kw = norm(r.get(ck,""))
            if not kw: continue
            vol = _intval(r.get(cv)) or 0
            low = _num(r.get(cl)) or 0.0
            high = _num(r.get(ch)) or 0.0
            comp = _comp_num(r.get(cc))
            data[kw] = {"vol": vol, "low": low, "high": high, "comp": comp}
    return data

def gkp_rank(cands: List[str], gkp: Dict[str, Dict], min_vol: int) -> List[str]:
    scored = []
    for kw in cands:
        m = gkp.get(kw)
        if not m or m["vol"] < min_vol: continue
        mid = (m["low"]+m["high"])/2 if (m["low"] and m["high"]) else (m["low"] or m["high"] or 0.1)
        score = math.log10(max(1,m["vol"])+1) * mid * (1.1 - m["comp"])
        scored.append((score, kw))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [k for _,k in scored]
# -------- end GKP --------

def write_keywords(rows: List[Tuple[str,str,str,str,str,str]], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "keywords.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["theme_type","theme_name","keyword","match_type","landing_url","priority"]); w.writerows(rows)
    return path

def write_assets(groups: Dict[str, Dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "asset_groups.json")
    with open(path, "w", encoding="utf-8") as f: json.dump(groups, f, indent=2, ensure_ascii=False)
    return path

def main() -> None:
    ap = argparse.ArgumentParser("Deliverable 2 – PMax themes (optional GKP filter)")
    ap.add_argument("--config", default="configs/d2.yaml"); ap.add_argument("--out", default="deliverables/2")
    args = ap.parse_args()

    cfg = read_yaml(args.config)
    mods = cfg.get("modifiers", {}) or {}
    heads = [norm(x) for x in mods.get("heads",[])]; quals = [norm(x) for x in mods.get("qualifiers",[])]; tails = [norm(x) for x in mods.get("long_tail",[])]
    negatives = {norm(x) for x in mods.get("negatives",[])}; brand = {norm(x) for x in mods.get("brand_terms",[])} | read_terms_csv("brand_keywords.csv")
    banned = {norm(x) for x in mods.get("banned_terms",[])}; comp_terms = read_terms_csv("competitor_keywords.csv")
    gen = cfg.get("generation",{}) or {}; match_types = gen.get("match_types",["exact","phrase"]); limit = int(gen.get("max_keywords_per_theme",120))
    gkp_cfg = cfg.get("gkp",{}) or {}; gkp_data = load_gkp(gkp_cfg.get("csv_path")) if gkp_cfg.get("enabled", True) else {}; min_vol = int(gkp_cfg.get("min_volume", 500))

    themes = []
    for t in THEME_KEYS:
        for it in (cfg.get("themes",{}).get(t,[]) or []):
            if not isinstance(it, dict): it = {"name": str(it), "seeds": [str(it)]}
            themes.append((t, it))
    if not themes: raise SystemExit("No themes found in config.")

    rows: List[Tuple[str,str,str,str,str,str]] = []; groups: Dict[str, Dict] = {}
    for ttype, item in themes:
        name = (item.get("name") or "").strip(); url = (item.get("landing_url") or "").strip(); prio = str(item.get("priority","medium")).lower()
        seeds = [norm(s) for s in (item.get("seeds") or []) if str(s).strip()]
        if not name or not seeds: continue
        cand = filter_kw(expand(seeds, heads, quals, tails), negatives, banned, brand, comp_terms)
        top = (gkp_rank(cand, gkp_data, min_vol) or cand)[:limit] if gkp_data else cand[:limit]
        for kw in top:
            for mt in match_types: rows.append((ttype, name, kw, mt, url, prio))
        groups[name] = {"theme_type": ttype, "landing_url": url, "priority": prio, "audience_signals": list(dict.fromkeys(seeds + top[:10]))}

    print("Wrote:", write_keywords(rows, args.out)); print("Wrote:", write_assets(groups, args.out))

if __name__ == "__main__":
    main()
