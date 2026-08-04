#!/usr/bin/env bash
# ============================================================================
#  GhayoomiBot — نصب خودکار روی سرور VPS (Ubuntu 22.04 / 24.04)
#  سازنده: ARIAMIR — https://t.me/Ariamir_academy — https://ariamir.ir
#
#  اجرا (یک خط، با root):
#  curl -fsSL https://raw.githubusercontent.com/Ghost87/Ghayoomibot/main/deploy/install.sh | sudo bash
# ============================================================================
set -euo pipefail

GREEN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
say(){  echo -e "${GREEN}[✓]${NC} $*"; }
warn(){ echo -e "${YEL}[!]${NC} $*"; }
die(){  echo -e "${RED}[✗]${NC} $*"; exit 1; }

[ "$(id -u)" -eq 0 ] || die "باید با یوزر root اجرا شود:  curl ... | sudo bash"

APP_DIR=/opt/Ghayoomibot
REPO=https://github.com/Ghost87/Ghayoomibot.git
BACKUP_DIR=/opt/ghayoomi-backups
SERVICE=ghayoomibot

echo
echo -e "${CYAN}🤖 نصب خودکار قیومی‌بات روی VPS — ARIAMIR${NC}"
echo "=============================================="

# ---------- 1) بسته‌های سیستم ----------
say "به‌روزرسانی بسته‌ها و نصب ابزارهای لازم (python/git/ufw)…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y >/dev/null
apt-get install -y python3 python3-venv python3-pip git ufw curl >/dev/null

# ---------- 2) دریافت سورس ----------
if [ -d "$APP_DIR/.git" ]; then
  say "نسخه‌ای از سورس روی سرور هست — به‌روزرسانی…"
  git -C "$APP_DIR" pull --ff-only || warn "pull ناموفق؛ با نسخه فعلی ادامه می‌دهیم"
else
  say "کلون سورس ربات از گیت‌هاب در $APP_DIR …"
  git clone --depth 1 "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

# ---------- 3) محیط مجازی و وابستگی‌ها ----------
say "ساخت venv و نصب کتابخانه‌های پایتون…"
python3 -m venv venv
./venv/bin/pip install -q -U pip
./venv/bin/pip install -q -r requirements.txt

# ---------- 4) ساخت .env تعاملی ----------
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  [ -f .env.example ] && cp .env.example "$ENV_FILE" || : > "$ENV_FILE"
  echo
  warn "تنظیمات اولیه (.env) — برای هر مورد مقدار را تایپ و Enter بزنید"
  exec </dev/tty || true

  set_kv(){  # set_kv KEY VALUE
    if grep -qE "^$1=" "$ENV_FILE"; then
      sed -i -E "s|^$1=.*|$1=$2|" "$ENV_FILE"
    else
      echo "$1=$2" >> "$ENV_FILE"
    fi
  }

  BOT_TOKEN=""
  while [ -z "$BOT_TOKEN" ]; do
    read -rp "  🔑 توکن ربات (از BotFather): " BOT_TOKEN
    case "$BOT_TOKEN" in *:*) : ;; *) warn "فرمت توکن معتبر نیست (باید شامل : باشد)"; BOT_TOKEN="";; esac
  done
  read -rp "  👑 آیدی عددی ادمین‌ها (با کاما — مثل: 8975757230): " ADMIN_USER_IDS
  read -rp "  🧾 یوزرنیم ورود پنل /admin (مثل: ARIAdmin): " ADMIN_LOGIN
  read -rp "  🔐 رمز ورود پنل /admin: " ADMIN_PASSWORD
  read -rp "  👥 آیدی عددی گروه دریافت رزومه (الان ندارید؟ Enter — بعداً پر می‌شود): " ADMIN_GROUP_ID

  set_kv BOT_TOKEN "$BOT_TOKEN"
  [ -n "${ADMIN_USER_IDS:-}" ]  && set_kv ADMIN_USER_IDS "$ADMIN_USER_IDS"
  [ -n "${ADMIN_LOGIN:-}" ]     && { set_kv ADMIN_USERNAME "$ADMIN_LOGIN" 2>/dev/null || true; set_kv ADMIN_LOGIN "$ADMIN_LOGIN" 2>/dev/null || true; }
  [ -n "${ADMIN_PASSWORD:-}" ]  && set_kv ADMIN_PASSWORD "$ADMIN_PASSWORD"
  [ -n "${ADMIN_GROUP_ID:-}" ]  && set_kv ADMIN_GROUP_ID "$ADMIN_GROUP_ID"
  say "فایل .env ساخته شد"
else
  say ".env موجود است — بدون تغییر نگه داشته شد"
fi

# ---------- 5) سرویس systemd ----------
say "ساخت سرویس سیستمی (اجرا هنگام بوت + ری‌استارت خودکار)…"
cat > /etc/systemd/system/$SERVICE.service <<UNIT
[Unit]
Description=GhayoomiBot Telegram Bot (ARIAMIR)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable $SERVICE >/dev/null 2>&1 || true

# ---------- 6) فایروال ----------
say "تنظیم فایروال (فقط SSH باز)…"
ufw allow 22/tcp >/dev/null || true
ufw allow 9011/tcp >/dev/null || true
ufw --force enable >/dev/null

# ---------- 7) بکاپ روزانه ----------
say "راه‌اندازی بکاپ روزانه‌ی دیتابیس (ساعت 03:30، نگهداری ۱۴ نسخه)…"
mkdir -p "$BACKUP_DIR"
cat > /etc/cron.d/$SERVICE-backup <<'CRON'
30 3 * * * root mkdir -p /opt/ghayoomi-backups && tar -czf /opt/ghayoomi-backups/ghayoomi-$(date +\%F-\%H\%M).tgz -C /opt/Ghayoomibot data 2>/dev/null; find /opt/ghayoomi-backups -name 'ghayoomi-*.tgz' -mtime +14 -delete 2>/dev/null
CRON
chmod 644 /etc/cron.d/$SERVICE-backup

# ---------- 8) اجرا ----------
STARTED=0
if grep -qE "^BOT_TOKEN=[0-9]+:.+" "$ENV_FILE" 2>/dev/null; then
  say "توکن پیدا شد — اجرای ربات…"
  systemctl restart $SERVICE
  sleep 4
  STARTED=1
else
  warn "توکن داخل .env کامل نیست — ربات فعلاً اجرا نشد؛ بعد از پر کردن .env:"
  warn "    systemctl restart $SERVICE"
fi

echo
echo "=============================================="
if [ "$STARTED" -eq 1 ]; then
  systemctl --no-pager --full status $SERVICE | head -n 12 || true
  echo
  say "لاگ‌های زنده:"
  journalctl -u $SERVICE -n 12 --no-pager || true
  echo
  say "🎉 نصب کامل شد!"
else
  say "نصب بدون اجرا کامل شد"
fi
echo
echo -e "${CYAN}📌 نکته‌های مهم:${NC}"
echo "  • دیدن لاگ زنده:        journalctl -u $SERVICE -f"
echo "  • ویرایش تنظیمات:       nano $APP_DIR/.env  (بعد: systemctl restart $SERVICE)"
echo "  • بکاپ‌ها:              $BACKUP_DIR"
echo "  • اگر آیدی گروه رزومه را نداشتید: ربات را عضو گروه کنید، سپس آیدی را در .env بگذارید"
echo "  • سازنده: ARIAMIR — https://t.me/Ariamir_academy — https://ariamir.ir"
