# ---- ビルドステージ ----
FROM python:3.11-slim AS builder

WORKDIR /app

# システム依存のみ先にコピー（スーパーレイヤーキャッシュ効かせる）
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ---- 本番ステージ ----
FROM python:3.11-slim

WORKDIR /app

# ライブラリのみコピー
 COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# ソースコード
COPY . .

# 非 root ユーザーで起動（セキュリティ）
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
