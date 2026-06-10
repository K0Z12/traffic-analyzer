#!/usr/bin/env python3
"""
Retry all 'Proxy Failed' rows in SDR_Cons_enriched.csv using the live server.
Updates rows in-place and prints progress.
"""
import csv, urllib.parse, urllib.request, json, time, os

OUTPUT = "/Users/kaustabhdas/Downloads/SDR_Cons_enriched.csv"
DELAY  = 3.0

def fmt(n):
    if n is None: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.0f}K"
    return str(n)

def size_label(v):
    if v is None: return "No Data"
    if v <= 50_000: return "Small"
    if v <= 90_000: return "Medium"
    return "Big"

def fetch_traffic(domain):
    while True:
        try:
            url = f"http://localhost:8787/api/analyze?domain={urllib.parse.quote(domain)}"
            resp = urllib.request.urlopen(url, timeout=60)
            data = json.loads(resp.read())
            label = data.get("tierLabel", "")
            if "rate-limited" in label or "temporarily" in label:
                print(f"\n  ⚠️  Rate-limited! Waiting 5 min…", flush=True)
                time.sleep(300)
                continue
            if "Proxy fetch failed" in label:
                return "PROXY_FAILED"
            return data.get("monthlyVisits")
        except Exception as e:
            print(f"  fetch error ({domain}): {e}", flush=True)
            time.sleep(3)
            return "PROXY_FAILED"

# Load existing CSV
with open(OUTPUT, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
    fieldnames = list(rows[0].keys())

failed_indices = [i for i, r in enumerate(rows) if r.get("Traffic Size") == "Proxy Failed"]
total_failed = len(failed_indices)

if total_failed == 0:
    print("No 'Proxy Failed' rows found — nothing to retry.", flush=True)
    exit(0)

print(f"{'═'*75}", flush=True)
print(f"  Retry Proxy Failed — {total_failed} rows to re-enrich", flush=True)
print(f"{'═'*75}", flush=True)
print(f"  {'#':<5} {'Company':<24} {'Domain':<28} {'Traffic':<10} Size", flush=True)
print(f"  {'─'*70}", flush=True)

fixed = 0
still_failed = 0

for idx, row_i in enumerate(failed_indices):
    row = rows[row_i]
    domain = row.get("Domain", "").strip().lower()
    if not domain:
        still_failed += 1
        continue

    traffic_raw = fetch_traffic(domain)
    proxy_failed = (traffic_raw == "PROXY_FAILED")
    if proxy_failed:
        traffic_raw = None
        sl = "Proxy Failed"
        still_failed += 1
    else:
        sl = size_label(traffic_raw)
        fixed += 1

    rows[row_i]["Traffic (Monthly)"] = fmt(traffic_raw)
    rows[row_i]["Traffic Size"] = sl

    icon = {"Big":"🔴","Medium":"🟡","Small":"🟢","No Data":"⚪","Proxy Failed":"🔁"}.get(sl,"⚪")
    print(f"  {idx+1:<5} {row.get('Company','')[:23]:<24} {domain[:27]:<28} {fmt(traffic_raw):<10} {icon} {sl}", flush=True)

    # Save after every row
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if (idx + 1) % 25 == 0:
        pct = (idx + 1) / total_failed * 100
        print(f"\n  Progress: {idx+1}/{total_failed} ({pct:.0f}%)  ✅ Fixed:{fixed}  🔁 Still Failed:{still_failed}\n", flush=True)

    time.sleep(DELAY)

print(f"\n{'═'*75}", flush=True)
print(f"  ✅ Done — {total_failed} retried | {fixed} fixed | {still_failed} still failed", flush=True)
print(f"  📁 {OUTPUT}", flush=True)
print(f"{'═'*75}", flush=True)
