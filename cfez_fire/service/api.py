import html
import json
import shutil
import sqlite3
import time
from base64 import b64encode, b64decode
from pathlib import Path

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from configs.logging_config import logger as parse_logger
from configs.general_constants import DOMAIN_TO_NAME
from utils.web_fetcher import WebFetcher, UrlParser
from src.parser_factory import ParserFactory


app = FastAPI(
    title="cfez_fire 数据同步 API",
    description="管理系统的后端服务。提供版本更新检查、用户登录验证、摄像头数据分发、用户反馈收集等功能。\n\n"
    "## 加密说明\n"
    "- **请求体加密**: 客户端用 RSA-2048 OAEP 公钥加密 JSON → `EncryptedBody.data`\n"
    "- **响应体加密**: 服务端用 AES-256-CBC 加密 JSON → `response.data`\n"
    "- 反馈接口使用 AES 双向加密",
    version="1.0.0",
    contact={"name": "cfez_fire"},
)

AVATAR_DIR = Path(__file__).resolve().parent / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/avatars", StaticFiles(directory=str(AVATAR_DIR)), name="avatars")

LATEST_VERSION = "v1.0.0"

CAMERA_GROUPS = {
    "A楼  明德楼": [
        ["A101前", "http://192.168.35.11", "账号：admin  密码：a1234567"],
        ["A101后", "http://192.168.35.12", "账号：admin  密码：a1234567"],
        ["A102前", "http://192.168.35.13", "账号：admin  密码：a1234567"],
        ["A102后", "http://192.168.35.14", "账号：admin  密码：a1234567"],
        ["A103前", "http://192.168.35.15", "账号：admin  密码：a1234567"],
        ["A103后", "http://192.168.35.16", "账号：admin  密码：a1234567"],
        ["A104前", "http://192.168.35.17", "账号：admin  密码：a1234567"],
        ["A104后", "http://192.168.35.18", "账号：admin  密码：a1234567"],
        ["A105前", "http://192.168.35.19", "账号：admin  密码：a1234567"],
        ["A105后", "http://192.168.35.20", "账号：admin  密码：a1234567"],
        ["A205前", "http://192.168.35.21", "账号：admin  密码：a1234567"],
        ["A205后", "http://192.168.35.22", "账号：admin  密码：a1234567"],
        ["A206前", "http://192.168.35.23", "账号：admin  密码：a1234567"],
        ["A206后", "http://192.168.35.24", "账号：admin  密码：a1234567"],
        ["A207前", "http://192.168.35.25", "账号：admin  密码：a1234567"],
        ["A207后", "http://192.168.35.26", "账号：admin  密码：a1234567"],
        ["A208前", "http://192.168.35.27", "账号：admin  密码：a1234567"],
        ["A208后", "http://192.168.35.28", "账号：admin  密码：a1234567"],
        ["A304前", "http://192.168.35.31", "账号：admin  密码：a1234567"],
        ["A304后", "http://192.168.35.32", "账号：admin  密码：a1234567"],
        ["A305前", "http://192.168.35.33", "账号：admin  密码：a1234567"],
        ["A305后", "http://192.168.35.34", "账号：admin  密码：a1234567"],
        ["A306前", "http://192.168.35.35", "账号：admin  密码：a1234567"],
        ["A306后", "http://192.168.35.36", "账号：admin  密码：a1234567"],
        ["A307前", "http://192.168.35.37", "账号：admin  密码：a1234567"],
        ["A307后", "http://192.168.35.38", "账号：admin  密码：a1234567"],
        ["A403前", "http://192.168.35.39", "账号：admin  密码：a1234567"],
        ["A403后", "http://192.168.35.40", "账号：admin  密码：a1234567"],
        ["A404前", "http://192.168.35.41", "账号：admin  密码：a1234567"],
        ["A404后", "http://192.168.35.42", "账号：admin  密码：a1234567"],
        ["A405前", "http://192.168.35.43", "账号：admin  密码：a1234567"],
        ["A405后", "http://192.168.35.44", "账号：admin  密码：a1234567"],
        ["A406前", "http://192.168.35.45", "账号：admin  密码：a1234567"],
        ["A406后", "http://192.168.35.46", "账号：admin  密码：a1234567"],
        ["A407前", "http://192.168.35.47", "账号：admin  密码：a1234567"],
        ["A407后", "http://192.168.35.48", "账号：admin  密码：a1234567"],
        ["A503前", "http://192.168.35.49", "账号：admin  密码：a1234567"],
        ["A503后", "http://192.168.35.50", "账号：admin  密码：a1234567"],
        ["A504前", "http://192.168.35.51", "账号：admin  密码：a1234567"],
        ["A504后", "http://192.168.35.52", "账号：admin  密码：a1234567"],
        ["A505前", "http://192.168.35.53", "账号：admin  密码：a1234567"],
        ["A506前", "http://192.168.35.55", "账号：admin  密码：a1234567"],
        ["A506后", "http://192.168.35.56", "账号：admin  密码：a1234567"],
        ["A507前", "http://192.168.35.57", "账号：admin  密码：a1234567"],
        ["A507后", "http://192.168.35.58", "账号：admin  密码：a1234567"],
    ],
    "B楼  敏学楼": [
        ["B101前", "http://192.168.35.59", "账号：admin  密码：a1234567"],
        ["B101后", "http://192.168.35.60", "账号：admin  密码：a1234567"],
        ["B102前", "http://192.168.35.61", "账号：admin  密码：a1234567"],
        ["B102后", "http://192.168.35.62", "账号：admin  密码：a1234567"],
        ["B103后", "http://192.168.35.64", "账号：admin  密码：a1234567"],
        ["B104前", "http://192.168.35.65", "账号：admin  密码：a1234567"],
        ["B104后", "http://192.168.35.66", "账号：admin  密码：a1234567"],
        ["B105前", "http://192.168.35.67", "账号：admin  密码：a1234567"],
        ["B105后", "http://192.168.35.68", "账号：admin  密码：a1234567"],
        ["B205前", "http://192.168.35.69", "账号：admin  密码：a1234567"],
        ["B205后", "http://192.168.35.70", "账号：admin  密码：a1234567"],
        ["B206前", "http://192.168.35.71", "账号：admin  密码：a1234567"],
        ["B206后", "http://192.168.35.72", "账号：admin  密码：a1234567"],
        ["B207前", "http://192.168.35.73", "账号：admin  密码：a1234567"],
        ["B207后", "http://192.168.35.74", "账号：admin  密码：a1234567"],
        ["B208前", "http://192.168.35.75", "账号：admin  密码：a1234567"],
        ["B208后", "http://192.168.35.76", "账号：admin  密码：a1234567"],
        ["B304前", "http://192.168.35.79", "账号：admin  密码：a1234567"],
        ["B304后", "http://192.168.35.80", "账号：admin  密码：a1234567"],
        ["B305前", "http://192.168.35.81", "账号：admin  密码：a1234567"],
        ["B305后", "http://192.168.35.82", "账号：admin  密码：a1234567"],
        ["B306前", "http://192.168.35.83", "账号：admin  密码：a1234567"],
        ["B306后", "http://192.168.35.84", "账号：admin  密码：a1234567"],
        ["B307前", "http://192.168.35.85", "账号：admin  密码：a1234567"],
        ["B307后", "http://192.168.35.86", "账号：admin  密码：a1234567"],
        ["B403前", "http://192.168.35.87", "账号：admin  密码：a1234567"],
        ["B403后", "http://192.168.35.88", "账号：admin  密码：a1234567"],
        ["B404前", "http://192.168.35.89", "账号：admin  密码：a1234567"],
        ["B404后", "http://192.168.35.90", "账号：admin  密码：a1234567"],
        ["B405前", "http://192.168.35.91", "账号：admin  密码：a1234567"],
        ["B405后", "http://192.168.35.92", "账号：admin  密码：a1234567"],
        ["B406前", "http://192.168.35.93", "账号：admin  密码：a1234567"],
        ["B406后", "http://192.168.35.94", "账号：admin  密码：a1234567"],
        ["B407前", "http://192.168.35.95", "账号：admin  密码：a1234567"],
        ["B407后", "http://192.168.35.96", "账号：admin  密码：a1234567"],
        ["B503前", "http://192.168.35.97", "账号：admin  密码：a1234567"],
        ["B503后", "http://192.168.35.98", "账号：admin  密码：a1234567"],
        ["B504前", "http://192.168.35.99", "账号：admin  密码：a1234567"],
        ["B504后", "http://192.168.35.100", "账号：admin  密码：a1234567"],
        ["B505前", "http://192.168.35.101", "账号：admin  密码：a1234567"],
        ["B505后", "http://192.168.35.102", "账号：admin  密码：a1234567"],
        ["B506前", "http://192.168.35.103", "账号：admin  密码：a1234567"],
        ["B506后", "http://192.168.35.104", "账号：admin  密码：a1234567"],
        ["B507前", "http://192.168.35.105", "账号：admin  密码：a1234567"],
        ["B507后", "http://192.168.35.106", "账号：admin  密码：a1234567"],
    ],
    "C楼  极远楼": [
        ["C101前", "http://192.168.35.107", "账号：admin  密码：a1234567"],
        ["C101后", "http://192.168.35.108", "账号：admin  密码：a1234567"],
        ["C102前", "http://192.168.35.109", "账号：admin  密码：a1234567"],
        ["C102后", "http://192.168.35.110", "账号：admin  密码：a1234567"],
        ["C103前", "http://192.168.35.111", "账号：admin  密码：a1234567"],
        ["C103后", "http://192.168.35.112", "账号：admin  密码：a1234567"],
        ["C104前", "http://192.168.35.113", "账号：admin  密码：a1234567"],
        ["C104后", "http://192.168.35.114", "账号：admin  密码：a1234567"],
        ["C105前", "http://192.168.35.115", "账号：admin  密码：a1234567"],
        ["C105后", "http://192.168.35.116", "账号：admin  密码：a1234567"],
        ["C205前", "http://192.168.35.117", "账号：admin  密码：a1234567"],
        ["C205后", "http://192.168.35.118", "账号：admin  密码：a1234567"],
        ["C206前", "http://192.168.35.119", "账号：admin  密码：a1234567"],
        ["C206后", "http://192.168.35.120", "账号：admin  密码：a1234567"],
        ["C207前", "http://192.168.35.121", "账号：admin  密码：a1234567"],
        ["C207后", "http://192.168.35.122", "账号：admin  密码：a1234567"],
        ["C208前", "http://192.168.35.123", "账号：admin  密码：a1234567"],
        ["C208后", "http://192.168.35.124", "账号：admin  密码：a1234567"],
        ["C304前", "http://192.168.35.127", "账号：admin  密码：a1234567"],
        ["C304后", "http://192.168.35.128", "账号：admin  密码：a1234567"],
        ["C305前", "http://192.168.35.129", "账号：admin  密码：a1234567"],
        ["C305后", "http://192.168.35.130", "账号：admin  密码：a1234567"],
        ["C306前", "http://192.168.35.131", "账号：admin  密码：a1234567"],
        ["C306后", "http://192.168.35.132", "账号：admin  密码：a1234567"],
        ["C307前", "http://192.168.35.133", "账号：admin  密码：a1234567"],
        ["C307后", "http://192.168.35.134", "账号：admin  密码：a1234567"],
        ["C403前", "http://192.168.35.135", "账号：admin  密码：a1234567"],
        ["C403后", "http://192.168.35.136", "账号：admin  密码：a1234567"],
        ["C404前", "http://192.168.35.137", "账号：admin  密码：a1234567"],
        ["C404后", "http://192.168.35.138", "账号：admin  密码：a1234567"],
        ["C405前", "http://192.168.35.139", "账号：admin  密码：a1234567"],
        ["C405后", "http://192.168.35.140", "账号：admin  密码：a1234567"],
        ["C406前", "http://192.168.35.141", "账号：admin  密码：a1234567"],
        ["C406后", "http://192.168.35.142", "账号：admin  密码：a1234567"],
        ["C407前", "http://192.168.35.143", "账号：admin  密码：a1234567"],
        ["C407后", "http://192.168.35.144", "账号：admin  密码：a1234567"],
        ["C503前", "http://192.168.35.145", "账号：admin  密码：a1234567"],
        ["C503后", "http://192.168.35.146", "账号：admin  密码：a1234567"],
        ["C504前", "http://192.168.35.147", "账号：admin  密码：a1234567"],
        ["C504后", "http://192.168.35.148", "账号：admin  密码：a1234567"],
        ["C505前", "http://192.168.35.149", "账号：admin  密码：a1234567"],
        ["C505后", "http://192.168.35.150", "账号：admin  密码：a1234567"],
        ["C506前", "http://192.168.35.151", "账号：admin  密码：a1234567"],
        ["C506后", "http://192.168.35.152", "账号：admin  密码：a1234567"],
        ["C507前", "http://192.168.35.153", "账号：admin  密码：a1234567"],
        ["C507后", "http://192.168.35.154", "账号：admin  密码：a1234567"],
    ],
}
DOWNLOAD_URL = ""
RELEASE_NOTES = ""

