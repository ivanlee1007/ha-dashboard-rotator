# ha-dashboard-rotator 中文使用說明書

`ha-dashboard-rotator` 是一個 Home Assistant 自訂整合，用來讓指定的 Lovelace Dashboard 分頁依照設定的時間自動輪播。

它不是只有後端排程，而是 **後端整合 + 前端控制器** 的組合：

- **後端整合**：儲存設定、提供 entities / services、維護 runtime 狀態
- **前端控制器**：實際在瀏覽器頁面上切換 dashboard view
- **可選狀態卡**：顯示目前 client / target / alias / runtime 狀態，並提供快捷操作

---

## 1. 功能總覽

目前版本：`0.1.20`

### 目前已支援

- 依 view 設定不同輪播秒數
- 支援單一 dashboard profile
- 頁面隱藏時暫停輪播
- 使用者互動後暫停一段時間
- 可指定只讓某一個 client 自動輪播
- 可替 client 設定 alias（例如 `lobby-tablet`）
- 提供 GUI 式 Views Editor（新增 / 編輯 / 刪除 view）
- 提供 Client Management UI
- 提供 Client Details 檢視
- 顯示 client 的 `presence` 與 `last seen`
- 提供狀態卡 `custom:dashboard-rotator-status`
- 內建繁體中文（`zh-Hant`）設定/選項流程翻譯
- 狀態卡會依 HA 語系自動切成繁中常用標籤

### 適合的場景

- 大廳展示看板
- 工廠 / 農場監控輪播頁
- 平板 / kiosk 固定輪播多個 dashboard 畫面
- 多台裝置中，只指定某一台做自動輪播

---

## 2. 安裝方式

### 方法 A：透過 HACS 安裝

如果你已經有 HACS：

1. 到 **HACS → Integrations**
2. 新增自訂 Repository：
   - Repository: `https://github.com/ivanlee1007/ha-dashboard-rotator`
   - Category: `Integration`
3. 安裝 **Dashboard Rotator**
4. 重新啟動 Home Assistant

### 方法 B：手動安裝

把整個資料夾複製到：

```text
/config/custom_components/dashboard_rotator
```

然後重新啟動 Home Assistant。

---

## 3. 第一次設定

重啟後到：

**設定 → 裝置與服務 → 新增整合 → Dashboard Rotator**

目前整合採 **單一 profile** 模式，也就是一個 config entry 對應一組 dashboard 輪播設定。

### 設定內容包含

- **Profile name**：設定名稱
- **Dashboard base path**：dashboard 根路徑，例如 `/lovelace-uninus`
- **Enabled**：是否啟用
- **Default interval**：預設輪播秒數
- **Pause after interaction**：使用者互動後暫停幾秒
- **Only rotate when page is visible**：頁面可見時才輪播
- **Start delay**：頁面載入後延遲幾秒才開始輪播
- **Target client ID**：指定只讓某個 client 輪播（可空白）
- **Views editor**：GUI 管理各個輪播頁
- **Advanced JSON**：進階 fallback 編輯模式

---

## 4. Dashboard Path 與 View Path 怎麼填

### Dashboard base path

例如你的 Lovelace Dashboard 網址是：

```text
/lovelace-uninus/home
```

那麼：

- `dashboard_path` 應填：`/lovelace-uninus`

### 每個 View 的 path

例如：

- `/lovelace-uninus/home`
- `/lovelace-uninus/weather`
- `/lovelace-uninus/power`

### 規則

每個 view 的 `path` 都必須：

- 以 `dashboard_path` 開頭
- 是完整路徑
- `seconds` 必須大於 0
- 至少要有一個 enabled view

---

## 5. Views Editor（GUI 編輯器）

本整合已提供 GUI 式 views editor，不需要一開始就手寫 JSON。

### 可以做的事

- 新增 view
- 編輯 view
- 刪除 view
- 設定 view 標題
- 設定每個 view 的秒數
- 啟用 / 停用某個 view
- 調整插入位置

### 每個 View 的欄位

- **Path**：該 view 的完整路徑
- **Seconds**：停留秒數
- **Title**：顯示名稱（可空白）
- **Enabled**：是否參與輪播

### 進階模式

如果你想直接手改 JSON，也可以進到：

- **Advanced JSON**

去編輯 `views_json`。

---

## 6. Client Management（客戶端管理）

這是目前這個整合最重要的功能之一。

因為實際輪播發生在 **瀏覽器 client** 上，所以整合會追蹤最近有回報狀態的 client。

### Client Management 頁可以做什麼

- 看目前有哪些已知 client
- 選擇 target client
- 清除 target client
- 編輯 alias
- 清除 alias
- 查看 client details

### 什麼是 target client？

如果你有多個瀏覽器同時開著同一個 dashboard：

