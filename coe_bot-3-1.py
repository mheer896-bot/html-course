"""
╔══════════════════════════════════════════════════════════════════╗
║  🎓 بوت طلاب هندسة الحاسبات — جامعة البصرة                     ║
║  Version: 4.0  |  3-Level + Categories System                    ║
╚══════════════════════════════════════════════════════════════════╝
"""

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os, json, logging

# ══════════════════════════════════════════════
#  السجلات
# ══════════════════════════════════════════════
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
#  الإعدادات
# ══════════════════════════════════════════════
API_TOKEN = "8872332163:AAFG6KdU8IIwzZXbUOhYhLUVTjDNGk_4XA0"
ADMIN_IDS = [858804480, 7491786054]  # ماهر + Mohammed Hadi
DB_FILE   = "coe_materials.json"

# ══════════════════════════════════════════════
#  الثوابت
# ══════════════════════════════════════════════
STAGES = {"1":"المرحلة الأولى","2":"المرحلة الثانية",
          "3":"المرحلة الثالثة","4":"المرحلة الرابعة"}
COURSES = {"s1":"الكورس الأول — الفصل الأول",
           "s2":"الكورس الثاني — الفصل الثاني"}

CATEGORIES = {
    "lec": ("📚", "المحاضرات"),
    "hw":  ("📝", "الواجبات"),
    "lab": ("🔬", "المختبر"),
    "exp": ("🧪", "التجارب"),
}

SE = {"1":"1️⃣","2":"2️⃣","3":"3️⃣","4":"4️⃣"}
CE = {"s1":"📗","s2":"📘"}
FT_ICON = {"document":"📄","photo":"🖼️","video":"🎬",
           "audio":"🎵","voice":"🎙️","unknown":"📎"}

# ══════════════════════════════════════════════
#  قاعدة البيانات
# ══════════════════════════════════════════════
"""
هيكل البيانات:
{
  "stage1": {
    "s1": {
      "subjects": [
        {
          "name": "Microprocessors",
          "lec":  {"Lec 1": {"file_id":"...","file_type":"document"}, ...},
          "hw":   {},
          "lab":  {},
          "exp":  {}
        },
        ...
      ]
    },
    "s2": { "subjects": [] }
  },
  ...
}
"""

def _default_db():
    return {
        f"stage{s}": {
            "s1": {"subjects": []},
            "s2": {"subjects": []}
        }
        for s in ("1","2","3","4")
    }

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE,"r",encoding="utf-8") as f:
                data = json.load(f)
            # تحقق من المفاتيح الناقصة
            db = _default_db()
            for sk in db:
                if sk in data:
                    for ck in ("s1","s2"):
                        if ck in data[sk]:
                            node = data[sk][ck]
                            if isinstance(node, dict) and "subjects" in node:
                                db[sk][ck]["subjects"] = node["subjects"]
            logger.info("✅ DB loaded.")
            return db
        except Exception as e:
            logger.error(f"DB load error: {e}")
    db = _default_db()
    save_db(db)
    return db

def save_db(db):
    try:
        with open(DB_FILE,"w",encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"DB save error: {e}")

# ══════════════════════════════════════════════
#  دوال الوصول للبيانات
# ══════════════════════════════════════════════
def get_subjects(sid, ck) -> list:
    return materials.get(f"stage{sid}",{}).get(ck,{}).get("subjects",[])

def get_subject(sid, ck, idx) -> dict | None:
    subs = get_subjects(sid, ck)
    return subs[idx] if 0 <= idx < len(subs) else None

def get_cat_files(sid, ck, subj_idx, cat) -> dict:
    sub = get_subject(sid, ck, subj_idx)
    return sub.get(cat, {}) if sub else {}

def get_file_at(sid, ck, subj_idx, cat, file_idx):
    files = get_cat_files(sid, ck, subj_idx, cat)
    keys  = list(files.keys())
    if 0 <= file_idx < len(keys):
        k = keys[file_idx]
        return k, files[k]
    return None, None

# ══════════════════════════════════════════════
#  التهيئة
# ══════════════════════════════════════════════
bot         = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
materials   = load_db()
user_states: dict = {}

