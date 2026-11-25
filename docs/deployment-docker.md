# Docker Compose 部署

> **狀態（2026-11-25）**：設定已完成，但**尚未在 Docker 上實測**（撰寫時的 Mac 沒有 Docker）。已在容器外模擬驗證前後端連線與 CORS；映像建置、掛載權限與 `down`／`up` 後的資料保存，須在 Linux 主機依本文步驟實測。範圍見文末「驗證範圍」。

## 背景

本專案由 FastAPI 後端與 Next.js 16 前端組成。容器化將 Python 3.12、Node 22 與應用程式依賴固定在映像內，讓 Linux 主機不必重建本機 venv／Node 開發環境。後端使用現有 `requirements.txt`，前端使用 `package-lock.json` 與 `npm ci`，不新增應用程式依賴。

這份 Compose 配置使用 SQLite、手動稽核與現有的模型設定功能；沒有新增登入、排程或病房批次稽核。

## 架構與資料

| 呼叫端／資料 | 目的地 | 說明 |
|---|---|---|
| 瀏覽器 → 前端 | `http://localhost:3000` | 主機連接埠由 `FRONTEND_PORT` 決定；容器固定 3000 |
| 瀏覽器 → 後端 | `http://localhost:8000/api/v1/...` | 基底位址由 `PUBLIC_API_BASE_URL` 傳入前端 build arg；留空則使用 `http://localhost:${BACKEND_PORT:-8000}` |
| Server Component → 後端 | `http://backend:8000/api/v1/...` | 前端容器執行時的 `API_BASE_URL`；`backend` 是 Compose 服務名稱 |
| 主機 `./backend/data` | 後端 `/app/data` | 可寫 bind mount，含 `app.db`、SQLite 附屬檔與 `chatgpt/` 憑證 |
| 主機 `./data` | 後端 `/hospital-data` | 院方去識別化 JSON，唯讀 bind mount |

`BACKEND_PORT` 只改主機對外連接埠；後端容器固定監聽 8000。API 基底位址不含 `/api/v1`，該前綴由既有 API 呼叫路徑帶入。遠端瀏覽器不能使用 `backend` 這個容器名稱，也不能把 `localhost` 當成 Linux 主機。

Compose 以 `environment` 覆寫 `backend/.env` 的 `DATA_DIR=/app/data`、`DATABASE_URL=sqlite+aiosqlite:////app/data/app.db`、`CHATGPT_TOKEN_DIR=/app/data/chatgpt`、`HOSPITAL_DATA_DIR=/hospital-data` 及 `CORS_ORIGINS`。本配置固定使用 SQLite，不會沿用 `.env` 的 PostgreSQL 或主機路徑。

後端先執行 `alembic upgrade head`，成功後才以單一 worker 啟動 uvicorn。健康檢查使用映像內 Python GET `/api/v1/llm-providers`，不依賴院方資料或外部 LLM；成功後前端才啟動。這只證明 HTTP 服務可回應，不代表 DB 查詢、院方資料或模型連線都正常。`depends_on` 的健康條件用於啟動，不會在後端日後變成 unhealthy 時自動停止前端。

兩個映像的執行程序都不是 root。後端 builder 產生 wheel 並安裝到暫存前綴，runtime 只複製已安裝套件、程式、prompt 與 migration；編譯工具不進 runtime。runtime 安裝系統 `tzdata`，提供稽核使用的 Asia/Taipei 時區。前端只帶 standalone、`.next/static` 與 `public`，保留 3D 模型等本地資源。

## Linux 主機首次部署

1. 先自行安裝 Docker Engine 與 Docker Compose plugin，讓部署帳號可執行下列指令。本專案不提供主機安裝腳本，也不在主機安裝全域 npm／pip 套件。

   ```bash
   docker --version && docker compose version
   ```

