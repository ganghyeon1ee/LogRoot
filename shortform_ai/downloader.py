from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve


def download_audio(url: str, out_dir: str = "downloads") -> str:
    os.makedirs(out_dir, exist_ok=True)

    parsed = urlparse(url)
    filename = Path(parsed.path).name or "audio.mp3"
    target = Path(out_dir) / filename

    urlretrieve(url, target)
    return str(target)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