- 不指定 target client：所有符合條件的 client 都可能輪播
- 指定 `target_client_id`：只有指定的那一個 client 會自動輪播

這很適合：

- 一台平板做 kiosk 自動輪播
- 另一台桌機只是監看，不要被自動切頁

### Alias 是什麼？

client ID 通常會長這樣：

```text
dr-hvuvo979
```

不太好記，所以可以幫它取別名，例如：

```text
lobby-tablet
factory-tv
meeting-room-panel
```

之後在 UI 裡就比較好辨識。

---

## 7. Client Details 頁面

在 Client Management 裡可以進一步看單一 client 的詳細資訊。

目前會看到：

- **Status**
- **Presence**
- **Last seen**
- **Page title**
- **Current view**
- **Next view**
- **Page visible**
- **On managed dashboard**
- **Last update**
- **Is target client**

### Presence 代表什麼

可能值包含：

- `dashboard-active`：在受管理 dashboard 上，且正在輪播 / 導頁 / 暫停流程中
- `dashboard-idle`：在受管理 dashboard 上，但目前不是 active 輪播狀態
- `dashboard-hidden`：在受管理 dashboard 上，但頁面不可見或被背景化
- `other-page`：client 還活著，但目前不在受管理 dashboard 頁面上
- `stale`：client 超過一段時間沒有回報
- `offline`：目前沒有有效狀態

### Last seen 代表什麼

表示這個 client 距離上次 heartbeat / 狀態更新多久，例如：

- `0s ago`
- `5s ago`
- `1m 12s ago`

---

## 8. Runtime Sensor 與 Entities

整合會建立幾個 HA entities。

### 主要 entity

- `sensor.dashboard_rotator_runtime`
- `switch.dashboard_rotator_enabled`
- `button.dashboard_rotator_pause`
- `button.dashboard_rotator_resume`
- `button.dashboard_rotator_next_view`
- `button.dashboard_rotator_previous_view`

> 實際 entity_id 會依 Home Assistant 的 slug / entry 命名而變化，不一定完全長這樣。

### Runtime sensor 會提供的重要 attributes

- `profile`
- `command`
- `active_client_id`
- `active_client_alias`
- `active_client_count`
- `target_client_id`
- `client_state`
- `client_states`
- `version`

如果你要除錯，最值得先看的就是 runtime sensor。

---

## 9. 服務（Services）

目前支援以下 services：

- `dashboard_rotator.pause`
- `dashboard_rotator.resume`
- `dashboard_rotator.next_view`
- `dashboard_rotator.previous_view`
- `dashboard_rotator.jump_to_view`
- `dashboard_rotator.set_client_alias`

### 共通規則

所有「控制輪播」服務都支援可選的：

- `target_client_id`

也就是你可以指定只對某一個 client 下命令。

---

### 9.1 暫停輪播

```yaml
service: dashboard_rotator.pause
data:
  target_client_id: dr-abc12345
```

如果不填 `target_client_id`，就依目前 profile / runtime 邏輯決定套用對象。

---

### 9.2 恢復輪播

```yaml
service: dashboard_rotator.resume
data:
  target_client_id: dr-abc12345
```

---

### 9.3 跳到下一頁

```yaml
service: dashboard_rotator.next_view
data:
  target_client_id: dr-abc12345
```

---

### 9.4 跳到上一頁

```yaml
service: dashboard_rotator.previous_view
data:
  target_client_id: dr-abc12345
```

---

### 9.5 跳到指定頁面

```yaml
service: dashboard_rotator.jump_to_view
data:
  path: /lovelace-uninus/weather
  target_client_id: dr-abc12345
```

---

### 9.6 設定 / 清除 Alias

設定 alias：

```yaml
service: dashboard_rotator.set_client_alias
data:
  client_id: dr-abc12345
  alias: lobby-tablet
```

清除 alias：

```yaml
service: dashboard_rotator.set_client_alias
data:
  client_id: dr-abc12345
  alias: ""
```

---

## 10. 狀態卡（Optional Status Card）

因為整合會註冊前端控制器，所以也提供一張可選的卡：

```yaml
type: custom:dashboard-rotator-status
```

如果你想指定 entity，也可以這樣寫：

```yaml
type: custom:dashboard-rotator-status
entity: sensor.dashboard_rotator_runtime
```

如果你想明確指定控制哪顆啟用開關，也可以額外給：

```yaml
type: custom:dashboard-rotator-status
entity: sensor.uninus_dashboard_rotator_test_runtime
enabled_entity: switch.uninus_dashboard_rotator_test_enabled
```

> 若未指定 `enabled_entity`，卡片會自動從 `sensor.xxx_runtime` 推導成 `switch.xxx_enabled`。

### 這張卡目前會顯示

