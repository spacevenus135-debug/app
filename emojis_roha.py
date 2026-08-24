"""
emojis_roha.py — Roha Giveaway Bot
Premium Emoji Registry + Button Builder
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• EMOJI dict        → tg-emoji HTML tags for message bodies
• EMOJI_IDS dict    → raw custom emoji document IDs for button icons
• STYLE_MAP dict    → Telegram button color styles
• btn()             → InlineKeyboardButton with premium icon + color style
• e()               → shortcut to get emoji HTML string by key
• BT                → plain Unicode fallbacks (for alerts / non-HTML contexts)
"""

import html as _html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# ════════════════════════════════════════════════════════════════════════════
# ◆ INTERNAL BUILDER
# ════════════════════════════════════════════════════════════════════════════

def _ce(emoji_id: str, fallback: str) -> str:
    """Wrap a custom emoji document ID into a Telegram HTML tag."""
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

# ════════════════════════════════════════════════════════════════════════════
# ◆ PREMIUM EMOJI IDS  (for InlineKeyboardButton icon_custom_emoji_id)
# ════════════════════════════════════════════════════════════════════════════

EMOJI_IDS: dict[str, str] = {
    # ── Buttons ─────────────────────────────────────────────────────────────
    "redeem"       : "5418010521309815154",   # 🎫
    "leaderboard"  : "5467406098367521267",   # 🏆
    "profile"      : "5445174334031166029",   # 👤
    "help"         : "5289930378885214069",   # 💡
    "admin_panel"  : "6266995104687330978",   # 👑
    "stats"        : "5445146408153806223",   # 📊
    "users"        : "5454371323595744068",   # 👥
    "accounts"     : "5303102515301083665",   # 📦
    "codes"        : "5316858509571144216",   # 🔑
    "broadcast"    : "5474263443152316384",   # 📣
    "settings"     : "5367890024907771329",   # ⚙️
    "back"         : "5253997076169115797",   # 🔙
    "add"          : "6100395724162210221",   # ➕
    "generate"     : "5305652587708572354",   # 🔢
    "ban"          : "5116151848855667552",   # 🚫
    "unban"        : "5444987348334965906",   # ✅
    "refresh"      : "5454245266305604993",   # 🔄
    "search"       : "5258274739041883702",   # 🔍
    "finduser"     : "5258274739041883702",   # 🔍
    "admins"       : "6266995104687330978",   # 👑
    "toggle"       : "5454245266305604993",   # 🔄
    "set_welcome"  : "6026306335715365949",   # 👋
    "set_prefix"   : "5316858509571144216",   # 🔑
    "set_length"   : "5305652587708572354",   # 🔢
    "set_max"      : "6282846669335702032",   # 🔒
    "lock"         : "6282846669335702032",   # 🔒
    "check"        : "5444987348334965906",   # ✅
    "cross"        : "5447647474984449520",   # ❌
    "fire"         : "5116414868357907335",   # 🔥
    "star"         : "6026106482297147601",   # ⭐
    "diamond"      : "5343636681473935403",   # 💎
    "gift"         : "5283031441637148958",   # 🎁
    "key"          : "5316858509571144216",   # 🔑
    "shield"       : "5472308992514464048",   # 🛡️
    "user"         : "5445174334031166029",   # 👤
    "people"       : "5454371323595744068",   # 👥
    "crown"        : "6266995104687330978",   # 👑
    "trophy"       : "5467406098367521267",   # 🏆
    "ticket"       : "5418010521309815154",   # 🎫
    "chart"        : "5445146408153806223",   # 📊
    "box"          : "5303102515301083665",   # 📦
    "gear"         : "5367890024907771329",   # ⚙️
    "wave"         : "6026306335715365949",   # 👋
    "thunder"      : "5219943216781995020",   # ⚡
    "info"         : "5289930378885214069",   # 💡
    "bell"         : "5116445341150872576",   # 📢
    "rocket"       : "4904936030232117798",   # 🚀
    "trash"        : "5445267414562389170",   # 🗑
    "id_card"      : "5447311106030726740",   # 🆔
    "link"         : "6267115986541877538",   # 🔗
    "clock"        : "5303243514782443814",   # ⏱️
    "hourglass"    : "5258113901106580375",   # ⏳
    "wallet"       : "5283232570660634549",   # 💰
    "card"         : "6267128480601741166",   # 💳
    "warning"      : "4915853119839011973",   # ⚠️
    "stop"         : "5275969776668134187",   # ⛔
    "money"        : "5283232570660634549",   # 💰
    "sparkle"      : "5253971897070706249",   # ✨
    "bolt"         : "5219943216781995020",   # ⚡
    "heart"        : "5881784744949062058",   # 🥰
    "party"        : "5172632227871196306",   # 🎉
    "green_dot"    : "6100395724162210221",   # 🟢
    "red_dot"      : "5852753450382659113",   # 🔴
    # ── New additions ────────────────────────────────────────────────────────
    "gift_box"     : "6267008582294705964",   # 🎁
    "target"       : "6267291337171670780",   # 🎯
    "mobile"       : "6267140231632262769",   # 📱
    "sparkle_new"  : "6267039884016358504",   # ✨
    "crown_new"    : "6266967801580231067",   # 👑
    "diamond_new"  : "6267071898702583835",   # 💎
    # ── Platforms ────────────────────────────────────────────────────────────
    "netflix"      : "5318911503938634641",   # 🎬
    "paramount"    : "5346134750417403743",   # 🏔️
    "disney"       : "5332394707655869572",   # ✨
    "amazon"       : "5346056560537779652",   # 🛒
    "xbox"         : "5373019729566908647",   # 🎮
    "steam"        : "5373144051690258848",   # ⚙️
    "playstation"  : "5373306783706137993",   # 🎮
    "chatgpt"      : "5359726582447487916",   # 🤖
    "capcut"       : "5364339557712020484",   # 🎞️
    "spotify"      : "5346074681004801565",   # 🎵
}

