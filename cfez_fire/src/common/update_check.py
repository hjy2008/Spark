import requests
import tempfile
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

from datetime import datetime

from common.crypto import encrypt_payload, aes_encrypt, aes_decrypt

DEBUG = True

def dbg(*args, **kwargs):
    if DEBUG:
        kwargs["flush"] = kwargs.get("flush", True)
        tag = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}]"
        print(tag, *args, **kwargs)


_session = requests.Session()
_session.proxies = {"http": None, "https": None}

HOST = "https://79ecf59845b9061dd3d3a9d55cf83772.hjylock.top"
# HOST = "http://192.168.1.34:9825"
# HOST = "http://127.0.0.1:8000"
API_URL = f"{HOST}/check-updates"
LOGIN_URL = f"{HOST}/login"
AUTO_LOGIN_URL = f"{HOST}/auto-login"
FEEDBACK_URL = f"{HOST}/feedback"
UPLOAD_AVATAR_URL = f"{HOST}/upload-avatar"
CRASH_REPORT_URL = f"{HOST}/crash-report"
MEDIA_PARSE_URL = f"{HOST}/media_parse"
CURRENT_VERSION = "v1.0.1"


class CheckUpdateThread(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, url=None, current_version=None, parent=None):
        super().__init__(parent)
        self.url = url or API_URL
        self.current_version = current_version or CURRENT_VERSION
        dbg(f"[CheckUpdateThread] __init__ url={self.url}")

    def run(self):
        dbg("[CheckUpdateThread] run() started")
        try:
            body = encrypt_payload({"current_version": self.current_version})
            dbg(f"[CheckUpdateThread] POST {self.url}")
            resp = _session.post(self.url, json={"data": body}, timeout=5)
            dbg(f"[CheckUpdateThread] HTTP {resp.status_code}")
            resp.raise_for_status()
            decrypted = aes_decrypt(resp.json()["data"])
            dbg(f"[CheckUpdateThread] response keys={list(decrypted.keys())}")
            self.finished.emit(decrypted)
        except Exception as e:
            dbg(f"[CheckUpdateThread] error: {e}")
            self.finished.emit({"has_update": False, "error": str(e)})


class DownloadThread(QThread):
    finished = pyqtSignal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        dbg(f"[DownloadThread] __init__ url={url}")

    def run(self):
        dbg("[DownloadThread] run() started")
        try:
            resp = _session.get(self.url, stream=True, timeout=30)
            resp.raise_for_status()
            content_length = resp.headers.get("Content-Length", "unknown")
            dbg(f"[DownloadThread] HTTP {resp.status_code}, Content-Length={content_length}")

            suffix = Path(self.url).suffix or ".exe"
            dest = Path(tempfile.gettempdir()) / f"update{suffix}"
            dbg(f"[DownloadThread] saving to {dest}")

            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            dbg(f"[DownloadThread] done, size={dest.stat().st_size}")
            self.finished.emit(str(dest))
        except Exception as e:
            dbg(f"[DownloadThread] error: {e}")
            self.finished.emit("")


class LoginThread(QThread):
    loginFinished = pyqtSignal(dict)

    def __init__(self, url, username, phone, device_info=None, parent=None):
        super().__init__(parent)
        self.url = url
        self.username = username
        self.phone = phone
        self.device_info = device_info or {}
        dbg(f"[LoginThread] __init__ user={username} url={url}")

    def run(self):
        dbg("[LoginThread] run() started")
        try:
            payload = {"username": self.username, "phone": self.phone}
            payload.update(self.device_info)
            dbg(f"[LoginThread] payload keys={list(payload.keys())}")

            body = encrypt_payload(payload)
            dbg(f"[LoginThread] POST {self.url}")
            resp = _session.post(self.url, json={"data": body}, timeout=10)
            dbg(f"[LoginThread] HTTP {resp.status_code}")

            if not resp.ok:
                dbg(f"[LoginThread] HTTP not OK: {resp.status_code}")
                try:
                    err = aes_decrypt(resp.json()["data"])
                    dbg(f"[LoginThread] error response keys={list(err.keys())}")
                    self.loginFinished.emit({"success": False, "error": err.get("error", "请求失败")})
                except Exception as e2:
                    dbg(f"[LoginThread] decrypt error: {e2}")
                    self.loginFinished.emit({"success": False, "error": f"HTTP {resp.status_code}"})
                return

            dbg("[LoginThread] decrypting response")
            decrypted = aes_decrypt(resp.json()["data"])
            dbg(f"[LoginThread] response keys={list(decrypted.keys())}, success={decrypted.get('success')}")
            self.loginFinished.emit(decrypted)
        except Exception as e:
            dbg(f"[LoginThread] exception: {e}")
            self.loginFinished.emit({"success": False, "error": str(e)})


