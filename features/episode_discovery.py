"""Read-only discovery of dated and undated NTN episode folders."""

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional, Tuple

from .episode_naming import extract_ntn_number


FOLDER_PATTERN = re.compile(
    r"^(?:(\d{2})[ -](\d{2})[ -](\d{2})\s+)?NTN\s*(\d+)\b", re.I)
FINAL_PATTERN = re.compile(r"^ntn(\d+)(?:-\d{2,})?\.mp3$", re.I)
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".aiff", ".wma"}


def recording_order(path: Path):
    stem = re.sub(r"^recoding\b", "recording", path.stem.casefold())
    parts = re.split(r"(\d+)", stem)
    return (tuple((1, int(part)) if part.isdecimal() else (0, part)
                  for part in parts), path.name.casefold(), path.name)


@dataclass(frozen=True)
class EpisodeFolder:
    path: Path
    episode_date: Optional[date]
    number: int
    recordings: Tuple[Path, ...]
    finals: Tuple[Path, ...]
    problems: Tuple[str, ...]

    @property
    def pending(self) -> bool:
        return self.selectable and not self.finals

    @property
    def selectable(self) -> bool:
        return bool(self.recordings) and not self.problems

    @property
    def output_name(self) -> str:
        return f"ntn{self.number}.mp3"


def inspect_episode(path: Path) -> EpisodeFolder:
    match = FOLDER_PATTERN.match(path.name)
    if match is None:
        raise ValueError(f"Nombre de carpeta no reconocido: {path.name}")
    episode_date = None
    if match.group(1) is not None:
        year, month, day = (int(value) for value in match.groups()[:3])
        episode_date = date(2000 + year, month, day)
    number = extract_ntn_number(path.name)
    if number is None:
        raise ValueError(f"Falta numero NTN: {path.name}")
    recordings = []
    finals = []
    problems = []
    for file in sorted(path.iterdir(), key=lambda item: item.name.casefold()):
        if not file.is_file():
            continue
        final = FINAL_PATTERN.fullmatch(file.name)
        if final:
            finals.append(file)
            if int(final.group(1)) != number:
                problems.append(f"Final {file.name} no coincide con NTN {number}.")
            continue
        if file.suffix.casefold() in AUDIO_EXTENSIONS:
            recordings.append(file)
    recordings.sort(key=recording_order)
    return EpisodeFolder(path, episode_date, number,
                         tuple(recordings),
                         tuple(finals), tuple(problems))


def discover_episodes(root: Path) -> Tuple[List[EpisodeFolder], List[str]]:
    if not root.is_dir():
        raise FileNotFoundError(f"No existe el directorio de podcasts: {root}")
    episodes = []
    warnings = []
    for folder in root.iterdir():
        if not folder.is_dir() or not FOLDER_PATTERN.match(folder.name):
            continue
        try:
            episodes.append(inspect_episode(folder))
        except (OSError, ValueError) as error:
            warnings.append(f"No se pudo revisar {folder.name}: {error}")
    episodes.sort(key=lambda episode: (episode.episode_date or date.min,
                                       episode.path.name.casefold()),
                  reverse=True)
    return episodes, warnings