# ════════════════════════════════════════════════════════════════════════════
# ◆ STYLE MAP  (Telegram button color styles)
# ════════════════════════════════════════════════════════════════════════════

STYLE_MAP: dict[str, str] = {
    "primary" : "primary",
    "success" : "success",
    "danger"  : "danger",
    "default" : "default",
}

BUTTON_STYLES: dict[str, str] = {
    "redeem"      : "primary",
    "leaderboard" : "default",
    "profile"     : "default",
    "help"        : "default",
    "admin_panel" : "danger",
    "stats"       : "primary",
    "users"       : "primary",
    "accounts"    : "primary",
    "codes"       : "primary",
    "broadcast"   : "primary",
    "settings"    : "default",
    "back"        : "default",
    "add"         : "success",
    "generate"    : "success",
    "ban"         : "danger",
    "unban"       : "success",
    "toggle"      : "default",
    "refresh"     : "default",
    "finduser"    : "primary",
    "search"      : "primary",
    "admins"      : "danger",
    "check"       : "success",
    "cross"       : "danger",
    "shield"      : "default",
    "crown"       : "danger",
    "key"         : "primary",
    "chart"       : "primary",
    "gear"        : "default",
    "set_welcome" : "default",
    "set_prefix"  : "default",
    "set_length"  : "default",
    "set_max"     : "default",
    "lock"        : "default",
    "wave"        : "default",
    "gift"        : "success",
    "ticket"      : "primary",
    "trophy"      : "default",
    "star"        : "default",
    "diamond"     : "primary",
    "fire"        : "danger",
    "thunder"     : "default",
    "user"        : "default",
    "people"      : "primary",
    "box"         : "primary",
    # ── Platforms ─────────────────────────────────────────────────────────────
    "netflix"     : "danger",
    "paramount"   : "primary",
    "disney"      : "primary",
    "amazon"      : "default",
    "xbox"        : "success",
    "steam"       : "default",
    "playstation" : "primary",
    "chatgpt"     : "success",
    "capcut"      : "default",
    "spotify"     : "success",
}

# ════════════════════════════════════════════════════════════════════════════
# ◆ PREMIUM EMOJI REGISTRY  (message body — HTML parse mode only)
# ════════════════════════════════════════════════════════════════════════════

