FROM python:3.12-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

# C／C++ 編譯工具只留在 builder，避免增加 runtime 體積。
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip wheel --wheel-dir=/wheels -r requirements.txt \
    && pip install --no-index --find-links=/wheels --prefix=/install -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime

ARG APP_UID=1000
ARG APP_GID=1000
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# 稽核以 Asia/Taipei 判斷日期，slim 映像須有時區資料庫。
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    # GID 已存在（例：Debian 內建的 100 users）時沿用該群組，避免 groupadd 重複而建置失敗
    && (getent group "${APP_GID}" >/dev/null || groupadd --gid "${APP_GID}" app) \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home app \
    && mkdir -p /app/data \
    && chown "${APP_UID}:${APP_GID}" /app/data

COPY --from=builder /install/ /usr/local/
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY docker/entrypoint.sh ./docker/entrypoint.sh

USER app
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/app/docker/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
