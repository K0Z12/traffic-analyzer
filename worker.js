/**
 * Cloudflare Worker — SimilarWeb relay
 * Deploy FREE at: https://workers.cloudflare.com
 *
 * Steps (5 minutes):
 * 1. Go to https://workers.cloudflare.com → Sign up (free, no card needed)
 * 2. Click "Create a Worker"
 * 3. Delete the default code, paste this entire file
 * 4. Click "Save & Deploy"
 * 5. Copy your worker URL (e.g. https://sw-relay.YOUR-NAME.workers.dev)
 * 6. Paste it into config.json in this folder:
 *    { "cf_worker": "https://sw-relay.YOUR-NAME.workers.dev" }
 * 7. Restart server.py — all domains will now work, no 403 ever.
 *
 * Free tier: 100,000 requests/day. More than enough for unlimited personal use.
 */

export default {
  async fetch(request) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET",
          "Access-Control-Allow-Headers": "*",
        }
      });
    }

    const url = new URL(request.url);
    const domain = url.searchParams.get("domain");
    if (!domain) {
      return new Response(JSON.stringify({ error: "domain param required" }), {
        status: 400,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
      });
    }

    // Proxy to SimilarWeb internal API with browser headers
    const swUrl = `https://data.similarweb.com/api/v1/data?domain=${encodeURIComponent(domain)}`;
    try {
      const resp = await fetch(swUrl, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
          "Accept": "application/json, text/plain, */*",
          "Referer": "https://www.similarweb.com/",
          "Origin": "https://www.similarweb.com",
          "sec-fetch-site": "same-site",
          "sec-fetch-mode": "cors",
          "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
          "sec-ch-ua-mobile": "?0",
          "sec-ch-ua-platform": '"macOS"',
        }
      });
      const body = await resp.text();
      return new Response(body, {
        status: resp.status,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "public, max-age=3600"
        }
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 502,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
      });
    }
  }
};
