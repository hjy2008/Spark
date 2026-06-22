# cfez_fire

食堂火灾监控管理客户端 —— PyQt5 桌面应用 + FastAPI 后端服务。

## 技术栈

| 层 | 技术 | 路径 |
|---|---|---|
| 客户端 GUI | PyQt5 + [qfluentwidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) `SplitFluentWindow` | `src/` |
| 后端 API | FastAPI + uvicorn | `service/api.py` |
| 数据库 | SQLite (`data.db` 用户 / `suggest.db` 反馈) | `service/` |
| 加密 | RSA-OAEP (请求体) + AES-256-CBC (响应体) | `src/common/crypto.py` / `service/api.py` |
| 容器化 | Docker | `service/Dockerfile` + `docker-compose.yml` |

## 快速开始

### 前置

```bash
python -m venv .venv
.venv\Scripts\activate
pip install PyQt5 qfluentwidgets python-pptx python-docx requests cryptography pywin32 fastapi uvicorn
```

### 启动服务端

```bash
cd service
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

或使用 Docker：

```bash
cd service
docker compose up -d
```

首次部署需同步用户数据（从远程智慧食堂 API）：

```bash
python service/database.py
```

### 启动客户端

```bash
.venv\Scripts\activate
python src/main.py
```

## 项目结构

```
cfez_fire/
├── src/
│   ├── main.py                     # 应用入口，SplitFluentWindow
│   ├── common/
│   │   ├── config_items.py         # 配置项定义（字体/字号/行距）
│   │   ├── crypto.py               # 客户端 RSA + AES 加密
│   │   ├── style_sheet.py          # QSS 样式表枚举
│   │   └── update_check.py         # 网络线程（检查更新/登录/反馈）
│   ├── ui/
│   │   ├── home_interface.py       # 首页
│   │   ├── monitor_interface.py    # 监控（登录后展示摄像头树）
│   │   ├── music_interface.py      # 音乐搜索与播放器
│   │   ├── settings_interface.py   # 设置与反馈
│   │   └── sync_interface.py       # PPT → DOCX 转换
│   ├── resource/
│   │   ├── qss/{light,dark}/       # 各界面样式表
│   │   └── img/logo.jpg            # 应用图标
│   └── config/config.json          # 持久化配置
├── service/
│   ├── api.py                      # FastAPI 应用（5 个端点）
│   ├── database.py                 # 一键同步远程用户到 data.db
│   ├── key.py                      # RSA 密钥对生成器
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── private_key.pem
│   ├── public_key.pem
│   ├── data.db                     # 用户表 + 登录日志
│   └── suggest.db                  # 用户反馈
├── AGENTS.md
└── README.md
```

## 功能

- **监控** — 登录后展示摄像头树，点击摄像头在桌面创建 `.lnk` 快捷方式（Edge 打开）
- **音乐** — 搜索/播放/下载歌曲（数据源：gequbao.com），LRC 歌词滚动动画
- **PPT 转换** — 将 `.pptx` 转为 `.docx`，支持字体/字号/行距配置
- **反馈** — 客户端内提交，服务端 `/suggestions` 页面管理
- **更新检查** — 启动时自动检查新版本

## API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/check-updates` | 版本更新检查（RSA 加密请求） |
| POST | `/login` | 用户登录（返回摄像头数据） |
| POST | `/feedback` | 提交用户反馈 |
| GET | `/suggestions` | 反馈列表管理页 |
| DELETE | `/suggestions/{id}` | 删除反馈 |
| GET | `/login_status` | 登录记录（HTTP Basic Auth） |

## 配置

PPT 转换参数（`src/common/config_items.py`）：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `FontName` | 等线 | 字体名称 |
| `FontSize` | 12 | 字号（8–72） |
| `LineSpacing` | 18 | 行距（10–40 pt） |

## 开发说明

- 主题切换 `lazy=True` 避免样式重复应用
- `LoginThread.loginFinished` 信号（非 `finished`）避免与 C++ `QThread.finished` 冲突
- qfluentwidgets `LineEdit.setCompleter()` 不调 `super().setCompleter()`，触发补全菜单需调用 `_showCompleterMenu()` 而非 `complete()`
- `BreadcrumbBar` 透明背景，字体/间距/边距需手动设置
- 服务端登录限流：每 IP 5 次/60s，每日每设备 20 次

## Release
**v1.0.1** | 2026-06-23

Spark 正式发布！

[Download](https://github.com/hjy2008/Spark/releases/tag/v1.0.1)

**v1.0.0** | 2026-06-23

内测版

[Download](https://github.com/hjy2008/Spark/releases/tag/v1.0.0)

**v1.0.0** | 2026-06-22

test1

[Download](https://github.com/hjy2008/Spark/releases/tag/v1.0.0)


**v1.0.0** | 2026-06-22

test1

[Download](https://github.com/hjy2008/Spark/releases/tag/v1.0.0)
