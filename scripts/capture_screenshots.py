"""
Playwright script to capture screenshots and create animated GIF of the NTN Podcast Creator app.

Usage:
1. Start the application: python app.py
2. Run this script: python scripts/capture_screenshots.py

Requirements:
- playwright (pip install playwright)
- playwright install chromium
- Pillow (pip install Pillow)
- Application running at http://localhost:7860
"""
import os
import sys
import time
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_DIR = Path(__file__).parent.parent
SCREENSHOTS_DIR = BASE_DIR / "docs" / "images" / "screenshots"
APP_URL = "http://localhost:7860"
SCREENSHOT_DELAY = 2  # seconds between screenshots for GIF

# Ensure screenshots directory exists
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Check dependencies
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright not installed. Please install it:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("❌ Pillow not installed. Please install it:")
    print("   pip install Pillow")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ requests not installed. Please install it:")
    print("   pip install requests")
    sys.exit(1)


async def capture_app_screenshots():
    """Capture screenshots of the application in various states."""

    async with async_playwright() as p:
        print("🚀 Starting browser...")
        browser = await p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        print(f"📱 Navigating to {APP_URL}...")
        try:
            await page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            # If domcontentloaded fails, try without wait_until
            print("   Retrying without strict wait condition...")
            await page.goto(APP_URL, timeout=60000)

        # Wait for Gradio interface to load
        print("   Waiting for Gradio interface to fully load...")
        await page.wait_for_timeout(5000)

        # Try to wait for main container if available
        try:
            await page.wait_for_selector('div[class*="container"]', timeout=10000)
        except Exception:
            pass  # Container might already be loaded or selector might be different

        screenshots = []

        # Screenshot 1: Initial view
        print("📸 Screenshot 1: Initial application view...")
        screenshot_path = SCREENSHOTS_DIR / "01-initial-view.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        print(f"   Saved: {screenshot_path}")
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 2: Show voice file upload area
        print("📸 Screenshot 2: Voice file upload area...")
        # Scroll to voice upload if needed
        await page.evaluate("window.scrollTo(0, 200)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "02-voice-upload.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 3: Intro/Outro section
        print("📸 Screenshot 3: Intro/Outro selection...")
        await page.evaluate("window.scrollTo(0, 600)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "03-intro-outro.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 4: Background music section
        print("📸 Screenshot 4: Background music section...")
        await page.evaluate("window.scrollTo(0, 1000)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "04-background-music.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 5: Audio processing options
        print("📸 Screenshot 5: Audio processing options...")
        await page.evaluate("window.scrollTo(0, 1400)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "05-audio-processing.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 6: LUFS normalization
        print("📸 Screenshot 6: LUFS normalization...")
        await page.evaluate("window.scrollTo(0, 1800)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "06-lufs-normalization.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 7: Transcription options
        print("📸 Screenshot 7: Transcription options...")
        await page.evaluate("window.scrollTo(0, 2200)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "07-transcription.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 8: Create button and output
        print("📸 Screenshot 8: Create button and output...")
        await page.evaluate("window.scrollTo(0, 2600)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "08-create-button.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)
        screenshots.append(screenshot_path)
        await page.wait_for_timeout(SCREENSHOT_DELAY * 1000)

        # Screenshot 9: Full page overview
        print("📸 Screenshot 9: Full page overview...")
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)
        screenshot_path = SCREENSHOTS_DIR / "09-full-overview.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        screenshots.append(screenshot_path)

        # Screenshot 10: Standalone Denoiser tab (if exists)
        print("📸 Screenshot 10: Checking for standalone denoiser tab...")
        # Try to find and click standalone denoiser tab
        try:
            denoiser_tab = await page.query_selector('text="Standalone AI Denoiser"')
            if denoiser_tab:
                await denoiser_tab.click()
                await page.wait_for_timeout(2000)
                screenshot_path = SCREENSHOTS_DIR / "10-standalone-denoiser.png"
                await page.screenshot(path=str(screenshot_path), full_page=False)
                screenshots.append(screenshot_path)
                print(f"   Saved: {screenshot_path}")
        except Exception as e:
            print(f"   Could not capture standalone denoiser tab: {e}")

        # Screenshot 11: Settings tab (if exists)
        print("📸 Screenshot 11: Checking for settings tab...")
        try:
            # Go back to first tab
            podcast_tab = await page.query_selector('text="Podcast Creator"')
            if podcast_tab:
                await podcast_tab.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass

        print(f"\n✅ Captured {len(screenshots)} screenshots successfully!")
        print(f"📁 Screenshots saved to: {SCREENSHOTS_DIR}")

        await browser.close()

        return screenshots


async def create_animated_gif():
    """Create an animated GIF showing the application workflow."""
    print("\n🎬 Creating animated GIF...")

    try:
        from PIL import Image
        import glob

        # Get all screenshots in order
        screenshot_files = sorted(glob.glob(str(SCREENSHOTS_DIR / "*.png")))

        if not screenshot_files:
            print("❌ No screenshots found to create GIF")
            return None

        print(f"📸 Found {len(screenshot_files)} screenshots")

        # Load images
        images = []
        for img_path in screenshot_files:
            img = Image.open(img_path)
            # Resize to reasonable size for GIF (max width 1200px)
            if img.width > 1200:
                ratio = 1200 / img.width
                new_size = (1200, int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            images.append(img)

        # Save as animated GIF
        gif_path = BASE_DIR / "docs" / "images" / "app-demo.gif"

        # Durations: show each frame for 3 seconds (3000ms), last frame for 5 seconds
        durations = [3000] * (len(images) - 1) + [5000]

        images[0].save(
            gif_path,
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0,  # Loop forever
            optimize=False  # Keep quality
        )

        print(f"✅ Animated GIF created: {gif_path}")
        print(f"   Size: {gif_path.stat().st_size / (1024*1024):.2f} MB")
        print(f"   Frames: {len(images)}")

        return gif_path

    except ImportError:
        print("❌ PIL/Pillow not installed. Installing...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip",
                       "install", "Pillow"], check=True)
        print("✅ Pillow installed. Please run the script again.")
        return None
    except Exception as e:
        print(f"❌ Error creating GIF: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main execution function."""
    print("=" * 70)
    print("📷 NTN Podcast Creator - Screenshot Capture Tool")
    print("=" * 70)
    print()

    # Check if app is running
    import requests
    try:
        response = requests.get(APP_URL, timeout=5)
        if response.status_code != 200:
            print(f"❌ App not responding correctly at {APP_URL}")
            print("   Please start the application first: python app.py")
            return
    except Exception as e:
        print(f"❌ Cannot connect to app at {APP_URL}")
        print(f"   Error: {e}")
        print("   Please start the application first: python app.py")
        return

    print(f"✅ App is running at {APP_URL}\n")

    # Capture screenshots
    await capture_app_screenshots()

    # Create animated GIF
    gif_path = await create_animated_gif()

    print("\n" + "=" * 70)
    print("🎉 Screenshot capture complete!")
    print("=" * 70)
    print(f"\n📁 Screenshots directory: {SCREENSHOTS_DIR}")
    if gif_path:
        print(f"🎬 Animated GIF: {gif_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
