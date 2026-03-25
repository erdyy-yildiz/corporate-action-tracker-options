import json, os, sys, tempfile
import yfinance as yf
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

SEEN_FILE = os.path.expanduser("~/.openclaw/occ_seen_ids.json")
POSITIONS_FILE = os.path.expanduser("~/.openclaw/workspace/positions.json")

def load_seen():
    if os.path.exists(SEEN_FILE):
        return set(json.load(open(SEEN_FILE)))
    return set()

def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        return json.load(open(POSITIONS_FILE))
    return []

def get_stock_context(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if len(hist) >= 2:
            change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            return f"{ticker} moved {change:+.1f}% yesterday, closing at ${hist['Close'].iloc[-1]:.2f}"
    except:
        pass
    return f"No recent price data for {ticker}"

def scrape_occ_for_ticker(ticker, context, page):
    memo_links = []
    search_url = f"https://www.theocc.com/search?query={ticker}"

    page.goto(search_url, wait_until="domcontentloaded")

    try:
        page.wait_for_function("document.title !== 'Just a moment...'", timeout=30000)
    except:
        pass

    page.wait_for_timeout(3000)

    # Click load more if exists
    while True:
        try:
            load_more = page.query_selector("button:has-text('Load more'), a:has-text('Load more'), button:has-text('Show more')")
            if load_more:
                load_more.click()
                page.wait_for_timeout(2000)
            else:
                break
        except:
            break

    links = page.query_selector_all("a")
    for link in links:
        href = link.get_attribute("href") or ""
        text = link.inner_text().strip()
        if text and any(k in href.lower() for k in ["memo", "bulletin", "infomemo", ".pdf"]):
            full_url = f"https://www.theocc.com{href}" if href.startswith("/") else href
            memo_links.append({"id": href, "title": text, "url": full_url, "ticker": ticker})

    print(f"  {ticker}: found {len(memo_links)} memo links", file=sys.stderr)

    # Download and read each PDF
    results = []
    for memo in memo_links:
        try:
            with page.expect_download(timeout=10000) as download_info:
                page.evaluate("""(url) => {
                    const links = Array.from(document.querySelectorAll('a'));
                    const match = links.find(a => a.href.includes(url));
                    if (match) match.click();
                }""", memo["id"])

            download = download_info.value
            tmp_path = tempfile.mktemp(suffix=".pdf")
            download.save_as(tmp_path)

            reader = PdfReader(tmp_path)
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
            os.unlink(tmp_path)
            memo["pdf_text"] = text.strip()
            print(f"  {ticker}: extracted {len(text)} chars from {memo['title']}", file=sys.stderr)

        except Exception as e:
            memo["pdf_text"] = ""
            print(f"  {ticker}: PDF error — {e}", file=sys.stderr)

        results.append(memo)

    return results

def run_scan(tickers):
    all_results = []
    seen = load_seen()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            accept_downloads=True
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        # Load OCC once first to get past Cloudflare
        page.goto("https://www.theocc.com/search", wait_until="domcontentloaded")
        try:
            page.wait_for_function("document.title !== 'Just a moment...'", timeout=30000)
        except:
            pass
        page.wait_for_timeout(3000)
        print(f"Cloudflare cleared: {page.title()}", file=sys.stderr)

        for ticker in tickers:
            print(f"\nScanning {ticker}...", file=sys.stderr)
            memos = scrape_occ_for_ticker(ticker, context, page)
            new_memos = [m for m in memos if m["id"] not in seen]

            for memo in new_memos:
                all_results.append({
                    "ticker": ticker,
                    "title": memo["title"],
                    "url": memo["url"],
                    "pdf_text": memo.get("pdf_text", ""),
                    "stock_context": get_stock_context(ticker)
                })
                seen.add(memo["id"])

        browser.close()

    save_seen(seen)
    return all_results

if __name__ == "__main__":
    # --fresh clears seen IDs for testing
    if "--fresh" in sys.argv:
        if os.path.exists(SEEN_FILE):
            os.remove(SEEN_FILE)
            print("Cleared seen IDs", file=sys.stderr)
        sys.argv.remove("--fresh")

    # Tickers from command line or positions.json
    if len(sys.argv) > 1:
        tickers = [t.upper() for t in sys.argv[1:]]
    else:
        tickers = load_positions()

    if not tickers:
        print("NO_POSITIONS")
        sys.exit(0)

    print(f"Scanning tickers: {tickers}", file=sys.stderr)
    results = run_scan(tickers)

    if not results:
        print("NO_NEW_MEMOS")
        sys.exit(0)

    print(json.dumps(results, indent=2))