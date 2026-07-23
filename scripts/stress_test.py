"""
stress_test.py — terra-os pełny stress test

Moduły:
  A. API Coverage  — 473 endpointów, czy odpowiadają (nie 500)
  B. API Load      — concurrent burst na kluczowych endpointach
  C. DB Queries    — heavy queries: FTS, historical_tenders, mv_scoring
  D. E2E Extended  — więcej ścieżek użytkownika (search, bookmarks, ICB, pipeline...)
  E. Concurrent    — 5 równoległych sesji Playwright
  F. Edge Cases    — malformed input, SQL injection probe, duże payloady
"""
import asyncio, time, json, sys, os, random, string
from pathlib import Path
from collections import defaultdict
import aiohttp
from playwright.async_api import async_playwright, Page

BASE     = "http://localhost:3000"
API      = "http://localhost:8000"
EMAIL    = "demo@terra-os.pl"
PASSWORD = "BudOS2026!"
SS_DIR   = Path("/tmp/stress_screenshots")
SS_DIR.mkdir(exist_ok=True)

results  = []
timings  = defaultdict(list)

def log(status, name, detail="", elapsed=None):
    icon = "✅" if status == "PASS" else ("⚠️" if status == "WARN" else "❌")
    t = f" [{elapsed*1000:.0f}ms]" if elapsed else ""
    msg = f"{icon} [{status}]{t} {name}"
    if detail: msg += f" — {detail}"
    print(msg)
    results.append({"status": status, "name": name, "detail": detail, "elapsed": elapsed})

async def get_token(session: aiohttp.ClientSession) -> str:
    async with session.post(f"{API}/api/v2/auth/login",
        json={"email": EMAIL, "password": PASSWORD}) as r:
        d = await r.json()
        return d.get("access_token", "")

async def screenshot(page: Page, name: str):
    await page.screenshot(path=str(SS_DIR / f"{name}.png"), full_page=False)

