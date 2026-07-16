"""Loads backend/.env (gitignored) into the environment. Keeps keys out of code
and out of shell history. Call load_env() at process start."""
import os
import pathlib


def load_env():
    f = pathlib.Path(__file__).parent / ".env"
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