2. 將同一版本專案放到 Linux 主機，以下指令皆在專案根目錄執行。初次複製設定時保留已存在的檔案：

   ```bash
   umask 077
   test -e .env || cp .env.example .env
   test -e backend/.env || cp backend/.env.example backend/.env
   id -u && id -g
   mkdir -p backend/data data
   ```

   編輯根目錄 `.env`，將 `APP_UID`／`APP_GID` 設為上面 Linux 部署帳號的 UID／GID（預設都是 1000）。若改 `BACKEND_DATA_DIR` 或 `HOSPITAL_DATA_HOST_DIR`，請預先建立對應的主機目錄並放入資料；相對路徑以專案根目錄為準。不要讓 Docker 代建資料目錄，否則目錄可能屬於 root。

   院方資料須另行放入 `data/<YYYYMMDD>/<病房>/`；空目錄不會提供病患資料。部署帳號與後端 UID 必須能讀取院方檔案並穿越各層目錄。Compose 不使用 `frontend/.env.local`。

3. 依實際連線方式調整公開 API 與 CORS（見後文），再建置映像。這一步需要取得基底映像及 npm／pip／Debian 套件的網路存取；不會啟動應用程式或執行 migration。

   ```bash
   docker compose build
   ```

4. **全新資料庫**才需要產生新的 Fernet 金鑰。使用已建好的後端映像，不需在主機安裝 Python；這個指令覆寫 entrypoint，不會執行 migration：

   ```bash
   docker compose run --rm --no-deps --entrypoint python backend -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

   將結果填入 `backend/.env` 的 `LLM_KEY_ENCRYPTION_KEY`。此檔經 `env_file` 注入後端，不會 COPY 進映像。若搬移既有 DB，必須沿用原金鑰；換新金鑰會使已儲存的 API key 無法解密。不要把金鑰貼入 issue 或提交版控。

5. **啟動會執行 migration 並可能更新 DB schema；使用既有資料前先停止寫入並備份。** 檢查與啟動：

   ```bash
   docker compose config --quiet
   docker compose up -d
   docker compose ps
   docker compose logs --tail=100 backend frontend
   ```

   在 Linux 主機瀏覽 `http://localhost:3000`；從其他電腦連線請先套用下節設定。另檢查首頁、病患資料與模型設定；健康檢查通過不等於完整功能驗證。避免分享可能含敏感內容的 log；不要貼出完整 `docker compose config`，其展開結果可能含後端機密。

   持續追蹤 log（Ctrl+C 只結束追蹤）：

   ```bash
   docker compose logs -f --tail=100 backend frontend
   ```

   停止並移除容器與專案網路：

   ```bash
   docker compose down
   ```

   bind mount 目錄、SQLite 與 token 不會因 `down` 被刪除。兩個服務都設定 `restart: unless-stopped`；主動停止後須自行重新啟動。

## 改前端或後端連接埠

只在 Linux 主機本機瀏覽時，例如修改根目錄 `.env`：

```dotenv
FRONTEND_PORT=3100
BACKEND_PORT=8000
PUBLIC_API_BASE_URL=
CORS_ALLOWED_ORIGINS=
```

```bash
docker compose up -d
```

前端變成 `http://localhost:3100`，CORS 自動變成 `["http://localhost:3100"]`，不必重新 build 前端。Compose 會重建設定有變的容器。

若已明確填入 `CORS_ALLOWED_ORIGINS`，它會取代預設值，必須自行同步新的來源連接埠。只改 `backend/.env` 裡的 CORS 不會生效，因為 Compose 的 `environment` 優先。

若修改 `BACKEND_PORT`，且 `PUBLIC_API_BASE_URL` 留空，前端 build arg 的預設值也會改變，因此需執行：

```bash
docker compose build frontend && docker compose up -d
```

如果明確設定了 `PUBLIC_API_BASE_URL`，須自行同步可由瀏覽器到達的新後端位址。容器間 `API_BASE_URL=http://backend:8000` 始終不變。

## 從其他電腦以 IP／網域連線

例如 Linux 主機 IP 為 `192.168.1.20`，根目錄 `.env` 設為：

```dotenv
FRONTEND_PORT=3100
BACKEND_PORT=8100
PUBLIC_API_BASE_URL=http://192.168.1.20:8100
CORS_ALLOWED_ORIGINS='["http://192.168.1.20:3100"]'
```

```bash
docker compose build frontend && docker compose up -d
```

使用者開啟 `http://192.168.1.20:3100`；瀏覽器直接呼叫 `http://192.168.1.20:8100/api/v1/...`，Server Component 仍呼叫 `http://backend:8000/api/v1/...`。兩個主機連接埠都必須能從使用者電腦連到。

