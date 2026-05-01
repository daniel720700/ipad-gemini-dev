"""SA Dashboard scraper — Seeking Alpha API 직접 수집."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

TICKERS = ["TSLA", "GOOGL", "AMZN", "LITE", "SNDK", "CRDO", "MU", "DELL", "AMD", "NVDA", "ARM", "BE"]
DATA_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_FILE = DATA_DIR / "sa_cache.json"
SESSION_FILE = DATA_DIR / "sa_session.json"

# SA Quant grade numeric ID → letter grade
GRADE_MAP = {
    1: "A+", 2: "A", 3: "A-",
    4: "B+", 5: "B", 6: "B-",
    7: "C+", 8: "C", 9: "C-",
    10: "D+", 11: "D", 12: "D-",
    13: "F",
}

SA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://seekingalpha.com/",
    "Origin": "https://seekingalpha.com",
}


def load_cache() -> Optional[dict]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _load_cookies() -> Optional[dict]:
    if SESSION_FILE.exists():
        try:
            data = json.loads(SESSION_FILE.read_text())
            return {c["name"]: c["value"] for c in data.get("cookies", [])}
        except Exception:
            pass
    return None


def _quant_signal(score: float) -> str:
    if score >= 4.5:
        return "Strong Buy"
    if score >= 3.5:
        return "Buy"
    if score >= 2.5:
        return "Hold"
    if score >= 1.5:
        return "Sell"
    return "Strong Sell"


def _sa_get(url: str, cookies: dict, retries: int = 2) -> Optional[dict]:
    for attempt in range(retries):
        try:
            r = requests.get(url, cookies=cookies, headers=SA_HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(3 * (attempt + 1))
        except Exception:
            time.sleep(1)
    return None


def _fmt(v, digits: int = 2) -> Optional[float]:
    if v is None:
        return None
    try:
        return round(float(v), digits)
    except Exception:
        return None


def _fetch_ticker(symbol: str, cookies: dict) -> dict:
    result: dict = {
        "ticker": symbol,
        "quant_rating": None, "quant_signal": None,
        "quant_valuation": None, "quant_growth": None,
        "quant_profitability": None, "quant_momentum": None, "quant_revisions": None,
        "sa_analyst_rating": None, "sector": None,
        "pe_fwd": None, "pe_sector_grade": None, "pe_5y_avg": None, "peg_fwd": None,
        "revenue_growth_fwd": None, "eps_growth_fwd": None, "eps_lt_cagr": None,
        "gross_margin": None, "net_margin": None, "cfo": None,
        "rsi": None,
        "eps_up": None, "eps_down": None, "rev_up": None, "rev_down": None,
    }

    # ── 1) Ratings API (Quant Rating + sub-grades + Analyst) ────────
    ratings_resp = _sa_get(
        f"https://seekingalpha.com/api/v3/symbols/{symbol}/ratings", cookies
    )
    if ratings_resp:
        items = ratings_resp.get("data", [])
        if items:
            r = items[0].get("attributes", {}).get("ratings", {})
            quant = r.get("quantRating")
            if quant is not None:
                result["quant_rating"] = _fmt(quant)
                result["quant_signal"] = _quant_signal(float(quant))
            result["quant_valuation"]     = GRADE_MAP.get(r.get("valueGrade"))
            result["quant_growth"]        = GRADE_MAP.get(r.get("growthGrade"))
            result["quant_profitability"] = GRADE_MAP.get(r.get("profitabilityGrade"))
            result["quant_momentum"]      = GRADE_MAP.get(r.get("momentumGrade"))
            result["quant_revisions"]     = GRADE_MAP.get(r.get("epsRevisionsGrade"))
            sell = r.get("sellSideRating")
            if sell is not None:
                result["sa_analyst_rating"] = _fmt(sell)

    time.sleep(0.5)  # rate-limit 방지

    # ── 2) Metrics API (재무 수치) ────────────────────────────────────
    metrics_resp = _sa_get(
        f"https://seekingalpha.com/api/v3/symbols/{symbol}/metrics", cookies
    )
    if metrics_resp:
        included = metrics_resp.get("included", [])
        data_items = metrics_resp.get("data", [])

        id_to_field = {
            item["id"]: item["attributes"]["field"]
            for item in included
            if item.get("type") == "metric_type"
        }

        fv: dict = {}
        for item in data_items:
            tid = (
                item.get("relationships", {})
                .get("metric_type", {})
                .get("data", {})
                .get("id")
            )
            if tid and tid in id_to_field:
                fv[id_to_field[tid]] = item.get("attributes", {}).get("value")

        def g(key):
            return _fmt(fv.get(key))

        result["pe_fwd"]   = g("pe_nongaap_fy1")
        result["pe_5y_avg"] = g("pe_nongaap_fy1_avg_5y")
        result["peg_fwd"]  = g("peg_nongaap_fy1")
        result["gross_margin"] = g("gross_margin")
        result["net_margin"]   = g("net_margin")
        result["rsi"]          = g("rsi_14d_smth_250d")
        result["eps_lt_cagr"]  = g("eps_ltg")

        # 매출성장(FWD): FY1 컨센서스 vs TTM 매출
        rev_est = fv.get("consensus_revenue_estimates_annual")
        rev_ttm = fv.get("total_revenue")
        if rev_est and rev_ttm and float(rev_ttm) > 0:
            result["revenue_growth_fwd"] = round(
                (float(rev_est) / float(rev_ttm) - 1) * 100, 2
            )

        # EPS 성장(FWD): FY1 컨센서스 Non-GAAP vs 최근 GAAP 성장률
        eps_fwd = fv.get("eps_gaap_growth_3y_annual_fwd")
        if eps_fwd is not None:
            result["eps_growth_fwd"] = _fmt(float(eps_fwd) * 100)
        else:
            result["eps_growth_fwd"] = g("diluted_eps_growth")

        # CFO ($B)
        cfo = fv.get("nocf") or fv.get("cash_from_operations_as_reported")
        if cfo:
            result["cfo"] = round(float(cfo) / 1e9, 2)

        # Earnings Revisions (분기 = 3개월)
        result["eps_up"]   = g("eps_revision_analysts_num_up_quarterly")
        result["eps_down"] = g("eps_revision_analysts_num_down_quarterly")
        result["rev_up"]   = g("revenue_revision_analysts_num_up_quarterly")
        result["rev_down"] = g("revenue_revision_analysts_num_down_quarterly")

    # ── 3) 섹터: yfinance 보완 ────────────────────────────────────────
    if result["sector"] is None:
        try:
            import yfinance as yf
            result["sector"] = yf.Ticker(symbol).info.get("sector")
        except Exception:
            pass

    print(
        f"  ✅ {symbol}: Quant={result['quant_rating']}({result['quant_signal']})"
        f"  P/E={result['pe_fwd']}  RSI={result['rsi']}"
        f"  매출성장={result['revenue_growth_fwd']}%"
    )
    return result


# ── 전체 실행 ────────────────────────────────────────────────────────
async def run_scraper(email: str, password: str) -> dict:
    """email/password는 서버 호환성용 (SA API는 세션 쿠키 사용)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    cookies = _load_cookies()
    if not cookies:
        print("❌ SA 세션 쿠키 없음 — 대시보드에서 로그인 후 새로고침하세요.")
        return {"error": "no_session", "updated_at": datetime.now().isoformat()}

    results: dict = {}
    for symbol in TICKERS:
        print(f"수집 중: {symbol} ...")
        results[symbol] = _fetch_ticker(symbol, cookies)
        time.sleep(1)  # rate-limit 방지

    output = {
        "updated_at": datetime.now().isoformat(),
        "stocks": results,
        "source": "Seeking Alpha API",
        "note": "SA API 직접 수집 (session cookie 기반)",
    }
    CACHE_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print("✅ 수집 완료")
    return output
