
# FiveM Warn API and Discord Bot

此專案是一個結合 **FiveM 警告管理 API** 和 **Discord 機器人** 的應用程式，提供玩家警告記錄的新增、查詢與刪除功能。
```markdown
## 功能特性

### API 功能
- **新增警告記錄**：透過 `/add-identifiers` 路由新增玩家的警告記錄。
- **查詢警告記錄**：透過 `/search-warns` 路由搜尋警告記錄。
- **刪除警告記錄**：透過 `/delete-warn/{warn_id}` 路由刪除指定的警告記錄。

### Discord 機器人功能
- **新增警告**：使用 `/addwarn` 指令新增警告記錄。
- **查詢警告**：使用 `/searchwarn` 指令搜尋警告記錄。
- **刪除警告**：使用 `/deletewarn` 指令刪除指定的警告記錄。
- **分頁顯示**：查詢結果支援分頁顯示，方便瀏覽多筆記錄。

## 專案結構

```
run.py
api/
    api.py
bot/
    bot.py
```

- `run.py`：主程式入口，啟動 API 和 Discord 機器人。
- `api/api.py`：API 伺服器的實作，包含資料庫操作與路由處理。
- `bot/bot.py`：Discord 機器人的實作，包含指令處理與互動邏輯。

## 安裝與使用

### 1. 安裝依賴
請確保已安裝 Python 3.8 或以上版本，並執行以下指令安裝所需套件：

```bash
pip install -r requirements.txt
```

### 2. 設置資料庫
專案會自動初始化 SQLite 資料庫，無需手動設置。

### 3. 配置 Discord Bot Token
在 `run.py` 中，將 `BOT_TOKEN` 替換為您的 Discord 機器人 Token。

```python
BOT_TOKEN = "Your_Discord_Bot_Token"
```

### 4. 啟動專案
執行以下指令啟動 API 和 Discord 機器人：

```bash
python run.py
```

### 5. 使用 API
API 預設運行於 `http://<本機IP>:3000`，可透過以下路由進行操作：
- `POST /add-identifiers`：新增警告記錄
- `GET /search-warns`：查詢警告記錄
- `DELETE /delete-warn/{warn_id}`：刪除警告記錄

### 6. 使用 Discord 機器人
在 Discord 中，使用以下指令與機器人互動：
- `/addwarn`：新增警告記錄
- `/searchwarn`：查詢警告記錄
- `/deletewarn`：刪除警告記錄

## 注意事項
- 請勿將 Discord Bot Token 公開，避免安全風險。
- 若需修改 API 運行的 IP 或 Port，請調整 `api/api.py` 中的 `start_api` 函數。

## 貢獻
歡迎提交 Issue 或 Pull Request，協助改進此專案。

## 授權
此專案採用 MIT 授權條款。
