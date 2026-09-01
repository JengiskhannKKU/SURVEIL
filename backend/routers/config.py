from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from oculus import config as oculus_config
from oculus.wordlists import WORDLIST_DIR_ENV, default_wordlist, discover_wordlists

router = APIRouter(prefix="/api/config", tags=["config"])


class WordlistDirUpdate(BaseModel):
    wordlist_dir: Optional[str] = None  # empty/None clears the override


def _status() -> dict:
    return {
        "wordlist_dir": oculus_config.get_wordlist_dir(),
        "wordlist_dir_env": os.environ.get(WORDLIST_DIR_ENV),
        "default_wordlist": default_wordlist(),
        "wordlists_found": len(discover_wordlists()),
    }


@router.get("")
def get_config() -> dict:
    return _status()


@router.put("/wordlist-dir")
def update_wordlist_dir(body: WordlistDirUpdate) -> dict:
    value = (body.wordlist_dir or "").strip() or None
    if value:
        path = Path(value).expanduser()
        if not path.exists():
            raise HTTPException(status_code=400, detail=f"Path does not exist: {value}")
        value = str(path)
    oculus_config.set_wordlist_dir(value)
    return _status()
