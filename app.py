"""
ClipSnap - YouTube Segment Downloader
Jalankan: python app.py
Buka:     http://localhost:5000

Install:
  pip install flask flask-cors yt-dlp
  pkg install ffmpeg  (Termux)
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os, tempfile, uuid, threading, time, glob, subprocess

app  = Flask(__name__, static_folder=".")
CORS(app)

TEMP_DIR    = tempfile.mkdtemp(prefix="clipsnap_")
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

# ─── Job store ───────────────────────────────────────────────────────
jobs = {}

# ─── Cleanup ─────────────────────────────────────────────────────────
def cleanup_worker():
    while True:
        time.sleep(300)
        now = time.time()
        for f in glob.glob(os.path.join(TEMP_DIR, "*")):
            try:
                if os.path.isfile(f) and (now - os.path.getmtime(f)) > 1800:
                    os.remove(f)
            except:
                pass
        to_del = [k for k,v in list(jobs.items()) if time.time() - v.get("created",0) > 3600]
        for k in to_del:
            jobs.pop(k, None)

threading.Thread(target=cleanup_worker, daemon=True).start()


def secs_to_hms(s):
    s = int(s)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def build_base_args():
    """Argumen dasar yt-dlp, pakai cookies kalau ada"""
    args = []
    if os.path.exists(COOKIES_FILE):
        args += ["--cookies", COOKIES_FILE]
    # Pura-pura jadi YouTube Android supaya tidak kena bot detection
    args += [
        "--extractor-args", "youtube:player_client=android",
        "--user-agent", "com.google.android.youtube/19.09.37 (Linux; U; Android 11) gzip",
    ]
    return args


# ─── Routes ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/api/info", methods=["POST"])
def get_info():
    data = request.get_json()
    url  = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "URL kosong"}), 400
    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }
        if os.path.exists(COOKIES_FILE):
            opts["cookiefile"] = COOKIES_FILE

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "title":      info.get("title", "Unknown"),
            "duration":   info.get("duration", 0),
            "thumbnail":  info.get("thumbnail", ""),
            "uploader":   info.get("uploader", ""),
            "view_count": info.get("view_count", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/start-download", methods=["POST"])
def start_download():
    data  = request.get_json()
    url   = (data.get("url") or "").strip()
    start = float(data.get("start", 0))
    end   = float(data.get("end",   60))
    fmt   = data.get("format", "mp4")

    if not url:
        return jsonify({"error": "URL kosong"}), 400
    if end <= start:
        return jsonify({"error": "Waktu akhir harus lebih besar dari waktu awal"}), 400

    job_id = uuid.uuid4().hex[:12]
    jobs[job_id] = {
        "status":   "queued",
        "progress": 0,
        "message":  "Antri...",
        "file":     None,
        "error":    None,
        "created":  time.time(),
    }

    t = threading.Thread(target=run_download, args=(job_id, url, start, end, fmt), daemon=True)
    t.start()
    return jsonify({"job_id": job_id})


def run_download(job_id, url, start, end, fmt):
    def update(status, progress, message):
        jobs[job_id].update({"status": status, "progress": progress, "message": message})

    try:
        uid      = uuid.uuid4().hex[:8]
        out_tmpl = os.path.join(TEMP_DIR, f"clip_{uid}.%(ext)s")
        section  = f"*{start}-{end}"
        base     = build_base_args()

        update("running", 10, "Menghubungi YouTube...")

        if fmt == "mp3":
            cmd = ["yt-dlp"] + base + [
                "--download-sections", section,
                "--force-keyframes-at-cuts",
                "-f", "bestaudio/best",
                "-x", "--audio-format", "mp3",
                "--audio-quality", "192K",
                "--newline",
                "-o", out_tmpl,
                "--no-playlist",
                url,
            ]
        else:
            cmd = ["yt-dlp"] + base + [
                "--download-sections", section,
                "--force-keyframes-at-cuts",
                "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "--merge-output-format", "mp4",
                "--newline",
                "-o", out_tmpl,
                "--no-playlist",
                url,
            ]

        update("running", 20, "Mengunduh dari YouTube...")

        # Gabung stdout+stderr supaya dapat semua output yt-dlp
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        last_pct = [20]

        # Thread auto-progress (backup kalau parsing gagal)
        def auto_progress():
            msgs = ["Mengunduh video...", "Memproses...", "Hampir selesai..."]
            i = 0
            while proc.poll() is None:
                time.sleep(5)
                if last_pct[0] < 75:
                    last_pct[0] = min(last_pct[0] + 10, 80)
                    update("running", last_pct[0], msgs[i % len(msgs)])
                    i += 1

        threading.Thread(target=auto_progress, daemon=True).start()

        # Baca output yt-dlp line by line
        all_output = []
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            all_output.append(line)
            if "[download]" in line and "%" in line:
                try:
                    pct = float(line.split("%")[0].split()[-1])
                    mapped = 20 + int(pct * 0.65)
                    last_pct[0] = mapped
                    update("running", mapped, f"Mengunduh... {pct:.0f}%")
                except:
                    pass
            elif "[Merger]" in line or "Merging" in line:
                last_pct[0] = 88
                update("running", 88, "Menggabungkan video & audio...")
            elif "[ffmpeg]" in line:
                last_pct[0] = 93
                update("running", 93, "Memotong segmen...")

        proc.wait()

        if proc.returncode != 0:
            # Cari baris error dari output
            errors = [l for l in all_output if "ERROR" in l]
            msg = errors[-1] if errors else "yt-dlp gagal. Cek URL atau koneksi."
            raise Exception(msg)

        update("running", 96, "Menyiapkan file...")

        files = glob.glob(os.path.join(TEMP_DIR, f"clip_{uid}.*"))
        if not files:
            raise Exception("File tidak ditemukan. Pastikan ffmpeg terinstall.")

        result_file = files[0]
        ext    = os.path.splitext(result_file)[1]
        s_str  = secs_to_hms(start).replace(":", "-")
        e_str  = secs_to_hms(end).replace(":", "-")
        dl_name = f"clip_{s_str}_to_{e_str}{ext}"

        jobs[job_id].update({
            "status":   "done",
            "progress": 100,
            "message":  "Selesai!",
            "file":     result_file,
            "dl_name":  dl_name,
            "ext":      ext,
        })

    except Exception as e:
        jobs[job_id].update({
            "status":  "error",
            "progress": 0,
            "message":  "Gagal",
            "error":    str(e),
        })


@app.route("/api/job/<job_id>", methods=["GET"])
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job tidak ditemukan"}), 404
    return jsonify({
        "status":   job["status"],
        "progress": job["progress"],
        "message":  job["message"],
        "error":    job.get("error"),
    })


@app.route("/api/file/<job_id>", methods=["GET"])
def get_file(job_id):
    job = jobs.get(job_id)
    if not job or job["status"] != "done":
        return jsonify({"error": "File belum siap"}), 404
    if not job.get("file") or not os.path.exists(job["file"]):
        return jsonify({"error": "File tidak ditemukan di server"}), 404
    ext = job.get("ext", ".mp4")
    return send_file(
        job["file"],
        as_attachment=True,
        download_name=job.get("dl_name", f"clip{ext}"),
        mimetype="video/mp4" if ext == ".mp4" else "audio/mpeg"
    )


if __name__ == "__main__":
    has_cookies = os.path.exists(COOKIES_FILE)
    print("\n╔════════════════════════════════╗")
    print("║  ClipSnap Server AKTIF         ║")
    print("║  Buka: http://localhost:5000   ║")
    print(f"║  Cookies: {'✅ ADA' if has_cookies else '❌ TIDAK ADA'}              ║")
    print("╚════════════════════════════════╝\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