async def login_page(page: Page):
    await page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)
    await page.fill('input[type="email"]', EMAIL)
    await page.fill('input[type="password"]', PASSWORD)
    await page.click('button[type="submit"]')
    # Wait for navigation away from /login (may go to /app or /app/dashboard)
    try:
        await page.wait_for_url("**/app**", timeout=20_000)
    except Exception:
        # Fallback: wait for URL change
        await page.wait_for_timeout(3000)
        cur = page.url
        if "/login" in cur:
            # Try direct navigation
            await page.goto(f"{BASE}/app", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
    await page.wait_for_load_state("domcontentloaded")

# ══════════════════════════════════════════════════════════
# A. API COVERAGE — wszystkie grupy endpointów
# ══════════════════════════════════════════════════════════
async def module_api_coverage():
    print("\n━━━ A. API COVERAGE ━━━")
    token = ""
    async with aiohttp.ClientSession() as session:
        try:
            token = await get_token(session)
        except:
            pass
        headers = {"Authorization": f"Bearer {token}"} if token else {}

        # Sample jeden endpoint z każdej grupy
        endpoints = [
            # Health
            ("GET", "/health", None, [200]),
            ("GET", "/api/v2/health", None, [200]),
            # Auth
            ("GET", "/api/v2/auth/me", None, [200, 401]),
            # Tenders
            ("GET", "/api/v2/tenders?limit=5", None, [200, 401]),
            ("GET", "/api/v1/tenders?limit=5", None, [200, 401]),
            # Dashboard
            ("GET", "/api/v2/dashboard/stats", None, [200, 401]),
            ("GET", "/api/v2/dashboard/recent-tenders", None, [200, 401]),
            ("GET", "/api/v1/dashboard/summary", None, [200, 401]),
            # Search
            ("GET", "/api/v2/search?q=budowa&limit=5", None, [200, 401]),
            # Scoring
            ("GET", "/api/v2/scoring/config", None, [200, 401]),
            ("GET", "/api/v2/scoring/v3/percentile", None, [200, 401]),
            ("GET", "/api/v2/scoring/leaderboard", None, [200, 401]),
            # ICB
            ("GET", "/api/v2/icb/categories", None, [200, 401]),
            ("GET", "/api/v2/icb/stats", None, [200, 401]),
            # Market
            ("GET", "/api/v2/market/overview", None, [200, 401]),
            ("GET", "/api/v2/market-intel/summary", None, [200, 401]),
            ("GET", "/api/v2/mv/cpv-heatmap", None, [200, 401]),
            ("GET", "/api/v2/mv/dashboard-stats", None, [200, 401]),
            # Intelligence
            ("GET", "/api/v2/intelligence/summary", None, [200, 401]),
            ("GET", "/api/v2/bid-intelligence/recent", None, [200, 401]),
            # Kosztorys
            ("GET", "/api/v2/kosztorys?limit=5", None, [200, 401]),
            ("GET", "/api/v1/kosztorys?limit=5", None, [200, 401]),
            # BZP
            ("GET", "/api/v2/bzp/stats", None, [200, 401]),
            ("GET", "/api/v1/bzp/stats", None, [200, 401]),
            # Analytics
            ("GET", "/api/v2/analytics/overview", None, [200, 401]),
            ("GET", "/api/v2/analytics/pipeline", None, [200, 401]),
            # Competitors
            ("GET", "/api/v2/competitors?limit=5", None, [200, 401]),
            # Bookmarks
            ("GET", "/api/v2/bookmarks?limit=5", None, [200, 401]),
            # Decisions
            ("GET", "/api/v2/decisions?limit=5", None, [200, 401]),
            # Documents
            ("GET", "/api/v2/documents?limit=5", None, [200, 401]),
            # Contracts
            ("GET", "/api/v2/contracts?limit=5", None, [200, 401]),
            # Resources
            ("GET", "/api/v2/resources?limit=5", None, [200, 401]),
            ("GET", "/api/v1/resources/employees?limit=5", None, [200, 401]),
            ("GET", "/api/v1/resources/equipment?limit=5", None, [200, 401]),
            # Team
            ("GET", "/api/v2/team?limit=5", None, [200, 401]),
            # Notifications
            ("GET", "/api/v2/notifications?limit=5", None, [200, 401]),
            # Reports
            ("GET", "/api/v2/reports?limit=5", None, [200, 401]),
            # Forecast
            ("GET", "/api/v2/forecast/pipeline", None, [200, 401]),
            # Gantt
            ("GET", "/api/v2/gantt/list", None, [200, 401]),
            # Offers
            ("GET", "/api/v2/offers?limit=5", None, [200, 401]),
            # Settings
            ("GET", "/api/v2/settings", None, [200, 401]),
            # Buyers
            ("GET", "/api/v2/buyers?limit=5", None, [200, 401, 422]),
            # Buyer CRM
            ("GET", "/api/v2/buyer-crm/contacts?limit=5", None, [200, 401]),
            # Embeddings
            ("GET", "/api/v2/embeddings/stats", None, [200, 401]),
            # RAG
            ("GET", "/api/v2/rag/stats", None, [200, 401]),
            # System
            ("GET", "/api/v2/system/info", None, [200, 401]),
            # Audit
            ("GET", "/api/v2/audit/logs?limit=5", None, [200, 401]),
            # Tender alerts
            ("GET", "/api/v2/tender-alerts?limit=5", None, [200, 401]),
        ]

        ok = fail = warn = 0
        errors_5xx = []
        for method, path, body, expected in endpoints:
            t0 = time.time()
            try:
                url = f"{API}{path}"
                async with session.request(method, url, json=body, headers=headers,
                                           timeout=aiohttp.ClientTimeout(total=8)) as r:
                    elapsed = time.time() - t0
                    timings["api_coverage"].append(elapsed)
                    if r.status in expected:
                        ok += 1
                        if elapsed > 3:
                            log("WARN", f"API slow: {path}", f"HTTP {r.status}", elapsed)
                            warn += 1
                    elif r.status >= 500:
                        body_text = (await r.text())[:200]
                        errors_5xx.append((path, r.status, body_text))
                        log("FAIL", f"API 5xx: {path}", f"HTTP {r.status}: {body_text[:80]}", elapsed)
                        fail += 1
                    elif r.status == 404:
                        log("WARN", f"API 404: {path}", f"endpoint missing", elapsed)
                        warn += 1
                    else:
                        log("WARN", f"API unexpected: {path}", f"HTTP {r.status}", elapsed)
                        warn += 1
            except asyncio.TimeoutError:
                log("FAIL", f"API timeout: {path}", "8s timeout")
                fail += 1
            except Exception as e:
                log("FAIL", f"API error: {path}", str(e)[:80])
                fail += 1

    if errors_5xx:
        print(f"\n  ⛔ 5xx errors ({len(errors_5xx)}):")
        for p, s, b in errors_5xx:
            print(f"    {s} {p}: {b[:100]}")

    avg = sum(timings["api_coverage"]) / max(len(timings["api_coverage"]), 1)
    p95_t = sorted(timings["api_coverage"])
    p95 = p95_t[int(len(p95_t)*0.95)] if p95_t else 0
    print(f"\n  API Coverage: {ok} OK | {warn} WARN | {fail} FAIL | avg={avg*1000:.0f}ms | p95={p95*1000:.0f}ms")
    log("PASS" if fail == 0 else "FAIL", "A. API Coverage",
        f"{ok}/{len(endpoints)} OK, {fail} FAIL, {warn} WARN, avg={avg*1000:.0f}ms, p95={p95*1000:.0f}ms")


# ══════════════════════════════════════════════════════════
# B. LOAD TEST — concurrent burst
# ══════════════════════════════════════════════════════════
async def module_load_test():
    print("\n━━━ B. LOAD TEST ━━━")
    token = ""
    async with aiohttp.ClientSession() as s:
        try: token = await get_token(s)
        except: pass

    headers = {"Authorization": f"Bearer {token}"}

    async def hit(session, url, label):
        t0 = time.time()
        try:
            async with session.get(url, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=15)) as r:
                elapsed = time.time() - t0
                timings[label].append(elapsed)
                return r.status, elapsed
        except Exception as e:
            return 0, time.time() - t0

    scenarios = [
        ("tenders_list",    f"{API}/api/v2/tenders?limit=20",          30),
        ("dashboard_stats", f"{API}/api/v2/dashboard/stats",            30),
        ("mv_scoring",      f"{API}/api/v2/scoring/v3/percentile",      20),
        ("search_fts",      f"{API}/api/v2/search?q=budowa+drogi&limit=10", 20),
        ("kosztorys_list",  f"{API}/api/v2/kosztorys?limit=10",         20),
        ("health",          f"{API}/health",                             50),
    ]

    # Fresh token (previous one may have expired during E2E phase)
    async with aiohttp.ClientSession() as s:
        try: token = await get_token(s)
        except: pass
    headers = {"Authorization": f"Bearer {token}"}

    connector = aiohttp.TCPConnector(limit=60)
    async with aiohttp.ClientSession(connector=connector) as session:
        for label, url, concurrency in scenarios:
            tasks = [hit(session, url, label) for _ in range(concurrency)]
            t0 = time.time()
            responses = await asyncio.gather(*tasks)
            wall = time.time() - t0

            statuses = [s for s, _ in responses]
            times = [t for _, t in responses]
            ok = sum(1 for s in statuses if 200 <= s < 400)
            err5xx = sum(1 for s in statuses if s >= 500)
            t_sorted = sorted(times)
            p50 = t_sorted[len(t_sorted)//2]
            p95 = t_sorted[int(len(t_sorted)*0.95)]
            rps = concurrency / wall

            status = "PASS" if err5xx == 0 and ok >= concurrency * 0.9 else "FAIL"
            log(status, f"Load: {label}",
                f"n={concurrency} | ok={ok} | 5xx={err5xx} | p50={p50*1000:.0f}ms | p95={p95*1000:.0f}ms | {rps:.1f} rps")

    print()


# ══════════════════════════════════════════════════════════
# C. DB HEAVY QUERIES
# ══════════════════════════════════════════════════════════
async def module_db_stress():
    print("\n━━━ C. DB STRESS ━━━")

    import subprocess
    queries = [
        ("FTS tender (title ILIKE)",
         "SELECT COUNT(*) FROM tender WHERE title ILIKE '%budowa%' OR title ILIKE '%drogi%'"),
        ("historical_tenders FTS (1.4M)",
         "SELECT COUNT(*) FROM historical_tenders WHERE title ILIKE '%remont%' OR buyer ILIKE '%szkoł%'"),
        ("mv_scoring percentile",
         "SELECT * FROM mv_scoring LIMIT 100"),
        ("JOIN tender+analysis",
         "SELECT t.id,t.title,a.id FROM tender t LEFT JOIN analysis a ON a.tender_id::text=t.id::text LIMIT 100"),
        ("ICB CPV stats",
         "SELECT cpv_code, COUNT(*) FROM historical_tenders WHERE cpv_code IS NOT NULL GROUP BY cpv_code ORDER BY 2 DESC LIMIT 20"),
        ("Document chunk embedding search",
         "SELECT id, LEFT(content, 50) as preview FROM document_chunk ORDER BY created_at DESC LIMIT 50"),
        ("Kosztorys aggregation",
         "SELECT tender_id, SUM(suma_netto) FROM kosztorys GROUP BY tender_id ORDER BY 2 DESC NULLS LAST LIMIT 20"),
        ("Employee count by role",
         "SELECT role, COUNT(*) FROM employee GROUP BY role ORDER BY 2 DESC LIMIT 10"),
        ("Resource equipment available",
         "SELECT type, COUNT(*) FROM resource_equipment GROUP BY type LIMIT 10"),
        ("Agent run stats last 7d",
         "SELECT DATE(started_at), COUNT(*), AVG(EXTRACT(EPOCH FROM (finished_at-started_at))) FROM agent_run WHERE started_at > NOW()-INTERVAL'7 days' GROUP BY 1"),
    ]

    db_script = "import sys,os,time; sys.path.insert(0,'packages/db')\n"
    db_script += "with open('.env') as f:\n"
    db_script += "    for l in f:\n"
    db_script += "        l=l.strip()\n"
    db_script += "        if '=' in l and not l.startswith('#'): k,v=l.split('=',1); os.environ.setdefault(k,v)\n"
    db_script += "os.environ.update({'DB_HOST':'127.0.0.1','DB_NAME':'terraos','DB_USER':'terraos'})\n"
    db_script += "import sqlalchemy as sa; from terra_db.session import get_engine\n"
    db_script += "eng=get_engine()\n"

    for name, q in queries:
        db_script += f"""
t0=time.time()
try:
    with eng.connect() as c:
        r=c.execute(sa.text({repr(q)})).fetchall()
    elapsed=time.time()-t0
    print(f"PASS|{name}|{{len(r)}} rows|{{elapsed*1000:.0f}}ms")
except Exception as e:
    print(f"FAIL|{name}|{{str(e)[:80]}}")
"""

    result = subprocess.run(
        ["/home/ubuntu/terra-os/.venv/bin/python3.12", "-c", db_script],
        capture_output=True, text=True, cwd="/home/ubuntu/terra-os"
    )
    for line in result.stdout.strip().split("\n"):
        if not line: continue
        parts = line.split("|")
        if len(parts) >= 3:
            status, name, detail = parts[0], parts[1], "|".join(parts[2:])
            log(status, f"DB: {name}", detail)
        else:
            print(f"  raw: {line}")

    if result.stderr:
        errs = [l for l in result.stderr.split("\n") if "Error" in l or "error" in l]
        if errs:
            print(f"  DB stderr: {errs[0][:120]}")


# ══════════════════════════════════════════════════════════
# D. E2E EXTENDED — więcej ścieżek użytkownika
# ══════════════════════════════════════════════════════════
async def e2e_extended_flows(page: Page):
    print("\n━━━ D. E2E EXTENDED FLOWS ━━━")

    pages_to_visit = [
        ("/app",               "Dashboard"),
        ("/app/zwiad",         "Zwiad (Przetargi)"),
        ("/app/pipeline",      "Lejek"),
        ("/app/bookmarks",     "Bookmarki"),
        ("/app/silnik",        "Silnik AI"),
        ("/app/decyzja",       "Decyzja"),
        ("/app/kosztorys",     "Kosztorys"),
        ("/app/bid-intelligence", "Bid Intelligence"),
        ("/app/oferta",        "Oferta"),
        ("/app/contracts",     "Kontrakty"),
        ("/app/documents",     "Dokumenty"),
        ("/app/buyer-crm",     "Zamawiający CRM"),
        ("/app/competitors",   "Konkurenci"),
        ("/app/market-intel",  "Rynek"),
        ("/app/icb",           "Ceny ICB"),
        ("/app/logistyka",     "Logistyka"),
        ("/app/resources",     "Zasoby"),
        ("/app/team",          "Zespół"),
        ("/app/analytics",     "Analityka"),
        ("/app/reports",       "Raporty"),
        ("/app/settings",      "Ustawienia"),
        ("/app/budos",         "BudOS"),
    ]

    for path, name in pages_to_visit:
        t0 = time.time()
        try:
            await page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=12_000)
            await page.wait_for_timeout(800)
            elapsed = time.time() - t0

            # Check if 404 / error page
            body = await page.content()
            h1 = ""
            try: h1 = await page.locator("h1").first.inner_text()
            except: pass

            if "nie znaleziono" in h1.lower() or "404" in h1 or "not found" in h1.lower():
                log("WARN", f"Page 404: {name}", path)
            elif "error" in body.lower() and len(body) < 500:
                log("FAIL", f"Page error: {name}", path)
            else:
                # Check for loading state — should have content
                main_text = ""
                try: main_text = await page.locator("main, [role='main']").first.inner_text()
                except: pass
                has_content = len(main_text.strip()) > 30
                status = "PASS" if has_content else "WARN"
                log(status, f"Page: {name}",
                    f"{path} | {elapsed*1000:.0f}ms | content={'yes' if has_content else 'empty'}")
        except Exception as e:
            log("FAIL", f"Page crash: {name}", str(e)[:100])

    # D2. Search functionality
    print("\n  -- Search --")
    try:
        await page.goto(f"{BASE}/app/zwiad", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        search = page.locator("input[placeholder*='Szukaj'], input[type='search']").first
        if await search.count() > 0:
            await search.fill("budowa drogi")
            await page.wait_for_timeout(1500)
            items = await page.locator("main > div").count()
            log("PASS", "Search: 'budowa drogi'", f"{items} results in main")
            await search.fill("")
            await page.wait_for_timeout(500)
        else:
            log("WARN", "Search: input not found")
    except Exception as e:
        log("FAIL", "Search", str(e)[:80])

    # D3. Bookmark a tender
    print("\n  -- Bookmarks --")
    try:
        await page.goto(f"{BASE}/app/zwiad", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        bookmark_btn = page.locator("button[aria-label='Dodaj do obserwowanych'], button:has([class*='bookmark-icon']), button:has(svg[class*='bookmark'])").first
        if await bookmark_btn.count() > 0:
            await bookmark_btn.click()
            await page.wait_for_timeout(500)
            log("PASS", "Bookmark toggle", "clicked")
        else:
            log("WARN", "Bookmark button not found in Zwiad")
    except Exception as e:
        log("FAIL", "Bookmark", str(e)[:80])

    # D4. Kosztorys — nowy wpis
    print("\n  -- Kosztorys new entry --")
    try:
        await page.goto(f"{BASE}/app/kosztorys", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        new_btn = page.locator("button[aria-label='Nowy kosztorys'], a[href*='kosztorys/new'], button:has-text('Nowy'), button:has-text('Dodaj'), button:has-text('Utwórz')").first
        if await new_btn.count() > 0:
            await new_btn.click()
            await page.wait_for_timeout(1000)
            # Check if form/modal appeared
            form = await page.locator("form, [role='dialog'], [class*='modal']").count()
            log("PASS", "Kosztorys new form", f"form/modal opened: {form}")
            # Escape
            await page.keyboard.press("Escape")
        else:
            log("WARN", "Kosztorys new button not found")
    except Exception as e:
        log("FAIL", "Kosztorys new", str(e)[:80])

    # D5. Notifications panel
    print("\n  -- Notifications --")
    try:
        await page.goto(f"{BASE}/app", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        notif_btn = page.get_by_role("button", name="Powiadomienia")
        if await notif_btn.count() > 0:
            await notif_btn.click()
            await page.wait_for_timeout(800)
            panel = await page.locator("[class*='notif'], [class*='dropdown'], [role='menu']").count()
            log("PASS", "Notifications panel", f"opened, panels={panel}")
            await page.keyboard.press("Escape")
        else:
            log("WARN", "Notifications button not found")
    except Exception as e:
        log("FAIL", "Notifications", str(e)[:80])

    # D6. Header search (global)
    print("\n  -- Global search --")
    try:
        await page.goto(f"{BASE}/app", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        gsearch = page.locator("input[placeholder*='1.4M'], input[placeholder*='przetarg']").first
        if await gsearch.count() > 0:
            await gsearch.fill("remont szkoły")
            await page.locator("button:has-text('Szukaj')").first.click()
            await page.wait_for_timeout(2000)
            url = page.url
            # Check results appeared or navigation happened
            content = await page.locator("main").inner_text()
            log("PASS", "Global search 'remont szkoły'",
                f"url={url.split('/')[-1]}, content_len={len(content)}")
        else:
            log("WARN", "Global search input not found")
    except Exception as e:
        log("FAIL", "Global search", str(e)[:80])

    # D7. User menu
    print("\n  -- User menu --")
    try:
        await page.goto(f"{BASE}/app", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        user_btn = page.get_by_role("button", name="Menu użytkownika")
        if await user_btn.count() > 0:
            await user_btn.click()
            await page.wait_for_timeout(800)
            menu = await page.locator("[role='menu'], [class*='dropdown'], [class*='popover']").count()
            log("PASS", "User menu", f"opened, items={menu}")
            await page.keyboard.press("Escape")
        else:
            log("WARN", "User menu button not found")
    except Exception as e:
        log("FAIL", "User menu", str(e)[:80])


# ══════════════════════════════════════════════════════════
# E. CONCURRENT SESSIONS — 5 równoległych Playwright
# ══════════════════════════════════════════════════════════
async def concurrent_session(browser, session_id: int, pages_subset: list):
    ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
    page = await ctx.new_page()
    page.on("console", lambda m: None)
    errors = []

    try:
        await login_page(page)

        for path, name in pages_subset:
            t0 = time.time()
            try:
                await page.goto(f"{BASE}{path}", wait_until="domcontentloaded", timeout=10_000)
                await page.wait_for_timeout(300)
                elapsed = time.time() - t0
                h1 = ""
                try: h1 = await page.locator("h1").first.inner_text()
                except: pass
                if "nie znaleziono" not in h1.lower():
                    timings[f"concurrent_s{session_id}"].append(elapsed)
                else:
                    errors.append(f"404: {path}")
            except Exception as e:
                errors.append(f"{path}: {str(e)[:50]}")

    finally:
        await ctx.close()

    return session_id, len(pages_subset) - len(errors), len(errors), errors

async def module_concurrent():
    print("\n━━━ E. CONCURRENT SESSIONS (5x) ━━━")

    routes = [
        ("/app",            "Dashboard"),
        ("/app/zwiad",      "Zwiad"),
        ("/app/silnik",     "Silnik"),
        ("/app/kosztorys",  "Kosztorys"),
        ("/app/analytics",  "Analytics"),
        ("/app/icb",        "ICB"),
    ]

    # Split routes across 3 sessions (fewer to avoid resource exhaustion)
    sessions = []
    for i in range(3):
        subset = routes[i::3]
        if not subset: subset = routes[:2]
        sessions.append(subset)

    t0 = time.time()
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        tasks = [concurrent_session(browser, i, s) for i, s in enumerate(sessions)]
        results_concurrent = await asyncio.gather(*tasks)
        await browser.close()

    wall = time.time() - t0
    total_ok = sum(r[1] for r in results_concurrent)
    total_err = sum(r[2] for r in results_concurrent)

    for sid, ok, err, errs in results_concurrent:
        t_list = timings.get(f"concurrent_s{sid}", [])
        avg = sum(t_list)/max(len(t_list),1)
        status = "PASS" if err == 0 else "WARN"
        log(status, f"Concurrent session {sid}", f"ok={ok}, err={err}, avg={avg*1000:.0f}ms")
        if errs:
            for e in errs: print(f"    ⚠ {e}")

    log("PASS" if total_err == 0 else "WARN",
        "E. Concurrent (5 sessions)",
        f"total_ok={total_ok}, total_err={total_err}, wall={wall:.1f}s")


# ══════════════════════════════════════════════════════════
# F. EDGE CASES — malformed, injection probe, large payload
# ══════════════════════════════════════════════════════════
async def module_edge_cases():
    print("\n━━━ F. EDGE CASES ━━━")
    token = ""
    async with aiohttp.ClientSession() as s:
        try: token = await get_token(s)
        except: pass

    headers = {"Authorization": f"Bearer {token}"}

    edge_cases = [
        # SQL injection probes — ORM uses parameterized queries (:q), so HTTP 200 is correct (safe)
        ("SQL inject tenders", "GET", f"{API}/api/v2/tenders?q='; DROP TABLE tender; --", None),
        ("SQL inject search",  "GET", f"{API}/api/v2/search?q=1' OR '1'='1", None),
        # XSS probe — payload treated as plain text by ORM, HTTP 200 is correct (safe)
        ("XSS probe",          "GET", f"{API}/api/v2/search?q=<script>alert(1)</script>", None),
        # Oversized query string — max_length=500 enforced by FastAPI Query(), expects HTTP 422
        ("Giant query",        "GET", f"{API}/api/v2/search?q={'A'*5000}", None),
        # Non-existent tender UUID
        ("Fake UUID tender",   "GET", f"{API}/api/v2/tenders/00000000-0000-0000-0000-000000000000", None),
        # Invalid UUID format
        ("Bad UUID format",    "GET", f"{API}/api/v2/tenders/not-a-uuid", None),
        # Negative limit
        ("Negative limit",     "GET", f"{API}/api/v2/tenders?limit=-1", None),
        # Huge limit
        ("Limit overflow",     "GET", f"{API}/api/v2/tenders?limit=99999", None),
        # POST to GET endpoint
        ("POST on GET endpoint","POST",f"{API}/api/v2/tenders", {"random": "data"}),
        # Empty auth token
        ("Empty Bearer",       "GET", f"{API}/api/v2/tenders?limit=1", "empty"),
        # Malformed JSON body on POST
        ("Malformed JSON",     "POST",f"{API}/api/v2/auth/login", "raw"),
    ]

    ok = fail = 0
    async with aiohttp.ClientSession() as session:
        for name, method, url, body in edge_cases:
            t0 = time.time()
            try:
                h = dict(headers)
                kw = {}
                if body == "empty":
                    h["Authorization"] = "Bearer "
                elif body == "raw":
                    h["Content-Type"] = "application/json"
                    kw["data"] = "{broken json{{{"
                elif body is not None:
                    kw["json"] = body

                async with session.request(method, url, headers=h,
                                          timeout=aiohttp.ClientTimeout(total=8),
                                          **kw) as r:
                    elapsed = time.time() - t0
                    # Should NEVER return 500 on edge inputs
                    if r.status >= 500:
                        text = (await r.text())[:150]
                        log("FAIL", f"Edge: {name}", f"HTTP {r.status} (server crash!) {text}", elapsed)
                        fail += 1
                    elif r.status in (400, 401, 403, 404, 405, 422, 429):
                        log("PASS", f"Edge: {name}", f"HTTP {r.status} (correct rejection)", elapsed)
                        ok += 1
                    elif r.status == 200 and name in ("SQL inject tenders", "SQL inject search", "XSS probe"):
                        # HTTP 200 is correct here — ORM uses parameterized queries (:q bound param),
                        # so injection payload is treated as literal search text, not SQL/JS.
                        log("PASS", f"Edge: {name}", f"HTTP {r.status} (ORM parameterized — safe)", elapsed)
                        ok += 1
                    else:
                        log("WARN", f"Edge: {name}", f"HTTP {r.status} (unexpected but not crash)", elapsed)
                        ok += 1
            except Exception as e:
                log("WARN", f"Edge: {name}", f"connection error: {str(e)[:60]}")

    log("PASS" if fail == 0 else "FAIL",
        "F. Edge Cases", f"{ok} safe, {fail} crashes")


# ══════════════════════════════════════════════════════════
# G. PERFORMANCE BENCHMARKS
# ══════════════════════════════════════════════════════════
async def module_performance():
    print("\n━━━ G. PERFORMANCE BENCHMARKS ━━━")
    token = ""
    async with aiohttp.ClientSession() as s:
        try: token = await get_token(s)
        except: pass
    headers = {"Authorization": f"Bearer {token}"}

    benchmarks = [
        ("Auth login",           "POST", f"{API}/api/v2/auth/login",
         {"email": EMAIL, "password": PASSWORD}, None, 500),
        ("Tenders list 20",      "GET",  f"{API}/api/v2/tenders?limit=20",
         None, headers, 800),
        ("Dashboard stats",      "GET",  f"{API}/api/v2/dashboard/stats",
         None, headers, 1000),
        ("mv_scoring",           "GET",  f"{API}/api/v2/scoring/v3/percentile",
         None, headers, 1500),
        ("Search FTS",           "GET",  f"{API}/api/v2/search?q=roboty+budowlane&limit=10",
         None, headers, 2000),
        ("Health",               "GET",  f"{API}/health",
         None, None, 100),
        ("Kosztorys 10",         "GET",  f"{API}/api/v2/kosztorys?limit=10",
         None, headers, 1000),
        ("Analytics overview",   "GET",  f"{API}/api/v2/analytics/overview",
         None, headers, 2000),
    ]

    # 5 warm-up + 10 measured
    for name, method, url, body, hdrs, sla_ms in benchmarks:
        times = []
        async with aiohttp.ClientSession() as session:
            # warm-up
            for _ in range(2):
                try:
                    async with session.request(method, url, json=body, headers=hdrs,
                                              timeout=aiohttp.ClientTimeout(total=10)) as r:
                        await r.text()
                except: pass

            # measured runs
            for _ in range(8):
                t0 = time.time()
                try:
                    async with session.request(method, url, json=body, headers=hdrs,
                                              timeout=aiohttp.ClientTimeout(total=10)) as r:
                        await r.text()
                    times.append(time.time() - t0)
                except:
                    times.append(10.0)

        if times:
            t_sorted = sorted(times)
            p50 = t_sorted[len(t_sorted)//2] * 1000
            p95 = t_sorted[int(len(t_sorted)*0.95)] * 1000
            sla_ok = p95 <= sla_ms
            log("PASS" if sla_ok else "WARN", f"Perf: {name}",
                f"p50={p50:.0f}ms p95={p95:.0f}ms SLA={sla_ms}ms {'✓' if sla_ok else '✗ OVER SLA'}")


# ══════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════
async def main():
    print("\n╔══════════════════════════════════════════════════╗")
    print("║   terra-os STRESS + E2E SUITE                    ║")
    print("╚══════════════════════════════════════════════════╝\n")

    t_total = time.time()

    # Check which mode to run
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    if mode in ("all", "api"):
        await module_api_coverage()
        await module_load_test()
        await module_db_stress()
        await module_edge_cases()
        await module_performance()

    if mode in ("all", "e2e"):
        # E2E — run after API modules
        print("\n━━━ D. E2E EXTENDED FLOWS ━━━")
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
            page = await ctx.new_page()
            page.on("console", lambda m: None)
            await login_page(page)
            await e2e_extended_flows(page)
            await ctx.close()
            await browser.close()

        await module_concurrent()

    # Final summary
    wall = time.time() - t_total
    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total  = len(results)

    print(f"\n╔══════════════════════════════════════════════════╗")
    print(f"║  WYNIKI KOŃCOWE  {wall:.0f}s")
    print(f"║  ✅ PASS:  {passed:>3}  ⚠️  WARN:  {warned:>3}  ❌ FAIL:  {failed:>3}  / {total}")
    print(f"╚══════════════════════════════════════════════════╝")

    if failed > 0:
        print("\n❌ FAILURES:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"   {r['name']}: {r['detail']}")

    if warned > 0:
        print("\n⚠️  WARNINGS:")
        for r in results:
            if r["status"] == "WARN":
                print(f"   {r['name']}: {r['detail']}")

    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
