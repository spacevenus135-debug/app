#!/usr/bin/env python3
"""
💎 PREMIUM TELEGRAM GIVEAWAY BOT — UPGRADED
Animated Premium Emojis + Pro Admin Panel + Redeem Code System
"""

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    MessageEntity
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
import sqlite3
import random
import string
import datetime
import logging
import html
import re
import asyncio

# ── Roha premium emoji + keyboard system ────────────────────────────────────
from emojis_roha import (
    e, b, BT, EMOJI, DIV, PLATFORMS,
    btn, url_btn, back_btn, confirm_btn, danger_btn, row,
    kb_main, kb_admin_dash, kb_settings,
    kb_accounts_panel, kb_codes_panel, kb_user_action, kb_back,
    kb_platform_select,
    kb_add_accounts_platform_select,
    kb_generate_codes_platform_select,
    get_platforms, register_custom_app_emoji,
    kb_apps_panel, kb_remove_custom_app_select,
)

# Legacy alias so existing PE['x'] calls in message bodies still work
PE = EMOJI

# ── Regex to strip <tg-emoji emoji-id="..."> tags but keep the fallback glyph
_TG_EMOJI_RE = re.compile(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', re.DOTALL)


def _strip_custom_emoji(text: str) -> str:
    """Remove tg-emoji wrapper tags, keeping the inner fallback unicode glyph."""
    return _TG_EMOJI_RE.sub(r'\1', text)


async def safe_edit_message_text(query, text, **kwargs):
    """
    Wrapper around CallbackQuery.edit_message_text that survives dead/invalid
    custom emoji document IDs (Telegram raises BadRequest: Document_invalid).

    1. Try the edit as-is.
    2. If Telegram rejects it for an emoji/document reason, strip the
       <tg-emoji> tags to their plain fallback glyphs and retry.
    3. Swallow the harmless 'message is not modified' case; log + re-raise
       anything else.
    """
    try:
        return await query.edit_message_text(text, **kwargs)
    except BadRequest as exc:
        err = str(exc).lower()
        if "document_invalid" in err or "custom emoji" in err or "emoji" in err:
            logging.getLogger(__name__).warning(
                "[safe_edit_message_text] custom emoji rejected (%s) - retrying plain", exc
            )
            plain_text = _strip_custom_emoji(text)
            try:
                return await query.edit_message_text(plain_text, **kwargs)
            except BadRequest as exc2:
                if "message is not modified" in str(exc2).lower():
                    return None
                logging.getLogger(__name__).error(
                    "[safe_edit_message_text] retry also failed: %s", exc2
                )
                raise
        if "message is not modified" in err:
            return None
        raise

# ════════════════════════════════════════════════════════════════════════════
# ◆ CONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

BOT_TOKEN   = "8713091305:AAEO45WUbXwqnCMKgFkvYrzr0Y4pStApiI4"
ADMIN_IDS   = {8744777152}
DB_FILE     = "bot_data.db"

# States
STATE_ADD_ACCOUNTS          = 1
STATE_BROADCAST             = 2
STATE_SEARCH_USER           = 3
STATE_GENERATE_CODES        = 4
STATE_ADD_ADMIN             = 5
STATE_SET_WELCOME           = 6
STATE_CODE_PREFIX           = 7
STATE_AWAIT_PLATFORM_CODE   = 8   # user typing their redeem code
STATE_ADD_ACCOUNTS_LINES    = 9   # admin pasting account lines after platform chosen
STATE_GENERATE_CODES_COUNT  = 10  # admin typing count after platform chosen
STATE_ADD_CUSTOM_APP        = 11  # admin typing NAME|EMOJI_ID|PREFIX

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════════════════
# ◆ DATABASE
# ════════════════════════════════════════════════════════════════════════════

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _migrate_db(conn):
    """
    Safe migration — adds any missing columns to existing tables
    without touching data. Runs every startup, idempotent.
    """
    cursor = conn.cursor()

    # ── users table migrations ────────────────────────────────────────────
    existing_cols = {
        row[1] for row in cursor.execute("PRAGMA table_info(users)")
    }
    migrations_users = {
        "referral_by"    : "INTEGER",
        "is_admin"       : "INTEGER DEFAULT 0",
        "ban_reason"     : "TEXT",
        "redeemed_count" : "INTEGER DEFAULT 0",
        "is_banned"      : "INTEGER DEFAULT 0",
    }
    for col, col_type in migrations_users.items():
        if col not in existing_cols:
            logger.info(f"[MIGRATE] Adding column users.{col}")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")

    # ── accounts table migrations ─────────────────────────────────────────
    existing_acc_cols = {
        row[1] for row in cursor.execute("PRAGMA table_info(accounts)")
    }
    migrations_accounts = {
        "extra_info"    : "TEXT",
        "redeemed_by"   : "INTEGER",
        "redeemed_code" : "TEXT",
        "redeemed_at"   : "TIMESTAMP",
        "is_redeemed"   : "INTEGER DEFAULT 0",
        "platform"      : "TEXT",   # ← platform slug stored per-account
    }
    for col, col_type in migrations_accounts.items():
        if col not in existing_acc_cols:
            logger.info(f"[MIGRATE] Adding column accounts.{col}")
            cursor.execute(f"ALTER TABLE accounts ADD COLUMN {col} {col_type}")

    # ── redeem_codes table migrations ─────────────────────────────────────
    existing_rc_cols = {
        row[1] for row in cursor.execute("PRAGMA table_info(redeem_codes)")
    }
    migrations_rc = {
        "expires_at" : "TIMESTAMP",
        "used_by"    : "INTEGER",
        "used_at"    : "TIMESTAMP",
        "account_id" : "INTEGER",
        "is_used"    : "INTEGER DEFAULT 0",
        "platform"   : "TEXT",
    }
    for col, col_type in migrations_rc.items():
        if col not in existing_rc_cols:
            logger.info(f"[MIGRATE] Adding column redeem_codes.{col}")
            cursor.execute(f"ALTER TABLE redeem_codes ADD COLUMN {col} {col_type}")

    conn.commit()
    logger.info("[MIGRATE] Schema migration complete.")


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id        INTEGER PRIMARY KEY,
        username       TEXT,
        first_name     TEXT,
        last_name      TEXT,
        join_date      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_banned      INTEGER   DEFAULT 0,
        ban_reason     TEXT,
        redeemed_count INTEGER   DEFAULT 0,
        is_admin       INTEGER   DEFAULT 0,
        referral_by    INTEGER
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        account_type   TEXT NOT NULL,
        email          TEXT NOT NULL,
        password       TEXT NOT NULL,
        extra_info     TEXT,
        platform       TEXT,
        added_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_redeemed    INTEGER DEFAULT 0,
        redeemed_by    INTEGER,
        redeemed_code  TEXT,
        redeemed_at    TIMESTAMP,
        FOREIGN KEY (redeemed_by) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS redeem_codes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        code        TEXT UNIQUE NOT NULL,
        account_id  INTEGER,
        platform    TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at  TIMESTAMP,
        is_used     INTEGER DEFAULT 0,
        used_by     INTEGER,
        used_at     TIMESTAMP,
        FOREIGN KEY (account_id) REFERENCES accounts(id),
        FOREIGN KEY (used_by)    REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS bot_config (
        key   TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS broadcast_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        message    TEXT,
        sent_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS custom_apps (
        slug       TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        emoji_id   TEXT NOT NULL,
        prefix     TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_codes_code      ON redeem_codes(code);
    CREATE INDEX IF NOT EXISTS idx_accounts_type   ON accounts(account_type);
    CREATE INDEX IF NOT EXISTS idx_users_banned    ON users(is_banned);
    """)

    _migrate_db(conn)

    defaults = {
        "welcome_text"  : "Claim your premium accounts below.",
        "code_prefix"   : "GIFT",
        "code_length"   : "12",
        "max_per_user"  : "5",
        "bot_name"      : "Roha Giveaway Bot",
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO bot_config(key,value) VALUES(?,?)", (k, v))

    conn.commit()
    conn.close()

# ─── Config helpers ───────────────────────────────────────────────────────

def cfg_get(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_config WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None

def cfg_set(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO bot_config(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()

# ─── User helpers ─────────────────────────────────────────────────────────

def register_user(user_id, username=None, first_name=None, last_name=None, referral_by=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO users(user_id,username,first_name,last_name,referral_by) VALUES(?,?,?,?,?)",
        (user_id, username, first_name, last_name, referral_by)
    )
    conn.execute(
        "UPDATE users SET username=?,first_name=?,last_name=? WHERE user_id=?",
        (username, first_name, last_name, user_id)
    )
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def is_banned(user_id):
    conn = get_conn()
    row = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return bool(row["is_banned"]) if row else False

def is_admin(user_id):
    if user_id in ADMIN_IDS:
        return True
    conn = get_conn()
    row = conn.execute("SELECT is_admin FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return bool(row["is_admin"]) if row else False

def get_users(limit=10000, offset=0):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM users WHERE is_banned=0 ORDER BY join_date DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_count():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()
    conn.close()
    return row["c"]

def ban_user(user_id, reason="No reason"):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=1, ban_reason=? WHERE user_id=?", (reason, user_id))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=0, ban_reason=NULL WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ─── Account helpers ──────────────────────────────────────────────────────

def _parse_account_line(raw_line: str) -> tuple[str, str, str]:
    """
    Parse a raw account line into (email, password, full_raw_line).

    Supports formats:
      email:password | extra...
      email:password|extra...
      TYPE|EMAIL|PASSWORD|EXTRA   (legacy pipe-delimited)

    Returns (email, password, raw_line_stripped).
    The full raw line is always stored as extra_info so nothing is lost.
    """
    line = raw_line.strip()
    if not line:
        return None, None, None

    # ── Detect legacy pipe-only format: TYPE|EMAIL|PASSWORD|EXTRA ───────────
    # Heuristic: if first segment has no "@" and no ":", it's a TYPE field
    first_seg = line.split("|")[0].strip()
    if "|" in line and "@" not in first_seg and ":" not in first_seg:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            email    = parts[1]
            password = parts[2]
            return email, password, line

    # ── Primary format: email:password | extra... ────────────────────────────
    # Split only on the FIRST colon to get email
    colon_idx = line.find(":")
    if colon_idx == -1:
        return None, None, line  # can't parse, store raw anyway

    email = line[:colon_idx].strip()

    # Everything after the first colon
    rest = line[colon_idx + 1:]

    # Password ends at first " |" or "|" separator
    pipe_idx = rest.find("|")
    if pipe_idx != -1:
        password = rest[:pipe_idx].strip()
    else:
        # No pipe — password is the rest (might be "password extra" space-split)
        space_idx = rest.find(" ")
        if space_idx != -1:
            password = rest[:space_idx].strip()
        else:
            password = rest.strip()

    return email, password, line


def add_accounts_bulk(rows):
    """
    rows = list of (platform_slug, raw_line) tuples.
    Parses each raw_line, extracts email/password, stores full line as extra_info.
    Returns (added_count, error_count).
    """
    conn = get_conn()
    c = conn.cursor()
    added  = 0
    errors = 0
    for platform_slug, raw_line in rows:
        email, password, full_line = _parse_account_line(raw_line)
        if not email or not password or not full_line:
            errors += 1
            continue
        # account_type mirrors the platform slug for backward compat
        c.execute(
            """INSERT INTO accounts
               (account_type, email, password, extra_info, platform)
               VALUES (?, ?, ?, ?, ?)""",
            (platform_slug, email, password, full_line, platform_slug)
        )
        added += 1
    conn.commit()
    conn.close()
    return added, errors


def get_accounts(redeemed=None, limit=50, offset=0, acc_type=None, platform=None):
    conn = get_conn()
    q = "SELECT * FROM accounts WHERE 1=1"
    params = []
    if redeemed is not None:
        q += " AND is_redeemed=?"
        params.append(1 if redeemed else 0)
    if acc_type:
        q += " AND account_type=?"
        params.append(acc_type)
    if platform:
        q += " AND platform=?"
        params.append(platform)
    q += " ORDER BY id LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_available_count(acc_type=None, platform=None):
    conn = get_conn()
    q = "SELECT COUNT(*) as c FROM accounts WHERE is_redeemed=0"
    params = []
    if acc_type:
        q += " AND account_type=?"
        params.append(acc_type)
    if platform:
        q += " AND platform=?"
        params.append(platform)
    row = conn.execute(q, params).fetchone()
    conn.close()
    return row["c"]

def get_account_types():
    conn = get_conn()
    rows = conn.execute(
        "SELECT account_type, COUNT(*) as total, SUM(is_redeemed) as redeemed FROM accounts GROUP BY account_type"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ─── Custom apps helpers ──────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """
    Turn a display name into a URL/callback-safe slug.
    e.g. "DAZN" -> "dazn", "Apple TV+" -> "apple_tv"
    """
    slug = name.strip().lower()
    out = []
    for ch in slug:
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_", "+"):
            out.append("_")
    slug = "".join(out).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "app"


def get_custom_apps():
    """Return all admin-added custom apps as a list of dicts."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT slug, name, emoji_id, prefix, created_at FROM custom_apps ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_custom_app(name: str, emoji_id: str, prefix: str):
    """
    Insert a new custom app. Returns (ok: bool, message_or_slug: str).
    Rejects if the resulting slug collides with a built-in platform or an
    existing custom app.
    """
    name   = name.strip()
    prefix = prefix.strip().upper().replace(" ", "")
    if not name or not emoji_id.strip().isdigit() or not prefix:
        return False, "invalid_input"

    slug = _slugify(name)
    if slug in PLATFORMS:
        return False, "slug_collision_builtin"

    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM custom_apps WHERE slug=?", (slug,)).fetchone()
    if exists:
        conn.close()
        return False, "slug_collision_custom"

    conn.execute(
        "INSERT INTO custom_apps(slug, name, emoji_id, prefix) VALUES(?,?,?,?)",
        (slug, name, emoji_id.strip(), prefix)
    )
    conn.commit()
    conn.close()

    # Make the emoji usable immediately (buttons + message bodies) without restart
    register_custom_app_emoji(slug, emoji_id.strip())
    return True, slug


def remove_custom_app(slug: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM custom_apps WHERE slug=?", (slug,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("DELETE FROM custom_apps WHERE slug=?", (slug,))
    conn.commit()
    conn.close()
    return True

# ─── Code helpers ─────────────────────────────────────────────────────────

def generate_code(prefix="GIFT", length=12):
    chars = string.ascii_uppercase + string.digits
    rand_part = ''.join(random.choices(chars, k=length - len(prefix) - 1))
    return f"{prefix}-{rand_part}"

def create_codes_batch(account_ids, expires_hours=None, platform: str | None = None):
    """
    Generate redeem codes for a list of account IDs.
    Platform prefix is used if slug found in the merged platform registry
    (built-in PLATFORMS + admin-added custom apps).
    """
    all_platforms = get_platforms()
    if platform and platform in all_platforms:
        prefix = all_platforms[platform][2]
    else:
        prefix = cfg_get("code_prefix") or "GIFT"
    length = int(cfg_get("code_length") or 12)
    conn = get_conn()
    codes = []
    expires_at = None
    if expires_hours:
        expires_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=expires_hours)).isoformat()
    for acc_id in account_ids:
        while True:
            code = generate_code(prefix, length)
            exists = conn.execute("SELECT 1 FROM redeem_codes WHERE code=?", (code,)).fetchone()
            if not exists:
                break
        conn.execute(
            "INSERT INTO redeem_codes(code,account_id,platform,expires_at) VALUES(?,?,?,?)",
            (code, acc_id, platform, expires_at)
        )
        codes.append(code)
    conn.commit()
    conn.close()
    return codes

def redeem_code(code, user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM redeem_codes WHERE code=?", (code,)).fetchone()
    if not row:
        conn.close()
        return "not_found"
    if row["is_used"]:
        conn.close()
        return "used"
    if row["expires_at"] and datetime.datetime.utcnow().isoformat() > row["expires_at"]:
        conn.close()
        return "expired"
    max_per = int(cfg_get("max_per_user") or 5)
    u = conn.execute("SELECT redeemed_count FROM users WHERE user_id=?", (user_id,)).fetchone()
    if u and u["redeemed_count"] >= max_per:
        conn.close()
        return "limit"
    acc = conn.execute("SELECT * FROM accounts WHERE id=?", (row["account_id"],)).fetchone()
    if not acc:
        conn.close()
        return "no_account"
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE redeem_codes SET is_used=1, used_by=?, used_at=? WHERE code=?",
        (user_id, now, code)
    )
    conn.execute(
        "UPDATE accounts SET is_redeemed=1, redeemed_by=?, redeemed_code=?, redeemed_at=? WHERE id=?",
        (user_id, code, now, acc["id"])
    )
    conn.execute(
        "UPDATE users SET redeemed_count = redeemed_count + 1 WHERE user_id=?",
        (user_id,)
    )
    conn.commit()
    conn.close()
    result = dict(acc)
    result["_platform"] = row["platform"]
    return result

def get_stats():
    conn = get_conn()
    total_users   = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    banned_users  = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_banned=1").fetchone()["c"]
    total_acc     = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    avail_acc     = conn.execute("SELECT COUNT(*) as c FROM accounts WHERE is_redeemed=0").fetchone()["c"]
    total_codes   = conn.execute("SELECT COUNT(*) as c FROM redeem_codes").fetchone()["c"]
    used_codes    = conn.execute("SELECT COUNT(*) as c FROM redeem_codes WHERE is_used=1").fetchone()["c"]
    conn.close()
    return {
        "total_users"  : total_users,
        "banned_users" : banned_users,
        "total_acc"    : total_acc,
        "avail_acc"    : avail_acc,
        "total_codes"  : total_codes,
        "used_codes"   : used_codes,
    }

# ────────────────────────────────────────────────────────────────────────────
# ◆ REDEEM MESSAGE BUILDER
# Produces the clean full-account-line display, no email/password split.
# ────────────────────────────────────────────────────────────────────────────

def _build_redeem_msg(result: dict, plat_slug_hint: str | None = None) -> str:
    """
    Build the success message shown to a user after a successful redemption.
    Displays the full raw account line (extra_info) without splitting fields.
    """
    resolved_slug = result.get("_platform") or plat_slug_hint or result.get("platform") or result.get("account_type", "").lower()
    plat_info     = get_platforms().get(resolved_slug)

    if plat_info:
        plat_name, plat_ek, _ = plat_info
        plat_icon = PE.get(plat_ek, PE.get("gift", ""))
    else:
        plat_name = result.get("account_type", "Premium")
        plat_icon = PE.get("gift", "")

    # Use the stored full raw line; fall back to email:password if somehow missing
    raw_account = result.get("extra_info") or f"{result['email']}:{result['password']}"

    return (
        f"{PE['party']} <b>CODE REDEEMED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{plat_icon} <b>Platform:</b>  {html.escape(plat_name)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{PE['clipboard']} <b>Account Details:</b>\n"
        f"<code>{html.escape(raw_account)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{PE['check']} Enjoy your {html.escape(plat_name)} account!"
    )

# ════════════════════════════════════════════════════════════════════════════
# ◆ COMMANDS
# ════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref  = None
    if ctx.args:
        try:
            ref = int(ctx.args[0])
            if ref == user.id:
                ref = None
        except ValueError:
            ref = None

    if is_banned(user.id):
        await update.message.reply_text(
            f"{PE['ban']} <b>You are banned from using this bot.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    register_user(user.id, user.username, user.first_name, user.last_name, ref)
    welcome = cfg_get("welcome_text") or "Welcome!"
    name    = html.escape(user.first_name or "User")

    _crown   = '<tg-emoji emoji-id="6266995104687330978">👑</tg-emoji>'
    _diamond = '<tg-emoji emoji-id="5343636681473935403">💎</tg-emoji>'
    _fire    = '<tg-emoji emoji-id="5116414868357907335">🔥</tg-emoji>'
    _star    = '<tg-emoji emoji-id="6026106482297147601">⭐</tg-emoji>'
    _gift    = '<tg-emoji emoji-id="5283031441637148958">🎁</tg-emoji>'
    _trophy  = '<tg-emoji emoji-id="5467406098367521267">🏆</tg-emoji>'
    _check   = '<tg-emoji emoji-id="5444987348334965906">✅</tg-emoji>'
    _bell    = '<tg-emoji emoji-id="5116445341150872576">📢</tg-emoji>'
    _bolt    = '<tg-emoji emoji-id="5219943216781995020">⚡</tg-emoji>'
    _key     = '<tg-emoji emoji-id="5316858509571144216">🔑</tg-emoji>'

    text = (
        f"{_crown} {_diamond} {_fire} {_star} {_trophy}\n"
        f"<b>✦ Welcome to Roha Giveaway Bot ✦</b>\n"
        f"{_trophy} {_star} {_fire} {_diamond} {_crown}\n\n"
        f"{_gift}  <b>Hey {name}!</b>\n\n"
        f"{_check}  {html.escape(welcome)}\n\n"
        f"{_bolt} Fast  •  {_key} Secure  •  {_bell} Instant\n\n"
        f"{_diamond} Use the buttons below to get started."
    )

    await update.message.reply_text(
        text,
        reply_markup=kb_main(is_admin(user.id)),
        parse_mode=ParseMode.HTML
    )

async def cmd_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_banned(user.id):
        await update.message.reply_text(f"{PE['ban']} You are banned.", parse_mode=ParseMode.HTML)
        return
    if not ctx.args:
        await update.message.reply_text(
            f"{PE['key']} <b>Usage:</b> <code>/redeem YOUR_CODE</code>",
            parse_mode=ParseMode.HTML
        )
        return
    code   = ctx.args[0].strip().upper()
    result = redeem_code(code, user.id)

    if result == "not_found":
        msg = f"{PE['error']} Code <code>{html.escape(code)}</code> not found."
    elif result == "used":
        msg = f"{PE['ban']} This code has already been used."
    elif result == "expired":
        msg = f"{PE['expired']} This code has expired."
    elif result == "limit":
        msg = f"{PE['stop']} You have reached the maximum redemption limit."
    elif result == "no_account":
        msg = f"{PE['warning']} No account linked to this code."
    else:
        msg = _build_redeem_msg(result)

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def cmd_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u    = get_user(user.id)
    if not u:
        register_user(user.id, user.username, user.first_name, user.last_name)
        u = get_user(user.id)
    status = f"{PE['ban']} BANNED" if u["is_banned"] else f"{PE['check']} ACTIVE"
    admin_badge = f"\n{PE['crown']} <b>Admin</b>" if u["is_admin"] else ""
    msg = f"""
{PE['user']} <b>YOUR PROFILE</b>
━━━━━━━━━━━━━━━━━━━━━━━
{PE['id_card']} <b>ID:</b>       <code>{user.id}</code>
{PE['wave']}  <b>Name:</b>     {html.escape(user.first_name or 'N/A')}
{PE['link']}  <b>Username:</b> @{html.escape(user.username or 'N/A')}
{PE['clock']} <b>Joined:</b>   {str(u['join_date'])[:10]}
{PE['gift']}  <b>Redeemed:</b> {u['redeemed_count']}
{PE['shield']} <b>Status:</b>  {status}{admin_badge}
━━━━━━━━━━━━━━━━━━━━━━━
{PE['link']} <b>Referral link:</b>
<code>https://t.me/YourBot?start={user.id}</code>
""".strip()
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = f"""
{PE['info']} <b>BOT HELP</b>
━━━━━━━━━━━━━━━━━━━━━━━
/start — Launch the bot
/redeem CODE — Redeem a code
/profile — View your profile
/leaderboard — Top redeemers
/help — This message
/about — About this bot
━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def cmd_about(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    bot_name = cfg_get("bot_name") or "Premium Giveaway Bot"
    msg = f"""
{PE['diamond']} <b>{html.escape(bot_name)}</b>
━━━━━━━━━━━━━━━━━━━━━━━
{PE['rocket']} Premium account giveaway system
{PE['shield']} Secure code redemption
{PE['crown']} Admin management panel
{PE['star']} Leaderboard system
━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    rows = conn.execute(
        "SELECT user_id, first_name, username, redeemed_count FROM users ORDER BY redeemed_count DESC LIMIT 10"
    ).fetchall()
    conn.close()
    lines = [f"{PE['trophy']} <b>TOP REDEEMERS</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇","🥈","🥉"] + ["🏅"]*7
    for i, r in enumerate(rows):
        name = html.escape(r["first_name"] or r["username"] or f"User{r['user_id']}")
        lines.append(f"{medals[i]} {name} — <b>{r['redeemed_count']}</b> redeemed")
    if not rows:
        lines.append("No data yet.")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

# ════════════════════════════════════════════════════════════════════════════
# ◆ CALLBACK HANDLER
# ════════════════════════════════════════════════════════════════════════════

async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Thin wrapper: answers the callback immediately (so Telegram always clears
    the button's loading spinner), then routes to _route_callback. Any
    exception raised while building/sending a response is caught here so it
    can never fail silently — the admin sees a visible alert AND the full
    traceback is logged, instead of the button just doing nothing.
    """
    q = update.callback_query
    await q.answer()
    try:
        await _route_callback(update, ctx)
    except Exception:
        logger.exception(f"[callback_handler] Unhandled error for data={q.data!r}")
        try:
            await q.answer(
                "⚠️ Something went wrong handling that button. Check the bot logs.",
                show_alert=True,
            )
        except Exception:
            pass


async def _route_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    user = q.from_user
    data = q.data

    # ── USER CALLBACKS ────────────────────────────────────────────────────
    if data == "u:redeem":
        await safe_edit_message_text(q, 
            f"{PE['gift_box']} <b>REDEEM CODE</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['mobile']} Select your platform to redeem a code:",
            reply_markup=kb_platform_select(), parse_mode=ParseMode.HTML
        )

    elif data.startswith("u:platform:"):
        slug = data.split(":", 2)[2]
        all_platforms = get_platforms()
        if slug not in all_platforms:
            await q.answer("Unknown platform.", show_alert=True)
            return
        plat_name, emoji_key, prefix = all_platforms[slug]
        plat_emoji = PE.get(emoji_key, "")
        ctx.user_data["state"]            = STATE_AWAIT_PLATFORM_CODE
        ctx.user_data["redeem_platform"]  = slug
        await safe_edit_message_text(q, 
            f"{plat_emoji} <b>{html.escape(plat_name)}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['key']} Send your <b>{html.escape(plat_name)}</b> code:\n\n"
            f"<i>Format: {html.escape(prefix)}-XXXXXXXX</i>",
            reply_markup=kb_back("u:redeem"), parse_mode=ParseMode.HTML
        )

    elif data == "u:profile":
        u = get_user(user.id)
        if not u:
            register_user(user.id, user.username, user.first_name, user.last_name)
            u = get_user(user.id)
        status = f"{PE['ban']} BANNED" if u["is_banned"] else f"{PE['check']} ACTIVE"
        msg = f"""
{PE['user']} <b>YOUR PROFILE</b>
━━━━━━━━━━━━━━━━━━━━━━━
{PE['id_card']} <b>ID:</b>       <code>{user.id}</code>
{PE['wave']}  <b>Name:</b>     {html.escape(user.first_name or 'N/A')}
{PE['gift']}  <b>Redeemed:</b> {u['redeemed_count']}
{PE['shield']} <b>Status:</b>  {status}
━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
        await safe_edit_message_text(q, msg, reply_markup=kb_back("u:back"), parse_mode=ParseMode.HTML)

    elif data == "u:help":
        await safe_edit_message_text(q, 
            f"{PE['info']} Use /redeem CODE to claim a premium account.",
            reply_markup=kb_back("u:back"), parse_mode=ParseMode.HTML
        )

    elif data == "u:lb":
        conn = get_conn()
        rows = conn.execute(
            "SELECT user_id,first_name,username,redeemed_count FROM users ORDER BY redeemed_count DESC LIMIT 10"
        ).fetchall()
        conn.close()
        lines = [f"{PE['trophy']} <b>TOP REDEEMERS</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
        medals = ["🥇","🥈","🥉"]+["🏅"]*7
        for i,r in enumerate(rows):
            name = html.escape(r["first_name"] or r["username"] or str(r["user_id"]))
            lines.append(f"{medals[i]} {name} — <b>{r['redeemed_count']}</b>")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        await safe_edit_message_text(q, "\n".join(lines), reply_markup=kb_back("u:back"), parse_mode=ParseMode.HTML)

    elif data == "u:back":
        welcome = cfg_get("welcome_text") or "Welcome!"
        name    = html.escape(user.first_name or "User")
        await safe_edit_message_text(q, 
            (
                '<tg-emoji emoji-id="6266995104687330978">👑</tg-emoji>'
                f' <b>Welcome back, {name}!</b>\n\n'
                '<tg-emoji emoji-id="5444987348334965906">✅</tg-emoji>'
                f' {html.escape(welcome)}'
            ),
            reply_markup=kb_main(is_admin(user.id)), parse_mode=ParseMode.HTML
        )

    # ── ADMIN CALLBACKS ───────────────────────────────────────────────────
    elif data == "a:dash":
        if not is_admin(user.id):
            return
        s = get_stats()
        msg = f"""
{PE['crown']} <b>ADMIN DASHBOARD</b>
━━━━━━━━━━━━━━━━━━━━━━━
{PE['people']} Users:       <code>{s['total_users']}</code>
{PE['ban']}   Banned:      <code>{s['banned_users']}</code>
{PE['box']}   Accounts:    <code>{s['total_acc']}</code>
{PE['check']} Available:   <code>{s['avail_acc']}</code>
{PE['key']}   Codes Total: <code>{s['total_codes']}</code>
{PE['gift']}  Codes Used:  <code>{s['used_codes']}</code>
━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
        await safe_edit_message_text(q, msg, reply_markup=kb_admin_dash(), parse_mode=ParseMode.HTML)

    elif data == "a:stats":
        if not is_admin(user.id): return
        s = get_stats()
        lines = [
            f"{PE['chart']} <b>DETAILED STATS</b>\n━━━━━━━━━━━━━━━━━━━━━━━",
            f"{PE['people']} Total Users:    <code>{s['total_users']}</code>",
            f"{PE['ban']}   Banned Users:   <code>{s['banned_users']}</code>",
            f"{PE['box']}   Total Accounts: <code>{s['total_acc']}</code>",
            f"{PE['check']} Available:      <code>{s['avail_acc']}</code>",
            f"{PE['key']}   Total Codes:    <code>{s['total_codes']}</code>",
            f"{PE['gift']}  Used Codes:     <code>{s['used_codes']}</code>",
        ]
        types = get_account_types()
        if types:
            lines.append(f"\n{PE['box']} <b>BY TYPE:</b>")
            for t in types:
                lines.append(f"  • {html.escape(t['account_type'])}: {t['total']} total, {t['redeemed']} used")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        await safe_edit_message_text(q, 
            "\n".join(lines), reply_markup=kb_back("a:dash"), parse_mode=ParseMode.HTML
        )

    elif data == "a:users":
        if not is_admin(user.id): return
        users = get_users(limit=20)
        lines = [f"{PE['people']} <b>RECENT USERS</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
        for u in users:
            flag = "🚫" if u["is_banned"] else "✅"
            name = html.escape(u["first_name"] or u["username"] or str(u["user_id"]))
            lines.append(f"{flag} <code>{u['user_id']}</code> — {name} ({u['redeemed_count']} redeemed)")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        await safe_edit_message_text(q, 
            "\n".join(lines), reply_markup=kb_back("a:dash"), parse_mode=ParseMode.HTML
        )

    elif data == "a:accounts":
        if not is_admin(user.id): return
        avail  = get_available_count()
        types  = get_account_types()
        lines  = [f"{PE['box']} <b>ACCOUNTS OVERVIEW</b>\n━━━━━━━━━━━━━━━━━━━━━━━",
                  f"{PE['check']} Available: <code>{avail}</code>\n"]
        for t in types:
            lines.append(f"• {html.escape(t['account_type'])}: {t['total']} total / {t['redeemed']} redeemed")
        await safe_edit_message_text(q, "\n".join(lines), reply_markup=kb_accounts_panel(), parse_mode=ParseMode.HTML)

    # ── ADD ACCOUNTS → platform picker ────────────────────────────────────
    elif data == "a:add_acc_platform":
        if not is_admin(user.id): return
        await safe_edit_message_text(q, 
            f"{PE['box']} <b>ADD ACCOUNTS</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['target']} Choose the platform for these accounts:",
            reply_markup=kb_add_accounts_platform_select(), parse_mode=ParseMode.HTML
        )

    elif data.startswith("a:add_acc_plat:"):
        if not is_admin(user.id): return
        slug = data.split(":", 2)[2]
        all_platforms = get_platforms()
        if slug not in all_platforms:
            await q.answer("Unknown platform.", show_alert=True)
            return
        plat_name, emoji_key, _ = all_platforms[slug]
        plat_emoji = PE.get(emoji_key, "")
        ctx.user_data["state"]           = STATE_ADD_ACCOUNTS_LINES
        ctx.user_data["add_acc_platform"] = slug
        await safe_edit_message_text(q, 
            f"{plat_emoji} <b>ADD {html.escape(plat_name.upper())} ACCOUNTS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['clipboard']} Paste account lines below.\n\n"
            f"<b>Each line must be one full account string, e.g.:</b>\n"
            f"<code>email:password | User = X | Plan = Y | ...</code>\n\n"
            f"{PE['info']} One account per line. The entire line is stored as-is.",
            reply_markup=kb_back("a:add_acc_platform"), parse_mode=ParseMode.HTML
        )

    elif data == "a:codes":
        if not is_admin(user.id): return
        conn = get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM redeem_codes").fetchone()["c"]
        used  = conn.execute("SELECT COUNT(*) as c FROM redeem_codes WHERE is_used=1").fetchone()["c"]
        conn.close()
        await safe_edit_message_text(q, 
            f"{PE['key']} <b>CODES</b>\n━━━━━━━━━━━━━━━━━━━━━━━\nTotal: <code>{total}</code>\nUsed:  <code>{used}</code>\nFree:  <code>{total-used}</code>",
            reply_markup=kb_codes_panel(), parse_mode=ParseMode.HTML
        )

    # ── GENERATE CODES → platform picker ──────────────────────────────────
    elif data == "a:gen_codes_platform":
        if not is_admin(user.id): return
        await safe_edit_message_text(q, 
            f"{PE['key']} <b>GENERATE CODES</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['target']} Choose the platform to generate codes for:",
            reply_markup=kb_generate_codes_platform_select(), parse_mode=ParseMode.HTML
        )

    elif data.startswith("a:gen_codes_plat:"):
        if not is_admin(user.id): return
        slug = data.split(":", 2)[2]
        all_platforms = get_platforms()
        if slug not in all_platforms:
            await q.answer("Unknown platform.", show_alert=True)
            return
        plat_name, emoji_key, _ = all_platforms[slug]
        plat_emoji = PE.get(emoji_key, "")
        avail = get_available_count(platform=slug)
        ctx.user_data["state"]              = STATE_GENERATE_CODES_COUNT
        ctx.user_data["gen_codes_platform"] = slug
        await safe_edit_message_text(q, 
            f"{plat_emoji} <b>GENERATE {html.escape(plat_name.upper())} CODES</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['box']} Available {html.escape(plat_name)} accounts: <code>{avail}</code>\n\n"
            f"{PE['generate']} How many codes? Send a number (1–1000):",
            reply_markup=kb_back("a:gen_codes_platform"), parse_mode=ParseMode.HTML
        )

    elif data == "a:broadcast":
        if not is_admin(user.id): return
        ctx.user_data["state"] = STATE_BROADCAST
        await safe_edit_message_text(q, 
            f"{PE['broadcast']} <b>BROADCAST</b>\n\nSend the message to broadcast to all users.\n\nHTML formatting supported.",
            reply_markup=kb_back("a:dash"), parse_mode=ParseMode.HTML
        )

    elif data == "a:settings":
        if not is_admin(user.id): return
        await safe_edit_message_text(q, 
            f"{b('gear')} <b>SETTINGS</b>", reply_markup=kb_settings(), parse_mode=ParseMode.HTML
        )

    elif data == "a:set_welcome":
        if not is_admin(user.id): return
        ctx.user_data["state"] = STATE_SET_WELCOME
        await safe_edit_message_text(q, 
            f"{PE['wave']} Send the new welcome text:", reply_markup=kb_back("a:settings"), parse_mode=ParseMode.HTML
        )

    elif data == "a:set_prefix":
        if not is_admin(user.id): return
        ctx.user_data["state"] = STATE_CODE_PREFIX
        await safe_edit_message_text(q, 
            f"{PE['key']} Send new code prefix (e.g. GIFT, PREM):", reply_markup=kb_back("a:settings"), parse_mode=ParseMode.HTML
        )

    elif data == "a:set_length":
        if not is_admin(user.id): return
        ctx.user_data["state"] = "set_length"
        await safe_edit_message_text(q, 
            f"{PE['thunder']} Send code length (6–32):", reply_markup=kb_back("a:settings"), parse_mode=ParseMode.HTML
        )

    elif data == "a:set_maxuser":
        if not is_admin(user.id): return
        ctx.user_data["state"] = "set_maxuser"
        await safe_edit_message_text(q, 
            f"{PE['lock']} Send max redemptions per user:", reply_markup=kb_back("a:settings"), parse_mode=ParseMode.HTML
        )

    # ── CUSTOM APPS MANAGEMENT ──────────────────────────────────────────────
    elif data == "a:apps":
        if not is_admin(user.id): return
        custom = get_custom_apps()
        await safe_edit_message_text(q, 
            f"{PE['box']} <b>MANAGE APPS</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['info']} Built-in platforms: <code>{len(PLATFORMS)}</code>\n"
            f"{b('add')} Custom apps: <code>{len(custom)}</code>\n\n"
            f"{PE['target']} Add new apps here without touching the code.",
            reply_markup=kb_apps_panel(), parse_mode=ParseMode.HTML
        )

    elif data == "a:app_add":
        if not is_admin(user.id): return
        ctx.user_data["state"] = STATE_ADD_CUSTOM_APP
        await safe_edit_message_text(q, 
            f"{b('add')} <b>ADD CUSTOM APP</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['info']} Send in this format:\n"
            f"<code>NAME|EMOJI_ID|PREFIX</code>\n\n"
            f"{PE['sparkle']} Example:\n"
            f"<code>DAZN|5318911503938634641|DAZN</code>\n\n"
            f"{PE['key']} EMOJI_ID is the numeric Telegram premium custom emoji document ID.",
            reply_markup=kb_back("a:dash"), parse_mode=ParseMode.HTML
        )

    elif data == "a:app_list":
        if not is_admin(user.id): return
        custom = get_custom_apps()
        if not custom:
            lines = [f"{PE['box']} <b>CUSTOM APPS</b>\n━━━━━━━━━━━━━━━━━━━━━━━", f"{PE['info']} No custom apps added yet."]
        else:
            lines = [f"{PE['box']} <b>CUSTOM APPS ({len(custom)})</b>\n━━━━━━━━━━━━━━━━━━━━━━━"]
            for app in custom:
                icon = PE.get(app["slug"], PE.get("gift", ""))
                lines.append(
                    f"{icon} <b>{html.escape(app['name'])}</b> — "
                    f"slug: <code>{app['slug']}</code> — prefix: <code>{html.escape(app['prefix'])}</code>"
                )
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━")
        await safe_edit_message_text(q, 
            "\n".join(lines), reply_markup=kb_back("a:apps"), parse_mode=ParseMode.HTML
        )

    elif data == "a:app_remove":
        if not is_admin(user.id): return
        custom = get_custom_apps()
        await safe_edit_message_text(q, 
            f"{PE['trash']} <b>REMOVE CUSTOM APP</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['warning']} Tap an app to permanently delete it.\n"
            f"{PE['info']} Existing accounts/codes for it are kept, but it will disappear from all menus.",
            reply_markup=kb_remove_custom_app_select(custom), parse_mode=ParseMode.HTML
        )

    elif data.startswith("a:app_del:"):
        if not is_admin(user.id): return
        slug = data.split(":", 2)[2]
        ok = remove_custom_app(slug)
        if ok:
            await q.answer(f"Removed '{slug}'.", show_alert=True)
        else:
            await q.answer("App not found.", show_alert=True)
        custom = get_custom_apps()
        await safe_edit_message_text(q, 
            f"{PE['trash']} <b>REMOVE CUSTOM APP</b>\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['warning']} Tap an app to permanently delete it.",
            reply_markup=kb_remove_custom_app_select(custom), parse_mode=ParseMode.HTML
        )

    elif data == "a:admins":
        if not is_admin(user.id): return
        ctx.user_data["state"] = STATE_ADD_ADMIN
        await safe_edit_message_text(q, 
            f"{PE['crown']} <b>MANAGE ADMINS</b>\n\nSend the user ID to toggle admin status:",
            reply_markup=kb_back("a:dash"), parse_mode=ParseMode.HTML
        )

    elif data == "a:finduser":
        if not is_admin(user.id): return
        ctx.user_data["state"] = STATE_SEARCH_USER
        await safe_edit_message_text(q, 
            f"{PE['search']} Send the user ID to search:",
            reply_markup=kb_back("a:dash"), parse_mode=ParseMode.HTML
        )

    elif data.startswith("a:toggle_ban:"):
        if not is_admin(user.id): return
        uid = int(data.split(":")[2])
        u   = get_user(uid)
        if not u:
            await q.answer("User not found", show_alert=True)
            return
        if u["is_banned"]:
            unban_user(uid)
            await q.answer(f"User {uid} unbanned.", show_alert=True)
        else:
            ban_user(uid, "Banned by admin")
            await q.answer(f"User {uid} banned.", show_alert=True)
        u = get_user(uid)
        status = f"{PE['ban']} BANNED" if u["is_banned"] else f"{PE['check']} ACTIVE"
        lines = [
            f"{PE['people']} <b>USER</b>",
            f"{PE['key']}  <b>ID:</b> <code>{uid}</code>",
            f"{PE['shield']} <b>Status:</b> {status}",
        ]
        await safe_edit_message_text(q, 
            "\n".join(lines), reply_markup=kb_user_action(uid, bool(u["is_banned"])), parse_mode=ParseMode.HTML
        )

    elif data.startswith("a:toggle_admin:"):
        if not is_admin(user.id): return
        uid = int(data.split(":")[2])
        conn = get_conn()
        row  = conn.execute("SELECT is_admin FROM users WHERE user_id=?", (uid,)).fetchone()
        if row:
            new_status = 0 if row["is_admin"] else 1
            conn.execute("UPDATE users SET is_admin=? WHERE user_id=?", (new_status, uid))
            conn.commit()
            label = "promoted" if new_status else "demoted"
            await q.answer(f"User {uid} {label}.", show_alert=True)
        conn.close()

# ════════════════════════════════════════════════════════════════════════════
# ◆ TEXT MESSAGE HANDLER (state machine)
# ════════════════════════════════════════════════════════════════════════════

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text    = update.message.text.strip()
    state   = ctx.user_data.get("state")

    # ── Platform code redemption (available to ALL users) ─────────────────
    if state == STATE_AWAIT_PLATFORM_CODE:
        if is_banned(user_id):
            await update.message.reply_text(
                f"{PE['ban']} You are banned.", parse_mode=ParseMode.HTML
            )
            ctx.user_data["state"] = None
            return

        code      = text.strip().upper()
        plat_slug = ctx.user_data.pop("redeem_platform", None)
        ctx.user_data["state"] = None
        result    = redeem_code(code, user_id)

        if result == "not_found":
            msg = f"{PE['error']} Code <code>{html.escape(code)}</code> not found."
        elif result == "used":
            msg = f"{PE['ban']} This code has already been used."
        elif result == "expired":
            msg = f"{PE['expired']} This code has expired."
        elif result == "limit":
            msg = f"{PE['stop']} You have reached the maximum redemption limit."
        elif result == "no_account":
            msg = f"{PE['warning']} No account linked to this code."
        else:
            msg = _build_redeem_msg(result, plat_slug)

        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
        return

    # ── Admin-only states ─────────────────────────────────────────────────
    if not is_admin(user_id):
        return

    # ── Admin: paste account lines after selecting platform ───────────────
    if state == STATE_ADD_ACCOUNTS_LINES:
        platform_slug = ctx.user_data.pop("add_acc_platform", None)
        ctx.user_data["state"] = None

        if not platform_slug:
            await update.message.reply_text(
                f"{PE['ban']} Session expired. Please start over.", parse_mode=ParseMode.HTML
            )
            return

        raw_lines = [l for l in text.split("\n") if l.strip()]
        to_add    = [(platform_slug, line) for line in raw_lines]
        added, errors = add_accounts_bulk(to_add)

        all_platforms = get_platforms()
        plat_name = all_platforms.get(platform_slug, (platform_slug,))[0]
        plat_emoji_key = all_platforms.get(platform_slug, ("", "gift", ""))[1]
        plat_icon = PE.get(plat_emoji_key, "")

        await update.message.reply_text(
            f"{PE['check']} <b>ACCOUNTS ADDED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{plat_icon} <b>Platform:</b> {html.escape(plat_name)}\n"
            f"{PE['fire']} Added:  <code>{added}</code>\n"
            f"{PE['ban']} Errors: <code>{errors}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['info']} Full account lines stored as-is.",
            parse_mode=ParseMode.HTML
        )
        return

    # ── Admin: type count after selecting platform for code generation ─────
    elif state == STATE_GENERATE_CODES_COUNT:
        platform_slug = ctx.user_data.pop("gen_codes_platform", None)
        ctx.user_data["state"] = None

        if not platform_slug:
            await update.message.reply_text(
                f"{PE['ban']} Session expired. Please start over.", parse_mode=ParseMode.HTML
            )
            return

        try:
            count = int(text)
            avail = get_available_count(platform=platform_slug)

            if count < 1 or count > 1000:
                await update.message.reply_text(f"{PE['ban']} Enter 1–1000.", parse_mode=ParseMode.HTML)
                return
            all_platforms = get_platforms()
            if count > avail:
                plat_name = all_platforms.get(platform_slug, (platform_slug,))[0]
                await update.message.reply_text(
                    f"{PE['ban']} Only <code>{avail}</code> available {html.escape(plat_name)} accounts.",
                    parse_mode=ParseMode.HTML
                )
                return

            acc_ids = [a["id"] for a in get_accounts(redeemed=False, platform=platform_slug, limit=count)]
            codes   = create_codes_batch(acc_ids, platform=platform_slug)
            chunk   = "\n".join(codes)
            plat_name = all_platforms.get(platform_slug, (platform_slug,))[0]
            msg = (
                f"{PE['key']} <b>CODES GENERATED ({len(codes)})</b>\n"
                f"{PE.get(all_platforms.get(platform_slug, ('','gift',''))[1], '')} Platform: {html.escape(plat_name)}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<code>{chunk}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{PE['rocket']} Ready for distribution!"
            )
            if len(msg) > 4000:
                for i in range(0, len(codes), 50):
                    chunk = "\n".join(codes[i:i+50])
                    await update.message.reply_text(f"<code>{chunk}</code>", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

        except ValueError:
            await update.message.reply_text(f"{PE['ban']} Invalid number.", parse_mode=ParseMode.HTML)
        return

    # ── Admin: add a custom app (NAME|EMOJI_ID|PREFIX) ──────────────────────
    elif state == STATE_ADD_CUSTOM_APP:
        ctx.user_data["state"] = None
        parts = [p.strip() for p in text.split("|")]
        if len(parts) != 3 or not all(parts):
            await update.message.reply_text(
                f"{PE['ban']} <b>Invalid format.</b>\n\n"
                f"{PE['info']} Use: <code>NAME|EMOJI_ID|PREFIX</code>\n"
                f"{PE['sparkle']} Example: <code>DAZN|5318911503938634641|DAZN</code>",
                parse_mode=ParseMode.HTML
            )
            return

        name, emoji_id, prefix = parts
        ok, result = add_custom_app(name, emoji_id, prefix)

        if not ok:
            reasons = {
                "invalid_input": f"{PE['ban']} Invalid input — check name, numeric EMOJI_ID, and prefix.",
                "slug_collision_builtin": f"{PE['ban']} That name collides with a built-in platform. Choose another name.",
                "slug_collision_custom": f"{PE['ban']} A custom app with that name already exists.",
            }
            await update.message.reply_text(
                reasons.get(result, f"{PE['ban']} Could not add app."), parse_mode=ParseMode.HTML
            )
            return

        slug = result
        icon = PE.get(slug, PE.get("gift", ""))
        await update.message.reply_text(
            f"{PE['check']} <b>CUSTOM APP ADDED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{icon} <b>Name:</b>   {html.escape(name)}\n"
            f"{PE['key']} <b>Slug:</b>   <code>{slug}</code>\n"
            f"{PE['ticket']} <b>Prefix:</b> <code>{html.escape(prefix.upper())}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{PE['rocket']} It now appears in Redeem Code, Add Accounts, and Generate Codes menus.",
            parse_mode=ParseMode.HTML
        )
        return

    # ── Legacy STATE_ADD_ACCOUNTS (kept for backward compat / direct use) ──
    elif state == STATE_ADD_ACCOUNTS:
        lines   = text.split("\n")
        to_add  = []
        errors  = 0
        for line in lines:
            parts = line.strip().split("|")
            if len(parts) >= 3:
                # Legacy format: TYPE|EMAIL|PASSWORD|EXTRA
                to_add.append(("unknown", line.strip()))
            elif ":" in line:
                # New format: raw email:pass|extra line, no platform set
                to_add.append(("unknown", line.strip()))
            else:
                errors += 1
        added, parse_errors = add_accounts_bulk(to_add) if to_add else (0, 0)
        errors += parse_errors
        await update.message.reply_text(
            f"{PE['check']} <b>ACCOUNTS ADDED</b>\n\n{PE['fire']} Added:  <code>{added}</code>\n{PE['ban']} Errors: <code>{errors}</code>",
            parse_mode=ParseMode.HTML
        )
        ctx.user_data["state"] = None

    elif state == STATE_GENERATE_CODES:
        try:
            count = int(text)
            avail = get_available_count()
            if count < 1 or count > 1000:
                await update.message.reply_text(f"{PE['ban']} Enter 1–1000.", parse_mode=ParseMode.HTML)
                return
            if count > avail:
                await update.message.reply_text(
                    f"{PE['ban']} Only <code>{avail}</code> accounts available.", parse_mode=ParseMode.HTML
                )
                return
            acc_ids = [a["id"] for a in get_accounts(redeemed=False, limit=count)]
            codes   = create_codes_batch(acc_ids)
            chunk   = "\n".join(codes)
            msg     = f"{PE['key']} <b>CODES GENERATED ({len(codes)})</b>\n\n━━━━━━━━━━━━━━━━━━━━━━━\n<code>{chunk}</code>\n━━━━━━━━━━━━━━━━━━━━━━━\n\n{PE['rocket']} Ready for distribution!"
            if len(msg) > 4000:
                for i in range(0, len(codes), 50):
                    chunk = "\n".join(codes[i:i+50])
                    await update.message.reply_text(f"<code>{chunk}</code>", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
            ctx.user_data["state"] = None
        except ValueError:
            await update.message.reply_text(f"{PE['ban']} Invalid number.", parse_mode=ParseMode.HTML)

    elif state == STATE_BROADCAST:
        users  = get_users(limit=10000)
        sent   = 0
        failed = 0
        progress_msg = await update.message.reply_text(
            f"{PE['bell']} Broadcasting to <code>{len(users)}</code> users…",
            parse_mode=ParseMode.HTML
        )
        for u in users:
            try:
                await ctx.bot.send_message(chat_id=u["user_id"], text=text, parse_mode=ParseMode.HTML)
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.04)
        conn = get_conn()
        conn.execute("INSERT INTO broadcast_log(message,sent_count,fail_count) VALUES(?,?,?)", (text, sent, failed))
        conn.commit(); conn.close()
        await progress_msg.edit_text(
            f"{PE['check']} <b>BROADCAST DONE</b>\n\n{PE['rocket']} Sent:   <code>{sent}</code>\n{PE['ban']} Failed: <code>{failed}</code>",
            parse_mode=ParseMode.HTML
        )
        ctx.user_data["state"] = None

    elif state == STATE_SEARCH_USER:
        try:
            uid  = int(text)
            u    = get_user(uid)
            if not u:
                await update.message.reply_text(f"{PE['ban']} User not found.", parse_mode=ParseMode.HTML)
                ctx.user_data["state"] = None
                return
            status = f"{PE['ban']} BANNED" if u["is_banned"] else f"{PE['check']} ACTIVE"
            msg = f"""
{PE['people']} <b>USER FOUND</b>
━━━━━━━━━━━━━━━━━━━━━━━
{PE['key']}  <b>ID:</b>       <code>{uid}</code>
{PE['wave']} <b>Name:</b>     {html.escape(u.get('first_name') or 'N/A')}
@  <b>Username:</b> @{html.escape(u.get('username') or 'N/A')}
{PE['bell']} <b>Joined:</b>   {str(u['join_date'])[:10]}
{PE['gift']} <b>Redeemed:</b> {u['redeemed_count']}
{PE['shield']} <b>Status:</b>  {status}
━━━━━━━━━━━━━━━━━━━━━━━
""".strip()
            await update.message.reply_text(
                msg, reply_markup=kb_user_action(uid, bool(u["is_banned"])), parse_mode=ParseMode.HTML
            )
            ctx.user_data["state"] = None
        except ValueError:
            await update.message.reply_text(f"{PE['ban']} Invalid ID.", parse_mode=ParseMode.HTML)

    elif state == STATE_ADD_ADMIN:
        try:
            uid  = int(text)
            conn = get_conn()
            row  = conn.execute("SELECT is_admin FROM users WHERE user_id=?", (uid,)).fetchone()
            if not row:
                await update.message.reply_text(f"{PE['ban']} User not found.", parse_mode=ParseMode.HTML)
            else:
                new_status = 0 if row["is_admin"] else 1
                conn.execute("UPDATE users SET is_admin=? WHERE user_id=?", (new_status, uid))
                conn.commit()
                label = "promoted to Admin" if new_status else "removed from Admin"
                await update.message.reply_text(
                    f"{PE['crown']} User <code>{uid}</code> {label}.", parse_mode=ParseMode.HTML
                )
            conn.close()
            ctx.user_data["state"] = None
        except ValueError:
            await update.message.reply_text(f"{PE['ban']} Invalid ID.", parse_mode=ParseMode.HTML)

    elif state == STATE_SET_WELCOME:
        cfg_set("welcome_text", text)
        await update.message.reply_text(f"{PE['check']} Welcome text updated.", parse_mode=ParseMode.HTML)
        ctx.user_data["state"] = None

    elif state == STATE_CODE_PREFIX:
        cfg_set("code_prefix", text.upper().replace(" ",""))
        await update.message.reply_text(
            f"{PE['check']} Code prefix set to <code>{html.escape(text.upper())}</code>.", parse_mode=ParseMode.HTML
        )
        ctx.user_data["state"] = None

    elif state == "set_length":
        try:
            n = int(text)
            if 6 <= n <= 32:
                cfg_set("code_length", str(n))
                await update.message.reply_text(f"{PE['check']} Code length set to <code>{n}</code>.", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(f"{PE['ban']} Must be 6–32.", parse_mode=ParseMode.HTML)
        except ValueError:
            await update.message.reply_text(f"{PE['ban']} Invalid number.", parse_mode=ParseMode.HTML)
        ctx.user_data["state"] = None

    elif state == "set_maxuser":
        try:
            n = int(text)
            if n >= 1:
                cfg_set("max_per_user", str(n))
                await update.message.reply_text(f"{PE['check']} Max per user set to <code>{n}</code>.", parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text(f"{PE['ban']} Must be ≥ 1.", parse_mode=ParseMode.HTML)
        except ValueError:
            await update.message.reply_text(f"{PE['ban']} Invalid number.", parse_mode=ParseMode.HTML)
        ctx.user_data["state"] = None

# ════════════════════════════════════════════════════════════════════════════
# ◆ GLOBAL ERROR HANDLER
# ════════════════════════════════════════════════════════════════════════════

async def global_error_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    """
    Catches any exception not already handled locally (e.g. inside command
    handlers or text_handler). Without this, python-telegram-bot silently
    swallows the error after logging it once — this makes sure it's always
    logged clearly with a full traceback, and never crashes the bot process.
    """
    logger.exception("Unhandled exception while processing an update", exc_info=ctx.error)


# ════════════════════════════════════════════════════════════════════════════
# ◆ MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    init_db()

    # Re-register every saved custom app's emoji into the live registries so
    # buttons/messages have icon_custom_emoji_id set from the very first
    # request (get_platforms() would do this lazily anyway, but this avoids
    # any race on the first callback after a restart).
    for app_row in get_custom_apps():
        register_custom_app_emoji(app_row["slug"], app_row["emoji_id"])
    logger.info(f"[STARTUP] Loaded {len(get_custom_apps())} custom app(s).")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("redeem",      cmd_redeem))
    app.add_handler(CommandHandler("profile",     cmd_profile))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("about",       cmd_about))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(global_error_handler)

    logger.info(f"🚀 Bot started | Admin IDs: {ADMIN_IDS}")
    app.run_polling(allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    main()