EMOJI: dict[str, str] = {
    # ── Status ──────────────────────────────────────────────────────────────
    "check"        : _ce("5444987348334965906", "✅"),
    "check2"       : _ce("6253414379442670769", "✅"),
    "cross"        : _ce("5447647474984449520", "❌"),
    "ban"          : _ce("5116151848855667552", "🚫"),
    "stop"         : _ce("5275969776668134187", "⛔"),
    "warning"      : _ce("4915853119839011973", "⚠️"),
    "info"         : _ce("5289930378885214069", "ℹ️"),
    "error"        : _ce("5447644880824181073", "⚠️"),
    "danger"       : _ce("5852753450382659113", "🔴"),
    "alert"        : _ce("4915853119839011973", "⚠️"),

    # ── Premium / VIP ────────────────────────────────────────────────────────
    "crown"        : _ce("6266995104687330978", "👑"),
    "crown2"       : _ce("5303547611351902889", "👑"),
    "diamond"      : _ce("5343636681473935403", "💎"),
    "gem"          : _ce("5343636681473935403", "💎"),
    "premium"      : _ce("5343636681473935403", "💎"),
    "vip"          : _ce("5343636681473935403", "💎"),
    "trophy"       : _ce("5467406098367521267", "🏆"),
    "medal"        : _ce("5467406098367521267", "🏅"),
    "gold"         : _ce("5467406098367521267", "🥇"),
    "star"         : _ce("6026106482297147601", "⭐"),
    "sparkle"      : _ce("5253971897070706249", "✨"),
    "fire"         : _ce("5116414868357907335", "🔥"),
    "flame"        : _ce("6100586674113222901", "🔥"),
    "bolt"         : _ce("5219943216781995020", "⚡"),
    "rocket"       : _ce("4904936030232117798", "🚀"),

    # ── People / Social ──────────────────────────────────────────────────────
    "user"         : _ce("5445174334031166029", "👤"),
    "users"        : _ce("5454371323595744068", "👥"),
    "people"       : _ce("5454371323595744068", "👥"),
    "wave"         : _ce("6026306335715365949", "👋"),
    "heart"        : _ce("5881784744949062058", "🥰"),
    "party"        : _ce("5172632227871196306", "🎉"),
    "id_card"      : _ce("5447311106030726740", "🆔"),
    "shield"       : _ce("5472308992514464048", "🛡"),
    "admin"        : _ce("5472308992514464048", "🛡"),

    # ── Actions / Navigation ─────────────────────────────────────────────────
    "gift"         : _ce("5283031441637148958", "🎁"),
    "ticket"       : _ce("5418010521309815154", "🎫"),
    "key"          : _ce("5316858509571144216", "🔑"),
    "lock"         : _ce("6282846669335702032", "🔒"),
    "unlock"       : _ce("5444987348334965906", "✅"),
    "search"       : _ce("5258274739041883702", "🔍"),
    "refresh"      : _ce("5454245266305604993", "🔄"),
    "back"         : _ce("5253997076169115797", "🔙"),
    "add"          : _ce("6100395724162210221", "➕"),
    "link"         : _ce("6267115986541877538", "🔗"),
    "broadcast"    : _ce("5474263443152316384", "📣"),
    "bell"         : _ce("5116445341150872576", "📢"),
    "megaphone"    : _ce("5116445341150872576", "📢"),

    # ── Data / Stats ─────────────────────────────────────────────────────────
    "chart"        : _ce("5445146408153806223", "📊"),
    "stats"        : _ce("5231200819986047254", "📊"),
    "clipboard"    : _ce("5444931419270839381", "📋"),
    "box"          : _ce("5303102515301083665", "📦"),
    "folder"       : _ce("6100672624998750369", "📁"),
    "gear"         : _ce("5367890024907771329", "⚙️"),
    "settings"     : _ce("5367890024907771329", "⚙️"),
    "generate"     : _ce("5305652587708572354", "🔢"),
    "trash"        : _ce("5445267414562389170", "🗑"),

    # ── Time ────────────────────────────────────────────────────────────────
    "clock"        : _ce("5303243514782443814", "⏱️"),
    "timer"        : _ce("5303243514782443814", "⏱️"),
    "hourglass"    : _ce("5258113901106580375", "⏳"),
    "pending"      : _ce("5258113901106580375", "⏳"),
    "expired"      : _ce("6266866272848321043", "⏰"),
    "calendar"     : _ce("5116575178012235794", "📅"),

    # ── Finance ─────────────────────────────────────────────────────────────
    "wallet"       : _ce("5283232570660634549", "💰"),
    "money"        : _ce("5283232570660634549", "💰"),
    "cash"         : _ce("5447579253723918909", "💸"),
    "card"         : _ce("6267128480601741166", "💳"),

    # ── Misc / Extra ─────────────────────────────────────────────────────────
    "thunder"      : _ce("5219943216781995020", "⚡"),
    "live"         : _ce("5219672809936006424", "🔥"),
    "red_dot"      : _ce("5852753450382659113", "🔴"),
    "green_dot"    : _ce("6100395724162210221", "🟢"),
    "yellow_dot"   : _ce("5895443668663275064", "🟡"),
    "blue_dot"     : _ce("5472308992514464048", "🔵"),
    "pin"          : _ce("6100395724162210221", "📌"),
    "target"       : _ce("6100395724162210221", "🎯"),
    # ── New additions ────────────────────────────────────────────────────────
    "gift_box"     : _ce("6267008582294705964", "🎁"),
    "target_new"   : _ce("6267291337171670780", "🎯"),
    "mobile"       : _ce("6267140231632262769", "📱"),
    "sparkle_new"  : _ce("6267039884016358504", "✨"),
    "crown_new"    : _ce("6266967801580231067", "👑"),
    "diamond_new"  : _ce("6267071898702583835", "💎"),
    # ── Platforms ────────────────────────────────────────────────────────────
    "netflix"      : _ce("5318911503938634641", "🎬"),
    "paramount"    : _ce("5346134750417403743", "🏔️"),
    "disney"       : _ce("5332394707655869572", "✨"),
    "amazon"       : _ce("5346056560537779652", "🛒"),
    "xbox"         : _ce("5373019729566908647", "🎮"),
    "steam"        : _ce("5373144051690258848", "⚙️"),
    "playstation"  : _ce("5373306783706137993", "🎮"),
    "chatgpt"      : _ce("5359726582447487916", "🤖"),
    "capcut"       : _ce("5364339557712020484", "🎞️"),
    "spotify"      : _ce("5346074681004801565", "🎵"),
}

