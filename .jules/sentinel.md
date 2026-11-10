# Sentinel's Journal

## 2026-04-27 - yt-dlp CLI Argument Injection & Unrestricted URL SSRF
**Vulnerability:** User-provided video URLs were passed directly into subprocess command lists (`cmd.append(url)` and `cmd + [...] + [url]`) without format or domain validation. If a user passed CLI options (e.g. `--help` or options with arguments), yt-dlp parsed them as flags rather than URLs. Furthermore, yt-dlp supports hundreds of extractors and protocols; allowing arbitrary URLs opened the server to SSRF or unexpected network fetches.
**Learning:** Even when avoiding shell interpolation with `shell=False` or passing arguments as lists in `subprocess.run`/`Popen`, CLI tools can interpret leading hyphens as option flags. Additionally, external video fetch utilities should strictly restrict input domain schemes and hostnames when built for specific platforms like YouTube.
**Prevention:** Strictly validate URL scheme and whitelist trusted hostnames (`ALLOWED_YOUTUBE_HOSTS`) before handing off to the CLI tool, and always prepend `--` before positional user arguments as defense-in-depth to terminate flag parsing in yt-dlp.
