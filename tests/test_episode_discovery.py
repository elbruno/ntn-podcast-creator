"""Folder classification without loading audio or hydrating OneDrive files."""

from pathlib import Path

import pytest

from features.episode_discovery import discover_episodes, inspect_episode


def folder(root, name, files):
    path = root / name
    path.mkdir()
    for file in files:
        (path / file).write_bytes(b"original")
    return path


def test_discovery_date_order_and_nonrecursive_scope(tmp_path):
    older = folder(tmp_path, "26 09 30 NTN 575 Test", ["Recording.m4a"])
    newer = folder(tmp_path, "26 10 11 NTN 580 Test", ["recording.MP3"])
    archive = folder(tmp_path, "Archive", [])
    folder(archive, "26 10 12 NTN 581", ["Recording.m4a"])
    draft = folder(tmp_path, "NTN 999 ideas", ["Recording.m4a"])
    folder(tmp_path, "Ideas NTN 998", ["Recording.m4a"])
    episodes, warnings = discover_episodes(tmp_path)
    assert not warnings
    assert [episode.path for episode in episodes] == [newer, older, draft]
    assert all(episode.pending for episode in episodes)


def test_undated_drafts_have_no_date_and_stable_name_order(tmp_path):
    second = folder(tmp_path, "NTN 999 Zebra", ["Recording.m4a"])
    first = folder(tmp_path, "ntn 999 Alpha", ["recording.MP3"])
    episodes, warnings = discover_episodes(tmp_path)
    assert not warnings
    assert [episode.path for episode in episodes] == [second, first]
    assert all(episode.episode_date is None for episode in episodes)
    assert all(episode.number == 999 and episode.pending for episode in episodes)
    assert all(episode.output_name == "ntn999.mp3" for episode in episodes)


def test_numeric_recording_order(tmp_path):
    names = ["Recording.m4a"] + [f"Recoding ({index}).wav" for index in range(2, 11)]
    path = folder(tmp_path, "26 10 01 NTN 576", reversed(names))
    episode = inspect_episode(path)
    assert [file.name for file in episode.recordings] == names
    assert episode.pending
    assert episode.output_name == "ntn576.mp3"


@pytest.mark.parametrize("name", ["ntn580.mp3", "NTN580-03.MP3", "ntn580-100.mp3"])
@pytest.mark.parametrize("prefix", ["26 10 11 ", ""])
def test_existing_final_excluded(tmp_path, name, prefix):
    path = folder(tmp_path, prefix + "NTN 580", ["Recording.m4a", name])
    assert not inspect_episode(path).pending


@pytest.mark.parametrize("prefix", ["26 10 11 ", ""])
def test_mismatched_final_warns_and_excludes(tmp_path, prefix):
    path = folder(tmp_path, prefix + "NTN 580", ["Recording.m4a", "ntn581.mp3"])
    episode = inspect_episode(path)
    assert not episode.pending
    assert "no coincide" in episode.problems[0]


@pytest.mark.parametrize("names", [
    ["Recording.m4a", "Recoding.wav"],
    ["Recording (2).m4a"],
    ["Recording (1).m4a"],
    ["Recording.m4a", "Recording (3).m4a"],
    ["Recording.m4a", "Recording (0).m4a"],
])
@pytest.mark.parametrize("prefix", ["26 10 11 ", ""])
def test_arbitrary_recording_indices_are_allowed(tmp_path, names, prefix):
    episode = inspect_episode(folder(tmp_path, prefix + "NTN 580", names))
    assert episode.pending
    assert not episode.problems
    assert {path.name for path in episode.recordings} == set(names)


@pytest.mark.parametrize("name", ["nt580.mp3", "ntn580_final.mp3", "ntn580 (1).mp3",
                                 "ntn580-1.mp3", "interview.FLAC", "voice.OGG",
                                 "part.aac", "part.aiff", "part.wma"])
def test_arbitrary_audio_is_a_recording(tmp_path, name):
    episode = inspect_episode(folder(tmp_path, "NTN 580", [name]))
    assert episode.pending and not episode.finals
    assert [path.name for path in episode.recordings] == [name]


def test_natural_order_and_generated_eligibility(tmp_path):
    episode = inspect_episode(folder(tmp_path, "NTN 580", [
        "part 10.WAV", "part 2.wav", "part 1.wav", "ntn580.mp3",
        "ntn580-01.mp3", "notes.txt", "ntn580.mp3.part",
    ]))
    assert episode.selectable and not episode.pending
    assert [path.name for path in episode.recordings] == [
        "part 1.wav", "part 2.wav", "part 10.WAV"]
    assert len(episode.finals) == 2


def test_unrelated_mp3_and_invalid_date(tmp_path):
    path = folder(tmp_path, "26 10 11 NTN 580", ["Recording.wav", "music.mp3", "ntn580.mp3.part"])
    folder(tmp_path, "26 02 30 NTN 581", ["Recording.m4a"])
    episodes, warnings = discover_episodes(tmp_path)
    assert len(episodes) == 1 and episodes[0].pending
    assert episodes[0].path == path
    assert "26 02 30" in warnings[0]


def test_missing_root_and_access_error(tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError):
        discover_episodes(tmp_path / "missing")
    path = folder(tmp_path, "26 10 11 NTN 580", ["Recording.m4a"])
    original = Path.iterdir

    def denied(self):
        if self == path:
            raise PermissionError("denied")
        return original(self)

    monkeypatch.setattr(Path, "iterdir", denied)
    episodes, warnings = discover_episodes(tmp_path)
    assert not episodes and "denied" in warnings[0]
