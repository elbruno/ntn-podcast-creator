"""Local version allocation is independent of server RSS naming."""

import pytest

from features.episode_naming import reserve_local_output


@pytest.mark.parametrize("occupied,expected", [
    ([], "ntn123.mp3"),
    (["NTN123.MP3"], "ntn123-01.mp3"),
    (["ntn123.mp3", "ntn123-01.mp3"], "ntn123-02.mp3"),
    (["ntn123.mp3", "ntn123-02.mp3"], "ntn123-01.mp3"),
    (["ntn123.mp3.quality.json"], "ntn123-01.mp3"),
    (["ntn123_transcript.txt"], "ntn123-01.mp3"),
    (["ntn123_denoised.flac"], "ntn123-01.mp3"),
])
def test_local_versions_preserve_existing_files(tmp_path, occupied, expected):
    for name in occupied:
        (tmp_path / name).write_bytes(b"keep")
    with reserve_local_output(tmp_path, "ntn123") as path:
        assert path.name == expected
        assert (tmp_path / f".ntn-local-reservation-{path.stem}").exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(occupied)
    assert all(path.read_bytes() == b"keep" for path in tmp_path.iterdir())


def test_versions_beyond_99(tmp_path):
    (tmp_path / "ntn123.mp3").touch()
    for index in range(1, 100):
        (tmp_path / f"ntn123-{index:02d}.mp3").touch()
    with reserve_local_output(tmp_path, "ntn123") as path:
        assert path.name == "ntn123-100.mp3"


def test_reservation_is_exclusive_and_never_retires_other_marker(tmp_path):
    with reserve_local_output(tmp_path, "ntn123"):
        with pytest.raises(FileExistsError, match="Destino reservado"):
            with reserve_local_output(tmp_path, "ntn123"):
                pytest.fail("Must not acquire another client's reservation")
        assert (tmp_path / ".ntn-local-reservation-ntn123").exists()
    assert not list(tmp_path.iterdir())


def test_reservation_released_after_failure(tmp_path):
    with pytest.raises(RuntimeError, match="failed"):
        with reserve_local_output(tmp_path, "ntn123"):
            raise RuntimeError("failed")
    assert not list(tmp_path.iterdir())
