import sys, os, re, json, csv, io
import pandas as pd, yaml

DEFAULT_CPC={"Brand":(3,8),"Category":(12,35),"Competitor":(10,28),"Location":(12,30),"LongTail":(5,15)}
CAT_PAT={"Protein/Whey":[r"\bwhey\b",r"\bprotein\b",r"\bprotein powder\b",r"\bwhey isolate\b"],
         "Creatine":[r"\bcreatine\b"],"Mass Gainer":[r"\bmass gainer\b",r"\bweight gainer\b"],
         "Pre Workout":[r"\bpre[- ]?workout\b"],"BCAA":[r"\bbcaa\b"],"Multivitamin":[r"\bmultivitamin\b"],
         "Omega 3 / Fish Oil":[r"\bomega ?3\b",r"\bfish oil\b"],"Fat Burner":[r"\bfat burner\b"],
         "Sports Nutrition":[r"\bsports nutrition\b",r"\bbuy supplements online\b"]}
LT_TRIG=[r"\bhow to\b",r"\bwhat is\b",r"\bvs\b",r"\bbenefits?\b",r"\bbest\b",r"\bfor (men|women|beginners|weight loss)\b",r"\bis .* safe\b"]
NEG_SEEDS=["job","jobs","career","salary","wholesale","distributor","free","download","pdf","ppt","torrent","recipe","how to make","side effects","amazon","flipkart","meesho","temu","coupon code","fake","scam","used","olx","quora","reddit","govt","notes","ban","banned"]

def load_cfg(p):
  with open(p,"r",encoding="utf-8") as f: return yaml.safe_load(f)

def norm_hdr(s):
  s=str(s).strip().lower().replace("–","-").replace("—","-")
  s=s.replace("avg. monthly searches","avg_monthly_searches").replace("average monthly searches","avg_monthly_searches")
  s=s.replace("top of page bid","top_of_page_bid")
  s=re.sub(r"[^a-z0-9]+","_",s)
  return s.strip("_")

def to_num(x):
  if pd.isna(x): return pd.NA
  s=str(x).lower().replace(",","").replace("₹","").replace("rs.","").replace("rs","").replace("inr","").strip()
  s=s.replace("--","").replace("—","")
  try: return float(s)
  except: return pd.NA

def map_cols(df):
  if df.empty: return df
  df=df.copy(); df.columns=[norm_hdr(c) for c in df.columns]
  pick=lambda opts: next((c for c in opts if c in df.columns), None)
  out=pd.DataFrame()
  k=pick(["keyword","keywords","keyword_text","plan_keyword","search_term","query","search_keyword"]); out["keyword"]=df[k] if k else ""
  v=pick(["avg_monthly_searches","average_monthly_searches","avg_monthly_searches_exact_match_only","avg_monthly_searches_(exact_match_only)","search_volume","volume","avg_searches"]); out["avg_monthly_searches"]=df[v].map(to_num) if v else pd.NA
  c=pick(["competition","comp","competition_level","competition_index","competition_indexed_value"]); out["competition"]=df[c] if c else ""
  lo=pick(["top_of_page_bid_low","top_of_page_bid_low_range","top_of_page_bid_low_inr","top_of_page_bid_low_range_inr","top_of_page_bid_low_(inr)","top_of_page_bid_low_micros","low_top_of_page_bid"])
  hi=pick(["top_of_page_bid_high","top_of_page_bid_high_range","top_of_page_bid_high_inr","top_of_page_bid_high_range_inr","top_of_page_bid_high_(inr)","top_of_page_bid_high_micros","high_top_of_page_bid"])
  out["top_of_page_bid_low"]=df[lo].map(to_num) if lo else pd.NA
  out["top_of_page_bid_high"]=df[hi].map(to_num) if hi else pd.NA
  loc=pick(["location","locations","geo","country","city","targeting_location"]); out["location"]=df[loc] if loc else ""
  lp=pick(["landing_page","final_url","url","destination_url","page"]); out["landing_page"]=df[lp] if lp else ""
  out["keyword"]=out["keyword"].astype(str).str.strip().str.lower()
  return out[out["keyword"]!=""]

