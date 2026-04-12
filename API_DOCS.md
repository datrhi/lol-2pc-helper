# Tài liệu API — League of Legends (LCU) & Riot Client (RC)

Tài liệu này ghi lại các API local mà League Client (LCU) và Riot Client (RC) expose trên máy.
Tất cả đều là REST API chạy trên `127.0.0.1` với HTTPS và Basic Auth.

---

## Mục lục

- [1. Cách kết nối](#1-cách-kết-nối)
- [2. Riot Client API (RC)](#2-riot-client-api-rc)
- [3. League Client API (LCU)](#3-league-client-api-lcu)
- [4. WebSocket Events](#4-websocket-events)

---

## 1. Cách kết nối

### Riot Client (RC)

Lấy `port` và `token` từ process `RiotClientServices` hoặc `Riot Client`:

```bash
# Từ process args (macOS)
ps aux | grep "Riot Client --app-port" | grep -oE '\-\-app-port=[0-9]+' | cut -d= -f2
ps aux | grep "Riot Client --app-port" | grep -oE '\-\-remoting-auth-token=[^ ]+' | cut -d= -f2
```

```bash
# Gọi API
curl -sk -u "riot:<TOKEN>" "https://127.0.0.1:<PORT>/riotclient/region-locale"
```

### League Client (LCU)

Đọc file lockfile:

| Platform | Đường dẫn lockfile |
|---|---|
| macOS | `/Applications/League of Legends.app/Contents/LoL/lockfile` |
| Windows | `C:\Riot Games\League of Legends\lockfile` |

Nội dung lockfile: `LeagueClient:{pid}:{port}:{token}:{protocol}`

```bash
# Gọi API
curl -sk -u "riot:<TOKEN>" "https://127.0.0.1:<PORT>/lol-summoner/v1/current-summoner"
```

### Auth chung

- **Method**: HTTP Basic Auth
- **Username**: `riot`
- **Password**: `<token>` từ lockfile hoặc process args
- **SSL**: Tự ký, cần disable verify (`-k` hoặc `verify=False`)

---

## 2. Riot Client API (RC)

> RC là launcher chính của Riot, quản lý việc cài đặt/cập nhật/khởi chạy game.
> Tổng cộng: **759 endpoints**. Dưới đây là các endpoint quan trọng nhất.

### 2.1. Thông tin hệ thống

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/riotclient/app-name` | Tên ứng dụng (`"Riot Client"`) |
| GET | `/riotclient/app-port` | Port đang chạy |
| GET | `/riotclient/region-locale` | Region và ngôn ngữ |
| GET | `/riotclient/machine-id` | ID máy tính (mã hóa) |
| GET | `/riotclient/system-info/v1/basic-info` | Thông tin phần cứng (OS, RAM, CPU) |
| GET | `/riotclient/command-line-args` | Các tham số dòng lệnh khi khởi chạy |
| GET | `/riotclient/build-number` | Số build hiện tại |
| GET | `/riotclient/auth-token` | Token xác thực hiện tại |
| GET | `/riotclient/affinity` | Affinity hiện tại |

**Ví dụ response** — `/riotclient/region-locale`:
```json
{
  "locale": "vi_VN",
  "region": "VN2",
  "webLanguage": "vi_VN",
  "webRegion": "VN2"
}
```

**Ví dụ response** — `/riotclient/system-info/v1/basic-info`:
```json
{
  "operatingSystem": {
    "edition": "",
    "platform": "Mac",
    "versionMajor": "15.7",
    "versionMinor": "3"
  },
  "physicalMemory": 17179869184,
  "physicalProcessorCores": 10,
  "processorSpeed": 2400
}
```

### 2.2. Quản lý sản phẩm / Game

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/patch/v1/installs` | Danh sách game đã cài |
| GET | `/product-session/v1/external-sessions` | Session các game đang chạy |
| POST | `/product-launcher/v1/products/{productId}/patchlines/{patchlineId}` | **Khởi chạy game** |

**Khởi chạy League of Legends:**
```bash
curl -sk -u "riot:<TOKEN>" -X POST \
  "https://127.0.0.1:<PORT>/product-launcher/v1/products/league_of_legends/patchlines/live"
```

Response: trả về session ID (string) nếu thành công.

**Ví dụ response** — `/patch/v1/installs`:
```json
["league_of_legends.live.game_patch", "league_of_legends.live"]
```

**Ví dụ response** — `/product-session/v1/external-sessions`:
```json
{
  "host_app": {
    "exitCode": 0,
    "exitReason": null,
    "patchlineFullName": "riot_client",
    "phase": "None",
    "productId": "riot_client",
    "version": "0"
  }
}
```

### 2.3. Xác thực / Tài khoản

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/entitlements/v1/token` | Access token (JWT) |
| GET | `/riot-client-auth/v1/authorization` | Thông tin xác thực |
| GET | `/rso-auth/v1/authorization` | RSO auth state |
| GET | `/player-account/aliases/v1/active` | Alias đang dùng (gameName#tagLine) |

### 2.4. Chat & Bạn bè

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/chat/v1/session` | Session chat hiện tại |
| GET PUT | `/chat/v1/settings` | Cài đặt chat |
| GET | `/chat/v3/friends` | Danh sách bạn bè |
| GET | `/chat/v3/blocked` | Danh sách bị chặn |
| GET | `/chat/v5/messages` | Tin nhắn |
| GET | `/chat/v6/conversations` | Danh sách hội thoại |
| GET | `/chat/v4/presences` | Trạng thái online bạn bè |
| DELETE PUT | `/chat/v2/me` | Cập nhật trạng thái bản thân |

### 2.5. Thoát / Điều khiển

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/Exit` | Thoát Riot Client |
| POST | `/process-control/v1/process/quit` | Thoát process |

---

## 3. League Client API (LCU)

> LCU là client game League of Legends, có API riêng khi đang chạy.
> Tổng cộng: **948 event types**. Dưới đây là các endpoint phổ biến nhất.

### 3.1. Summoner (Người chơi)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-summoner/v1/current-summoner` | Thông tin người chơi hiện tại |
| GET | `/lol-summoner/v1/summoners/{summonerId}` | Thông tin theo ID |
| GET | `/lol-summoner/v1/summoners-by-puuid-cached/{puuid}` | Thông tin theo PUUID |
| GET | `/lol-summoner/v1/status` | Trạng thái summoner service |

**Ví dụ response** — `/lol-summoner/v1/current-summoner`:
```json
{
  "accountId": 3898534203778304,
  "gameName": "rage bait",
  "tagLine": "0912",
  "profileIconId": 7015,
  "summonerId": 3898534203778304,
  "summonerLevel": 14,
  "puuid": "18487d56-e1d9-5736-938f-8f8dccb2a390",
  "percentCompleteForNextLevel": 8,
  "xpSinceLastLevel": 98,
  "xpUntilNextLevel": 1128,
  "privacy": "PUBLIC",
  "unnamed": false
}
```

### 3.2. Login Session (Phiên đăng nhập)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-login/v1/session` | **Phiên đăng nhập hiện tại** |
| GET | `/lol-login/v1/login-connection-state` | Trạng thái kết nối |

**Ví dụ response khi bình thường** — `/lol-login/v1/session`:
```json
{
  "accountId": 3898534203778304,
  "connected": true,
  "error": null,
  "state": "SUCCEEDED",
  "puuid": "18487d56-...",
  "summonerId": 3898534203778304,
  "username": "hieudangtft",
  "isNewPlayer": true,
  "isInLoginQueue": false
}
```

**Ví dụ response khi bị đăng nhập nơi khác** (`LOGGED_IN_ELSEWHERE`):
```json
{
  "accountId": 3898534203778304,
  "connected": false,
  "error": {
    "description": "Account logged elsewhere",
    "errorCode": "LCE-C17DA63E",
    "messageId": "LOGGED_IN_ELSEWHERE"
  },
  "state": "LOGGING_OUT",
  "puuid": "18487d56-...",
  "summonerId": 3898534203778304,
  "username": "hieudangtft"
}
```

**Các giá trị `state`:**
| State | Ý nghĩa |
|---|---|
| `SUCCEEDED` | Đăng nhập thành công, hoạt động bình thường |
| `LOGGING_OUT` | Đang bị đăng xuất (thường do `LOGGED_IN_ELSEWHERE`) |
| `IN_PROGRESS` | Đang đăng nhập |
| `ERROR` | Lỗi đăng nhập |

### 3.3. Gameflow (Luồng game)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-gameflow/v1/gameflow-phase` | **Phase hiện tại của client** |
| GET | `/lol-gameflow/v1/availability` | Client có sẵn sàng chơi không |
| GET | `/lol-gameflow/v1/gameflow-metadata/player-status` | Trạng thái chi tiết người chơi |
| GET | `/lol-gameflow/v1/session` | Session gameflow chi tiết |
| POST | `/lol-gameflow/v1/reconnect` | Reconnect vào game |
| POST | `/lol-gameflow/v1/pre-end-of-game/complete` | Bỏ qua màn hình sau game |

**Các giá trị `gameflow-phase`:**
| Phase | Ý nghĩa |
|---|---|
| `None` | Không làm gì, ở trang chủ |
| `Lobby` | Đang trong phòng chờ (lobby) |
| `Matchmaking` | Đang tìm trận |
| `ReadyCheck` | Đã tìm được trận, chờ Accept/Decline |
| `ChampSelect` | Đang chọn tướng |
| `GameStart` | Game đang load |
| `InProgress` | Đang trong trận |
| `Reconnect` | Có thể reconnect vào trận |
| `WaitingForStats` | Chờ thống kê sau trận |
| `PreEndOfGame` | Màn hình honor/tôn vinh |
| `EndOfGame` | Màn hình kết quả trận |

### 3.4. Lobby (Phòng chờ)

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/lol-lobby/v2/lobby` | **Tạo phòng chờ mới** |
| GET | `/lol-lobby/v2/lobby` | Lấy thông tin phòng hiện tại |
| DELETE | `/lol-lobby/v2/lobby` | Rời phòng |
| POST | `/lol-lobby/v2/lobby/matchmaking/search` | **Bắt đầu tìm trận** |
| DELETE | `/lol-lobby/v2/lobby/matchmaking/search` | **Hủy tìm trận** |
| GET | `/lol-lobby/v2/eligibility/initial-configuration-complete` | Kiểm tra đủ điều kiện |
| POST | `/lol-lobby/v2/lobby/members/{summonerId}/kick` | Kick thành viên |

**Tạo phòng chờ:**
```bash
curl -sk -u "riot:<TOKEN>" -X POST \
  "https://127.0.0.1:<PORT>/lol-lobby/v2/lobby" \
  -H "Content-Type: application/json" \
  -d '{"queueId": 420}'
```

**Các Queue ID phổ biến:**
| Queue ID | Chế độ (Tiếng Việt) | Chế độ (English) |
|---|---|---|
| 400 | Thường (Cấm Chọn) | Normal Draft |
| 420 | Xếp Hạng Đơn/Đôi | Ranked Solo/Duo |
| 440 | Xếp Hạng Linh Hoạt | Ranked Flex |
| 450 | ARAM | ARAM |
| 480 | Đấu Siêu Tốc | Swiftplay |
| 870 | Co-op vs AI (Cực Dễ) | Co-op Intro |
| 880 | Co-op vs AI (Dễ) | Co-op Beginner |
| 890 | Co-op vs AI (Trung Cấp) | Co-op Intermediate |
| 1090 | TFT Thường | TFT Normal |
| 1100 | TFT Xếp Hạng | TFT Ranked |
| 1700 | Võ Đài | Arena |
| 2300 | Loạn Đấu | Brawl |

### 3.5. Matchmaking (Tìm trận)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-matchmaking/v1/search` | Trạng thái tìm trận hiện tại |
| POST | `/lol-matchmaking/v1/ready-check/accept` | **Chấp nhận trận** |
| POST | `/lol-matchmaking/v1/ready-check/decline` | **Từ chối trận** |

### 3.6. Champ Select (Chọn tướng)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-champ-select/v1/session` | Session chọn tướng hiện tại |
| PATCH | `/lol-champ-select/v1/session/actions/{actionId}` | Chọn/ban tướng |
| POST | `/lol-champ-select/v1/session/actions/{actionId}/complete` | Xác nhận chọn/ban |
| GET | `/lol-champ-select/v1/all-grid-champions` | Danh sách tướng khả dụng |
| GET | `/lol-champ-select/v1/pickable-champion-ids` | ID tướng có thể chọn |
| GET | `/lol-champ-select/v1/bannable-champion-ids` | ID tướng có thể ban |

**Chọn tướng (trong phase action):**
```bash
curl -sk -u "riot:<TOKEN>" -X PATCH \
  "https://127.0.0.1:<PORT>/lol-champ-select/v1/session/actions/<actionId>" \
  -H "Content-Type: application/json" \
  -d '{"championId": 157}'
```

### 3.7. Ranked (Xếp hạng)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-ranked/v1/current-ranked-stats` | Thống kê xếp hạng hiện tại |
| GET | `/lol-ranked/v1/ranked-stats/{puuid}` | Thống kê theo PUUID |
| GET | `/lol-ranked/v1/splits-config` | Cấu hình mùa/split |

### 3.8. Chat (Tin nhắn trong game)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-chat/v1/me` | Thông tin chat bản thân |
| PUT | `/lol-chat/v1/me` | Cập nhật trạng thái (online/away/dnd) |
| GET | `/lol-chat/v1/friends` | Danh sách bạn bè |
| GET | `/lol-chat/v1/conversations` | Danh sách hội thoại |
| POST | `/lol-chat/v1/conversations/{id}/messages` | Gửi tin nhắn |
| GET | `/lol-chat/v1/blocked-players` | Danh sách chặn |

**Ví dụ response** — `/lol-chat/v1/me`:
```json
{
  "availability": "online",
  "gameName": "rage bait",
  "gameTag": "0912",
  "icon": 7015,
  "lol": {
    "gameStatus": "outOfGame",
    "level": "14",
    "rankedLeagueTier": "UNRANKED"
  }
}
```

### 3.9. Perks / Runes (Bảng ngọc)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-perks/v1/pages` | Tất cả bảng ngọc đã lưu |
| GET | `/lol-perks/v1/currentpage` | Bảng ngọc đang dùng |
| POST | `/lol-perks/v1/pages` | Tạo bảng ngọc mới |
| PUT | `/lol-perks/v1/pages/{id}` | Cập nhật bảng ngọc |
| DELETE | `/lol-perks/v1/pages/{id}` | Xóa bảng ngọc |

### 3.10. Collections / Inventory (Tướng & Trang bị)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-champions/v1/owned-champions-minimal` | Danh sách tướng đã sở hữu |
| GET | `/lol-collections/v1/inventories/{summonerId}/champions` | Tướng theo summoner |
| GET | `/lol-loot/v1/player-loot` | Tất cả loot (rương, mảnh, ...) |
| GET | `/lol-inventory/v1/inventory` | Inventory tổng |

### 3.11. Game Queues (Chế độ chơi)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-game-queues/v1/queues` | **Tất cả queue khả dụng** |
| GET | `/lol-game-queues/v1/queues/{queueId}` | Thông tin 1 queue |
| GET | `/lol-game-queues/v1/queues/type/{type}` | Queue theo loại |

### 3.12. End of Game (Kết thúc trận)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-end-of-game/v1/eog-stats-block` | Thống kê sau trận (LoL) |
| GET | `/lol-end-of-game/v1/tft-eog-stats` | Thống kê sau trận (TFT) |

### 3.13. Honor (Tôn vinh)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-honor-v2/v1/ballot` | Bảng honor sau trận |
| POST | `/lol-honor-v2/v1/honor-player` | Honor đồng đội |
| GET | `/lol-honor-v2/v1/profile` | Cấp honor bản thân |
| GET | `/lol-honor-v2/v1/recognition` | Lịch sử honor nhận được |

### 3.14. Missions / Events (Nhiệm vụ)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-missions/v1/missions` | Danh sách nhiệm vụ hiện tại |
| GET | `/lol-missions/v1/series` | Chuỗi nhiệm vụ |
| GET | `/lol-event-hub/v1/events` | Sự kiện đang diễn ra |

### 3.15. Spectator (Quan sát)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-spectator/v1/spectate` | Thông tin spectate |
| POST | `/lol-spectator/v1/spectate/launch` | Bắt đầu quan sát trận |

### 3.16. Replays (Xem lại trận)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-replays/v1/rofls` | Danh sách replay đã lưu |
| GET | `/lol-replays/v1/configuration` | Cấu hình replay |

### 3.17. Store / Loot (Cửa hàng)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-store/v1/getStoreUrl` | URL cửa hàng |
| GET | `/lol-loot/v1/player-loot` | Tất cả loot |
| POST | `/lol-loot/v1/recipes/{recipeName}/craft` | Craft loot |

### 3.18. Settings (Cài đặt)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-settings/v1/account/{category}` | Cài đặt tài khoản |
| PUT | `/lol-settings/v1/account/{category}` | Cập nhật cài đặt |
| GET | `/lol-game-settings/v1/game-settings` | Cài đặt in-game |
| PATCH | `/lol-game-settings/v1/game-settings` | Cập nhật cài đặt in-game |

### 3.19. Patch / Cập nhật

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/lol-patch/v1/game-version` | Phiên bản game hiện tại |
| GET | `/lol-patch/v1/products/league_of_legends/state` | Trạng thái cập nhật |

### 3.20. Process Control

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/process-control/v1/process/quit` | Thoát League Client |

---

## 4. WebSocket Events

Cả RC và LCU đều hỗ trợ WebSocket để nhận event real-time.

### Kết nối

```
wss://riot:<TOKEN>@127.0.0.1:<PORT>
```

### Subscribe

Gửi JSON message sau khi kết nối:
```json
[5, "OnJsonApiEvent"]
```

Hoặc subscribe event cụ thể:
```json
[5, "OnJsonApiEvent_lol-gameflow_v1_gameflow-phase"]
```

### Nhận event

Server gửi về array format `[opcode, event_name, data]`:
```json
[8, "OnJsonApiEvent", {
  "data": "Matchmaking",
  "eventType": "Update",
  "uri": "/lol-gameflow/v1/gameflow-phase"
}]
```

### Các event quan trọng (LCU)

| Event | Khi nào fire |
|---|---|
| `OnJsonApiEvent_lol-gameflow_v1_gameflow-phase` | Phase game thay đổi |
| `OnJsonApiEvent_lol-login_v1_session` | Session login thay đổi (bao gồm `LOGGED_IN_ELSEWHERE`) |
| `OnJsonApiEvent_lol-champ-select_v1_session` | Session chọn tướng thay đổi |
| `OnJsonApiEvent_lol-matchmaking_v1_search` | Trạng thái tìm trận thay đổi |
| `OnJsonApiEvent_lol-lobby_v2_lobby` | Thông tin phòng chờ thay đổi |
| `OnJsonApiEvent_lol-chat_v1_me` | Trạng thái chat bản thân thay đổi |
| `OnJsonApiEvent_lol-ranked_v1_current-ranked-stats` | Thống kê rank thay đổi |
| `OnJsonApiEvent_lol-end-of-game_v1_eog-stats-block` | Có kết quả sau trận |
| `OnJsonApiEvent_lol-honor-v2_v1_ballot` | Bảng honor xuất hiện |

### Các event quan trọng (RC)

| Event | Khi nào fire |
|---|---|
| `OnJsonApiEvent_product-session_v1_external-sessions` | Session game thay đổi (game mở/đóng) |
| `OnJsonApiEvent_chat_v4_presences` | Trạng thái online bạn bè thay đổi |
| `OnJsonApiEvent_entitlements_v1_token` | Token entitlement thay đổi |
| `OnJsonApiEvent_product-launcher_v1_is-launch-request-pending` | Đang chờ khởi chạy game |

---

## Ghi chú

- Tất cả API chỉ hoạt động khi client tương ứng đang chạy.
- Token thay đổi mỗi lần client khởi động lại.
- API không có rate limit (local API).
- Riot có thể thay đổi API bất cứ lúc nào vì đây là API nội bộ, không phải public API.
- Để xem đầy đủ endpoint, dùng: `GET /help` (LCU) hoặc `GET /swagger/v3/openapi.json` (RC).