class AutoLoginThread(QThread):
    loginFinished = pyqtSignal(dict)

    def __init__(self, url, encrypted_blob, parent=None):
        super().__init__(parent)
        self.url = url
        self.encrypted_blob = encrypted_blob
        dbg("[AutoLoginThread] __init__")

    def run(self):
        dbg("[AutoLoginThread] run() started")
        try:
            dbg(f"[AutoLoginThread] POST {self.url}")
            resp = _session.post(self.url, json={"data": self.encrypted_blob}, timeout=10)
            dbg(f"[AutoLoginThread] HTTP {resp.status_code}")
            if not resp.ok:
                dbg(f"[AutoLoginThread] HTTP not OK: {resp.status_code}")
                try:
                    err = aes_decrypt(resp.json()["data"])
                    self.loginFinished.emit({"success": False, "error": err.get("error", "请求失败")})
                except Exception:
                    self.loginFinished.emit({"success": False, "error": f"HTTP {resp.status_code}"})
                return
            decrypted = aes_decrypt(resp.json()["data"])
            dbg(f"[AutoLoginThread] success={decrypted.get('success')}")
            self.loginFinished.emit(decrypted)
        except Exception as e:
            dbg(f"[AutoLoginThread] exception: {e}")
            self.loginFinished.emit({"success": False, "error": str(e)})


class MediaParseThread(QThread):
    parseFinished = pyqtSignal(dict)
    parseError = pyqtSignal(str)

    def __init__(self, url, encrypted_data, parent=None):
        super().__init__(parent)
        self.url = url
        self.encrypted_data = encrypted_data
        dbg("[MediaParseThread] __init__")

    def run(self):
        dbg("[MediaParseThread] run() started")
        try:
            dbg(f"[MediaParseThread] POST {self.url}")
            resp = _session.post(self.url, json={"data": self.encrypted_data}, timeout=30)
            dbg(f"[MediaParseThread] HTTP {resp.status_code}")
            if not resp.ok:
                self.parseError.emit(f"HTTP {resp.status_code}")
                return
            decrypted = aes_decrypt(resp.json()["data"])
            dbg(f"[MediaParseThread] succ={decrypted.get('succ')}")
            if decrypted.get("succ"):
                self.parseFinished.emit(decrypted)
            else:
                self.parseError.emit(decrypted.get("retdesc", "解析失败"))
        except Exception as e:
            dbg(f"[MediaParseThread] exception: {e}")
            self.parseError.emit(str(e))


class FeedbackThread(QThread):
    feedbackFinished = pyqtSignal(dict)

    def __init__(self, url, device_info, parent=None):
        super().__init__(parent)
        self.url = url
        self.device_info = device_info
        dbg("[FeedbackThread] __init__")

    def run(self):
        dbg("[FeedbackThread] run() started")
        try:
            encrypted = aes_encrypt(self.device_info)
            resp = _session.post(self.url, json={"data": encrypted}, timeout=10)
            result = aes_decrypt(resp.json()["data"])
            dbg(f"[FeedbackThread] done, keys={list(result.keys())}")
            self.feedbackFinished.emit(result)
        except Exception as e:
            dbg(f"[FeedbackThread] exception: {e}")
            self.feedbackFinished.emit({"error": str(e)})


class UploadAvatarThread(QThread):
    uploadFinished = pyqtSignal(dict)

    def __init__(self, url, username, avatar_data, parent=None):
        super().__init__(parent)
        self.url = url
        self.username = username
        self.avatar_data = avatar_data
        dbg(f"[UploadAvatarThread] __init__ user={username}")

    def run(self):
        dbg("[UploadAvatarThread] run() started")
        try:
            dbg(f"[UploadAvatarThread] POST {self.url}")
            resp = _session.post(
                self.url,
                data={"username": self.username},
                files={"avatar": ("avatar.png", self.avatar_data, "image/png")},
                timeout=30,
            )
            resp.raise_for_status()
            decrypted = aes_decrypt(resp.json()["data"])
            dbg(f"[UploadAvatarThread] done, keys={list(decrypted.keys())}")
            self.uploadFinished.emit(decrypted)
        except Exception as e:
            dbg(f"[UploadAvatarThread] exception: {e}")
            self.uploadFinished.emit({"success": False, "error": str(e)})