# ══════════════════════════════════════════════
#  لوحات المفاتيح — الطلاب
# ══════════════════════════════════════════════
def kb_main():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*[InlineKeyboardButton(f"{SE[s]}  {STAGES[s]}",
             callback_data=f"VIEW|{s}") for s in ("1","2","3","4")])
    return kb

def kb_courses(sid):
    kb = InlineKeyboardMarkup(row_width=1)
    for ck, cn in COURSES.items():
        kb.add(InlineKeyboardButton(f"{CE[ck]}  {cn}",
               callback_data=f"COURSE|{sid}|{ck}"))
    kb.add(InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="MAIN"))
    return kb

def kb_subjects(sid, ck):
    kb = InlineKeyboardMarkup(row_width=1)
    subs = get_subjects(sid, ck)
    for i, sub in enumerate(subs):
        kb.add(InlineKeyboardButton(f"📖  {sub['name']}",
               callback_data=f"SUBJ|{sid}|{ck}|{i}"))
    kb.add(InlineKeyboardButton(f"🔙 {STAGES[sid]}", callback_data=f"VIEW|{sid}"))
    return kb

def kb_categories(sid, ck, subj_idx):
    kb = InlineKeyboardMarkup(row_width=2)
    sub = get_subject(sid, ck, subj_idx)
    if not sub:
        return kb
    buttons = []
    for cat, (icon, label) in CATEGORIES.items():
        count = len(sub.get(cat, {}))
        if count > 0:
            buttons.append(InlineKeyboardButton(
                f"{icon} {label} ({count})",
                callback_data=f"CAT|{sid}|{ck}|{subj_idx}|{cat}"
            ))
    if buttons:
        kb.add(*buttons)
    kb.add(InlineKeyboardButton("🔙 قائمة المواد",
           callback_data=f"COURSE|{sid}|{ck}"))
    return kb

def kb_files_list(sid, ck, subj_idx, cat):
    kb = InlineKeyboardMarkup(row_width=1)
    files = get_cat_files(sid, ck, subj_idx, cat)
    for i, (name, meta) in enumerate(files.items()):
        icon = FT_ICON.get(meta.get("file_type","unknown"),"📎")
        kb.add(InlineKeyboardButton(
            f"{icon}  {name}",
            callback_data=f"GETFILE|{sid}|{ck}|{subj_idx}|{cat}|{i}"
        ))
    sub = get_subject(sid, ck, subj_idx)
    sname = sub["name"] if sub else ""
    kb.add(InlineKeyboardButton(f"🔙 {sname}",
           callback_data=f"SUBJ|{sid}|{ck}|{subj_idx}"))
    return kb

# ══════════════════════════════════════════════
#  لوحات مفاتيح — الأدمن
# ══════════════════════════════════════════════
def kb_admin_home():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("➕  إضافة مادة جديدة",     callback_data="ADM|ADD_SUBJ"),
        InlineKeyboardButton("📤  رفع ملف لمادة",        callback_data="ADM|ADD_FILE"),
        InlineKeyboardButton("🗑️  حذف مادة",             callback_data="ADM|DEL_SUBJ"),
        InlineKeyboardButton("❌  حذف ملف",              callback_data="ADM|DEL_FILE"),
        InlineKeyboardButton("📊  إحصائيات",             callback_data="ADM|STATS"),
    )
    return kb

def kb_stage_sel(action):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*[InlineKeyboardButton(f"{SE[s]}  {STAGES[s]}",
             callback_data=f"{action}|{s}") for s in ("1","2","3","4")])
    kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
    return kb

def kb_course_sel(sid, action):
    kb = InlineKeyboardMarkup(row_width=1)
    for ck, cn in COURSES.items():
        kb.add(InlineKeyboardButton(f"{CE[ck]}  {cn}",
               callback_data=f"{action}|{sid}|{ck}"))
    kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
    return kb

def kb_subj_sel(sid, ck, action):
    kb = InlineKeyboardMarkup(row_width=1)
    subs = get_subjects(sid, ck)
    for i, sub in enumerate(subs):
        kb.add(InlineKeyboardButton(f"📖  {sub['name']}",
               callback_data=f"{action}|{sid}|{ck}|{i}"))
    kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
    return kb