_PRIVATE_KEY = (Path(__file__).resolve().parent / "private_key.pem").read_text(encoding="utf-8")

_AES_KEY = bytes.fromhex("2cae76666ad3ee4017ecbcc3d25a3fe163670382713bb21eb9bd11244be4db6c")
_AES_IV = bytes.fromhex("5306172bb00e3353c7cc8f0fbd31632d")

_DB_PATH = Path("/tmp/data.db")

_LIMIT = 5
_WINDOW = 60
_login_attempts: dict[str, list[float]] = {}


def _rate_limit(ip: str) -> bool:
    now = time.time()
    timestamps = _login_attempts.get(ip, [])
    timestamps = [t for t in timestamps if now - t < _WINDOW]
    if len(timestamps) >= _LIMIT:
        return False
    timestamps.append(now)
    _login_attempts[ip] = timestamps
    return True


_SUGGEST_DB_PATH = Path("/tmp/suggest.db")

_FEEDBACK_LIMIT = 5
_FEEDBACK_WINDOW = 60
_feedback_attempts: dict[str, list[float]] = {}


def _feedback_rate_limit(device_id: str) -> bool:
    now = time.time()
    timestamps = _feedback_attempts.get(device_id, [])
    timestamps = [t for t in timestamps if now - t < _FEEDBACK_WINDOW]
    if len(timestamps) >= _FEEDBACK_LIMIT:
        return False
    timestamps.append(now)
    _feedback_attempts[device_id] = timestamps
    return True


