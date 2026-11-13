"""校招投递管理台 —— Flask 入口：页面、鉴权、REST API。"""
import functools
import math
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from flask import (
    Flask, current_app, jsonify, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

import db as database

BASE_DIR = Path(__file__).resolve().parent

# 状态按流程先后排列，前端漏斗图直接复用这个顺序
STATUSES = ["已投递", "简历通过", "笔试", "一面", "二面", "HR面", "Offer", "已挂"]
INTERVIEW_STATUSES = ("笔试", "一面", "二面", "HR面", "Offer")
EDITABLE_FIELDS = [
    "company", "position", "city", "channel",
    "salary", "apply_date", "status", "jd_url", "note",
]


# ---------------------------------------------------------------- 工具函数

def local_now():
    """按配置时区取当前时间，避免部署到 UTC 服务器后日期偏移。"""
    return datetime.now(ZoneInfo(current_app.config["TIMEZONE"]))


def now_str():
    return local_now().strftime("%Y-%m-%d %H:%M:%S")


def row_to_dict(row):
    return {key: row[key] for key in row.keys()}


def clean_payload(data, partial=False):
    """校验并清洗入参，返回 (record, error)。"""
    record = {}
    for field in EDITABLE_FIELDS:
        value = data.get(field)
        if value is None:
            continue
        record[field] = value.strip() if isinstance(value, str) else str(value)

    if partial:
        if not record:
            return None, "没有需要更新的字段"
    else:
        record.setdefault("status", "已投递")
        for field in ("city", "channel", "salary", "jd_url", "note"):
            record.setdefault(field, "")
        for field, label in (("company", "公司"), ("position", "岗位"), ("apply_date", "投递日期")):
            if not record.get(field):
                return None, f"{label}不能为空"

    if "status" in record and record["status"] not in STATUSES:
        return None, "状态值不合法"
    if "apply_date" in record:
        try:
            datetime.strptime(record["apply_date"], "%Y-%m-%d")
        except ValueError:
            return None, "投递日期格式应为 YYYY-MM-DD"
    return record, None


def build_filters(keyword, status):
    """把筛选条件下推成 SQL 片段，避免全表捞出后在应用层过滤。"""
    where = " WHERE 1 = 1"
    params = []
    if keyword:
        where += " AND (company LIKE ? OR position LIKE ? OR note LIKE ?)"
        like = f"%{keyword}%"
        params += [like, like, like]
    if status:
        where += " AND status = ?"
        params.append(status)
    return where, params


def login_required(view):
    """接口未登录返回 401，页面未登录跳转登录页。"""

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "未登录或登录已过期"}), 401
            return redirect(url_for("login_page"))
        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------- 应用工厂

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE=str(BASE_DIR / "data" / "job_tracker.db"),
        TIMEZONE=os.environ.get("APP_TIMEZONE", "Asia/Shanghai"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        PAGE_SIZE_DEFAULT=20,
        PAGE_SIZE_MAX=100,
    )
    if test_config:
        app.config.update(test_config)

    app.json.ensure_ascii = False
    database.init_db(app.config["DATABASE"])
    app.teardown_appcontext(database.close_db)

    # ------------------------------------------------------------ 页面

    @app.get("/")
    @login_required
    def index():
        return render_template(
            "index.html",
            statuses=STATUSES,
            username=session.get("username", ""),
        )

    @app.get("/login")
    def login_page():
        if session.get("user_id"):
            return redirect(url_for("index"))
        return render_template("login.html")

    # ------------------------------------------------------------ 鉴权

    @app.get("/api/auth/status")
    def auth_status():
        conn = database.get_db()
        initialized = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] > 0
        return jsonify({
            "initialized": initialized,
            "logged_in": bool(session.get("user_id")),
            "username": session.get("username"),
        })

    @app.post("/api/auth/register")
    def register():
        conn = database.get_db()
        if conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"] > 0:
            return jsonify({"error": "系统已初始化，无法重复注册"}), 403

        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not 3 <= len(username) <= 20:
            return jsonify({"error": "用户名长度需为 3-20 个字符"}), 400
        if len(password) < 6:
            return jsonify({"error": "密码至少 6 位"}), 400

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), now_str()),
        )
        conn.commit()
        session.clear()
        session["user_id"] = cursor.lastrowid
        session["username"] = username
        session.permanent = True
        return jsonify({"username": username}), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        row = database.get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row is None or not check_password_hash(row["password_hash"], password):
            # 不区分"用户不存在"和"密码错误"，避免暴露账号是否注册
            return jsonify({"error": "用户名或密码错误"}), 401

        session.clear()
        session["user_id"] = row["id"]
        session["username"] = row["username"]
        session.permanent = True
        return jsonify({"username": row["username"]})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return "", 204

    # ------------------------------------------------------------ 投递记录

    @app.get("/api/applications")
    @login_required
    def list_applications():
        keyword = request.args.get("keyword", "").strip()
        status = request.args.get("status", "").strip()
        page_size = request.args.get("page_size", app.config["PAGE_SIZE_DEFAULT"], type=int)
        page_size = max(1, min(page_size, app.config["PAGE_SIZE_MAX"]))
        page = max(1, request.args.get("page", 1, type=int))

        where, params = build_filters(keyword, status)
        conn = database.get_db()

        total = conn.execute(
            f"SELECT COUNT(*) AS c FROM applications{where}", params
        ).fetchone()["c"]
        pages = math.ceil(total / page_size) if total else 0
        # 删到最后一页之后时回退到有效页，避免返回空白页
        if pages and page > pages:
            page = pages
        offset = (page - 1) * page_size

        rows = conn.execute(
            f"SELECT * FROM applications{where} "
            "ORDER BY apply_date DESC, id DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()

        return jsonify({
            "items": [row_to_dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        })

    @app.post("/api/applications")
    @login_required
    def create_application():
        record, error = clean_payload(request.get_json(silent=True) or {})
        if error:
            return jsonify({"error": error}), 400

        record["created_at"] = now_str()
        record["updated_at"] = record["created_at"]

        columns = ", ".join(record)
        placeholders = ", ".join("?" * len(record))
        conn = database.get_db()
        cursor = conn.execute(
            f"INSERT INTO applications ({columns}) VALUES ({placeholders})",
            list(record.values()),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(row_to_dict(row)), 201

    @app.put("/api/applications/<int:app_id>")
    @login_required
    def update_application(app_id):
        record, error = clean_payload(request.get_json(silent=True) or {}, partial=True)
        if error:
            return jsonify({"error": error}), 400

        conn = database.get_db()
        if conn.execute("SELECT 1 FROM applications WHERE id = ?", (app_id,)).fetchone() is None:
            return jsonify({"error": "记录不存在"}), 404

        record["updated_at"] = now_str()
        assignments = ", ".join(f"{field} = ?" for field in record)
        conn.execute(
            f"UPDATE applications SET {assignments} WHERE id = ?",
            [*record.values(), app_id],
        )
        conn.commit()
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return jsonify(row_to_dict(row))

    @app.delete("/api/applications/<int:app_id>")
    @login_required
    def delete_application(app_id):
        conn = database.get_db()
        cursor = conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "记录不存在"}), 404
        return "", 204

    @app.get("/api/stats")
    @login_required
    def stats():
        conn = database.get_db()
        total = conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]

        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM applications GROUP BY status"
        ).fetchall()
        by_status = {row["status"]: row["c"] for row in status_rows}

        channel_rows = conn.execute(
            "SELECT COALESCE(NULLIF(channel, ''), '未填写') AS name, COUNT(*) AS c "
            "FROM applications GROUP BY name ORDER BY c DESC"
        ).fetchall()

        # 时间范围在 Python 侧按配置时区算好再下推，避免依赖数据库服务器的时区
        cutoff = (local_now() - timedelta(days=29)).strftime("%Y-%m-%d")
        trend_rows = conn.execute(
            "SELECT apply_date AS day, COUNT(*) AS c FROM applications "
            "WHERE apply_date >= ? GROUP BY apply_date ORDER BY apply_date",
            (cutoff,),
        ).fetchall()

        interview = sum(by_status.get(status, 0) for status in INTERVIEW_STATUSES)
        offers = by_status.get("Offer", 0)

        return jsonify({
            "total": total,
            "interview": interview,
            "offers": offers,
            "interview_rate": round(interview / total * 100, 1) if total else 0.0,
            "offer_rate": round(offers / total * 100, 1) if total else 0.0,
            "by_status": by_status,
            "by_channel": [{"name": row["name"], "count": row["c"]} for row in channel_rows],
            "trend": [{"day": row["day"], "count": row["c"]} for row in trend_rows],
        })

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
