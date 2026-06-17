# B站视频下载界面 — 设计文档

## 概述

在导航栏新增「B站下载」界面，用户粘贴 B 站链接/BV 号 → 解析视频信息 → 下载并合并为 MP4。

## 界面布局

参照现有接口规范（`layout.setContentsMargins(36, 40, 36, 36)`, 12px spacing）：

- **TitleLabel** — "B站下载"
- **URL 输入栏** — `LineEdit` + "解析"按钮（`PushButton`），水平排列
- **视频信息展示** — 解析后显示封面缩略图、标题、UP 主、时长、播放量
- **保存路径** — `LineEdit`（只读）+ "浏览"按钮，默认 `./downloads/video/`
- **进度条** — `ProgressBar` + 状态文本（"正在下载 75%"）
- **下载按钮** — `PushButton`，解析前禁用，解析后启用

## 数据流

```
用户粘贴链接 → 点击解析
  → BilibiliAPI 解析 BV 号
  → bilibili_api.Video.get_info() → 返回标题/封面/UP主/时长
  → 展示到 UI

用户点击下载
  → bilibili_api.VideoDownloader 下载视频流 + 音频流
  → imageio-ffmpeg 获取 ffmpeg 路径
  → ffmpeg 合并视频流 + 音频流 → 输出 MP4
  → 更新进度条
```

## 依赖

| 包 | 用途 |
|---|------|
| `bilibili-api-python` | B 站视频信息解析、视频/音频流下载 |
| `imageio-ffmpeg` | 内置 ffmpeg 二进制，用于合并音视频流 |

需要 `pip install bilibili-api-python imageio-ffmpeg`

## 文件清单

| 文件 | 说明 |
|------|------|
| `src/ui/video_interface.py` | 界面类 `VideoInterface(QWidget)` |
| `src/resource/qss/light/video_interface.qss` | 浅色主题 QSS |
| `src/resource/qss/dark/video_interface.qss` | 深色主题 QSS |
| `src/common/style_sheet.py` | 追加 `VIDEO_INTERFACE` 枚举项 |
| `src/main.py` | 导入、实例化、注册到导航栏 |

## 遵循的模式

- `setObjectName("VideoInterface")`
- `StyleSheet.VIDEO_INTERFACE.apply(self)`
- `addSubInterface(..., "video_interface", FluentIcon.VIDEO, ...)`
- 线程安全：下载操作在 `QThread` 中执行，进度通过 signal 回传 UI
