-- 账号表：首次启动后可注册一个账号，之后注册接口关闭
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

-- 校招投递记录表
CREATE TABLE IF NOT EXISTS applications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT NOT NULL,                -- 公司名
    position    TEXT NOT NULL,                -- 岗位名
    city        TEXT    DEFAULT '',           -- 工作城市
    channel     TEXT    DEFAULT '',           -- 投递渠道：官网/BOSS/牛客/内推...
    salary      TEXT    DEFAULT '',           -- 薪资范围（原文记录即可）
    apply_date  TEXT    NOT NULL,             -- 投递日期 YYYY-MM-DD
    status      TEXT    NOT NULL DEFAULT '已投递',
    jd_url      TEXT    DEFAULT '',           -- 岗位 JD 链接
    note        TEXT    DEFAULT '',           -- 备注/复盘
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications (status);
CREATE INDEX IF NOT EXISTS idx_applications_date   ON applications (apply_date);