def read_csv_any(path,label):
  if not path or not os.path.exists(path):
    return pd.DataFrame(columns=["keyword","avg_monthly_searches","competition","top_of_page_bid_low","top_of_page_bid_high","location","landing_page","source"])
  header_markers=("keyword","keyword text","search term","plan keyword","search keyword")
  for enc in ("utf-16","utf-16-le","utf-16-be","utf-8-sig","utf-8","latin1"):
    try:
      with open(path,"r",encoding=enc,errors="ignore") as f: lines=f.readlines()
      hdr_idx=None
      for i,ln in enumerate(lines[:600]):
        s=ln.strip().lower()
        if any(m in s for m in header_markers) and any(d in ln for d in (",",";","\t","|")):
          hdr_idx=i; break
      if hdr_idx is None: continue
      header_line=lines[hdr_idx]
      try: sep=csv.Sniffer().sniff(header_line, delimiters=",;\t|").delimiter
      except Exception:
        counts={",":header_line.count(","), ";":header_line.count(";"), "\t":header_line.count("\t"), "|":header_line.count("|")}
        sep=max(counts, key=counts.get)
      body="".join(lines[hdr_idx:])
      df=pd.read_csv(io.StringIO(body), sep=sep, header=0, engine="python", dtype=str, on_bad_lines="skip")
      if df.shape[1]<2: continue
      mapped=map_cols(df)
      if not mapped.empty:
        mapped["source"]=label
        return mapped
    except Exception: continue
  return pd.DataFrame(columns=["keyword","avg_monthly_searches","competition","top_of_page_bid_low","top_of_page_bid_high","location","landing_page","source"])

def contains_any(t,terms): t=t.lower(); return any(re.search(rf"(^|[^a-z0-9]){re.escape(x.lower())}([^a-z0-9]|$)",t) for x in terms)
def intent_of(k,brand,comp,cities):
  if contains_any(k,brand): return "Brand"
  if contains_any(k,comp): return "Competitor"
  if any(c.lower() in k for c in set([*cities,"bangalore"])): return "Location"
  if any(re.search(p,k) for p in LT_TRIG): return "LongTail"
  return "Category"
def bucket_of(k):
  for b,ps in CAT_PAT.items():
    if any(re.search(p,k) for p in ps): return b
  return "Other"
def match_type(intent,k): return "Exact" if intent in ("Brand","Location") and len(k.split())<=3 else "Phrase"
def cpc_suggest(intent,low,high):
  if pd.notna(low) or pd.notna(high):
    l=float(low) if pd.notna(low) else float(high)*0.6; h=float(high) if pd.notna(high) else float(low)*1.4
  else: l,h=DEFAULT_CPC[intent]
  return round(l,2),round(h,2),round((l+h)/2,2)

def fallback_rows(cfg):
  seeds=["whey protein","protein powder","creatine monohydrate","mass gainer","pre workout","bcaa","multivitamin","fish oil"]
  rows=[{"keyword":kw,"avg_monthly_searches":pd.NA,"competition":"","top_of_page_bid_low":pd.NA,"top_of_page_bid_high":pd.NA,"location":"","landing_page":"","source":"fallback"} for kw in seeds]
  for city in cfg["targeting"].get("locations",[]):
    for root in ["whey protein","protein powder","supplements store"]:
      rows.append({"keyword":f"{root} {city}".lower(),"avg_monthly_searches":pd.NA,"competition":"","top_of_page_bid_low":pd.NA,"top_of_page_bid_high":pd.NA,"location":city,"landing_page":"","source":"fallback"})
  return pd.DataFrame(rows)

def fill_locations(df, cfg):
  cities = cfg.get("targeting", {}).get("locations", [])
  default_loc = cfg.get("targeting", {}).get("default_location_label", "India")
  kw = df["keyword"].astype(str).str.lower().tolist()
  existing = df.get("location", pd.Series([""]*len(df))).astype(str).tolist()
  out=[]
  for k, loc in zip(kw, existing):
    if loc.strip(): out.append(loc); continue
    found=None
    for c in cities:
      cl=c.lower()
      if cl in k or ("bangalore" in k and cl=="bengaluru"):
        found=c; break
    out.append(found or default_loc)
  df["location"]=out
  return df

