/**
 * Cloudflare Worker — SimilarWeb relay (with UA rotation)
 * Deploy FREE at: https://workers.cloudflare.com
 */

const USER_AGENTS = [
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
];

const SEC_CH_UA = [
  '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
  '"Chromium";v="123", "Google Chrome";v="123", "Not-A.Brand";v="8"',
  '"Google Chrome";v="124", "Not-A.Brand";v="99", "Chromium";v="124"',
];

export default {
  async fetch(request) {
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

    const ua  = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
    const cha = SEC_CH_UA[Math.floor(Math.random() * SEC_CH_UA.length)];
    const isMac = ua.includes("Macintosh");
    const isWin = ua.includes("Windows");

    const swUrl = `https://data.similarweb.com/api/v1/data?domain=${encodeURIComponent(domain)}`;
    try {
      const resp = await fetch(swUrl, {
        headers: {
          "User-Agent": ua,
          "Accept": "application/json, text/plain, */*",
          "Accept-Language": "en-US,en;q=0.9",
          "Referer": "https://www.similarweb.com/website/" + domain + "/",
          "Origin": "https://www.similarweb.com",
          "sec-fetch-site": "same-site",
          "sec-fetch-mode": "cors",
          "sec-fetch-dest": "empty",
          "sec-ch-ua": cha,
          "sec-ch-ua-mobile": "?0",
          "sec-ch-ua-platform": isMac ? '"macOS"' : isWin ? '"Windows"' : '"Linux"',
        }
      });
      const body = await resp.text();
      return new Response(body, {
        status: resp.status,
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store",
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