# ════════════════════════════════════════════════════════════════════════════
# ◆ PLAIN UNICODE FALLBACKS  (for alerts, non-HTML contexts)
# ════════════════════════════════════════════════════════════════════════════

BT: dict[str, str] = {
    "check"      : "✅",  "cross"      : "❌",  "ban"        : "🚫",
    "stop"       : "⛔",  "warning"    : "⚠️",  "info"       : "ℹ️",
    "crown"      : "👑",  "diamond"    : "💎",  "trophy"     : "🏆",
    "star"       : "⭐",  "sparkle"    : "✨",  "fire"       : "🔥",
    "bolt"       : "⚡",  "rocket"     : "🚀",  "user"       : "👤",
    "users"      : "👥",  "people"     : "👥",  "wave"       : "👋",
    "heart"      : "🥰",  "party"      : "🎉",  "gift"       : "🎁",
    "ticket"     : "🎫",  "key"        : "🔑",  "lock"       : "🔒",
    "search"     : "🔍",  "refresh"    : "🔄",  "back"       : "◀",
    "link"       : "🔗",  "broadcast"  : "📣",  "bell"       : "📢",
    "chart"      : "📊",  "stats"      : "📊",  "box"        : "📦",
    "gear"       : "⚙️",  "settings"   : "⚙️",  "generate"   : "⚡",
    "trash"      : "🗑",  "clock"      : "⏱️",  "hourglass"  : "⏳",
    "expired"    : "⏰",  "wallet"     : "💰",  "card"       : "💳",
    "leaderboard": "🏅",  "profile"    : "👤",  "help"       : "💡",
    "admin"      : "👑",  "add"        : "➕",  "codes"      : "🔑",
    "accounts"   : "📦",  "redeem"     : "🎫",  "shield"     : "🛡",
    "id_card"    : "🆔",  "unban"      : "✅",  "toggle"     : "🔄",
    "finduser"   : "🔍",  "admins"     : "👑",  "money"      : "💰",
    "thunder"    : "⚡",
    "gift_box"    : "🎁",   "target_new"  : "🎯",
    "mobile"      : "📱",   "sparkle_new" : "✨",
    "crown_new"   : "👑",   "diamond_new" : "💎",
    "netflix"     : "🎬",   "paramount"   : "🏔️",
    "disney"      : "✨",   "amazon"      : "🛒",
    "xbox"        : "🎮",   "steam"       : "⚙️",
    "playstation" : "🎮",   "chatgpt"     : "🤖",
    "capcut"      : "🎞️",   "spotify"     : "🎵",
}

# ════════════════════════════════════════════════════════════════════════════
# ◆ PLATFORM REGISTRY
# ════════════════════════════════════════════════════════════════════════════

