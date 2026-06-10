#!/usr/bin/env python3
"""
CSV Traffic Enrichment — slow & steady, never gets rate-limited.
- 1 worker only (sequential)
- 3s pause between every request
- Auto-detects rate limit → waits 5 min → resumes automatically
- Saves progress after every row so you can stop/resume anytime
"""
import csv, urllib.parse, urllib.request, json, time, os

INPUT     = "/Users/kaustabhdas/Downloads/SDR_With_Domains.csv"
OUTPUT    = "/Users/kaustabhdas/Downloads/SDR_Cons_enriched.csv"
PROGRESS  = "/tmp/enrich_progress_idx.txt"   # tracks last completed row index
DELAY     = 3.0    # seconds between requests — proxy rotation handles IPs
RATELIMIT_WAIT = 300  # 5 min wait when rate-limited

def extract_domain(url):
    url = (url or "").strip()
    if not url: return None
    if not url.startswith("http"): url = "http://" + url
    try:
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except:
        return None

def fmt(n):
    if n is None: return "—"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.0f}K"
    return str(n)

def size_label(v, proxy_failed=False):
    if proxy_failed: return "Proxy Failed"
    if v is None: return "No Data"
    if v <= 50_000: return "Small"
    if v <= 90_000: return "Medium"
    return "Big"

def fetch_traffic(domain):
    """Fetch with auto-retry on rate limit. Blocks until data returns."""
    while True:
        try:
            url = f"http://localhost:8787/api/analyze?domain={urllib.parse.quote(domain)}"
            resp = urllib.request.urlopen(url, timeout=45)
            data = json.loads(resp.read())
            label = data.get("tierLabel", "")
            # Detect rate limit response
            if "rate-limited" in label or "temporarily" in label:
                print(f"\n  ⚠️  Rate-limited! Waiting {RATELIMIT_WAIT//60} min before resuming…", flush=True)
                for remaining in range(RATELIMIT_WAIT, 0, -30):
                    print(f"     resuming in {remaining}s…", flush=True)
                    time.sleep(30)
                print("  ▶ Resuming…", flush=True)
                continue  # retry same domain
            if "Proxy fetch failed" in label:
                return "PROXY_FAILED"
            return data.get("monthlyVisits")
        except Exception as e:
            print(f"  fetch error ({domain}): {e}", flush=True)
            time.sleep(3)
            return "PROXY_FAILED"

# ── Load CSV ──────────────────────────────────────────────────────────────────
with open(INPUT, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

total      = len(rows)
fieldnames = list(rows[0].keys()) + ["Traffic (Monthly)", "Traffic Size"]
stats      = {"Big": 0, "Medium": 0, "Small": 0, "No Data": 0, "Proxy Failed": 0}

# Resume from last saved position if interrupted
start_from = 0
if os.path.exists(PROGRESS):
    try:
        start_from = int(open(PROGRESS).read().strip()) + 1
        print(f"  ▶ Resuming from row {start_from} (previous run interrupted)", flush=True)
    except:
        pass

# Count already-done stats from existing output
if start_from > 0 and os.path.exists(OUTPUT):
    with open(OUTPUT, encoding="utf-8") as f:
        done_rows = list(csv.DictReader(f))
        for r in done_rows:
            sl = r.get("Traffic Size", "No Data")
            stats[sl] = stats.get(sl, 0) + 1

print(f"{'═'*75}", flush=True)
print(f"  Traffic Enrichment — {total} companies | 1 worker | {DELAY}s delay | auto-retry", flush=True)
print(f"  Estimated time: ~{int(total * (DELAY + 18) / 3600)}–{int(total * (DELAY + 25) / 3600)} hours", flush=True)
print(f"{'═'*75}", flush=True)
print(f"  {'#':<5} {'Company':<24} {'Domain':<28} {'Traffic':<10} Size", flush=True)
print(f"  {'─'*70}", flush=True)

# Open output file (append if resuming, write fresh if starting new)
mode = "a" if start_from > 0 else "w"
with open(OUTPUT, mode, newline="", encoding="utf-8") as out:
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    if start_from == 0:
        writer.writeheader()

    start_time = time.time()
    done_count = start_from

    for i in range(start_from, total):
        row    = rows[i]
        domain = row.get("Domain", "").strip().lower() or extract_domain(row.get("Website", ""))

        traffic_raw = fetch_traffic(domain) if domain else None
        proxy_failed = (traffic_raw == "PROXY_FAILED")
        if proxy_failed: traffic_raw = None
        sl = size_label(traffic_raw, proxy_failed=proxy_failed)

        row["Traffic (Monthly)"] = fmt(traffic_raw)
        row["Traffic Size"]      = sl
        writer.writerow(row)
        out.flush()

        # Save progress index so we can resume if interrupted
        with open(PROGRESS, "w") as pf:
            pf.write(str(i))

        done_count += 1
        stats[sl] = stats.get(sl, 0) + 1

        elapsed = time.time() - start_time
        rate    = (done_count - start_from) / elapsed if elapsed > 0 else 0.01
        eta_min = (total - done_count) / rate / 60 if rate > 0 else 0
        pct     = done_count / total * 100
        icon    = {"Big":"🔴","Medium":"🟡","Small":"🟢","No Data":"⚪","Proxy Failed":"🔁"}.get(sl,"⚪")

        # Print every row for first 10, then every 5
        if done_count <= 10 or done_count % 5 == 0:
            print(
                f"  {done_count:<5} {row['Company'][:23]:<24} {str(domain or '—')[:27]:<28} "
                f"{fmt(traffic_raw):<10} {icon} {sl}",
                flush=True
            )
        # Summary bar every 50
        if done_count % 50 == 0:
            bar = "█" * int(pct/5) + "░" * (20 - int(pct/5))
            print(f"\n  [{bar}] {pct:.0f}%  {done_count}/{total}  ETA {eta_min:.0f}min  "
                  f"🔴{stats['Big']} 🟡{stats['Medium']} 🟢{stats['Small']} ⚪{stats['No Data']} 🔁{stats['Proxy Failed']}\n",
                  flush=True)

        time.sleep(DELAY)

# Done
elapsed = time.time() - start_time
print(f"\n{'═'*75}", flush=True)
print(f"  ✅ DONE — {total} rows in {elapsed/60:.0f} min", flush=True)
print(f"  🔴 Big:{stats['Big']}  🟡 Med:{stats['Medium']}  🟢 Small:{stats['Small']}  ⚪ No Data:{stats['No Data']}  🔁 Proxy Failed:{stats['Proxy Failed']}", flush=True)
print(f"  📁 {OUTPUT}", flush=True)
print(f"{'═'*75}", flush=True)
if os.path.exists(PROGRESS):
    os.remove(PROGRESS)
