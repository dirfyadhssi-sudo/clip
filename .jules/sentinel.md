# Sentinel's Journal

## 2026-04-27 - Flask static_folder Exposing Repository Root Directory
**Vulnerability:** Initializing a Flask application with `static_folder="."` registers Flask's default static view handler on `/<filename>` mapped to the repository root directory. This allowed unauthenticated remote attackers to download sensitive repository files including `cookies.txt` (containing YouTube authentication session tokens), source code (`app.py`), and Git metadata (`.git/config`).
**Learning:** Setting `static_folder="."` in Flask creates an unintended static file endpoint serving all files in current working directory. The home route `/` already handles serving `index.html` via `send_from_directory(".", "index.html")`, making `static_folder` unnecessary.
**Prevention:** Always initialize Flask with `static_folder=None` unless a dedicated, isolated static assets directory (e.g. `static/`) exists that contains no sensitive files, secrets, or source code.