# Maps platform slug → (display name, emoji_key, prefix used in codes)
PLATFORMS: dict[str, tuple[str, str, str]] = {
    "netflix"     : ("Netflix",      "netflix",     "NETFLIX"),
    "paramount"   : ("Paramount+",   "paramount",   "PARAMOUNT"),
    "disney"      : ("Disney+",      "disney",      "DISNEY"),
    "amazon"      : ("Amazon",       "amazon",      "AMAZON"),
    "xbox"        : ("Xbox",         "xbox",        "XBOX"),
    "steam"       : ("Steam",        "steam",       "STEAM"),
    "playstation" : ("PlayStation",  "playstation", "PS"),
    "chatgpt"     : ("ChatGPT",      "chatgpt",     "CHATGPT"),
    "capcut"      : ("CapCut",       "capcut",      "CAPCUT"),
    "spotify"     : ("Spotify",      "spotify",     "SPOTIFY"),
}

# ════════════════════════════════════════════════════════════════════════════
# ◆ CUSTOM APPS  (added by admin at runtime, stored in DB, no code edits)
# ════════════════════════════════════════════════════════════════════════════
#
# Custom platforms live in the `custom_apps` DB table (slug, name, emoji_id,
# prefix). To make them behave exactly like built-in PLATFORMS entries
# everywhere (buttons, messages, code prefixes) we register each one's emoji
# into EMOJI / EMOJI_IDS / BT / BUTTON_STYLES dynamically, keyed by its own
# slug. That means `emoji_key == slug` for every custom app.

CUSTOM_APP_STYLE_DEFAULT = "default"

def register_custom_app_emoji(slug, emoji_id, fallback="⭐", style=CUSTOM_APP_STYLE_DEFAULT):
    """
    Register a custom app's premium emoji into the live registries so it can
    be used anywhere a built-in platform's emoji_key would be used (message
    body tg-emoji tags, button icon_custom_emoji_id, plain-text fallback).
    Idempotent — safe to call repeatedly (e.g. on every bot startup).
    """
    EMOJI[slug]         = _ce(emoji_id, fallback)
    EMOJI_IDS[slug]     = emoji_id
    BT[slug]            = fallback
    BUTTON_STYLES[slug] = style


def get_platforms():
    """
    Unified view of ALL platforms — built-in (PLATFORMS) merged with
    admin-added custom apps (from the custom_apps DB table).
    Returns {slug: (display_name, emoji_key, code_prefix)}.

    Imported lazily to avoid a circular import with main.py (which imports
    PLATFORMS/EMOJI from this module).
    """
    merged = dict(PLATFORMS)
    try:
        from main import get_custom_apps  # lazy import — avoids circular import
        for app in get_custom_apps():
            slug = app["slug"]
            register_custom_app_emoji(slug, app["emoji_id"])
            merged[slug] = (app["name"], slug, app["prefix"])
    except Exception:
        pass
    return merged

# ════════════════════════════════════════════════════════════════════════════
# ◆ SHORTCUT FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

def e(key: str) -> str:
    """Get premium tg-emoji HTML string by key (for message bodies)."""
    return EMOJI.get(key, "")

def b(key: str) -> str:
    """Get plain Unicode emoji string by key (for button labels)."""
    return BT.get(key, "")

DIV = "━━━━━━━━━━━━━━━━━━━━━━━"

# ════════════════════════════════════════════════════════════════════════════
# ◆ BUTTON BUILDER
# ════════════════════════════════════════════════════════════════════════════

def btn(
    label: str,
    data: str,
    icon_key: str = "",
    style: str = "",
) -> InlineKeyboardButton:
    resolved_style = (
        style
        if style in STYLE_MAP
        else BUTTON_STYLES.get(icon_key, "default")
    )
    emoji_id = EMOJI_IDS.get(icon_key)
    api_kwargs: dict = {"style": resolved_style}
    if emoji_id:
        api_kwargs["icon_custom_emoji_id"] = emoji_id
    return InlineKeyboardButton(
        label,
        callback_data=data,
        api_kwargs=api_kwargs,
    )