def _init_suggest_db():
    conn = sqlite3.connect(str(_SUGGEST_DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS suggestions ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  device_id TEXT,"
        "  hostname TEXT,"
        "  os TEXT,"
        "  content TEXT,"
        "  created_at TEXT DEFAULT (datetime('now','localtime'))"
        ")"
    )
    conn.commit()
    conn.close()


_init_suggest_db()


def _init_crash_log_db():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS crash_logs ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  device_id TEXT,"
        "  hostname TEXT,"
        "  os TEXT,"
        "  traceback TEXT,"
        "  log_tail TEXT,"
        "  created_at TEXT DEFAULT (datetime('now','localtime'))"
        ")"
    )
    conn.commit()
    conn.close()


_init_crash_log_db()


_CRASH_LIMIT = 3
_CRASH_WINDOW = 300
_crash_attempts: dict[str, list[float]] = {}


def _crash_rate_limit(device_id: str) -> bool:
    now = time.time()
    timestamps = _crash_attempts.get(device_id, [])
    timestamps = [t for t in timestamps if now - t < _CRASH_WINDOW]
    if len(timestamps) >= _CRASH_LIMIT:
        return False
    timestamps.append(now)
    _crash_attempts[device_id] = timestamps
    return True


_ADMIN_USER = "admin"
_ADMIN_PASS = "admin123"
_basic_auth = HTTPBasic()
_admin_session: dict = {"ip": None, "last_seen": 0}
_admin_failures: dict[str, list[float]] = {}
_ADMIN_FAIL_LIMIT = 3
_ADMIN_FAIL_WINDOW = 86400


