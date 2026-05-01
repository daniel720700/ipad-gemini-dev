"""Flask server for SA Dashboard — login UI + daily auto-refresh."""

import asyncio
import csv
import io
import json
import os
import secrets
import threading
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import (Flask, jsonify, render_template, request,
                   Response, session, redirect, url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from scraper import load_cache, run_scraper, TICKERS, DATA_DIR

# ── Flask 설정 ──────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SA_SECRET_KEY") or secrets.token_hex(32)

# ── Rate Limiting (로그인 브루트포스 방지) ────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],          # 기본 제한 없음 (로그인에만 적용)
    storage_uri="memory://",
)

SETTINGS_FILE = DATA_DIR / "settings.json"

# ── 스크래핑 상태 ────────────────────────────────────────────────────
_scrape_lock  = threading.Lock()
_scrape_status = {"running": False, "message": "", "last_run": None}

# ── 설정 로드/저장 ───────────────────────────────────────────────────
def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {"refresh_hour": 7, "refresh_minute": 0}   # 기본: 매일 오전 7시


def save_settings(s: dict):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2))


# ── APScheduler ──────────────────────────────────────────────────────
scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _scheduled_scrape():
    """스케줄러가 호출하는 함수 — 저장된 자격증명 사용."""
    email    = _scrape_status.get("_email")
    password = _scrape_status.get("_password")
    if not email or not password:
        print("[스케줄] 자격증명 없음 — 건너뜀")
        return
    _run_scraper_bg(email, password)


def _apply_schedule(hour: int, minute: int):
    scheduler.remove_all_jobs()
    scheduler.add_job(
        _scheduled_scrape,
        CronTrigger(hour=hour, minute=minute, timezone="Asia/Seoul"),
        id="daily_refresh",
        replace_existing=True,
    )
    print(f"[스케줄] 매일 {hour:02d}:{minute:02d} (KST) 자동 갱신 설정됨")


def _next_run_str() -> str:
    jobs = scheduler.get_jobs()
    if not jobs:
        return "설정 안 됨"
    nxt = jobs[0].next_run_time
    if nxt:
        return nxt.strftime("%Y-%m-%d %H:%M KST")
    return "—"


# ── 스크래핑 공통 실행 ────────────────────────────────────────────────
def _run_scraper_bg(email: str, password: str):
    if _scrape_lock.locked():
        return
    def _work():
        with _scrape_lock:
            _scrape_status["running"] = True
            _scrape_status["message"] = "스크래핑 시작..."
            try:
                asyncio.run(run_scraper(email, password))
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                _scrape_status["message"] = f"완료 ({now})"
                _scrape_status["last_run"] = now
            except Exception as e:
                _scrape_status["message"] = f"오류: {e}"
            finally:
                _scrape_status["running"] = False
    threading.Thread(target=_work, daemon=True).start()


# ── 인증 헬퍼 ────────────────────────────────────────────────────────
def logged_in() -> bool:
    return bool(session.get("sa_email"))


# ── 라우트 ───────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html", logged_in=logged_in())


@app.route("/api/login", methods=["POST"])
@limiter.limit("5 per minute; 20 per hour")
def api_login():
    body = request.get_json(force=True) or {}
    email    = body.get("email", "").strip()
    password = body.get("password", "").strip()
    if not email or not password:
        return jsonify({"ok": False, "error": "이메일과 비밀번호를 입력하세요."}), 400

    session["sa_email"]    = email
    session["sa_password"] = password
    session.permanent      = True

    # 자격증명을 스케줄러용으로도 저장
    _scrape_status["_email"]    = email
    _scrape_status["_password"] = password

    return jsonify({"ok": True})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    _scrape_status.pop("_email", None)
    _scrape_status.pop("_password", None)
    return jsonify({"ok": True})


@app.route("/api/data")
def api_data():
    if not logged_in():
        return jsonify({"error": "login_required"}), 401
    data = load_cache()
    if data is None:
        return jsonify({"error": "no_data"}), 404
    return jsonify(data)


@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    if not logged_in():
        return jsonify({"error": "login_required"}), 401
    if _scrape_lock.locked():
        return jsonify({"status": "running"}), 202
    email    = session["sa_email"]
    password = session["sa_password"]
    _run_scraper_bg(email, password)
    return jsonify({"status": "started"})


@app.route("/api/status")
def api_status():
    settings = load_settings()
    return jsonify({
        **_scrape_status,
        "next_run": _next_run_str(),
        "refresh_hour":   settings["refresh_hour"],
        "refresh_minute": settings["refresh_minute"],
        "logged_in": logged_in(),
    })


@app.route("/api/schedule", methods=["POST"])
def api_schedule():
    if not logged_in():
        return jsonify({"error": "login_required"}), 401
    body = request.get_json(force=True) or {}
    hour   = int(body.get("hour",   7))
    minute = int(body.get("minute", 0))
    settings = load_settings()
    settings["refresh_hour"]   = hour
    settings["refresh_minute"] = minute
    save_settings(settings)
    _apply_schedule(hour, minute)
    return jsonify({"ok": True, "next_run": _next_run_str()})


@app.route("/api/export/csv")
def export_csv():
    if not logged_in():
        return redirect(url_for("index"))
    data = load_cache()
    if not data:
        return "데이터 없음", 404

    fields = [
        "ticker", "quant_rating", "quant_signal",
        "quant_valuation", "quant_growth", "quant_profitability",
        "quant_momentum", "quant_revisions",
        "sa_analyst_rating", "sector",
        "pe_fwd", "pe_sector_grade", "pe_5y_avg", "peg_fwd",
        "revenue_growth_fwd", "eps_growth_fwd", "eps_lt_cagr",
        "gross_margin", "net_margin", "cfo",
        "rsi",
        "eps_up", "eps_down", "rev_up", "rev_down",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for ticker in TICKERS:
        row = data["stocks"].get(ticker, {})
        writer.writerow({f: row.get(f, "") for f in fields})

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=sa_dashboard_{ts}.csv"},
    )


# ── Rate limit 초과 핸들러 ───────────────────────────────────────────
@app.errorhandler(429)
def rate_limit_handler(e):
    return jsonify({
        "ok": False,
        "error": "로그인 시도가 너무 많습니다. 잠시 후 다시 시도하세요."
    }), 429


# ── 앱 시작 ─────────────────────────────────────────────────────────
def create_app():
    settings = load_settings()
    if not scheduler.running:
        scheduler.start()
    _apply_schedule(settings["refresh_hour"], settings["refresh_minute"])
    return app


if __name__ == "__main__":
    port = int(os.environ.get("SA_PORT", 5050))
    print(f"✅ SA Dashboard → http://localhost:{port}")
    create_app().run(host="0.0.0.0", port=port, debug=False)