def url_btn(
    label: str,
    url: str,
    icon_key: str = "",
    style: str = "",
) -> InlineKeyboardButton:
    """URL button with premium emoji icon + style."""
    resolved_style = (
        style
        if style in STYLE_MAP
        else BUTTON_STYLES.get(icon_key, "default")
    )
    emoji_id = EMOJI_IDS.get(icon_key)
    api_kwargs: dict = {"style": resolved_style}
    if emoji_id:
        api_kwargs["icon_custom_emoji_id"] = emoji_id
    return InlineKeyboardButton(label, url=url, api_kwargs=api_kwargs)


def back_btn(cb: str = "u:back") -> InlineKeyboardButton:
    """Standard back button — style: default, icon: back arrow."""
    return btn("Back", cb, icon_key="back", style="default")


def confirm_btn(label: str, data: str) -> InlineKeyboardButton:
    """Green confirm / unban button."""
    return btn(label, data, icon_key="check", style="success")


def danger_btn(label: str, data: str) -> InlineKeyboardButton:
    """Red danger / ban button."""
    return btn(label, data, icon_key="ban", style="danger")


def row(*buttons: InlineKeyboardButton) -> list:
    """Wrap buttons into a keyboard row."""
    return list(buttons)


# ════════════════════════════════════════════════════════════════════════════
# ◆ KEYBOARD BUILDERS
# ════════════════════════════════════════════════════════════════════════════

def kb_main(is_admin_user: bool = False) -> InlineKeyboardMarkup:
    rows = [
        row(
            btn("Redeem Code", "u:redeem",  icon_key="redeem",      style="primary"),
            btn("Leaderboard", "u:lb",      icon_key="leaderboard",  style="default"),
        ),
        row(
            btn("Profile",     "u:profile", icon_key="profile",     style="default"),
            btn("Help",        "u:help",    icon_key="help",         style="default"),
        ),
    ]
    if is_admin_user:
        rows.append(row(
            btn("Admin Panel", "a:dash",    icon_key="admin_panel",  style="danger"),
        ))
    return InlineKeyboardMarkup(rows)


def kb_admin_dash() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        row(
            btn("Stats",     "a:stats",     icon_key="stats",      style="primary"),
            btn("Users",     "a:users",     icon_key="users",      style="primary"),
        ),
        row(
            btn("Accounts",  "a:accounts",  icon_key="accounts",   style="primary"),
            btn("Codes",     "a:codes",     icon_key="codes",      style="primary"),
        ),
        row(
            btn("Broadcast", "a:broadcast", icon_key="broadcast",  style="primary"),
            btn("Settings",  "a:settings",  icon_key="settings",   style="default"),
        ),
        row(
            btn("Admins",    "a:admins",    icon_key="admins",     style="danger"),
            btn("Find User", "a:finduser",  icon_key="finduser",   style="primary"),
        ),
        row(
            btn("➕ Add Custom App", "a:app_add", icon_key="add", style="success"),
        ),
        row(
            btn("Refresh",   "a:dash",      icon_key="refresh",    style="default"),
        ),
        row(back_btn("u:back")),
    ])


def kb_settings() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        row(btn("Set Welcome Text", "a:set_welcome", icon_key="set_welcome", style="default")),
        row(btn("Set Code Prefix",  "a:set_prefix",  icon_key="set_prefix",  style="default")),
        row(btn("Set Code Length",  "a:set_length",  icon_key="set_length",  style="default")),
        row(btn("Set Max Per User", "a:set_maxuser", icon_key="set_max",     style="default")),
        row(back_btn("a:dash")),
    ])


def kb_accounts_panel() -> InlineKeyboardMarkup:
    """Accounts panel — Add Accounts button now routes to platform picker."""
    return InlineKeyboardMarkup([
        row(btn("Add Accounts", "a:add_acc_platform", icon_key="add", style="success")),
        row(back_btn("a:dash")),
    ])


def kb_codes_panel() -> InlineKeyboardMarkup:
    """Codes panel — Generate Codes button now routes to platform picker."""
    return InlineKeyboardMarkup([
        row(btn("Generate Codes", "a:gen_codes_platform", icon_key="generate", style="success")),
        row(back_btn("a:dash")),
    ])


def kb_user_action(uid: int, is_banned: bool) -> InlineKeyboardMarkup:
    action_btn = (
        btn("Unban", f"a:toggle_ban:{uid}",   icon_key="unban",  style="success")
        if is_banned
        else btn("Ban", f"a:toggle_ban:{uid}", icon_key="ban",    style="danger")
    )
    return InlineKeyboardMarkup([
        row(action_btn, btn("Toggle Admin", f"a:toggle_admin:{uid}", icon_key="toggle", style="default")),
        row(back_btn("a:users")),
    ])