def build(cfg):
  b=read_csv_any(cfg["inputs"]["brand_csv"],"brand"); c=read_csv_any(cfg["inputs"]["competitor_csv"],"competitor")
  df=pd.concat([b,c],ignore_index=True)
  if df.empty: df=fallback_rows(cfg)
  df=df.drop_duplicates(subset=["keyword"])
  bt=[cfg["brand"]["name"],*cfg["brand"].get("brand_terms",[])]; ct=[cfg["competitor"]["name"],*cfg["competitor"].get("competitor_terms",[])]; cities=cfg["targeting"].get("locations",[])
  df["intent"]=df["keyword"].apply(lambda k:intent_of(k,bt,ct,cities))
  ads=[]
  for k,i in zip(df["keyword"],df["intent"]):
    if i=="Brand": ads.append("Brand Terms")
    elif i=="Competitor": ads.append("Competitor Terms")
    elif i=="Location":
      city=next((c for c in cities if c.lower() in k), None) or ("Bengaluru" if "bangalore" in k else "General"); ads.append(f"Location - {city}")
    elif i=="LongTail": ads.append("Long-Tail Informational Queries")
    else: ads.append(f"Category - {bucket_of(k)}")
  df["ad_group"]=ads
  df["campaign"]=df["intent"].map({"Brand":"Search - Brand","Competitor":"Search - Competitor","Location":"Search - Location","LongTail":"Search - LongTail","Category":"Search - Category"}).fillna("Search - Other")
  mts,lows,highs,maxes=[],[],[],[]
  for k,i,lo,hi in zip(df["keyword"],df["intent"],df.get("top_of_page_bid_low"),df.get("top_of_page_bid_high")):
    l,h,m=cpc_suggest(i,lo,hi); mts.append(match_type(i,k)); lows.append(l); highs.append(h); maxes.append(m)
  df["match_type"]=mts; df["suggested_cpc_low_inr"]=lows; df["suggested_cpc_high_inr"]=highs; df["suggested_max_cpc_inr"]=maxes
  vol=pd.to_numeric(df["avg_monthly_searches"],errors="coerce")
  if vol.notna().any(): df=df[vol>=cfg["filters"]["min_search_volume"]]
  k=cfg["filters"].get("max_keywords_per_group")
  if k: df=df.groupby(["campaign","ad_group"],as_index=False).apply(lambda g:g.sort_values("avg_monthly_searches",ascending=False,na_position="last").head(k)).reset_index(drop=True)
  df["category_bucket"]=df["ad_group"].str.replace("Category - ","",regex=False)
  df=fill_locations(df,cfg)
  return df

def _forecast_share(g,tot): return 1/len(g) if tot<=0 else g/tot
def _add_roas_cols(df,aov):
  df["cpa_inr"]=df["avg_cpc_inr"]/0.02; df["revenue_inr"]=df["est_conversions"]*(aov or 0)
  df["roas"]=df["revenue_inr"]/df["budget_inr"].replace(0, pd.NA); return df

def forecast_search(df,cfg):
  b=cfg.get("budgets",{}).get("search_monthly_inr",0) or 0; aov=cfg.get("budgets",{}).get("aov_inr",0) or 0
  if b<=0 or df.empty: return pd.DataFrame(columns=["campaign","ad_group","budget_inr","avg_cpc_inr","est_clicks","est_conversions","cpa_inr","revenue_inr","roas"])
  g=df.groupby(["campaign","ad_group"]).agg(avg_cpc_inr=("suggested_max_cpc_inr","mean"), vol=("avg_monthly_searches","sum")).reset_index()
  g["share"]=_forecast_share(g["vol"].fillna(0), g["vol"].fillna(0).sum()); g["budget_inr"]=g["share"]*b
  g["est_clicks"]=g["budget_inr"]/g["avg_cpc_inr"].clip(lower=1e-6); g["est_conversions"]=g["est_clicks"]*0.02
  return _add_roas_cols(g[["campaign","ad_group","budget_inr","avg_cpc_inr","est_clicks","est_conversions"]],aov)

def shopping_structure(df,cfg):
  b=cfg.get("budgets",{}).get("shopping_monthly_inr",0) or 0; aov=cfg.get("budgets",{}).get("aov_inr",0) or 0
  cat=df[df["ad_group"].str.startswith("Category -",na=False)].copy()
  if cat.empty or b<=0: return pd.DataFrame(columns=["campaign","ad_group","product_theme","example_keywords","budget_inr","avg_cpc_inr","est_clicks","est_conversions","cpa_inr","revenue_inr","roas"])
  top=cat.groupby("category_bucket").size().reset_index(name="kws"); top["share"]=top["kws"]/top["kws"].sum(); top["budget_inr"]=top["share"]*b
  ex=cat.groupby("category_bucket")["keyword"].apply(lambda s:", ".join(s.head(3))).reset_index(name="example_keywords")
  m=top.merge(ex,on="category_bucket",how="left"); m["avg_cpc_inr"]=(DEFAULT_CPC["Category"][0]+DEFAULT_CPC["Category"][1])/2
  m["est_clicks"]=m["budget_inr"]/m["avg_cpc_inr"]; m["est_conversions"]=m["est_clicks"]*0.02; m=_add_roas_cols(m,aov)
  m["campaign"]="Shopping - Standard"; m["ad_group"]=m["category_bucket"]; m["product_theme"]=m["category_bucket"]
  return m[["campaign","ad_group","product_theme","example_keywords","budget_inr","avg_cpc_inr","est_clicks","est_conversions","cpa_inr","revenue_inr","roas"]]