def _verify_admin(
    credentials: HTTPBasicCredentials = Depends(_basic_auth),
    request: Request = None,
):
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    failures = [t for t in _admin_failures.get(ip, []) if now - t < _ADMIN_FAIL_WINDOW]
    if len(failures) >= _ADMIN_FAIL_LIMIT:
        raise HTTPException(status_code=404)

    if credentials.username != _ADMIN_USER or credentials.password != _ADMIN_PASS:
        _admin_failures[ip] = failures + [now]
        raise HTTPException(status_code=404)

    _admin_failures.pop(ip, None)

    if _admin_session["ip"] and _admin_session["ip"] != ip:
        _admin_session["ip"] = None

    _admin_session["ip"] = ip
    _admin_session["last_seen"] = now
    return credentials.username


def _init_login_log_db():
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS login_log ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  username TEXT,"
        "  device_id TEXT,"
        "  hostname TEXT,"
        "  os TEXT,"
        "  success INTEGER,"
        "  created_at TEXT DEFAULT (datetime('now','localtime'))"
        ")"
    )
    conn.commit()
    conn.close()


_init_login_log_db()


def _device_daily_limit(device_id: str) -> bool:
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    conn = sqlite3.connect(str(_DB_PATH))
    row = conn.execute(
        "SELECT COUNT(*) FROM login_log WHERE device_id=? AND created_at>=?",
        (device_id, cutoff),
    ).fetchone()
    conn.close()
    return row is not None and row[0] < 20


def _log_login(username, device_id, hostname, os, success):
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        "INSERT INTO login_log (username, device_id, hostname, os, success) VALUES (?,?,?,?,?)",
        (username, device_id, hostname or "", os or "", 1 if success else 0),
    )
    conn.commit()
    conn.close()


def _parse_version(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("vV").split("."))


def _decrypt_payload(encrypted_b64: str) -> dict:
    key = serialization.load_pem_private_key(_PRIVATE_KEY.encode(), password=None)
    plain = key.decrypt(
        b64decode(encrypted_b64),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return json.loads(plain.decode("utf-8"))


def _aes_encrypt(obj: dict) -> str:
    plain = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plain) + padder.finalize()
    cipher = Cipher(algorithms.AES(_AES_KEY), modes.CBC(_AES_IV))
    encryptor = cipher.encryptor()
    return b64encode(encryptor.update(padded) + encryptor.finalize()).decode("ascii")


def _aes_decrypt(data_b64: str) -> dict:
    cipher = Cipher(algorithms.AES(_AES_KEY), modes.CBC(_AES_IV))
    decryptor = cipher.decryptor()
    padded = decryptor.update(b64decode(data_b64)) + decryptor.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    return json.loads(plain.decode("utf-8"))


class EncryptedBody(BaseModel):
    """RSA-OAEP 加密的请求体。"""
    data: str


@app.post("/check-updates", summary="检查版本更新", tags=["客户端"])
def check_updates(body: EncryptedBody):
    """客户端启动时调用，检测是否有新版本可用。

    - 请求体用 RSA 公钥加密，包含 `current_version`
    - 响应体用 AES-256-CBC 加密，包含更新信息

    **RSA 加密请求体格式 (解密后):**
    ```json
    {"current_version": "v1.0.0"}
    ```

    **AES 解密响应体格式:**
    ```json
    {"has_update": false, "latest_version": "v1.0.0", "download_url": "", "release_notes": ""}
    ```
    """
    payload = _decrypt_payload(body.data)
    current_version = payload.get("current_version", "v0.0.0")

    has_update = _parse_version(current_version) < _parse_version(LATEST_VERSION)
    result = {
        "has_update": has_update,
        "latest_version": LATEST_VERSION,
        "download_url": DOWNLOAD_URL,
        "release_notes": RELEASE_NOTES,
    }
    return {"data": _aes_encrypt(result)}


@app.post("/login", summary="用户登录", tags=["客户端"])
def login(body: EncryptedBody, request: Request):
    """验证用户身份，成功后返回摄像头分组数据。

    登录记录写入 `data.db` 的 `login_log` 表，受以下限制：
    - **IP 限流**: 每 IP 60 秒内最多 5 次
    - **设备日限**: 每设备 24 小时内最多 20 次

    **RSA 加密请求体格式 (解密后):**
    ```json
    {"username": "张三", "phone": "138xxxx", "device_id": "xxx", "hostname": "PC-1", "os": "Windows"}
    ```

    **AES 解密响应体格式 (成功):**
    ```json
    {"success": true, "camera_groups": {"A楼": [[...], ...]}}
    ```

    **AES 解密响应体格式 (失败):**
    ```json
    {"success": false}
    ```

    **429 响应 (限流):**
    ```json
    {"data": "AES加密的 {\"success\": false, \"error\": \"...\"}"}
    ```
    """
    ip = "unknown"
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    if not _rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={"data": _aes_encrypt({"success": False, "error": "请求过于频繁，请稍后再试"})},
        )

    payload = _decrypt_payload(body.data)
    username = payload.get("username", "")
    phone = payload.get("phone", "")
    device_id = payload.get("device_id", "")
    hostname = payload.get("hostname", "")
    os = payload.get("os", "")

    if device_id and not _device_daily_limit(device_id):
        _log_login(username, device_id, hostname, os, False)
        return JSONResponse(
            status_code=429,
            content={"data": _aes_encrypt({"success": False, "error": "该设备今日登录次数已达上限"})},
        )

    conn = sqlite3.connect(str(_DB_PATH))
    row = conn.execute(
        "SELECT name FROM users WHERE name=? AND phone=?", (username, phone)
    ).fetchone()
    conn.close()

    success = row is not None
    _log_login(username, device_id, hostname, os, success)

    result = {"success": success}
    if success:
        result["camera_groups"] = CAMERA_GROUPS
    return {"data": _aes_encrypt(result)}