def kb_back(cb: str) -> InlineKeyboardMarkup:
    """Single back button pointing to whatever cb you pass."""
    return InlineKeyboardMarkup([row(back_btn(cb))])


def kb_platform_select() -> InlineKeyboardMarkup:
    """
    Platform picker shown when the USER taps Redeem Code.
    Builds 2-per-row grid from ALL platforms (built-in + custom) automatically.
    """
    platforms = get_platforms()
    platform_keys = list(platforms.keys())
    rows_out = []
    for i in range(0, len(platform_keys), 2):
        pair = platform_keys[i:i + 2]
        r = []
        for slug in pair:
            name, emoji_key, _ = platforms[slug]
            style = BUTTON_STYLES.get(emoji_key, "default")
            r.append(btn(name, f"u:platform:{slug}", icon_key=emoji_key, style=style))
        rows_out.append(r)
    rows_out.append(row(back_btn("u:back")))
    return InlineKeyboardMarkup(rows_out)


def kb_add_accounts_platform_select() -> InlineKeyboardMarkup:
    """
    Platform picker shown to ADMIN when they tap Add Accounts.
    Routes to a:add_acc_plat:<slug> callbacks.
    2-per-row grid, coloured by platform style. Built-in + custom apps.
    """
    platforms = get_platforms()
    platform_keys = list(platforms.keys())
    rows_out = []
    for i in range(0, len(platform_keys), 2):
        pair = platform_keys[i:i + 2]
        r = []
        for slug in pair:
            name, emoji_key, _ = platforms[slug]
            style = BUTTON_STYLES.get(emoji_key, "default")
            r.append(btn(name, f"a:add_acc_plat:{slug}", icon_key=emoji_key, style=style))
        rows_out.append(r)
    rows_out.append(row(back_btn("a:accounts")))
    return InlineKeyboardMarkup(rows_out)


def kb_generate_codes_platform_select() -> InlineKeyboardMarkup:
    """
    Platform picker shown to ADMIN when they tap Generate Codes.
    Routes to a:gen_codes_plat:<slug> callbacks.
    2-per-row grid, coloured by platform style. Built-in + custom apps.
    """
    platforms = get_platforms()
    platform_keys = list(platforms.keys())
    rows_out = []
    for i in range(0, len(platform_keys), 2):
        pair = platform_keys[i:i + 2]
        r = []
        for slug in pair:
            name, emoji_key, _ = platforms[slug]
            style = BUTTON_STYLES.get(emoji_key, "default")
            r.append(btn(name, f"a:gen_codes_plat:{slug}", icon_key=emoji_key, style=style))
        rows_out.append(r)
    rows_out.append(row(back_btn("a:codes")))
    return InlineKeyboardMarkup(rows_out)


# ════════════════════════════════════════════════════════════════════════════
# ◆ CUSTOM APP MANAGEMENT UI  (admin dashboard)
# ════════════════════════════════════════════════════════════════════════════

def kb_apps_panel() -> InlineKeyboardMarkup:
    """Custom-apps management menu, reached directly from the Admin Dashboard."""
    return InlineKeyboardMarkup([
        row(btn("Add Custom App",    "a:app_add",    icon_key="add",   style="success")),
        row(btn("List Custom Apps",  "a:app_list",   icon_key="box",   style="primary")),
        row(btn("Remove Custom App", "a:app_remove", icon_key="trash", style="danger")),
        row(back_btn("a:dash")),
    ])


def kb_remove_custom_app_select(custom_apps: list) -> InlineKeyboardMarkup:
    """
    Picker listing only CUSTOM apps (built-ins can't be removed this way).
    custom_apps: list of dicts with 'slug' and 'name' keys.
    """
    rows_out = []
    for app in custom_apps:
        slug = app["slug"]
        emoji_key = slug  # custom apps register their emoji under their own slug
        style = BUTTON_STYLES.get(emoji_key, "danger")
        rows_out.append(row(btn(app["name"], f"a:app_del:{slug}", icon_key=emoji_key, style="danger")))
    if not custom_apps:
        rows_out.append(row(btn("No custom apps yet", "a:app_list", icon_key="info", style="default")))
    rows_out.append(row(back_btn("a:apps")))
    return InlineKeyboardMarkup(rows_out)
