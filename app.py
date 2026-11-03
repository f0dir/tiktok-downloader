from flask import Flask, render_template, request, send_file, jsonify
from yt_dlp import YoutubeDL
from urllib.parse import urlparse
from pathlib import Path
import tempfile, os, re, uuid, threading, time

app = Flask(__name__)
DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "tiktok_site_downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

def valid_tiktok_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return host == "tiktok.com" or host.endswith(".tiktok.com")
    except Exception:
        return False

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not valid_tiktok_url(url):
        return jsonify(error="أدخل رابط TikTok صحيحاً."), 400

    job_id = uuid.uuid4().hex
    output_template = str(DOWNLOAD_DIR / f"{job_id}.%(ext)s")
    opts = {
        "outtmpl": output_template,
        "format": "best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "socket_timeout": 20,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                mp4_candidate = str(Path(filename).with_suffix(".mp4"))
                if os.path.exists(mp4_candidate):
                    filename = mp4_candidate
            if not os.path.exists(filename):
                matches = list(DOWNLOAD_DIR.glob(job_id + ".*"))
                if not matches:
                    raise RuntimeError("لم يتم العثور على الملف بعد التحميل.")
                filename = str(matches[0])
            title = re.sub(r'[\\/:*?"<>|]+', "_", info.get("title") or "tiktok_video")
            return send_file(
                filename,
                as_attachment=True,
                download_name=f"{title}{Path(filename).suffix}",
                mimetype="video/mp4" if Path(filename).suffix == ".mp4" else "application/octet-stream"
            )
    except Exception as exc:
        return jsonify(error="تعذّر تحميل المقطع. قد يكون الرابط خاصاً أو أن TikTok غيّر طريقة الوصول. " + str(exc)[:220]), 502

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)