@app.post("/auto-login", summary="自动登录", tags=["客户端"])
def auto_login(body: EncryptedBody, request: Request):
    """用双加密凭证自动登录（AES→RSA 双层加密的 blob）。

    与 /login 共享 IP 限流和设备日限逻辑。
    """
    ip = "unknown"
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    if not _rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={"data": _aes_encrypt({"success": False, "error": "请求过于频繁，请稍后再试"})},
        )

    key = serialization.load_pem_private_key(_PRIVATE_KEY.encode(), password=None)
    try:
        rsa_plain = key.decrypt(
            b64decode(body.data),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        aes_cipher = Cipher(algorithms.AES(_AES_KEY), modes.CBC(_AES_IV))
        aes_decryptor = aes_cipher.decryptor()
        padded = aes_decryptor.update(b64decode(rsa_plain.decode("ascii"))) + aes_decryptor.finalize()
        unpadder = sym_padding.PKCS7(128).unpadder()
        plain = unpadder.update(padded) + unpadder.finalize()
        payload = json.loads(plain.decode("utf-8"))
    except Exception:
        return {"data": _aes_encrypt({"success": False, "error": "凭证无效"})}

    username = payload.get("username", "")
    phone = payload.get("phone", "")
    timestamp = payload.get("timestamp", 0)
    device_id = payload.get("device_id", "")
    hostname = payload.get("hostname", "")
    os = payload.get("os", "")

    now = time.time()
    if now - timestamp > 7 * 86400:
        _log_login(username, device_id, hostname, os, False)
        return {"data": _aes_encrypt({"success": False, "error": "登录凭证已过期"})}

    if device_id and not _device_daily_limit(device_id):
        _log_login(username, device_id, hostname, os, False)
        return JSONResponse(
            status_code=429,
            content={"data": _aes_encrypt({"success": False, "error": "该设备今日登录次数已达上限"})},
        )

    conn = sqlite3.connect(str(_DB_PATH))
    row = conn.execute(
        "SELECT name FROM users WHERE name=? AND phone=?", (username, phone)
    ).fetchone()
    conn.close()

    success = row is not None
    _log_login(username, device_id, hostname, os, success)

    result = {"success": success, "username": username, "phone": phone}
    if success:
        result["camera_groups"] = CAMERA_GROUPS
    return {"data": _aes_encrypt(result)}


@app.post("/upload-avatar", summary="上传头像", tags=["客户端"])
def upload_avatar(username: str = Form(...), avatar: UploadFile = File(...)):
    """上传用户头像。

    接收 multipart/form-data，包含 `username` 和 `avatar` 文件。

    **响应体 (AES 解密后):**
    ```json
    {"success": true, "url": "/avatars/xxx.png"}
    ```
    """
    if not avatar.content_type or not avatar.content_type.startswith("image/"):
        return {"data": _aes_encrypt({"success": False, "error": "仅支持图片格式"})}

    ext = Path(avatar.filename).suffix or ".png"
    dest = AVATAR_DIR / f"{username}{ext}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(avatar.file, f)

    return {"data": _aes_encrypt({"success": True, "url": f"/avatars/{username}{ext}"})}


class AesBody(BaseModel):
    """AES-256-CBC 加密的请求体。"""
    data: str


@app.post("/feedback", summary="提交用户反馈", tags=["客户端"])
def feedback(body: AesBody):
    """客户端提交用户反馈意见，存储在 `suggest.db`。

    受设备级限流：每设备 60 秒内最多 5 次。

    **AES 加密请求体格式 (解密后):**
    ```json
    {"device_id": "xxx", "hostname": "PC-1", "os": "Windows", "content": "反馈内容"}
    ```

    **AES 加密响应体格式 (解密后):**
    ```json
    {"success": true}
    ```
    """
    payload = _aes_decrypt(body.data)
    device_id = payload.get("device_id", "")
    content = payload.get("content", "").strip()
    if not content:
        return JSONResponse(
            status_code=400,
            content={"data": _aes_encrypt({"error": "反馈内容不能为空"})},
        )
    if not device_id:
        return JSONResponse(
            status_code=400,
            content={"data": _aes_encrypt({"error": "缺少设备标识"})},
        )

    if not _feedback_rate_limit(device_id):
        return JSONResponse(
            status_code=429,
            content={"data": _aes_encrypt({"error": "提交过于频繁，请稍后再试"})},
        )

    conn = sqlite3.connect(str(_SUGGEST_DB_PATH))
    conn.execute(
        "INSERT INTO suggestions (device_id, hostname, os, content) VALUES (?,?,?,?)",
        (device_id, payload.get("hostname", ""), payload.get("os", ""), content),
    )
    conn.commit()
    conn.close()
    return {"data": _aes_encrypt({"success": True})}


@app.post("/crash-report", summary="上报崩溃日志", tags=["客户端"])
def crash_report(body: EncryptedBody):
    """客户端异常崩溃时自动上报日志。

    RSA 加密请求体格式 (解密后):
    ```json
    {"device_id": "xxx", "hostname": "PC-1", "os": "Windows", "traceback": "...", "log_tail": "..."}
    ```
    """
    payload = _decrypt_payload(body.data)
    device_id = payload.get("device_id", "")
    if not device_id:
        return JSONResponse(
            status_code=400,
            content={"data": _aes_encrypt({"success": False, "error": "缺少设备标识"})},
        )

    if not _crash_rate_limit(device_id):
        return JSONResponse(
            status_code=429,
            content={"data": _aes_encrypt({"success": False, "error": "上报过于频繁"})},
        )

    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute(
        "INSERT INTO crash_logs (device_id, hostname, os, traceback, log_tail) VALUES (?,?,?,?,?)",
        (
            device_id,
            payload.get("hostname", ""),
            payload.get("os", ""),
            payload.get("traceback", ""),
            payload.get("log_tail", ""),
        ),
    )
    conn.commit()
    conn.close()
    return {"data": _aes_encrypt({"success": True})}


@app.post("/media_parse", summary="解析媒体链接", tags=["客户端"])
def parse_media(body: EncryptedBody):
    """解析抖音、B站、快手等平台的视频/图文链接。

    **RSA 加密请求体格式 (解密后):**
    ```json
    {"text": "https://v.douyin.com/xxxx/"}
    ```

    **AES 解密响应体格式:**
    ```json
    {"retcode": 200, "retdesc": "成功", "data": {...}, "succ": true}
    ```
    """
    try:
        payload = _decrypt_payload(body.data)
        text = payload.get("text", "")

        redirect_url = WebFetcher.fetch_redirect_url(UrlParser.get_url(text))
        platform = DOMAIN_TO_NAME.get(UrlParser.get_domain(redirect_url))
        real_url = UrlParser.extract_video_address(redirect_url)
        parse_logger.debug(f"real_url {real_url}")

        if not platform:
            parse_logger.error(f"This link is not supported for extraction: {real_url}")
            return {"data": _aes_encrypt({"retcode": 400, "retdesc": "该链接尚未支持提取", "data": None, "succ": False})}

        parser = ParserFactory.create_parser(platform, real_url)

        def safe_execute(func, default=None):
            try:
                return func()
            except Exception:
                return default

        max_attempts = 3 if platform == "小红书" else 1
        content_data = None
        for i in range(max_attempts):
            content_data = {
                "title": parser.get_title_content(),
                "video_url": parser.get_real_video_url(),
                "cover_url": parser.get_cover_photo_url(),
                "author": safe_execute(parser.get_author_info),
                "image_list": safe_execute(parser.get_image_list, default=[]),
                "audio_url": safe_execute(parser.get_audio_url),
            }
            if content_data["video_url"] or content_data["image_list"]:
                break

        processed_image_list = []
        if content_data.get("image_list"):
            for img in content_data["image_list"]:
                if isinstance(img, dict):
                    processed_image_list.append({
                        "url": UrlParser.convert_to_https(img.get("url")),
                        "live_photo_url": UrlParser.convert_to_https(img.get("live_photo_url")),
                    })
                else:
                    processed_image_list.append(UrlParser.convert_to_https(img))

        data_dict = {
            "video_id": UrlParser.get_video_id(redirect_url),
            "platform": platform,
            "title": content_data["title"],
            "video_url": UrlParser.convert_to_https(content_data["video_url"]),
            "audio_url": UrlParser.convert_to_https(content_data.get("audio_url")),
            "cover_url": UrlParser.convert_to_https(content_data["cover_url"]),
            "author": content_data["author"],
            "image_list": processed_image_list,
        }

        parse_logger.debug(f"Parse Success for platform {platform}")
        return {"data": _aes_encrypt({"retcode": 200, "retdesc": "成功", "data": data_dict, "succ": True})}

    except Exception as e:
        parse_logger.exception("Parse Error")
        return {"data": _aes_encrypt({"retcode": 500, "retdesc": "功能太火爆啦，请稍后再试", "data": None, "succ": False})}


@app.delete("/suggestions/{sid}", summary="删除反馈", tags=["管理"])
def delete_suggestion(sid: int):
    """根据 ID 删除一条用户反馈。"""
    conn = sqlite3.connect(str(_SUGGEST_DB_PATH))
    conn.execute("DELETE FROM suggestions WHERE id=?", (sid,))
    conn.commit()
    conn.close()
    return {"success": True}


_SUGGESTIONS_CSS = """
body { font-family: "Microsoft YaHei", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
h1 { color: #333; display:inline-block; }
h1 + div { float:right; margin-top:20px; }
table { width: 100%; border-collapse: separate; border-spacing: 0; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.1); border-radius: 8px; overflow: hidden; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #009faa; color: #fff; font-weight: 500; }
tr:hover { background: #f0f9fa; }
td { color: #555; }
td.content { max-width: 400px; word-break: break-all; }
.del { display:inline-block; background:#e74c3c; color:#fff; border-radius:6px; padding:4px 14px; font-size:13px; cursor:pointer; text-decoration:none; }
.del:hover { background:#c0392b; }
.toolbar { margin-bottom:12px; }
.toolbar button { margin-right:8px; padding:6px 18px; border:none; border-radius:6px; cursor:pointer; font-size:14px; }
.btn-export { background:#009faa; color:#fff; }
.btn-export:hover { background:#00808a; }
.btn-select { background:#6c757d; color:#fff; }
.btn-select:hover { background:#5a6268; }
.cb { width:20px; height:20px; cursor:pointer; }
"""


@app.get("/suggestions", response_class=HTMLResponse, summary="反馈管理页", tags=["管理"])
def list_suggestions():
    """返回 HTML 页面，列出所有用户反馈，支持在线删除。"""
    conn = sqlite3.connect(str(_SUGGEST_DB_PATH))
    rows = conn.execute(
        "SELECT id, device_id, hostname, content, created_at FROM suggestions ORDER BY id DESC"
    ).fetchall()
    conn.close()

    import html as _html
    total = len(rows)
    trs = "".join(
        f'<tr data-id="{r[0]}"><td><input class="cb" type="checkbox" value="{r[0]}"></td><td>{total - i}</td><td class="content">{_html.escape(str(r[3]))}</td><td>{_html.escape(str(r[1][:8]))}…({_html.escape(str(r[2]))})</td><td>{r[4]}</td><td><a class="del" href="javascript:;" onclick="del({r[0]})">删除</a></td></tr>'
        for i, r in enumerate(rows)
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>用户反馈</title><style>{_SUGGESTIONS_CSS}</style></head>
<body><h1>用户反馈</h1>
<div class="toolbar">
  <button class="btn-select" onclick="toggleAll()">全选</button>
  <button class="btn-export" onclick="exportCSV()">导出 CSV</button>
  <button class="btn-export" onclick="exportExcel()">导出 Excel</button>
</div>
<table><thead><tr><th style="width:30px"><input class="cb" type="checkbox" onchange="toggleAll()"></th><th style="width:40px">#</th><th class="content">反馈内容</th><th>设备</th><th>时间</th><th style="width:80px">操作</th></tr></thead>
<tbody>{trs}</tbody></table>
<script>
function del(id) {{
    if (!confirm("确定删除该反馈？")) return;
    fetch("/suggestions/"+id, {{method:"DELETE"}}).then(function(r){{
        if (r.ok) location.reload();
        else alert("删除失败");
    }});
}}
function toggleAll() {{
    var checked = document.querySelector("thead input.cb").checked;
    document.querySelectorAll("tbody input.cb").forEach(function(c) {{ c.checked = checked; }});
}}
function getSelected() {{
    var rows = [];
    document.querySelectorAll("tbody input.cb:checked").forEach(function(c) {{
        var tr = c.closest("tr");
        var tds = tr.querySelectorAll("td");
        rows.push({{
            id: c.value,
            num: tds[1].textContent.trim(),
            content: tds[2].textContent.trim(),
            device: tds[3].textContent.trim(),
            time: tds[4].textContent.trim()
        }});
    }});
    return rows;
}}
function exportCSV() {{
    var rows = getSelected();
    if (rows.length === 0) {{ alert("请至少选择一条反馈"); return; }}
    var csv = "\\uFEFF#,\\u5185\\u5bb9,\\u8bbe\\u5907,\\u65f6\\u95f4\\n";
    rows.forEach(function(r) {{ csv += r.num + ',"' + r.content + '","' + r.device + '","' + r.time + '"\\n'; }});
    var blob = new Blob([csv], {{type:"text/csv;charset=utf-8"}});
    var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "\\u53cd\\u9988.csv"; a.click();
}}
function exportExcel() {{
    var rows = getSelected();
    if (rows.length === 0) {{ alert("请至少选择一条反馈"); return; }}
    var xml = '<\\?xml version="1.0" encoding="UTF-8"?\\>\\n<?mso-application progid="Excel.Sheet"?\\>\\n<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\\n<Worksheet ss:Name="\\u53cd\\u9988"><Table>\\n<Row><Cell><Data ss:Type="String">#</Data></Cell><Cell><Data ss:Type="String">\\u5185\\u5bb9</Data></Cell><Cell><Data ss:Type="String">\\u8bbe\\u5907</Data></Cell><Cell><Data ss:Type="String">\\u65f6\\u95f4</Data></Cell></Row>';
    rows.forEach(function(r) {{ xml += '<Row><Cell><Data ss:Type="Number">' + r.num + '</Data></Cell><Cell><Data ss:Type="String">' + r.content + '</Data></Cell><Cell><Data ss:Type="String">' + r.device + '</Data></Cell><Cell><Data ss:Type="String">' + r.time + '</Data></Cell></Row>'; }});
    xml += '</Table></Worksheet></Workbook>';
    var blob = new Blob([xml], {{type:"application/vnd.ms-excel;charset=utf-8"}});
    var a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "\\u53cd\\u9988.xls"; a.click();
}}
</script>
</body></html>"""
    return HTMLResponse(content=html)


_LOGIN_STATUS_CSS = """
body { font-family: "Microsoft YaHei", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
h1 { color: #333; }
table { width: 100%; border-collapse: separate; border-spacing: 0; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.1); border-radius: 8px; overflow: hidden; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #009faa; color: #fff; font-weight: 500; }
tr:hover { background: #f0f9fa; }
td { color: #555; }
.ok { color: #27ae60; font-weight: bold; }
.fail { color: #e74c3c; font-weight: bold; }
"""


@app.get("/login_status", response_class=HTMLResponse, summary="登录记录页", tags=["管理"])
def login_status(_=Depends(_verify_admin)):
    """返回 HTML 页面，列出最近 200 条登录记录。

    需 HTTP Basic Auth 认证 (`admin` / `admin123`)。
    连续 3 次密码错误将锁定该 IP 24 小时。
    """
    conn = sqlite3.connect(str(_DB_PATH))
    rows = conn.execute(
        "SELECT id, username, device_id, hostname, os, success, created_at FROM login_log ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()

    import html as _html
    trs = "".join(
        f'<tr><td>{r[0]}</td><td>{_html.escape(r[1])}</td>'
        f'<td>{_html.escape(str(r[2])[:8])}…</td>'
        f'<td>{_html.escape(r[3])}</td><td>{_html.escape(r[4])}</td>'
        f'<td class="{"ok" if r[5] else "fail"}">{"成功" if r[5] else "失败"}</td>'
        f'<td>{r[6]}</td></tr>'
        for r in rows
    )
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>登录记录</title><style>{_LOGIN_STATUS_CSS}</style></head>
<body><h1>登录记录</h1>
<table><thead><tr><th>#</th><th>用户名</th><th>设备</th><th>主机名</th><th>系统</th><th>状态</th><th>时间</th></tr></thead>
    <tbody>{trs}</tbody></table></body></html>""")


_CRASH_LOG_CSS = """
body { font-family: "Microsoft YaHei", sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
h1 { color: #333; display:inline-block; }
h1 + div { float:right; margin-top:20px; }
table { width: 100%; border-collapse: separate; border-spacing: 0; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.1); border-radius: 8px; overflow: hidden; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #c0392b; color: #fff; font-weight: 500; }
tr:hover { background: #fdf2f2; }
td { color: #555; font-size: 13px; }
td.traceback { max-width: 500px; white-space: pre-wrap; word-break: break-all; font-family: Consolas, monospace; font-size: 12px; background: #fafafa; }
td.logtail { max-width: 400px; white-space: pre-wrap; word-break: break-all; font-family: Consolas, monospace; font-size: 12px; background: #fafafa; }
.detail-btn { display:inline-block; background:#c0392b; color:#fff; border-radius:6px; padding:4px 14px; font-size:13px; cursor:pointer; text-decoration:none; border:none; }
.detail-btn:hover { background:#a93226; }
.modal-overlay { display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,.5); z-index:1000; }
.modal { position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:#fff; border-radius:12px; padding:24px; width:80%; max-height:80vh; overflow:auto; z-index:1001; box-shadow: 0 8px 32px rgba(0,0,0,.3); }
.modal h2 { margin-top:0; color:#333; }
.modal pre { background:#1e1e1e; color:#d4d4d4; padding:16px; border-radius:8px; overflow:auto; max-height:50vh; font-size:12px; line-height:1.5; }
.modal .close-btn { position:absolute; top:12px; right:16px; font-size:24px; cursor:pointer; color:#999; background:none; border:none; }
.modal .close-btn:hover { color:#333; }
"""


@app.get("/crash-logs", response_class=HTMLResponse, summary="崩溃日志页", tags=["管理"])
def crash_logs_page(_=Depends(_verify_admin)):
    """返回 HTML 页面，列出最近 100 条崩溃日志。

    需 HTTP Basic Auth 认证 (`admin` / `admin123`)。
    """
    conn = sqlite3.connect(str(_DB_PATH))
    rows = conn.execute(
        "SELECT id, device_id, hostname, os, traceback, log_tail, created_at FROM crash_logs ORDER BY id DESC LIMIT 100"
    ).fetchall()
    conn.close()

    import html as _html

    def _build_row(r):
        tb_short = (r[4][:200] + "...") if len(r[4]) > 200 else r[4]
        return (
            f'<tr data-id="{r[0]}">'
            f'<td>{r[0]}</td>'
            f'<td>{_html.escape(str(r[1])[:8])}\u2026</td>'
            f'<td>{_html.escape(str(r[2]))}</td>'
            f'<td>{_html.escape(str(r[3]))}</td>'
            f'<td class="traceback">{_html.escape(tb_short)}</td>'
            f'<td>{r[6]}</td>'
            f'<td><button class="detail-btn" onclick="showDetail({r[0]})">详情</button></td>'
            f'</tr>'
        )

    trs = "".join(_build_row(r) for r in rows)

    # build JSON for JS
    import json as _json
    details_json = _json.dumps(
        [{"id": r[0], "traceback": r[4], "log_tail": r[5]} for r in rows],
        ensure_ascii=False,
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>崩溃日志</title><style>{_CRASH_LOG_CSS}</style></head>
<body><h1>崩溃日志</h1>
<table><thead><tr><th>#</th><th>设备</th><th>主机名</th><th>系统</th><th>异常摘要</th><th>时间</th><th>操作</th></tr></thead>
<tbody>{trs}</tbody></table>

<div class="modal-overlay" id="overlay" onclick="closeModal()"></div>
<div class="modal" id="modal">
  <button class="close-btn" onclick="closeModal()">&times;</button>
  <h2 id="modal-title">崩溃详情</h2>
  <h3>Traceback</h3>
  <pre id="modal-tb"></pre>
  <h3>运行日志</h3>
  <pre id="modal-log"></pre>
</div>

<script>
var details = {details_json};
var detailMap = {{}};
details.forEach(function(d) {{ detailMap[d.id] = d; }});

function showDetail(id) {{
    var d = detailMap[id];
    if (!d) return;
    document.getElementById("modal-title").textContent = "崩溃 #" + id;
    document.getElementById("modal-tb").textContent = d.traceback || "(无)";
    document.getElementById("modal-log").textContent = d.log_tail || "(无)";
    document.getElementById("overlay").style.display = "block";
    document.getElementById("modal").style.display = "block";
}}
function closeModal() {{
    document.getElementById("overlay").style.display = "none";
    document.getElementById("modal").style.display = "none";
}}
</script>
</body></html>"""
    return HTMLResponse(content=html)