def kb_cat_sel(sid, ck, subj_idx, action):
    kb = InlineKeyboardMarkup(row_width=2)
    for cat, (icon, label) in CATEGORIES.items():
        kb.add(InlineKeyboardButton(f"{icon} {label}",
               callback_data=f"{action}|{sid}|{ck}|{subj_idx}|{cat}"))
    kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
    return kb

def kb_del_files(sid, ck, subj_idx, cat):
    kb = InlineKeyboardMarkup(row_width=1)
    files = get_cat_files(sid, ck, subj_idx, cat)
    for i, name in enumerate(files):
        kb.add(InlineKeyboardButton(f"❌  {name}",
               callback_data=f"DFILE|{sid}|{ck}|{subj_idx}|{cat}|{i}"))
    kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
    return kb

# ══════════════════════════════════════════════
#  النصوص
# ══════════════════════════════════════════════
TXT_WELCOME = (
    "🎓 *أهلاً بك في بوت طلاب هندسة الحاسبات*\n"
    "🏛️ *جامعة البصرة — كلية الهندسة*\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "📚 محاضرات • 📝 واجبات • 🔬 مختبر • 🧪 تجارب\n"
    "📥 كل ملف يصلك مباشرة في المحادثة\n\n"
    "📌 *اختر مرحلتك الدراسية:*"
)
TXT_ADMIN = (
    "⚡ *لوحة تحكم البوت — هندسة الحاسبات*\n"
    "━━━━━━━━━━━━━━━━━━━━━\n"
    "اختر الإجراء:"
)

# ══════════════════════════════════════════════
#  الأوامر
# ══════════════════════════════════════════════
@bot.message_handler(commands=["start","help"])
def cmd_start(msg):
    bot.send_message(msg.chat.id, TXT_WELCOME, reply_markup=kb_main())

@bot.message_handler(commands=["admin"])
def cmd_admin(msg):
    if msg.chat.id not in ADMIN_IDS:
        bot.send_message(msg.chat.id, "🚫 *غير مصرّح.*")
        return
    bot.send_message(msg.chat.id, TXT_ADMIN, reply_markup=kb_admin_home())

@bot.message_handler(commands=["cancel"])
def cmd_cancel(msg):
    if msg.chat.id in user_states:
        del user_states[msg.chat.id]
        bot.send_message(msg.chat.id, "✅ تم الإلغاء.", reply_markup=kb_admin_home())
    else:
        bot.send_message(msg.chat.id, "ℹ️ لا توجد عملية جارية.")