def pmax_assets(df,cfg):
  b=cfg.get("budgets",{}).get("pmax_monthly_inr",0) or 0; aov=cfg.get("budgets",{}).get("aov_inr",0) or 0
  brand=df[df["intent"]=="Brand"]["keyword"].head(5); cat=df[df["ad_group"].str.startswith("Category -",na=False)]; loc=df[df["intent"]=="Location"]
  rows=[]; b_brand,b_cat,b_loc=b*0.3,b*0.5,b*0.2
  if not brand.empty:
    cpc=(DEFAULT_CPC["Brand"][0]+DEFAULT_CPC["Brand"][1])/2; clicks=b_brand/max(cpc,1e-6); conv=clicks*0.02
    rows.append({"campaign":"PMax - Core","asset_group":"Brand","audience_hint":"brand searchers","example_keywords":", ".join(brand),"budget_inr":b_brand,"avg_cpc_inr":cpc,"est_clicks":clicks,"est_conversions":conv})
  if not cat.empty:
    top=cat.groupby("category_bucket").size().reset_index(name="kws"); top["share"]=top["kws"]/top["kws"].sum()
    for _,r in top.sort_values("kws",ascending=False).head(5).iterrows():
      ex=", ".join(cat[cat["category_bucket"]==r["category_bucket"]]["keyword"].head(3))
      cpc=(DEFAULT_CPC["Category"][0]+DEFAULT_CPC["Category"][1])/2; bud=b_cat*r["share"]; clicks=bud/max(cpc,1e-6); conv=clicks*0.02
      rows.append({"campaign":"PMax - Core","asset_group":f"Category - {r['category_bucket']}","audience_hint":"in-market sports nutrition","example_keywords":ex,"budget_inr":bud,"avg_cpc_inr":cpc,"est_clicks":clicks,"est_conversions":conv})
  if not loc.empty:
    cities=loc["ad_group"].str.replace("Location - ","",regex=False).value_counts().index.tolist()
    per=b_loc/max(len(cities),1); cpc=(DEFAULT_CPC["Location"][0]+DEFAULT_CPC["Location"][1])/2
    for city in cities:
      ex=", ".join(loc[loc["ad_group"]==f"Location - {city}"]["keyword"].head(3)); clicks=per/max(cpc,1e-6); conv=clicks*0.02
      rows.append({"campaign":"PMax - Core","asset_group":f"Location - {city}","audience_hint":"geo intent","example_keywords":ex,"budget_inr":per,"avg_cpc_inr":cpc,"est_clicks":clicks,"est_conversions":conv})
  out=pd.DataFrame(rows)
  return _add_roas_cols(out,aov)[["campaign","asset_group","audience_hint","example_keywords","budget_inr","avg_cpc_inr","est_clicks","est_conversions","cpa_inr","revenue_inr","roas"]]

def write_excel(path,df,cfg):
  with pd.ExcelWriter(path,engine="openpyxl") as w:
    cols=["campaign","ad_group","keyword","match_type","suggested_max_cpc_inr","suggested_cpc_low_inr","suggested_cpc_high_inr","avg_monthly_searches","competition","top_of_page_bid_low","top_of_page_bid_high","location","landing_page","source","intent","category_bucket"]
    df[cols].to_excel(w,index=False,sheet_name="AdGroups")
    df.groupby(["campaign","ad_group"]).size().reset_index(name="keywords").to_excel(w,index=False,sheet_name="Summary")
    forecast_search(df,cfg).to_excel(w,index=False,sheet_name="Forecast_2pc_CVR")
    pd.DataFrame({"negative_keyword":NEG_SEEDS}).to_excel(w,index=False,sheet_name="Negatives")
    shopping_structure(df,cfg).to_excel(w,index=False,sheet_name="Shopping_Structure")
    pmax_assets(df,cfg).to_excel(w,index=False,sheet_name="PMax_Asset_Groups")
    bd=cfg.get("budgets",{}); pd.DataFrame([{"shopping_monthly_inr":bd.get("shopping_monthly_inr"),"search_monthly_inr":bd.get("search_monthly_inr"),"pmax_monthly_inr":bd.get("pmax_monthly_inr"),"aov_inr":bd.get("aov_inr")}]).to_excel(w,index=False,sheet_name="Budgets")
    pd.DataFrame([{"config_json":json.dumps(cfg,indent=2)}]).to_excel(w,index=False,sheet_name="Config")

def main():
  cfg_path=sys.argv[sys.argv.index("--config")+1] if "--config" in sys.argv else "config.yaml"
  cfg=load_cfg(cfg_path); out=cfg["output"]["file"]; df=build(cfg)
  write_excel(out,df,cfg); print(f"Wrote {out} with {len(df)} keywords.")

if __name__=="__main__": main()