"""Real browser regression for visible, single-click episode checkboxes."""

import socket
import wave
from pathlib import Path

import pytest

from tests.test_episode_ui import ui, screen


def test_episode_checkboxes_click_and_keyboard_toggle(ui, screen, tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runner:
        if not Path(runner.chromium.executable_path).is_file():
            pytest.skip("Playwright Chromium is not installed")
        paths = []
        for name in ("Recording.wav", "Second.wav"):
            path = tmp_path / name
            with wave.open(str(path), "wb") as stream:
                stream.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                stream.writeframes(b"\0\0" * 8000)
            paths.append(str(path))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        screen.launch(server_name="127.0.0.1", server_port=port,
                      prevent_thread_lock=True, quiet=True)
        browser = runner.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{port}")
            page.locator("#episode-hero input[type=file]").set_input_files(paths)
            page.locator("#episode-options").wait_for(state="visible")
            page.locator("#episode-options > button").click()
            master = page.get_by_role("checkbox", name="Add background music", exact=True)
            assert not master.is_checked()
            master.click()
            assert master.is_checked()
            assert master.evaluate("(e) => getComputedStyle(e).appearance") == "auto"
            master.press("Space")
            assert not master.is_checked()
            for name, initial in (("Recording.wav", True), ("Second.wav", False)):
                checkbox = page.get_by_role("checkbox", name=name, exact=True)
                assert checkbox.is_checked() is initial
                checkbox.click()
                assert checkbox.is_checked() is not initial
                checkbox.press("Space")
                assert checkbox.is_checked() is initial
            page.get_by_role("tab", name="Settings", exact=True).click()
            setting = page.get_by_role("checkbox", name="Intro-voice overlap (1 second)", exact=True)
            before = setting.is_checked()
            setting.click()
            assert setting.is_checked() is not before
            assert setting.evaluate("(e) => getComputedStyle(e).appearance") == "auto"
        finally:
            browser.close()
