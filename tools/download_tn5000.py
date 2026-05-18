from pathlib import Path
import sys
import time
import urllib.request


URL = "https://ndownloader.figshare.com/files/52597376"
DEST = Path(r"D:\AAAAAAA\bishe\datasets\raw\TN5000_forReview_download.py.part")
FINAL = Path(r"D:\AAAAAAA\bishe\datasets\raw\TN5000_forReview.zip")
CHUNK_SIZE = 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"


def human(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{n}B"


def get_total_size() -> int | None:
    req = urllib.request.Request(URL, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            length = resp.headers.get("Content-Length")
            return int(length) if length else None
    except Exception:
        return None


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    downloaded = DEST.stat().st_size if DEST.exists() else 0
    total = get_total_size()

    headers = {"User-Agent": USER_AGENT}
    if downloaded > 0:
        headers["Range"] = f"bytes={downloaded}-"

    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        mode = "ab" if downloaded > 0 and resp.status == 206 else "wb"
        if mode == "wb":
            downloaded = 0
        started = time.time()
        last_report = started

        with DEST.open(mode) as f:
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if now - last_report >= 10:
                    if total:
                        pct = downloaded / total * 100
                        print(f"{human(downloaded)} / {human(total)} ({pct:.2f}%)", flush=True)
                    else:
                        print(f"{human(downloaded)} downloaded", flush=True)
                    last_report = now

    final_size = DEST.stat().st_size
    if total and final_size < total:
        print(f"incomplete: {human(final_size)} / {human(total)}", flush=True)
        sys.exit(2)

    if FINAL.exists():
        FINAL.unlink()
    DEST.rename(FINAL)
    print(f"saved to {FINAL}", flush=True)


if __name__ == "__main__":
    main()