- rotator 啟用狀態
- 內嵌 HA 風格開關（可直接 on/off）
- 目前這個瀏覽器自己的 client ID（方便對照是哪一台 kiosk / 哪個分頁）
- 可一鍵把「目前這個瀏覽器」加入 target，也可直接清除全部 target
- status card 每個 client 小卡都可直接加入 / 移出 target
- 支援 multi-target（同時指定多個 target client）
- options flow 的 client management 現在可逐一加入 / 移除 target client
- target client
- active client
- active client alias
- 所有近期 client
- alias 快捷編輯按鈕

這張卡很適合放在：

- 管理者專用 dashboard
- 測試 view
- kiosk 維運頁

---

## 11. 輪播實際怎麼運作

整體流程如下：

1. Home Assistant 載入整合
2. 整合註冊前端 JS 控制器
3. 瀏覽器打開對應 dashboard 時，controller 開始監看目前頁面
4. 如果目前位於受管理 dashboard，且符合條件，就啟動計時器
5. 時間到後自動導向下一個 view
6. 若有手動互動，會暫停指定秒數
7. 若頁面不可見，且啟用了 `only_when_visible`，就會暫停

重點是：

> **實際切頁的是前端 controller，不是 HA 後端直接替你切頁。**

所以如果某個裝置從來沒打開過那個 dashboard，它不會無中生有開始輪播。

---

## 12. 建議使用方式

### 情境 A：單一 kiosk 平板輪播

建議：

- 設定 `dashboard_path`
- 建好 views
- 用 Client Management 找到平板的 client ID
- 設成 target client
- 幫它取 alias，例如 `lobby-tablet`

這樣之後最好管理。

### 情境 B：多台裝置都開同一 dashboard，但只想讓一台輪播

建議：

- 用 target client 鎖定那台裝置
- 其他裝置保留在監看模式

### 情境 C：測試與正式環境並存

建議：

- 替不同 client 設 alias
- 從 Client Details 看 `presence` / `last seen`
- 不要只靠 client ID 生記

---

## 13. 常見問題

### Q1：為什麼我設定好了，但沒有自動切頁？

請先檢查：

- 目前頁面是不是在正確的 `dashboard_path` 下
- 是否有至少一個 enabled view
- `seconds` 是否大於 0
- 該 client 是否被 target client 規則排除了
- 頁面是否在背景 / 不可見
- runtime sensor 是否有收到該 client 的 heartbeat

### Q2：為什麼有些 client 顯示 `other-page`？

表示該 client 還活著，但目前不在受管理的 dashboard 頁面上。

### Q3：為什麼有些 client 顯示 `stale`？

表示它一段時間沒回報了，可能：

- 分頁被關掉
- 網頁卡住
- 裝置睡眠
- 瀏覽器被背景凍結

### Q4：Alias 可以不用 JSON 手改嗎？

可以。現在已經可以直接透過：

- Client Management UI
- `set_client_alias` service

來管理。

### Q5：Views 一定要手寫 JSON 嗎？

不用。現在已經有 GUI editor。

只有你想直接做進階編輯時，才需要進 Advanced JSON。

---

## 14. 已知限制

目前仍是 MVP 階段，已知限制如下：

- 目前只支援 **單一 profile**
- `client_aliases` 底層仍是 JSON 儲存，但平常可以透過 UI 管理
- 還沒有 table / drag-and-drop 版 views editor
- 還沒有 multi-profile / 排程模式 / 隨機模式 / ping-pong 模式

---

## 15. 建議除錯順序

如果功能看起來不對，建議照這個順序查：

1. **看 runtime sensor**
   - 是否存在
   - state 是什麼
   - active / target client 是誰
2. **看 client_states**
   - 是否有 heartbeat
   - status / presence / last seen 是否合理
3. **看 Client Management UI**
   - 目標 client 是否設定正確
   - alias 是否對得上
4. **看 dashboard 路徑**
   - `dashboard_path` 與各 view path 是否一致
5. **必要時再用 service 測試**
   - `pause`
   - `resume`
   - `jump_to_view`

---

## 16. 專案資訊

- GitHub: <https://github.com/ivanlee1007/ha-dashboard-rotator>
- Domain: `dashboard_rotator`
- 類型：Home Assistant custom integration
- 前端卡：`custom:dashboard-rotator-status`

---

## 17. 給實際使用者的短建議

如果你只是想快速上線，照這樣做就夠：

1. 安裝整合
2. 設定 `dashboard_path`
3. 用 Views Editor 建 2~5 個 view
4. 打開目標平板上的 dashboard
5. 到 Client Management 找到那台平板
6. 設成 target client
7. 幫它取 alias
8. 觀察 runtime sensor 是否進入 `running`

這樣通常就能穩定跑起來。