# ══════════════════════════════════════════════
#  معالج الـ Callbacks
# ══════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: True)
def on_callback(call):
    bot.answer_callback_query(call.id)
    cid   = call.message.chat.id
    mid   = call.message.message_id
    parts = call.data.split("|")
    act   = parts[0]

    try:

        # ─── القائمة الرئيسية ───
        if act == "MAIN":
            bot.edit_message_text(TXT_WELCOME, chat_id=cid,
                                  message_id=mid, reply_markup=kb_main())

        # ─── كورسات مرحلة ───
        elif act == "VIEW":
            sid = parts[1]
            bot.edit_message_text(
                f"📂 *{STAGES[sid]}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"اختر الفصل الدراسي:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_courses(sid)
            )

        # ─── قائمة المواد ───
        elif act == "COURSE":
            sid, ck = parts[1], parts[2]
            subs = get_subjects(sid, ck)
            text = (
                f"📚 *{STAGES[sid]} — {COURSES[ck]}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 عدد المواد: *{len(subs)}*\n\n"
                f"اختر المادة:"
                if subs else
                f"📂 *{STAGES[sid]} — {COURSES[ck]}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ لا توجد مواد مضافة بعد."
            )
            bot.edit_message_text(text, chat_id=cid, message_id=mid,
                                  reply_markup=kb_subjects(sid, ck))

        # ─── تصنيفات المادة ───
        elif act == "SUBJ":
            sid, ck, idx = parts[1], parts[2], int(parts[3])
            sub = get_subject(sid, ck, idx)
            if not sub:
                bot.send_message(cid, "⚠️ المادة غير موجودة.")
                return
            # إحصاء الملفات
            counts = {cat: len(sub.get(cat,{})) for cat in CATEGORIES}
            total  = sum(counts.values())
            lines  = [f"📖 *{sub['name']}*",
                      f"📂 {STAGES[sid]} — {COURSES[ck]}",
                      f"━━━━━━━━━━━━━━━━━━━━━"]
            for cat,(icon,label) in CATEGORIES.items():
                lines.append(f"{icon} {label}: {counts[cat]} ملف")
            lines += [f"\n📦 الإجمالي: *{total} ملف*",
                      "\nاختر القسم:"]
            bot.edit_message_text("\n".join(lines), chat_id=cid, message_id=mid,
                                  reply_markup=kb_categories(sid, ck, idx))

        # ─── قائمة ملفات قسم ───
        elif act == "CAT":
            sid, ck, idx, cat = parts[1], parts[2], int(parts[3]), parts[4]
            sub   = get_subject(sid, ck, idx)
            files = get_cat_files(sid, ck, idx, cat)
            icon, label = CATEGORIES[cat]
            text = (
                f"{icon} *{label}*\n"
                f"📖 {sub['name']} — {STAGES[sid]}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 عدد الملفات: *{len(files)}*\n\n"
                f"اضغط للتحميل المباشر ⬇️"
                if files else
                f"{icon} *{label}*\n"
                f"📖 {sub['name']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"⚠️ لا توجد ملفات في هذا القسم."
            )
            bot.edit_message_text(text, chat_id=cid, message_id=mid,
                                  reply_markup=kb_files_list(sid, ck, idx, cat))

        # ─── إرسال الملف للطالب ───
        elif act == "GETFILE":
            sid, ck = parts[1], parts[2]
            subj_idx, cat, file_idx = int(parts[3]), parts[4], int(parts[5])
            name, meta = get_file_at(sid, ck, subj_idx, cat, file_idx)
            if meta is None:
                bot.send_message(cid, "⚠️ الملف غير موجود.")
                return
            sub      = get_subject(sid, ck, subj_idx)
            icon, label = CATEGORIES[cat]
            caption  = (
                f"📎 *{name}*\n"
                f"{icon} {label} — 📖 {sub['name']}\n"
                f"📂 {STAGES[sid]} — {COURSES[ck]}\n"
                f"🏛️ هندسة الحاسبات — جامعة البصرة"
            )
            _send_file(cid, meta["file_id"], meta.get("file_type","document"), caption)
            logger.info(f"[SEND] {name} → {cid}")

        # ══════════ لوحة الأدمن ══════════

        elif act == "ADM" and cid in ADMIN_IDS:
            sub_act = parts[1]

            if sub_act == "HOME":
                bot.edit_message_text(TXT_ADMIN, chat_id=cid,
                                      message_id=mid, reply_markup=kb_admin_home())

            elif sub_act == "ADD_SUBJ":
                bot.edit_message_text(
                    "➕ *إضافة مادة جديدة*\n━━━━━━━━━━━━━━━━━━━━━\n"
                    "📌 اختر المرحلة:",
                    chat_id=cid, message_id=mid,
                    reply_markup=kb_stage_sel("AS1")
                )

            elif sub_act == "ADD_FILE":
                bot.edit_message_text(
                    "📤 *رفع ملف*\n━━━━━━━━━━━━━━━━━━━━━\n"
                    "📌 اختر المرحلة:",
                    chat_id=cid, message_id=mid,
                    reply_markup=kb_stage_sel("AF1")
                )

            elif sub_act == "DEL_SUBJ":
                bot.edit_message_text(
                    "🗑️ *حذف مادة*\n━━━━━━━━━━━━━━━━━━━━━\n"
                    "📌 اختر المرحلة:",
                    chat_id=cid, message_id=mid,
                    reply_markup=kb_stage_sel("DS1")
                )

            elif sub_act == "DEL_FILE":
                bot.edit_message_text(
                    "❌ *حذف ملف*\n━━━━━━━━━━━━━━━━━━━━━\n"
                    "📌 اختر المرحلة:",
                    chat_id=cid, message_id=mid,
                    reply_markup=kb_stage_sel("DF1")
                )

            elif sub_act == "STATS":
                lines = ["📊 *إحصائيات المواد*\n━━━━━━━━━━━━━━━━━━━━━"]
                gtotal = 0
                for s in ("1","2","3","4"):
                    stotal = 0
                    lines.append(f"\n{SE[s]} *{STAGES[s]}*")
                    for ck in ("s1","s2"):
                        subs = get_subjects(s, ck)
                        ftotal = sum(
                            sum(len(sub.get(c,{})) for c in CATEGORIES)
                            for sub in subs
                        )
                        stotal += ftotal
                        lines.append(f"  {CE[ck]} {COURSES[ck][:12]}: {len(subs)} مادة — {ftotal} ملف")
                    gtotal += stotal
                lines.append(f"\n📦 *الإجمالي: {gtotal} ملف*")
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
                bot.edit_message_text("\n".join(lines), chat_id=cid,
                                      message_id=mid, reply_markup=kb)

        # ── إضافة مادة: الكورس ──
        elif act == "AS1" and cid in ADMIN_IDS:
            sid = parts[1]
            bot.edit_message_text(
                f"➕ *إضافة مادة — {STAGES[sid]}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر الكورس:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_course_sel(sid, "AS2")
            )

        # ── إضافة مادة: أدخل الاسم ──
        elif act == "AS2" and cid in ADMIN_IDS:
            sid, ck = parts[1], parts[2]
            user_states[cid] = {"action":"add_subj","sid":sid,"ck":ck}
            bot.send_message(
                cid,
                f"➕ *{STAGES[sid]} — {COURSES[ck]}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"✏️ أرسل *اسم المادة*\n\nمثال: `Microprocessors`\n\n"
                f"⚠️ /cancel للإلغاء"
            )

        # ── رفع ملف: الكورس ──
        elif act == "AF1" and cid in ADMIN_IDS:
            sid = parts[1]
            bot.edit_message_text(
                f"📤 *رفع ملف — {STAGES[sid]}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر الكورس:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_course_sel(sid, "AF2")
            )

        # ── رفع ملف: المادة ──
        elif act == "AF2" and cid in ADMIN_IDS:
            sid, ck = parts[1], parts[2]
            subs = get_subjects(sid, ck)
            if not subs:
                bot.send_message(cid,
                    f"⚠️ لا توجد مواد في *{STAGES[sid]} — {COURSES[ck]}*.\n"
                    f"أضف مادة أولاً من لوحة التحكم.")
                return
            bot.edit_message_text(
                f"📤 *رفع ملف — {STAGES[sid]} — {COURSES[ck]}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n📌 اختر المادة:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_subj_sel(sid, ck, "AF3")
            )

        # ── رفع ملف: القسم ──
        elif act == "AF3" and cid in ADMIN_IDS:
            sid, ck, idx = parts[1], parts[2], int(parts[3])
            sub = get_subject(sid, ck, idx)
            bot.edit_message_text(
                f"📤 *رفع ملف — {sub['name']}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر القسم:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_cat_sel(sid, ck, idx, "AF4")
            )

        # ── رفع ملف: جاهز للاستقبال ──
        elif act == "AF4" and cid in ADMIN_IDS:
            sid, ck, idx, cat = parts[1], parts[2], int(parts[3]), parts[4]
            sub = get_subject(sid, ck, idx)
            icon, label = CATEGORIES[cat]
            user_states[cid] = {
                "action":"wait_file","sid":sid,"ck":ck,
                "subj_idx":idx,"cat":cat
            }
            bot.send_message(
                cid,
                f"📤 *{sub['name']} — {icon} {label}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"أرسل الآن *الملف* (PDF، صورة، فيديو...)\n\n"
                f"⚠️ /cancel للإلغاء"
            )

        # ── حذف مادة: الكورس ──
        elif act == "DS1" and cid in ADMIN_IDS:
            sid = parts[1]
            bot.edit_message_text(
                f"🗑️ *حذف مادة — {STAGES[sid]}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر الكورس:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_course_sel(sid, "DS2")
            )

        # ── حذف مادة: اختر المادة ──
        elif act == "DS2" and cid in ADMIN_IDS:
            sid, ck = parts[1], parts[2]
            subs = get_subjects(sid, ck)
            if not subs:
                bot.send_message(cid, "⚠️ لا توجد مواد.")
                return
            bot.edit_message_text(
                f"🗑️ *حذف مادة — {STAGES[sid]} — {COURSES[ck]}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\naختر المادة:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_subj_sel(sid, ck, "DS3")
            )

        # ── حذف مادة: تنفيذ ──
        elif act == "DS3" and cid in ADMIN_IDS:
            sid, ck, idx = parts[1], parts[2], int(parts[3])
            sub = get_subject(sid, ck, idx)
            if sub:
                name = sub["name"]
                materials[f"stage{sid}"][ck]["subjects"].pop(idx)
                save_db(materials)
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
                bot.edit_message_text(
                    f"✅ *تم حذف المادة!*\n🗑️ `{name}`",
                    chat_id=cid, message_id=mid, reply_markup=kb
                )

        # ── حذف ملف: الكورس ──
        elif act == "DF1" and cid in ADMIN_IDS:
            sid = parts[1]
            bot.edit_message_text(
                f"❌ *حذف ملف — {STAGES[sid]}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر الكورس:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_course_sel(sid, "DF2")
            )

        # ── حذف ملف: المادة ──
        elif act == "DF2" and cid in ADMIN_IDS:
            sid, ck = parts[1], parts[2]
            bot.edit_message_text(
                f"❌ *حذف ملف — {STAGES[sid]}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر المادة:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_subj_sel(sid, ck, "DF3")
            )

        # ── حذف ملف: القسم ──
        elif act == "DF3" and cid in ADMIN_IDS:
            sid, ck, idx = parts[1], parts[2], int(parts[3])
            sub = get_subject(sid, ck, idx)
            bot.edit_message_text(
                f"❌ *حذف ملف — {sub['name']}*\n━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 اختر القسم:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_cat_sel(sid, ck, idx, "DF4")
            )

        # ── حذف ملف: اختر الملف ──
        elif act == "DF4" and cid in ADMIN_IDS:
            sid, ck, idx, cat = parts[1], parts[2], int(parts[3]), parts[4]
            files = get_cat_files(sid, ck, idx, cat)
            if not files:
                bot.send_message(cid, "⚠️ لا توجد ملفات في هذا القسم.")
                return
            icon, label = CATEGORIES[cat]
            sub = get_subject(sid, ck, idx)
            bot.edit_message_text(
                f"❌ *{icon} {label} — {sub['name']}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━\naختر الملف للحذف:",
                chat_id=cid, message_id=mid,
                reply_markup=kb_del_files(sid, ck, idx, cat)
            )

        # ── حذف ملف: تنفيذ ──
        elif act == "DFILE" and cid in ADMIN_IDS:
            sid, ck, idx, cat = parts[1], parts[2], int(parts[3]), parts[4]
            file_idx = int(parts[5])
            name, _ = get_file_at(sid, ck, idx, cat, file_idx)
            if name:
                del materials[f"stage{sid}"][ck]["subjects"][idx][cat][name]
                save_db(materials)
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🔙 لوحة التحكم", callback_data="ADM|HOME"))
                bot.edit_message_text(
                    f"✅ *تم حذف الملف!*\n❌ `{name}`",
                    chat_id=cid, message_id=mid, reply_markup=kb
                )

    except telebot.apihelper.ApiTelegramException as e:
        logger.error(f"TG error: {e}")
    except Exception as e:
        logger.error(f"Callback error '{call.data}': {e}")
        bot.send_message(cid, "⚠️ خطأ، حاول مجدداً.")

