"""RSS episode names and no-clobber output reservations."""

import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


def extract_ntn_number(title: Optional[str]) -> Optional[int]:
    match = re.search(r"ntn\s*(\d+)", title or "", re.IGNORECASE)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def next_rss_name(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            root = ET.fromstring(response.read())
        number = extract_ntn_number(root.findtext(".//channel/item/title"))
        if number is None:
            raise ValueError("RSS latest title has no NTN episode number")
        return f"ntn{number + 1}"
    except (OSError, ValueError, ET.ParseError) as error:
        raise ValueError(
            f"Cannot determine the next RSS episode: {error}. Supply -Name explicitly."
        ) from error


def validate_name(name: str) -> str:
    if (not isinstance(name, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", name)
            or name.upper() in {"CON", "PRN", "AUX", "NUL"}
            or re.fullmatch(r"(COM|LPT)[1-9]", name, re.IGNORECASE)):
        raise ValueError("Episode name must be a safe filename stem (letters, digits, - or _).")
    return name


@contextmanager
def reserve_output(directory: Path, name: str, automatic: bool) -> Iterator[Path]:
    """Called under render_lock; abandoned markers are safe to retire then."""
    directory.mkdir(parents=True, exist_ok=True)
    name = validate_name(name)
    number = extract_ntn_number(name)
    if automatic and not re.fullmatch(r"ntn\d+", name):
        raise ValueError("Automatic name must be an NTN episode number")
    while True:
        output = directory / f"{name}.mp3"
        marker = directory / f".ntn-reservation-{name}"
        # No cooperating renderer can own a marker while this caller owns
        # the directory's process-shared render lock.
        marker.unlink(missing_ok=True)
        if (not any(directory.glob(f"{name}.mp3*"))
                and not any(directory.glob(f"{name}_denoised.*"))
                and not (directory / f"{name}_transcript.txt").exists()):
            descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            break
        if not automatic:
            raise FileExistsError(f"Episode {name} already exists; choose another -Name.")
        if number is None:
            raise ValueError("Automatic name has no episode number")
        number += 1
        name = f"ntn{number}"
    try:
        yield output
    finally:
        marker.unlink(missing_ok=True)