使用網域時將上面的 IP 換成可解析到主機的網域。CORS 必須精確列出**瀏覽器開啟的前端來源**（協定、主機、連接埠，不含路徑與末尾斜線），不得使用 `*`。需要同時支援多個來源時可填 JSON 陣列，例如：

```dotenv
CORS_ALLOWED_ORIGINS='["http://audit.example.org:3100","http://localhost:3100"]'
```

`PUBLIC_API_BASE_URL` 在 `next build` 時以 `NEXT_PUBLIC_API_BASE_URL` 內嵌進瀏覽器 JS。只改容器執行時環境或 `docker compose restart` 不會改寫 JS；必須重新 build 並以 `up -d` 套用映像。此值公開可見，不能放機密。Server Component 使用執行時 `API_BASE_URL`，沒有此項內嵌限制。

若前方另有 HTTPS 反向代理，API 公開位址也要可經 HTTPS 存取，CORS 使用瀏覽器實際看到的前端 HTTPS 來源，避免混合內容封鎖。本 Compose 沒有提供 TLS 或反向代理。

## 從 Mac 搬移既有 SQLite 與憑證

搬移資料前，Linux 應使用與 Mac 資料庫相容的專案版本。不要讓兩個後端同時操作同一份 SQLite；不要只複製正在寫入的 `app.db`，否則可能漏掉 WAL 內資料。

**先選對資料庫檔。** 容器固定使用 `/app/data/app.db`。Mac 上 `npm run start:main` 用的是 `backend/data/main.db`，而 `app.db` 可能停在其他功能分支的 migration；把這種 `app.db` 帶到 main 版本，後端會因 `Can't locate revision` 停止（2026-11-25 以本機 `app.db` 實測即如此）。要部署 main 分支時，打包前先在 Mac 確認版本（於 `backend/`，`DATABASE_URL` 指向要搬的檔案後執行 `.venv/bin/python -m alembic current`），並在 Linux 解壓後把要用的檔案改名為 `app.db`（例：`mv backend/data/main.db backend/data/app.db`，原 `app.db` 先改名備份）。

1. 在 Mac 專案根目錄停止既有服務（若由其他方式啟動，須另行停止該後端），再打包整個資料目錄：

   ```bash
   npm stop
   umask 077
   tar -czf "$HOME/kvgh-backend-data.tgz" -C backend data
   scp "$HOME/kvgh-backend-data.tgz" deploy@linux-host:/home/deploy/
   scp backend/.env deploy@linux-host:/home/deploy/kvgh-backend.env
   ```

   封存檔包含 DB、SQLite 附屬檔及可能存在的 ChatGPT 登入憑證；另傳的 `.env` 含原 Fernet 金鑰。使用受控帳號與加密傳輸，勿提交或公開分享這些檔案。此操作不含根目錄院方 `data/`，該目錄須另行搬移。

2. 以下以 Linux 使用預設 `BACKEND_DATA_DIR=./backend/data`、已依首次部署建立目錄為例。**還原會替換部署使用的資料及機密設定；先停服務並保留原內容。** 在 Linux 專案根目錄執行：

   ```bash
   docker compose down
   umask 077
   mv backend/data "backend/data.before-import-$(date +%Y%m%d-%H%M%S)"
   cp backend/.env "backend/.env.before-import-$(date +%Y%m%d-%H%M%S)"
   tar --no-same-owner --no-same-permissions -xzf /home/deploy/kvgh-backend-data.tgz -C backend
   cp /home/deploy/kvgh-backend.env backend/.env
   ```

   若使用自訂資料路徑，請對應調整備份與解壓位置。備份 `.env` 的檔名同樣被 `.gitignore` 與 `.dockerignore` 排除。保留原 `LLM_KEY_ENCRYPTION_KEY`，不要重新產生；Mac `.env` 中的絕對路徑會由 Compose 覆寫。檢查模型設定內儲存的位址：Mac 的 `localhost`／區網 IP 可能需要在網頁設定頁更新。

3. 確認資料歸屬與容器 UID/GID 一致（見下節），再啟動：

   ```bash
   docker compose up -d
   docker compose logs --tail=100 backend
   ```

   後端會按目前程式的 migration 升級帶入的 DB；若版本不相容或出現找不到 revision，先停止並核對程式版本與備份，勿自行修改既有 migration 或直接覆蓋 DB。確認既有稽核紀錄、模型設定與解密正常後，再依主機資料保護流程處理傳輸封存檔與暫存 `.env`。

