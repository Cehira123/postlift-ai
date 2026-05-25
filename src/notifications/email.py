"""
メール通知モジュール
- aiosmtplib で非同期 SMTP 送信
- 環境変数 SMTP_HOST / SMTP_USER / SMTP_PASSWORD が未設定の場合は標準出力のみ

環境変数:
  SMTP_HOST     : SMTPサーバーホスト (例: smtp.sendgrid.net)
  SMTP_PORT     : SMTPポート番号 (デフォルト: 587)
  SMTP_USER     : SMTPユーザー名
  SMTP_PASSWORD : SMTPパスワード
  EMAIL_FROM    : 送信元アドレス (例: noreply@postlift.ai)
"""
from __future__ import annotations

import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@postlift.ai")


def _build_kpi_html(shop_domain: str, snapshot: dict) -> str:
    accept_rate = snapshot.get("accept_rate_pct", 0)
    extra_revenue = snapshot.get("extra_revenue", 0)
    total = snapshot.get("total_offers", 0)
    accepted = snapshot.get("accepted_offers", 0)

    bar_width = min(int(accept_rate), 100)
    revenue_fmt = f"¥{extra_revenue:,.0f}"

    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><style>
  body {{font-family: sans-serif; background:#f4f6f8; margin:0; padding:0;}}
  .card {{background:#fff; border-radius:8px; padding:24px; margin:16px auto; max-width:600px;}}
  .kpi {{display:flex; gap:16px; flex-wrap:wrap; margin:16px 0;}}
  .kpi-box {{flex:1; min-width:120px; background:#f0f4ff; border-radius:8px; padding:16px; text-align:center;}}
  .kpi-value {{font-size:2em; font-weight:bold; color:#3b5bdb;}}
  .kpi-label {{font-size:0.85em; color:#666; margin-top:4px;}}
  .bar-bg {{background:#eee; border-radius:4px; height:12px; margin:8px 0;}}
  .bar-fill {{background:#3b5bdb; height:12px; border-radius:4px; width:{bar_width}%;}}
  h1 {{color:#1a1a2e; font-size:1.4em;}}
  .footer {{text-align:center; font-size:0.8em; color:#999; margin-top:24px;}}
</style></head>
<body>
<div class="card">
  <h1>PostLift AI — 前日の成果レポート</h1>
  <p>ショップ: <strong>{shop_domain}</strong></p>
  <div class="kpi">
    <div class="kpi-box">
      <div class="kpi-value">{total}</div>
      <div class="kpi-label">オファー表示数</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-value">{accepted}</div>
      <div class="kpi-label">承諾数</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-value">{accept_rate}%</div>
      <div class="kpi-label">承諾率</div>
    </div>
    <div class="kpi-box">
      <div class="kpi-value">{revenue_fmt}</div>
      <div class="kpi-label">追加売上</div>
    </div>
  </div>
  <p>承諾率</p>
  <div class="bar-bg"><div class="bar-fill"></div></div>
  <div class="footer">
    PostLift AI — <a href="https://postlift.ai">postlift.ai</a>
  </div>
</div>
</body></html>"""


async def send_kpi_email(to_email: str, shop_domain: str, snapshot: dict) -> bool:
    """
    前日 KPI サマリーをメール送信する。
    SMTP が設定されていない場合はログ出力のみで True を返す。
    """
    subject = f"[PostLift AI] {shop_domain} — 昨日の成果レポート"
    html_body = _build_kpi_html(shop_domain, snapshot)
    text_body = (
        f"PostLift AI レポート: {shop_domain}\n"
        f"オファー: {snapshot.get('total_offers', 0)}, "
        f"承諾: {snapshot.get('accepted_offers', 0)}, "
        f"承諾率: {snapshot.get('accept_rate_pct', 0)}%, "
        f"追加売上: ¥{snapshot.get('extra_revenue', 0):,.0f}"
    )

    if not SMTP_HOST or not SMTP_USER:
        print(f"[email:log] TO={to_email} | {text_body}")
        return True

    try:
        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_FROM
        msg["To"] = to_email
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True,
        )
        print(f"[email:sent] TO={to_email} | {shop_domain}")
        return True
    except Exception as e:
        print(f"[email:error] TO={to_email} | {e}")
        return False
