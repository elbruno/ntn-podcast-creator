"""Adobe Audio Enhancer integration for podcast audio cleanup."""

import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional, Callable, Any

try:  # pragma: no cover - optional helper for local dev
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback when python-dotenv is missing
    load_dotenv = lambda *args, **kwargs: None  # type: ignore


# Load environment variables (no-op if python-dotenv isn't installed)
load_dotenv()


class AdobeAudioEnhancer:
    """Handles audio enhancement using Adobe's Enhance Speech tool.

    This class provides integration with Adobe Podcast Enhance Speech
    (https://podcast.adobe.com/enhance) to clean and enhance audio files
    before podcast creation.

    Note: This implementation uses browser automation via Playwright MCP server
    to upload audio files, wait for processing, and download enhanced results.
    """

    def __init__(self, playwright_available: bool = True):
        """Initialize the Adobe Audio Enhancer.

        Args:
            playwright_available: Whether Playwright browser automation is available
        """
        self.playwright_available = playwright_available
        self.enhance_url = "https://podcast.adobe.com/enhance"

    def is_available(self) -> bool:
        """Check if the enhancement service is available.

        Returns:
            True if the service can be used, False otherwise
        """
        return self.playwright_available

    def enhance_audio(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        timeout_seconds: int = 300,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Enhance audio file using Adobe Podcast Enhance Speech.

        This method uploads the audio file to Adobe Enhance, waits for processing,
        and downloads the enhanced result.

        Args:
            input_file: Path to input audio file
            output_file: Path for enhanced output (auto-generated if None)
            timeout_seconds: Maximum time to wait for enhancement (default: 300s)
            log_callback: Optional callback function for logging

        Returns:
            Path to enhanced audio file, or None if enhancement fails

        Raises:
            FileNotFoundError: If input file doesn't exist
            TimeoutError: If enhancement takes longer than timeout_seconds
            Exception: If enhancement fails for other reasons
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        # Validate input file
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Generate output file path if not provided
        if output_file is None:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(
                os.path.dirname(input_file),
                f"{base_name}_enhanced.mp3"
            )

        log(f"Starting audio enhancement for: {os.path.basename(input_file)}")

        # Check if service is available
        if not self.is_available():
            log("Warning: Adobe Enhance service not available, skipping enhancement")
            # Copy original file to output location
            shutil.copy2(input_file, output_file)
            return output_file

        try:
            # In a real implementation, this would use Playwright MCP server tools
            # to automate the browser interaction with Adobe Enhance
            enhanced_path = self._enhance_with_browser(
                input_file,
                output_file,
                timeout_seconds,
                log_callback
            )

            if enhanced_path and os.path.exists(enhanced_path):
                log(
                    f"✓ Audio enhancement complete: {os.path.basename(enhanced_path)}")
                return enhanced_path
            else:
                log("Enhancement failed, using original audio")
                shutil.copy2(input_file, output_file)
                return output_file

        except Exception as e:
            log(f"Error during enhancement: {e}")
            log("Falling back to original audio")
            shutil.copy2(input_file, output_file)
            return output_file

    def _enhance_with_browser(
        self,
        input_file: str,
        output_file: str,
        timeout_seconds: int,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """Enhance audio using browser automation (Playwright MCP).

        This method would use the Playwright MCP server tools to:
        1. Navigate to Adobe Enhance website
        2. Upload the audio file
        3. Wait for processing to complete
        4. Download the enhanced audio

        Args:
            input_file: Path to input audio file
            output_file: Path for enhanced output
            timeout_seconds: Maximum time to wait for enhancement
            log_callback: Optional callback function for logging

        Returns:
            Path to enhanced audio file, or None if enhancement fails
        """
        def log(message: str):
            if log_callback:
                log_callback(message)
            else:
                print(message)

        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
        except ImportError as exc:
            log("✗ Playwright is not installed. Run 'pip install playwright' followed by 'playwright install chromium'.")
            raise RuntimeError("Playwright dependency missing") from exc

        headless = os.environ.get("ADOBE_ENHANCE_HEADLESS", "true").lower() not in {
            "0", "false", "no"}
        email = os.environ.get("ADOBE_EMAIL")
        password = os.environ.get("ADOBE_PASSWORD")

        if email and password:
            log("Adobe credentials detected in environment variables. Will attempt automatic sign-in if prompted.")
        else:
            log("No Adobe credentials configured. Set ADOBE_EMAIL and ADOBE_PASSWORD if login is required.")

        file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
        log(f"Preparing to upload {os.path.basename(input_file)} ({file_size_mb:.2f} MB) to Adobe Enhance (timeout: {timeout_seconds}s)")

        start_time = time.time()
        deadline = start_time + max(timeout_seconds, 60)

        def remaining_time_ms() -> int:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise TimeoutError("Adobe Enhance processing timed out")
            # Always provide at least 1 second to Playwright operations
            return max(int(remaining * 1000), 1000)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            context = browser.new_context(accept_downloads=True)
            try:
                page = context.new_page()

                log(f"Navigating to {self.enhance_url} ...")
                page.goto(self.enhance_url, wait_until="domcontentloaded",
                          timeout=remaining_time_ms())
                self._try_dismiss_banner(page, log)

                if self._page_requires_login(page):
                    self._perform_login(
                        page=page,
                        email=email,
                        password=password,
                        log=log,
                        remaining_time_ms=remaining_time_ms,
                        playwright_timeout=PlaywrightTimeoutError
                    )

                upload_input = page.locator("input[type='file']")
                upload_input.wait_for(
                    state="attached", timeout=remaining_time_ms())
                log("Uploading file to Adobe Enhance...")
                upload_input.set_input_files(input_file)

                log("Waiting for Adobe Enhance to finish processing (this usually takes 2-5 minutes)...")
                enhanced_path = self._wait_for_processing_and_download(
                    page=page,
                    output_file=str(output_path),
                    log=log,
                    remaining_time_ms=remaining_time_ms,
                    playwright_timeout=PlaywrightTimeoutError
                )

                elapsed = time.time() - start_time
                log(f"Adobe Enhance completed in {elapsed:.1f} seconds")
                return enhanced_path
            finally:
                context.close()
                browser.close()

    def _page_requires_login(self, page: Any) -> bool:
        """Detect if Adobe prompts for authentication."""
        try:
            if any(token in page.url.lower() for token in ["login", "auth.adobe", "fed.adobe"]):
                return True
            email_inputs = page.locator("input[type='email']")
            return email_inputs.count() > 0
        except Exception:
            return False

    def _perform_login(
        self,
        page: Any,
        email: Optional[str],
        password: Optional[str],
        log: Callable[[str], None],
        remaining_time_ms: Callable[[], int],
        playwright_timeout: Any
    ) -> None:
        """Handle Adobe login flow if credentials are provided."""
        if not email or not password:
            log("Adobe login detected but ADOBE_EMAIL / ADOBE_PASSWORD are not set.")
            log("Set these environment variables (or update .env) so automation can sign in.")
            raise PermissionError(
                "Missing Adobe credentials for Enhance login")

        log("Adobe login page detected. Attempting automated sign-in...")

        try:
            email_field = page.locator("input[type='email']").first
            email_field.wait_for(state="visible", timeout=remaining_time_ms())
            email_field.fill(email)
        except playwright_timeout as exc:
            raise RuntimeError(
                "Unable to locate Adobe email input field") from exc

        self._click_continue(page, remaining_time_ms, playwright_timeout)

        try:
            password_field = page.locator("input[type='password']").first
            password_field.wait_for(
                state="visible", timeout=remaining_time_ms())
            password_field.fill(password)
        except playwright_timeout as exc:
            raise RuntimeError(
                "Unable to locate Adobe password input field") from exc

        self._click_continue(page, remaining_time_ms, playwright_timeout)

        try:
            page.wait_for_url(re.compile(r"enhance"),
                              timeout=remaining_time_ms())
        except playwright_timeout:
            # Some accounts require MFA; fall back to waiting for load state
            page.wait_for_load_state(
                "networkidle", timeout=remaining_time_ms())

        log("Adobe login completed successfully.")

    def _click_continue(
        self,
        page: Any,
        remaining_time_ms: Callable[[], int],
        playwright_timeout: Any
    ) -> None:
        """Click the most likely Continue/Sign-in button on Adobe auth screens."""
        button = page.get_by_role(
            "button",
            name=re.compile(
                r"(Continue|Next|Sign in|Submit|Log in)", re.IGNORECASE)
        )
        try:
            target = button.first
            target.wait_for(state="visible", timeout=remaining_time_ms())
            target.click()
        except playwright_timeout as exc:
            raise RuntimeError(
                "Cannot find Adobe Continue/Sign-in button") from exc

    def _try_dismiss_banner(self, page: Any, log: Callable[[str], None]) -> None:
        """Dismiss cookie or beta banners that may block interactions."""
        try:
            banner_button = page.get_by_role(
                "button",
                name=re.compile(
                    r"(Accept all|Accept|Dismiss|Okay)", re.IGNORECASE)
            )
            if banner_button.count() > 0 and banner_button.first.is_visible():
                banner_button.first.click()
                log("Dismissed Adobe cookie/consent banner")
        except Exception:
            # Non-blocking if banner isn't present
            return

    def _wait_for_processing_and_download(
        self,
        page: Any,
        output_file: str,
        log: Callable[[str], None],
        remaining_time_ms: Callable[[], int],
        playwright_timeout: Any
    ) -> str:
        """Poll until the Download button is ready, then grab the enhanced file."""
        download_button = page.get_by_role(
            "button", name=re.compile(r"Download", re.IGNORECASE)).first

        try:
            download_button.wait_for(
                state="visible", timeout=remaining_time_ms())
        except playwright_timeout as exc:
            raise TimeoutError(
                "Adobe Enhance never exposed a Download button") from exc

        # Poll until Adobe finishes processing (button becomes enabled)
        self._poll_until_enabled(download_button, remaining_time_ms, log)

        log("Download button enabled. Requesting enhanced audio...")
        with page.expect_download(timeout=remaining_time_ms()) as download_info:
            download_button.click()

        download = download_info.value
        suggested = download.suggested_filename or os.path.basename(
            output_file)
        destination = Path(output_file)
        download.save_as(str(destination))
        log(f"Downloaded enhanced audio ({suggested}) -> {destination}")

        return str(destination)

    def _poll_until_enabled(
        self,
        locator: Any,
        remaining_time_ms: Callable[[], int],
        log: Callable[[str], None],
        interval_seconds: int = 5
    ) -> None:
        """Poll a locator until it is enabled or the timeout expires."""
        while True:
            # This call will raise TimeoutError if we've exceeded the deadline
            remaining_time_ms()

            try:
                if locator.is_enabled():
                    return
            except Exception:
                # Ignore transient DOM refresh issues
                pass

            log("Adobe is still enhancing audio... checking again shortly")
            sleep_time = min(interval_seconds, max(
                1, remaining_time_ms() // 1000))
            time.sleep(sleep_time)


def enhance_audio_file(
    input_file: str,
    output_file: Optional[str] = None,
    enabled: bool = True,
    timeout_seconds: int = 300,
    log_callback: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Convenience function to enhance an audio file.

    Args:
        input_file: Path to input audio file
        output_file: Path for enhanced output (auto-generated if None)
        enabled: Whether enhancement is enabled (if False, returns original)
        timeout_seconds: Maximum time to wait for enhancement
        log_callback: Optional callback function for logging

    Returns:
        Path to enhanced audio file (or original if enhancement disabled/failed)
    """
    def log(message: str):
        if log_callback:
            log_callback(message)
        else:
            print(message)

    if not enabled:
        log("Audio enhancement is disabled")
        return input_file

    try:
        enhancer = AdobeAudioEnhancer()
        return enhancer.enhance_audio(
            input_file,
            output_file,
            timeout_seconds,
            log_callback
        )
    except Exception as e:
        log(f"Enhancement failed: {e}")
        return input_file