# ══════════════════════════════════════════════
#  إرسال الملف
# ══════════════════════════════════════════════
def _send_file(cid, file_id, file_type, caption):
    fn_map = {
        "document": bot.send_document,
        "photo":    bot.send_photo,
        "video":    bot.send_video,
        "audio":    bot.send_audio,
        "voice":    bot.send_voice,
    }
    fn = fn_map.get(file_type, bot.send_document)
    fn(cid, file_id, caption=caption, parse_mode="Markdown")

# ══════════════════════════════════════════════
#  استقبال ملفات الأدمن
# ══════════════════════════════════════════════
def _extract_file(msg):
    if msg.document:  return msg.document.file_id, "document"
    if msg.photo:     return msg.photo[-1].file_id, "photo"
    if msg.video:     return msg.video.file_id,     "video"
    if msg.audio:     return msg.audio.file_id,     "audio"
    if msg.voice:     return msg.voice.file_id,     "voice"
    return None, None

@bot.message_handler(
    content_types=["document","photo","video","audio","voice"],
    func=lambda m: m.chat.id in ADMIN_IDS and m.chat.id in user_states
)
def handle_file(msg):
    state = user_states.get(msg.chat.id, {})
    if state.get("action") != "wait_file":
        return
    file_id, ftype = _extract_file(msg)
    if not file_id:
        bot.send_message(msg.chat.id, "⚠️ نوع الملف غير مدعوم.")
        return
    user_states[msg.chat.id] = {**state, "action":"wait_name",
                                 "file_id":file_id, "file_type":ftype}
    sub  = get_subject(state["sid"], state["ck"], state["subj_idx"])
    icon, label = CATEGORIES[state["cat"]]
    bot.send_message(
        msg.chat.id,
        f"✅ *استُلم الملف!* ({ftype})\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📖 {sub['name']} — {icon} {label}\n\n"
        f"✏️ أرسل الآن *اسم الملف*\nمثال: `Lecture 3 — Memory Organization`\n\n"
        f"⚠️ /cancel للإلغاء"
    )

