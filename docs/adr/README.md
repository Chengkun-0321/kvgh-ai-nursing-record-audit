# 架構決策紀錄（ADR）

記錄「為什麼這樣設計」。遇到下列情況須新增 ADR：技術選型、資料格式對照、影響多個模組的設計、推翻既有決策。

- 檔名：`NNNN-英文-kebab-case.md`，編號遞增
- 已採用的 ADR 不修改內容；要推翻時新增一份，並把舊的狀態改為「由 NNNN 取代」

## 模板

```markdown
# ADR NNNN：標題

- 狀態：提議／採用／由 NNNN 取代／廢止
- 日期：YYYY-MM-DD

## 背景
為什麼需要做這個決定。

## 決策
決定了什麼。

## 影響
好處、代價、後續需要做的事。
```

## 索引

| 編號 | 標題 | 狀態 |
|---|---|---|
| [0001](0001-sqlite-to-postgresql.md) | DB 由 SQLite 過渡到 PostgreSQL | 採用 |
| [0002](0002-llm-phi-policy.md) | 病患資料外送 LLM 政策（暫行） | 採用（暫行） |
| [0003](0003-ward-scene-3d.md) | 病房場景改用 Blender 場景模組＋React Three Fiber | 提議（視角與設定檔部分由 0004 取代） |
| [0004](0004-ward-straight-view.md) | 病房地圖預設改為正視角，保留斜視角切換，場景滿版 | 提議 |
| [0005](0005-floating-glass-shell.md) | 桌機工作區外框改為全浮動液態玻璃 | 提議 |