## UID/GID 與權限排解

Linux bind mount 保留主機的數字 UID/GID，映像內的目錄擁有者不會覆蓋掛載目錄的權限。後端 `APP_UID`／`APP_GID` 預設 1000，前端使用 `node` 帳號且沒有主機資料掛載。

遇到 `Permission denied` 或 `unable to open database file`，先查看：

```bash
id -u && id -g
ls -ld backend/data backend/data/chatgpt data
docker compose run --rm --no-deps --entrypoint id backend
```

`chatgpt/` 尚未建立時 `ls` 可能回報不存在，可在後端成功啟動後再檢查。資料目錄必須可寫，SQLite 才能建立 journal／WAL；院方目錄只需可讀與可穿越。

優先讓根目錄 `.env` 的 `APP_UID`／`APP_GID` 對齊資料擁有者，修改後重新建置：

```bash
docker compose build backend && docker compose up -d
```

若必須更改既有資料歸屬，**遞迴 chown 會變更目錄內所有檔案擁有者；先確認路徑與備份，僅處理專案資料目錄。** 以下由有權限的管理者執行，`1000:1000` 必須換成實際 `APP_UID:APP_GID`；不要對整個專案、院方共享目錄或系統目錄執行：

```bash
chown -R 1000:1000 backend/data
```

不要使用 `chmod 777` 或讓後端改以 root 執行來繞過問題。後端會把 ChatGPT 目錄限制為 0700、既有憑證檔為 0600，entrypoint 的 `umask 077` 也限制新檔權限；若 token 目錄不屬於執行 UID，啟動時的權限設定可能失敗。啟用 SELinux 的主機還須由管理者確認 bind mount 標籤政策，本配置未加入 `:z`／`:Z` 自動重標記。

## 已知限制與維運邊界

- [資安與隱私規範](conventions/security-privacy.md) 明訂目前無登入與權限控管，LLM 設定頁正式上線前須控管權限。本 Compose 預設將兩個 port 發布到主機所有介面，應只部署於受控網路；CORS 不能取代登入或網路存取限制。
- SQLite 固定單 worker，不支援藉由增加後端副本擴展；執行中的稽核／登入狀態也在單一程序記憶體內。不要在稽核中任意重新建立後端容器。
- ChatGPT token 明文留在 bind mount，主機管理者與可讀取備份的人仍能取得；掛載持久化不等於加密。接真實資料或共用主機前的評估見資安規範與 [ADR 0002](adr/0002-llm-phi-policy.md)、[ADR 0006](adr/0006-llm-config-settings.md)。
- 院方資料以唯讀掛載，沒有新增寫回病歷的途徑；映像建置 context 的 `.dockerignore` 排除所有 `.env*`、資料目錄、DB、憑證與開發產物，後端亦只 COPY 明列的程式路徑。不要自行把敏感檔案放進程式碼或前端 `public/`。
- `backend/.env` 透過容器環境提供機密，擁有 Docker 管理權限者仍可查看；此配置未提供 Docker secrets、磁碟加密、自動備份、TLS、登入或監控告警。
- 原先存在 DB 的 Ollama／OpenAI 相容服務位址可能是 `localhost`；容器內 `localhost` 指自己，須改成容器可達的主機／院內服務位址。Linux 上不假設 `host.docker.internal` 自動可用。
- 基底映像使用版本系列標籤，未鎖定 digest；重建可能取得新版系統套件或間接依賴。正式環境應保留已驗證映像與資料備份，以便回復。
- 驗證範圍（2026-11-25，Mac、無 Docker）：已在容器外模擬執行環境——`NEXT_PUBLIC_API_BASE_URL` 內嵌後 `next build` 產出 standalone（建置時不需後端），以 `node server.js` 跑在 8080、後端跑在 8100 並設 `CORS_ORIGINS=["http://localhost:8080"]`，首頁病患清單、病患頁稽核結果、瀏覽器跨來源呼叫後端皆正常，3000 來源被 CORS 拒絕。**未驗證**：Docker 映像建置（apt／pip／npm 下載、非 root 權限）、Compose 插值、healthcheck、bind mount 權限、`down` 後重新 `up` 的資料保存。部署主機仍須依上述步驟實測。