@bot.message_handler(
    content_types=["text"],
    func=lambda m: m.chat.id in ADMIN_IDS and m.chat.id in user_states
)
def handle_text(msg):
    state = user_states.get(msg.chat.id, {})
    if msg.text.startswith("/"):
        return
    action = state.get("action")

    # ── اسم مادة جديدة ──
    if action == "add_subj":
        name = msg.text.strip()
        if not name:
            bot.send_message(msg.chat.id, "❌ الاسم فارغ.")
            return
        sid, ck = state["sid"], state["ck"]
        new_subj = {"name":name,"lec":{},"hw":{},"lab":{},"exp":{}}
        materials[f"stage{sid}"][ck]["subjects"].append(new_subj)
        save_db(materials)
        del user_states[msg.chat.id]
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("➕ إضافة مادة أخرى", callback_data="ADM|ADD_SUBJ"),
            InlineKeyboardButton("📤 رفع ملف للمادة",  callback_data="ADM|ADD_FILE"),
            InlineKeyboardButton("🔙 لوحة التحكم",     callback_data="ADM|HOME"),
        )
        bot.send_message(
            msg.chat.id,
            f"✅ *تمت إضافة المادة!*\n"
            f"📖 `{name}`\n"
            f"📂 {STAGES[sid]} — {COURSES[ck]}",
            reply_markup=kb
        )
        logger.info(f"[ADD_SUBJ] {name} → stage{sid}/{ck}")

    # ── اسم الملف ──
    elif action == "wait_name":
        name = msg.text.strip()
        if not name:
            bot.send_message(msg.chat.id, "❌ الاسم فارغ.")
            return
        sid      = state["sid"]
        ck       = state["ck"]
        idx      = state["subj_idx"]
        cat      = state["cat"]
        file_id  = state["file_id"]
        ftype    = state["file_type"]
        materials[f"stage{sid}"][ck]["subjects"][idx][cat][name] = {
            "file_id": file_id, "file_type": ftype
        }
        save_db(materials)
        del user_states[msg.chat.id]
        sub = get_subject(sid, ck, idx)
        icon, label = CATEGORIES[cat]
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(
            InlineKeyboardButton("📤 رفع ملف آخر",  callback_data="ADM|ADD_FILE"),
            InlineKeyboardButton("🔙 لوحة التحكم",  callback_data="ADM|HOME"),
        )
        bot.send_message(
            msg.chat.id,
            f"✅ *تم رفع الملف بنجاح!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📎 الاسم  : `{name}`\n"
            f"📎 النوع  : `{ftype}`\n"
            f"{icon} القسم  : {label}\n"
            f"📖 المادة : {sub['name']}\n"
            f"📂 {STAGES[sid]} — {COURSES[ck]}",
            reply_markup=kb
        )
        logger.info(f"[ADD_FILE] {name} → stage{sid}/{ck}/{sub['name']}/{cat}")

# ══════════════════════════════════════════════
#  تشغيل البوت
# ══════════════════════════════════════════════
if __name__ == "__main__":
    logger.info("🚀 CoE Bot v4.0 — University of Basra — Starting...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
