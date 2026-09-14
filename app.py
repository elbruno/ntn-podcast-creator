"""Main application for NTN Podcast Creator with Gradio UI."""

import os
import shutil
import datetime
import re
import json
import html
import math
import time
import tempfile
from copy import deepcopy
from dataclasses import asdict, fields, replace
import urllib.request
import xml.etree.ElementTree as ET
import gradio as gr
from typing import Optional, List, Tuple, Dict, Any
from features.audio_processor import (
    AudioProcessor, _quality_file_identity, _quality_preview_identity,
    _register_quality_preview, _cleanup_quality_preview,
    _read_quality_sidecar, _write_quality_sidecar,
)
from features.config_manager import ConfigManager, DEFAULT_RSS_FEED_URL
from features.audio_denoiser_processor import denoise_audio_file
from features.template_manager import TemplateManager
from features.audio_quality import AudioQualityConfig, AudioQualityReport


# Initialize components
config_manager = ConfigManager()
audio_processor = AudioProcessor()
template_manager = TemplateManager()

# Create necessary directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("audios/intro_audio", exist_ok=True)
os.makedirs("audios/outro_audio", exist_ok=True)
os.makedirs("audios/background_music", exist_ok=True)

# Load default audio files from dedicated folders
config_manager.load_default_audio_files()

# Store uploaded background tracks
background_tracks_list = []

# Cache for RSS feed lookups
rss_cache = {"url": None, "last_title": None, "next_slug": None, "error": None}


# Global variable for console log
console_log = []
# Global variable for real-time log updates
realtime_log_queue = []


def get_audio_duration(file_path: str) -> str:
    """Get audio duration in MM:SS format.

    Args:
        file_path: Path to audio file

    Returns:
        Duration string in MM:SS format or 'N/A' on error
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        duration_seconds = len(audio) / 1000
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    except Exception as e:
        log_message(f"Error getting duration for {file_path}: {e}")
        return "N/A"


def get_audio_duration_seconds(file_path: str) -> float:
    """Get audio duration in seconds.

    Args:
        file_path: Path to audio file

    Returns:
        Duration in seconds or 0.0 on error
    """
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0
    except Exception as e:
        log_message(f"Error getting duration for {file_path}: {e}")
        return 0.0


def generate_timeline_chart(voice_file, intro_file: Optional[str],
                            outro_file: Optional[str], has_background: bool,
                            background_tracks: Optional[List[str]] = None,
                            track_volumes: Optional[dict] = None,
                            voice_background_flags: Optional[List[bool]] = None) -> str:
    """Generate a visual timeline chart showing how audio segments are organized.

    Args:
        voice_file: Path to voice recording or list of paths
        intro_file: Path to intro audio
        outro_file: Path to outro audio
        has_background: Whether background music will be applied
        background_tracks: List of background track paths
        track_volumes: Dictionary mapping track paths to volumes
        voice_background_flags: Per-voice-file booleans indicating whether
            background should be applied on each uploaded voice track

    Returns:
        HTML string with timeline visualization
    """
    if not voice_file:
        return "<div style='padding: 20px; text-align: center; color: #666;'>Upload a voice recording to preview timeline</div>"

    # Handle multiple voice files
    voice_files = voice_file if isinstance(voice_file, list) else [voice_file]

    # Normalize per-file background flags (default True for all files)
    if voice_background_flags and isinstance(voice_background_flags, list):
        normalized_bg_flags = [
            bool(v) for v in voice_background_flags[:len(voice_files)]]
    else:
        normalized_bg_flags = []
    if len(normalized_bg_flags) < len(voice_files):
        normalized_bg_flags.extend(
            [True] * (len(voice_files) - len(normalized_bg_flags)))

    # Calculate total voice duration from all files
    voice_duration = 0.0
    for vf in voice_files:
        if vf:
            voice_duration += get_audio_duration_seconds(vf)

    # Get durations
    intro_duration = get_audio_duration_seconds(
        intro_file) if intro_file else 0.0
    outro_duration = get_audio_duration_seconds(
        outro_file) if outro_file else 0.0

    # Calculate total with overlaps (2 seconds total: 1s intro-voice + 1s voice-outro)
    overlap_seconds = 0.0
    if intro_duration > 0 and voice_duration > 0:
        overlap_seconds += 1.0  # intro-voice overlap
    if voice_duration > 0 and outro_duration > 0:
        overlap_seconds += 1.0  # voice-outro overlap

    total_duration = intro_duration + voice_duration + outro_duration - overlap_seconds

    if total_duration == 0:
        return "<div style='padding: 20px; text-align: center; color: #666;'>No audio files to preview</div>"

    # Calculate percentages
    intro_percent = (intro_duration / total_duration) * \
        100 if intro_duration > 0 else 0
    voice_percent = (voice_duration / total_duration) * \
        100 if voice_duration > 0 else 0
    outro_percent = (outro_duration / total_duration) * \
        100 if outro_duration > 0 else 0

    # Format durations
    def format_time(seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    # Build HTML visualization
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; border-radius: 8px;">
        <h3 style="margin-top: 0; color: #333;">📊 Podcast Timeline Preview</h3>
        <div style="margin: 20px 0;">
            <div style="font-size: 14px; color: #666; margin-bottom: 10px;">
                Total Duration: <strong>{format_time(total_duration)}</strong>
                {' (with 1s overlaps)' if overlap_seconds > 0 else ''}
            </div>
            <div style="position: relative; height: 80px;">
                <!-- Main timeline -->
                <div style="display: flex; height: 60px; border-radius: 4px; overflow: visible; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
    """

    # Add intro segment
    if intro_duration > 0:
        html += f"""
                    <div style="width: {intro_percent}%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                         display: flex; align-items: center; justify-content: center; color: white;
                         font-size: 12px; font-weight: bold; border-right: 2px solid white; position: relative;">
                        <div style="text-align: center; padding: 5px;">
                            <div>INTRO</div>
                            <div style="font-size: 10px; opacity: 0.9;">{format_time(intro_duration)}</div>
                        </div>
                        {"<div style='position: absolute; right: -10px; top: 0; bottom: 0; width: 20px; background: rgba(255,255,255,0.3); z-index: 10;'></div>" if voice_duration > 0 else ""}
                    </div>
        """

    # Add voice segments - show individual files when multiple are present
    if voice_duration > 0:
        # Calculate individual file durations and percentages
        voice_file_durations = []
        for vf in voice_files:
            if vf:
                duration = get_audio_duration_seconds(vf)
                percent = (duration / total_duration) * 100
                use_background = normalized_bg_flags[len(voice_file_durations)] if len(
                    normalized_bg_flags) > len(voice_file_durations) else True
                voice_file_durations.append(
                    (vf, duration, percent, use_background))

        # Color palette for voice recordings (varying shades of pink/red)
        voice_colors = [
            "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
            "linear-gradient(135deg, #fa709a 0%, #fee140 100%)",
            "linear-gradient(135deg, #ff6a88 0%, #ff99ac 100%)",
            "linear-gradient(135deg, #fc6767 0%, #ec008c 100%)",
            "linear-gradient(135deg, #ff758c 0%, #ff7eb3 100%)"
        ]

        for idx, (vf_path, duration, percent, use_background) in enumerate(voice_file_durations):
            color = voice_colors[idx % len(voice_colors)]
            filename = os.path.basename(vf_path)
            # Shorten filename if too long
            display_name = filename if len(
                filename) <= 20 else filename[:17] + "..."

            # Determine if we show overlap indicators
            show_left_overlap = (intro_duration > 0 and idx == 0) or idx > 0
            show_right_overlap = (outro_duration > 0 and idx == len(
                voice_file_durations) - 1) or idx < len(voice_file_durations) - 1

            html += f"""
                    <div style="width: {percent}%; background: {color};
                         display: flex; align-items: center; justify-content: center; color: white;
                         font-size: 10px; font-weight: bold; border-right: 2px solid white; position: relative; overflow: hidden;">
                        <div style="text-align: center; padding: 2px; line-height: 1.2;">
                            <div style="font-size: 11px;">{display_name}</div>
                            <div style="font-size: 9px; opacity: 0.9;">{format_time(duration)}</div>
                            <div style="font-size: 8px; opacity: 0.95;">{'🎵 BG ON' if has_background and use_background else '🎵 BG OFF'}</div>
                        </div>
                        {"<div style='position: absolute; left: -10px; top: 0; bottom: 0; width: 20px; background: rgba(255,255,255,0.3); z-index: 10;'></div>" if show_left_overlap else ""}
                        {"<div style='position: absolute; right: -10px; top: 0; bottom: 0; width: 20px; background: rgba(255,255,255,0.3); z-index: 10;'></div>" if show_right_overlap else ""}
                    </div>
            """

    # Add outro segment
    if outro_duration > 0:
        html += f"""
                    <div style="width: {outro_percent}%; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                         display: flex; align-items: center; justify-content: center; color: white;
                         font-size: 12px; font-weight: bold; position: relative;">
                        <div style="text-align: center; padding: 5px;">
                            <div>OUTRO</div>
                            <div style="font-size: 10px; opacity: 0.9;">{format_time(outro_duration)}</div>
                        </div>
                        {"<div style='position: absolute; left: -10px; top: 0; bottom: 0; width: 20px; background: rgba(255,255,255,0.3); z-index: 10;'></div>" if voice_duration > 0 else ""}
                    </div>
        """

    html += """
                </div>
    """

    # Add background music layer on top of voice section
    if has_background and voice_duration > 0:
        if len(voice_files) == 1:
            # Single voice track: show one overlay only if enabled
            if normalized_bg_flags[0]:
                bg_start_percent = intro_percent
                bg_width_percent = voice_percent

                html += f"""
                <!-- Background music layer -->
                <div style="position: absolute; left: {bg_start_percent}%; width: {bg_width_percent}%; top: 0; height: 20px;
                     background: repeating-linear-gradient(45deg, #FFD700, #FFD700 10px, #FFA500 10px, #FFA500 20px);
                     border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 10px; font-weight: bold; color: #333; text-shadow: 1px 1px 2px rgba(255,255,255,0.8);">🎵 BACKGROUND MUSIC</span>
                </div>
                """
        else:
            # Multiple voice tracks: show overlay only on enabled segments
            voice_start_percent = intro_percent
            for _, _, segment_percent, use_background in voice_file_durations:
                if use_background:
                    html += f"""
                <!-- Background music segment layer -->
                <div style="position: absolute; left: {voice_start_percent}%; width: {segment_percent}%; top: 0; height: 20px;
                     background: repeating-linear-gradient(45deg, #FFD700, #FFD700 10px, #FFA500 10px, #FFA500 20px);
                     border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.2); display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 9px; font-weight: bold; color: #333; text-shadow: 1px 1px 2px rgba(255,255,255,0.8);">🎵 BG</span>
                </div>
                    """
                voice_start_percent += segment_percent

    html += """
            </div>
        </div>
    """

    html += """
            <div style="margin-top: 25px; padding: 10px; background: white; border-radius: 4px; font-size: 13px;">
                <div style="margin-bottom: 5px;"><strong>Legend:</strong></div>
    """

    if intro_duration > 0:
        html += "<div style='margin: 3px 0;'>🟣 <strong>INTRO</strong> - Plays first (no background music)</div>"

    if voice_duration > 0:
        if len(voice_files) > 1:
            html += f"<div style='margin: 3px 0;'>🔴 <strong>VOICE RECORDINGS</strong> - {len(voice_files)} file(s), total {format_time(voice_duration)}"
            if has_background:
                html += " (see background music layer above)"
            html += "</div>"
            # List individual files
            for idx, (vf_path, duration, _, use_background) in enumerate(voice_file_durations, start=1):
                filename = os.path.basename(vf_path)
                bg_status = "🎵 BG ON" if has_background and use_background else "🎵 BG OFF"
                html += f"<div style='margin-left: 15px; font-size: 12px;'>• {filename} - {format_time(duration)} - {bg_status}</div>"
        else:
            html += "<div style='margin: 3px 0;'>🔴 <strong>VOICE</strong> - Your recording"
            if has_background and normalized_bg_flags[0]:
                html += " (see background music layer above)"
            elif has_background and not normalized_bg_flags[0]:
                html += " (background music disabled for this track)"
            html += "</div>"

    if outro_duration > 0:
        html += "<div style='margin: 3px 0;'>🔵 <strong>OUTRO</strong> - Plays last (no background music)</div>"
    if has_background and voice_duration > 0:
        enabled_count = sum(1 for enabled in normalized_bg_flags if enabled)
        if len(voice_files) > 1:
            html += f"<div style='margin: 3px 0;'>🎵 <strong>BACKGROUND MUSIC</strong> - Enabled on {enabled_count}/{len(voice_files)} voice track(s)</div>"
        elif normalized_bg_flags[0]:
            html += "<div style='margin: 3px 0;'>🎵 <strong>BACKGROUND MUSIC</strong> - Plays during voice recording</div>"
        else:
            html += "<div style='margin: 3px 0;'>🎵 <strong>BACKGROUND MUSIC</strong> - Disabled for this voice track</div>"

        # Show background tracks with volumes
        if background_tracks and len(background_tracks) > 0:
            html += "<div style='margin-top: 10px; padding: 8px; background: #f8f9fa; border-radius: 3px;'>"
            html += "<div style='font-size: 12px; font-weight: bold; margin-bottom: 5px;'>🎼 Background Tracks:</div>"
            for track in background_tracks:
                if os.path.exists(track):
                    track_name = os.path.basename(track)
                    volume = track_volumes.get(track, config_manager.get_volume(
                    )) if track_volumes else config_manager.get_volume()
                    html += f"<div style='font-size: 11px; margin-left: 10px;'>• {track_name} - Volume: {volume}%</div>"
            html += "</div>"

    if overlap_seconds > 0:
        html += "<div style='margin: 3px 0; padding: 5px; background: #fff3cd; border-radius: 3px;'>⚡ <strong>Overlaps:</strong> 1-second smooth transitions between segments (shown as lighter areas)</div>"

    html += """
            </div>
        </div>
    </div>
    """

    return html


def log_message(message: str):
    """Add message to console log with timestamp."""
    import datetime
    global console_log, realtime_log_queue
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    console_log.append(formatted_message)
    realtime_log_queue.append(formatted_message)
    print(formatted_message)


def get_console_log() -> str:
    """Get console log as string."""
    global console_log
    return "\n".join(console_log) if console_log else "No logs yet"


def _legacy_bottom_console_html(console_text: str, visible: bool = True, show_close: bool = False, download_path: Optional[str] = None) -> str:
    """Generate bottom console HTML.

    Args:
        console_text: The console log text to display
        visible: Whether the console should be visible
        show_close: Whether to show the close button
        download_path: Optional file path for a download link

    Returns:
        HTML string for bottom console
    """
    # Show console even if empty, with a placeholder message
    if not console_text.strip():
        display_text = "Initializing..."
    else:
        # Get last 10 lines for the bottom console to avoid overload
        lines = console_text.strip().split('\n')
        last_lines = lines[-10:] if len(lines) > 10 else lines
        display_text = '\n'.join(last_lines)

    # Escape HTML characters
    display_text = (display_text
                    .replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
                    .replace('"', '&quot;')
                    .replace("'", '&#x27;'))

    close_button_html = ""
    if show_close:
        close_button_html = '<button class="close-btn" onclick="this.parentElement.parentElement.style.display=\'none\'">✖ Close</button>'

    display_style = "block" if visible else "none"

    download_html = ""
    if download_path and os.path.exists(download_path):
        download_href = f"file={download_path}"
        download_html = f"""
        <div style=\"margin-top: 8px;\">
            <a href=\"{download_href}\" download style=\"color: #8ab4f8; text-decoration: underline;\">⬇️ Download episode audio</a>
        </div>
        """

    return f"""
    <div style="position: fixed; bottom: 0; left: 0; right: 0; z-index: 9998; background: #1e1e1e; border-top: 2px solid #333; box-shadow: 0 -2px 4px rgba(0,0,0,0.3); max-height: 200px; overflow-y: auto; display: {display_style} !important; width: 100%;">
        <div style="background: #333; color: white; padding: 8px 20px; font-weight: bold; border-bottom: 1px solid #555; font-size: 14px; display: flex; justify-content: space-between; align-items: center;">
            <span>📋 Processing Log (Live Updates)</span>
            {close_button_html}
        </div>
        <div style="font-family: 'Courier New', monospace; background: #1e1e1e; color: #ffffff; padding: 10px 20px; font-size: 12px; line-height: 1.4; white-space: pre-wrap; max-height: 150px; overflow-y: auto;">
{display_text}
{download_html}
        </div>
    </div>
    """


def get_realtime_log() -> str:
    """Get real-time console log as string."""
    global realtime_log_queue
    if realtime_log_queue:
        # Return all queued messages and clear the queue
        messages = "\n".join(realtime_log_queue)
        realtime_log_queue.clear()
        return messages
    return ""


def clear_console_log():
    """Clear console log."""
    global console_log, realtime_log_queue
    console_log = []
    realtime_log_queue = []
    return "Console log cleared"


def resolve_intro_override_preview(intro_override_file) -> Optional[str]:
    """Resolve a one-time intro override path for preview purposes."""
    if not intro_override_file:
        return None

    if isinstance(intro_override_file, str):
        path = intro_override_file
    elif hasattr(intro_override_file, 'name'):
        path = intro_override_file.name
    else:
        path = str(intro_override_file)

    return path if os.path.exists(path) else None


def preview_timeline(voice_file, intro_override_file=None, voice_background_flags: Optional[List[bool]] = None) -> str:
    """Generate timeline preview.

    Args:
        voice_file: Path to voice recording or list of paths
        intro_override_file: Optional uploaded file to override intro

    Returns:
        HTML timeline chart
    """
    intro_file = resolve_intro_override_preview(
        intro_override_file) or config_manager.get_intro()
    outro_file = config_manager.get_outro()
    background_tracks = config_manager.get_background_tracks()
    track_volumes = config_manager.get_all_track_volumes()
    has_background = background_tracks is not None and len(
        background_tracks) > 0

    return generate_timeline_chart(voice_file, intro_file, outro_file, has_background, background_tracks, track_volumes, voice_background_flags)


def save_uploaded_file(uploaded_file, prefix: str = "file") -> Optional[str]:
    """Save uploaded file to uploads directory.

    Args:
        uploaded_file: Gradio uploaded file object or string path
        prefix: Prefix for filename

    Returns:
        Path to saved file or None
    """
    if uploaded_file is None:
        return None

    # Handle Gradio 6.0 string path
    if isinstance(uploaded_file, str):
        source_path = uploaded_file
        original_name = os.path.basename(uploaded_file)
    elif hasattr(uploaded_file, 'name'):
        source_path = uploaded_file.name
        original_name = os.path.basename(uploaded_file.name)
    else:
        log_message(f"Warning: Unknown file type for {prefix}")
        original_name = f"{prefix}.mp3"
        source_path = str(uploaded_file)

    # Create destination path
    dest_path = os.path.join("uploads", original_name)

    try:
        # Copy file to uploads directory
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            log_message(f"Saved {prefix} file: {original_name}")
        else:
            log_message(f"Error: Source file not found: {source_path}")
            return None
    except Exception as e:
        log_message(f"Error saving {prefix} file: {e}")
        return None

    return dest_path


def save_uploaded_files(uploaded_files, prefix: str = "voice") -> List[str]:
    """Save multiple uploaded files to uploads directory.

    Args:
        uploaded_files: List of Gradio uploaded file objects or single file
        prefix: Prefix for filenames

    Returns:
        List of paths to saved files
    """
    if uploaded_files is None:
        return []

    # Handle single file (convert to list for uniform processing)
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    saved_paths = []
    for i, uploaded_file in enumerate(uploaded_files):
        file_prefix = f"{prefix}_{i+1}" if len(uploaded_files) > 1 else prefix
        saved_path = save_uploaded_file(uploaded_file, file_prefix)
        if saved_path:
            saved_paths.append(saved_path)

    return saved_paths


def prioritize_recording_files(voice_files, enabled: bool = True) -> List[str]:
    """Prioritize files named Recording.m4a to appear first.

    Args:
        voice_files: Single path or list of paths
        enabled: Whether to apply prioritization

    Returns:
        Ordered list of voice file paths
    """
    if not voice_files:
        return []

    voice_list = voice_files if isinstance(
        voice_files, list) else [voice_files]
    if not enabled:
        return voice_list

    recording_files = [
        path for path in voice_list if os.path.basename(path).lower() == "recording.m4a"
    ]
    other_files = [
        path for path in voice_list if os.path.basename(path).lower() != "recording.m4a"
    ]
    return recording_files + other_files


def should_enable_background_for_filename(filename: str) -> bool:
    """Default background toggle: enabled only for files starting with 'recording'."""
    if not filename:
        return False
    return str(filename).strip().lower().startswith("recording")


def build_voice_order_rows(voice_files) -> List[List]:
    """Build default order table rows for uploaded voice files."""
    if not voice_files:
        return []

    if not isinstance(voice_files, list):
        voice_files = [voice_files]

    rows = []
    for idx, vf in enumerate(voice_files, start=1):
        if vf:
            base = os.path.basename(vf)
            rows.append(
                [idx, base, should_enable_background_for_filename(base)])
    return rows


def parse_background_enabled_value(value, default: bool = True) -> bool:
    """Parse a table value into a boolean for background enabled state."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"true", "yes", "y", "1", "on"}:
        return True
    if text in {"false", "no", "n", "0", "off"}:
        return False
    return default


def normalize_voice_order_table(order_table, voice_files=None, apply_move_action: bool = True) -> List[List]:
    """Normalize voice order rows and optionally apply one move action.

    Supports list/array rows, DataFrame-like objects, dict rows, and JSON strings.
    Output shape is always: [order_number, file_name, use_background_music]
    """
    voice_list = voice_files if isinstance(voice_files, list) else [
        voice_files] if voice_files else []
    voice_basenames = [os.path.basename(path) for path in voice_list if path]

    if order_table is None or order_table == "":
        if voice_basenames:
            return [[idx, name, should_enable_background_for_filename(name)] for idx, name in enumerate(voice_basenames, start=1)]
        return []

    try:
        if isinstance(order_table, str):
            parsed = json.loads(order_table.strip() or "[]")
            order_rows = parsed if isinstance(parsed, list) else []
        elif hasattr(order_table, "values"):
            order_rows = order_table.values.tolist()
        elif hasattr(order_table, "tolist"):
            order_rows = order_table.tolist()
        else:
            order_rows = order_table
    except Exception:
        order_rows = order_table

    if not isinstance(order_rows, list):
        if voice_basenames:
            return [[idx, name, should_enable_background_for_filename(name)] for idx, name in enumerate(voice_basenames, start=1)]
        return []

    parsed_rows = []
    for row_idx, row in enumerate(order_rows):
        if row is None:
            continue

        try:
            if isinstance(row, dict):
                order_val = row.get("Order", row.get("order", row.get(0)))
                name_val = row.get("File Name", row.get(
                    "file name", row.get("File", row.get(1))))
                use_background_val = row.get(
                    "Use Background Music",
                    row.get("use background music", row.get(
                        "Background Music", row.get("background music", row.get(2, should_enable_background_for_filename(name_val)))))
                )
                move_up_val = row.get("⬆️ Up", row.get(
                    "Up", row.get("up", row.get(3, False))))
                move_down_val = row.get("⬇️ Down", row.get(
                    "Down", row.get("down", row.get(4, False))))
            else:
                if len(row) < 2:
                    continue
                order_val, name_val = row[0], row[1]
                use_background_val = row[2] if len(
                    row) > 2 else should_enable_background_for_filename(name_val)
                move_up_val = row[3] if len(row) > 3 else False
                move_down_val = row[4] if len(row) > 4 else False
        except Exception:
            continue

        name = str(name_val).strip() if name_val is not None else ""
        if not name:
            continue

        try:
            order_num = float(order_val)
        except (TypeError, ValueError):
            order_num = float("inf")

        use_background = parse_background_enabled_value(
            use_background_val, default=True)
        move_up = parse_background_enabled_value(move_up_val, default=False)
        move_down = parse_background_enabled_value(
            move_down_val, default=False)
        parsed_rows.append({
            "order": order_num,
            "row_idx": row_idx,
            "name": name,
            "use_background": use_background,
            "move_up": move_up,
            "move_down": move_down,
        })

    parsed_rows.sort(key=lambda x: (x["order"], x["row_idx"]))
    normalized_rows = []

    if voice_basenames:
        # Keep only rows that match uploaded files and preserve duplicate filenames.
        available = {}
        for name in voice_basenames:
            available[name] = available.get(name, 0) + 1

        for row in parsed_rows:
            name = row["name"]
            if available.get(name, 0) > 0:
                normalized_rows.append({
                    "name": name,
                    "use_background": row["use_background"],
                    "move_up": row["move_up"],
                    "move_down": row["move_down"],
                })
                available[name] -= 1

        # Append missing uploaded files with defaults.
        for name in voice_basenames:
            if available.get(name, 0) > 0:
                normalized_rows.append({
                    "name": name,
                    "use_background": should_enable_background_for_filename(name),
                    "move_up": False,
                    "move_down": False,
                })
                available[name] -= 1
    else:
        for row in parsed_rows:
            normalized_rows.append({
                "name": row["name"],
                "use_background": row["use_background"],
                "move_up": row["move_up"],
                "move_down": row["move_down"],
            })

    if apply_move_action and len(normalized_rows) > 1:
        move_index = None
        move_direction = None

        for idx, row in enumerate(normalized_rows):
            is_up = bool(row["move_up"])
            is_down = bool(row["move_down"])

            # If both are selected in the same row, ignore to avoid ambiguity.
            if is_up and not is_down:
                move_index = idx
                move_direction = "up"
                break
            if is_down and not is_up:
                move_index = idx
                move_direction = "down"
                break

        if move_index is not None and move_direction == "up" and move_index > 0:
            normalized_rows[move_index -
                            1], normalized_rows[move_index] = normalized_rows[move_index], normalized_rows[move_index - 1]
        elif move_index is not None and move_direction == "down" and move_index < len(normalized_rows) - 1:
            normalized_rows[move_index +
                            1], normalized_rows[move_index] = normalized_rows[move_index], normalized_rows[move_index + 1]

    # Re-index order as 1..N and return compact rows.
    result_rows = []
    for idx, row in enumerate(normalized_rows, start=1):
        result_rows.append([idx, row["name"], bool(row["use_background"])])

    return result_rows


def render_voice_order_editor(order_rows) -> str:
    """Render a user-friendly row editor with per-row Up/Down buttons."""
    normalized = normalize_voice_order_table(
        order_rows, voice_files=None, apply_move_action=False)

    if not normalized:
        return """
        <div style="padding: 10px; border: 1px dashed #c7c7c7; border-radius: 8px; color: #666; background: #fafafa;">
            Upload voice files to arrange order.
        </div>
        """

    rows_html = []
    for idx, row in enumerate(normalized):
        order_num = int(row[0])
        filename = html.escape(str(row[1]))
        use_bg = bool(row[2])
        up_disabled = "disabled" if idx == 0 else ""
        down_disabled = "disabled" if idx == len(normalized) - 1 else ""
        checked = "checked" if use_bg else ""

        toggle_js = (
            "(function(){"
            "const root=document.getElementById('voice-order-state');"
            "if(!root)return;"
            "const input=root.querySelector('textarea,input');"
            "if(!input)return;"
            "let rows=[];"
            "try{rows=JSON.parse(input.value||'[]')}catch(e){return;}"
            f"if(!Array.isArray(rows)||!rows[{idx}])return;"
            f"rows[{idx}][2]=this.checked===true;"
            "rows=rows.map((r,n)=>[n+1,String((r&&r[1])||''),!!((r&&r.length>2)?r[2]:true)]);"
            "input.value=JSON.stringify(rows);"
            "input.dispatchEvent(new Event('input',{bubbles:true}));"
            "input.dispatchEvent(new Event('change',{bubbles:true}));"
            "})();"
        )

        move_up_js = (
            "(function(){"
            "const root=document.getElementById('voice-order-state');"
            "if(!root)return;"
            "const input=root.querySelector('textarea,input');"
            "if(!input)return;"
            "let rows=[];"
            "try{rows=JSON.parse(input.value||'[]')}catch(e){return;}"
            f"const i={idx};"
            "const t=i-1;"
            "if(!Array.isArray(rows)||t<0||t>=rows.length)return;"
            "const tmp=rows[i];rows[i]=rows[t];rows[t]=tmp;"
            "rows=rows.map((r,n)=>[n+1,String((r&&r[1])||''),!!((r&&r.length>2)?r[2]:true)]);"
            "input.value=JSON.stringify(rows);"
            "input.dispatchEvent(new Event('input',{bubbles:true}));"
            "input.dispatchEvent(new Event('change',{bubbles:true}));"
            "})();"
        )

        move_down_js = (
            "(function(){"
            "const root=document.getElementById('voice-order-state');"
            "if(!root)return;"
            "const input=root.querySelector('textarea,input');"
            "if(!input)return;"
            "let rows=[];"
            "try{rows=JSON.parse(input.value||'[]')}catch(e){return;}"
            f"const i={idx};"
            "const t=i+1;"
            "if(!Array.isArray(rows)||t<0||t>=rows.length)return;"
            "const tmp=rows[i];rows[i]=rows[t];rows[t]=tmp;"
            "rows=rows.map((r,n)=>[n+1,String((r&&r[1])||''),!!((r&&r.length>2)?r[2]:true)]);"
            "input.value=JSON.stringify(rows);"
            "input.dispatchEvent(new Event('input',{bubbles:true}));"
            "input.dispatchEvent(new Event('change',{bubbles:true}));"
            "})();"
        )

        toggle_js_attr = html.escape(toggle_js, quote=True)
        move_up_js_attr = html.escape(move_up_js, quote=True)
        move_down_js_attr = html.escape(move_down_js, quote=True)

        rows_html.append(f"""
        <tr>
            <td style=\"padding:8px; text-align:center; width:70px;\"><strong>{order_num}</strong></td>
            <td style=\"padding:8px;\">{filename}</td>
            <td style=\"padding:8px; text-align:center; width:140px;\">
                <label style=\"display:flex; align-items:center; justify-content:center; gap:6px; font-size:13px;\">
                    <input type=\"checkbox\" {checked} onchange=\"{toggle_js_attr}\" />
                    <span>Enable</span>
                </label>
            </td>
            <td style=\"padding:8px; text-align:center; width:150px;\">
                <button type=\"button\" {up_disabled} onclick=\"{move_up_js_attr}\" style=\"padding:4px 8px; margin-right:6px; border:1px solid #bbb; border-radius:6px; background:#fff; cursor:pointer;\">⬆️ Up</button>
                <button type=\"button\" {down_disabled} onclick=\"{move_down_js_attr}\" style=\"padding:4px 8px; border:1px solid #bbb; border-radius:6px; background:#fff; cursor:pointer;\">⬇️ Down</button>
            </td>
        </tr>
        """)

    return f"""
    <div style="border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: var(--bg-primary, #fff);">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead>
                <tr style="background: #f4f4f4;">
                    <th style="padding: 8px; border-bottom: 1px solid #ddd; width:70px;">Order</th>
                    <th style="padding: 8px; border-bottom: 1px solid #ddd; text-align:left;">File Name</th>
                    <th style="padding: 8px; border-bottom: 1px solid #ddd; width:140px;">Background</th>
                    <th style="padding: 8px; border-bottom: 1px solid #ddd; width:150px;">Actions</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """


def render_audio_health_card(analysis: Optional[Dict[str, Any]] = None) -> str:
    """Render HTML card for audio balance & level health check.

    Args:
        analysis: Analysis dict from audio_processor.analyze_levels() or None

    Returns:
        HTML formatted string for display
    """
    if not analysis or analysis.get("overall_status") in [None, "no_voice"]:
        return """
        <div style="padding: 12px 16px; border-radius: 8px; border: 1px dashed rgba(100,116,139,0.3); background: rgba(100,116,139,0.04); margin-top: 10px; font-size: 13px;">
            <div style="font-weight: 600; color: #64748b; margin-bottom: 4px;">🎚️ Inspector de Balance de Audio</div>
            <div style="color: #64748b;">Sube una grabación de voz para analizar automáticamente su volumen y su relación con la música de fondo.</div>
        </div>
        """

    status = analysis.get("overall_status", "optimal")
    badge_icon = analysis.get("badge_icon", "🟢")
    title = analysis.get("title", "Estado del Audio")
    voice_dbfs = analysis.get("voice_dbfs", "N/A")
    voice_label = analysis.get("voice_status_label", "")
    bg_dbfs = analysis.get("bg_dbfs")
    vmr = analysis.get("voice_to_music_ratio_db")
    balance_label = analysis.get("balance_status_label", "")
    warnings = analysis.get("warnings", [])
    recommendations = analysis.get("recommendations", [])

    if status == "danger":
        border_color = "#ef4444"
        bg_color = "rgba(239, 68, 68, 0.08)"
        title_color = "#dc2626"
    elif status == "warning":
        border_color = "#f59e0b"
        bg_color = "rgba(245, 158, 11, 0.08)"
        title_color = "#d97706"
    else:
        border_color = "#10b981"
        bg_color = "rgba(16, 185, 129, 0.08)"
        title_color = "#059669"

    html_parts = [
        f'<div style="padding: 14px 16px; border-radius: 8px; border: 1px solid {border_color}; background: {bg_color}; margin-top: 10px; font-size: 13px;">',
        f'<div style="font-weight: 700; color: {title_color}; font-size: 14px; margin-bottom: 8px;">{badge_icon} {title}</div>',
        '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px;">',
        f'<div><strong>🎙️ Nivel de Voz:</strong> <code>{voice_dbfs} dBFS</code><br/><span style="font-size: 11px; opacity: 0.8;">({voice_label})</span></div>'
    ]

    if bg_dbfs is not None:
        html_parts.append(
            f'<div><strong>🎵 Música de Fondo:</strong> <code>{bg_dbfs} dBFS</code><br/><span style="font-size: 11px; opacity: 0.8;">({balance_label})</span></div>')
    else:
        html_parts.append(
            '<div><strong>🎵 Música de Fondo:</strong> <span style="font-size: 11px; opacity: 0.8;">(Sin música)</span></div>')

    html_parts.append('</div>')

    if warnings:
        html_parts.append(
            '<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(100,100,100,0.15);">')
        for w in warnings:
            html_parts.append(
                f'<div style="color: {title_color}; margin-bottom: 2px;">⚠️ {w}</div>')
        html_parts.append('</div>')

    if recommendations:
        html_parts.append(
            '<div style="margin-top: 6px; font-size: 12px; opacity: 0.9;">')
        for r in recommendations:
            html_parts.append(
                f'<div style="color: #059669; font-weight: 500;">💡 {r}</div>')
        html_parts.append('</div>')

    html_parts.append('</div>')
    return "".join(html_parts)


def quality_settings_values():
    """Refresh controls from persisted settings (including after template loads)."""
    try:
        thresholds = asdict(config_manager.get_audio_quality_config())
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        thresholds = config_manager.get("audio_quality", {})
        log_message(f"Invalid saved audio quality settings: {error}. "
                    "Repair the raw JSON in Advanced quality thresholds; settings were not changed.")
    return (
        bool(config_manager.get("quality_gate_enabled", False)),
        json.dumps(thresholds, indent=2),
        config_manager.get("music_seed", 0),
    )


def save_quality_settings(enabled, thresholds_json, music_seed):
    """Validate the complete editor before saving anything; errors stay in the UI."""
    try:
        values = json.loads(thresholds_json)
        if not isinstance(values, dict):
            raise ValueError("Thresholds must be a JSON object")
        unknown = set(values) - \
            {item.name for item in fields(AudioQualityConfig)}
        if unknown:
            raise ValueError("Unknown thresholds: " +
                             ", ".join(sorted(unknown)))
        # The existing LUFS slider remains the single source of truth.
        quality = AudioQualityConfig.from_mapping(values)
        quality = replace(
            quality, target_lufs=config_manager.get_target_lufs())
        if isinstance(music_seed, bool) or music_seed is None:
            raise ValueError("Music seed must be an integer")
        seed = int(music_seed)
        if seed != float(music_seed) or abs(seed) > 2**53 - 1:
            raise ValueError(
                "Music seed must be an exact integer within ±(2^53 − 1)")
        config_manager.update_settings({"audio_quality": asdict(quality),
                                        "music_seed": seed, "quality_gate_enabled": enabled})
        return "Quality settings saved. Target LUFS follows the LUFS slider. Changes apply on the next render."
    except (ValueError, TypeError, OverflowError, OSError) as error:
        return "Quality settings not saved: " + str(error)


def set_quality_gate_enabled(enabled):
    """Keep opt-in independent of any unfinished advanced JSON edits."""
    try:
        config_manager.set("quality_gate_enabled", bool(enabled))
        return "Final quality gate {} for the next render.".format("enabled" if enabled else "disabled")
    except (ValueError, TypeError, OSError) as error:
        return "Quality setting not saved: " + str(error)


def save_render_quality_report(output_path, enabled, report, started_ns):
    """Persist only this request's callback report, bound to the exact export.

    The producer's matching metadata survives; metrics never come from disk.
    Disabled renders get only a receipt, never a copy of previous QC findings.
    """
    output_path = os.path.realpath(output_path)
    if report is not None and os.path.realpath(report.file_path or "") != output_path:
        raise ValueError("Quality report belongs to a different audio file")
    identity = _quality_file_identity(output_path)
    metadata = None
    try:
        producer = _read_quality_sidecar(output_path)
        if producer["identity"] == identity:
            metadata = producer.get("metadata")
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError) as error:
        log_message(f"Producer quality metadata unavailable: {error}")
    preview = report.preview_file if enabled and report is not None else None
    preview_identity = _register_quality_preview(preview, output_path)
    data = report.to_dict() if enabled and report is not None else {}
    if enabled and metadata is not None:
        data["metadata"] = metadata
    data.update({
        "schema": "ntn-quality-v1", "output_path": output_path,
        "identity": identity, "preview_identity": preview_identity,
        "ui": {"identity": identity, "started_ns": started_ns,
               "enabled": bool(enabled), "preview_identity": preview_identity,
               "override": False},
    })
    if _quality_file_identity(output_path) != identity:
        raise ValueError("Audio changed while saving the quality receipt")
    _write_quality_sidecar(output_path + ".quality.json", data)


def _load_render_quality_report(output_path, started_ns=0):
    """Reject missing, mismatched, stale or malformed receipts; never infer VMR."""
    if not output_path:
        raise ValueError("No exported audio for this render")
    output_path = os.path.realpath(output_path)
    output_root = os.path.realpath("outputs")
    if os.path.commonpath([output_root, output_path]) != output_root:
        raise ValueError("Audio is not a produced output")
    sidecar = output_path + ".quality.json"
    data = _read_quality_sidecar(output_path)
    receipt = data.get("ui")
    if (not isinstance(receipt, dict)
            or receipt.get("identity") != data["identity"]
            or receipt.get("started_ns", 0) < started_ns):
        raise ValueError("Stale quality report; render again to refresh it")
    if not isinstance(receipt.get("enabled"), bool):
        raise ValueError("Invalid quality gate state")
    report = None
    if receipt["enabled"] and "analysis_complete" in data:
        raw = data
        if not isinstance(raw, dict) or not isinstance(raw.get("analysis_complete"), bool):
            raise ValueError("Invalid quality report")
        for key in ("failures", "warnings", "analysis_errors", "recommendations"):
            if not isinstance(raw.get(key), list) or not all(isinstance(x, str) for x in raw[key]):
                raise ValueError("Invalid quality report notes")
        if os.path.realpath(raw.get("file_path") or "") != output_path:
            raise ValueError("Report does not describe this export")
        report = AudioQualityReport(**{item.name: raw[item.name]
                                       for item in fields(AudioQualityReport) if item.name in raw})
    return sidecar, data, report


def clear_final_quality_inspector(previous_preview=None):
    """First event in the render chain clears every previous result immediately."""
    if isinstance(previous_preview, dict):
        _cleanup_quality_preview(previous_preview.get("path"),
                                 previous_preview.get("identity"))
    else:
        _cleanup_quality_preview(previous_preview)
    return "", None, None, "", time.time_ns()


def remember_quality_preview(output_path, started_ns=0):
    """Keep the original preview receipt in session state, not a Gradio cache copy."""
    try:
        _, data, report = _load_render_quality_report(output_path, started_ns)
        if report is not None and report.preview_file:
            identity = data["ui"].get("preview_identity")
            if identity is not None and _quality_preview_identity(report.preview_file) == identity:
                return {"path": report.preview_file, "identity": identity}
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        pass
    return None


def render_final_quality_inspector(output_path, started_ns=0):
    """Load a render-local receipt, not mutable processor state or current config."""
    if not output_path:
        return "", None, None
    try:
        sidecar, data, report = _load_render_quality_report(
            output_path, started_ns)
        if not data["ui"]["enabled"]:
            return "<p>Final Audio Quality Gate was disabled for this render.</p>", None, None
        if report is None:
            return '<p style="color:#dc2626">QC unavailable. Audio exported, but not certified; rerender to check.</p>', None, None
        color, caption = {
            "PASS": ("#059669", "Ready to publish"),
            "WARN": ("#d97706", "Review recommended"),
            "FAIL": ("#dc2626", "Audio Quality Check Failed — publishing is not recommended"),
        }[report.status]
        acknowledgement = ("<p>Override acknowledged. Original QC result is unchanged; export remains available.</p>"
                           if data["ui"].get("override") else "")
        card = (f'<div style="border:2px solid {color};padding:16px;border-radius:8px">'
                f'<h3 style="color:{color}">{caption}</h3>' + report.to_html()
                + acknowledgement + "<p>VMR comes from the render's separate stems, not recovered from stereo.</p></div>")
        preview = report.preview_file
        if preview:
            # Only expose the analyzer's produced temporary preview, never an
            # arbitrary path injected into a sidecar or a stale replaced file.
            identity = data["ui"].get("preview_identity")
            valid_preview = (identity is not None
                             and identity == _quality_preview_identity(preview))
            if not valid_preview:
                preview = None
        return card, preview, sidecar
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        return '<p style="color:#dc2626">QC unavailable: ' + html.escape(str(error)) + "</p>", None, None


def acknowledge_quality_override(output_path, started_ns=0):
    """Record a deliberate acknowledgement without changing any QC findings."""
    try:
        sidecar, data, report = _load_render_quality_report(
            output_path, started_ns)
        if report is None or report.status == "PASS":
            return render_final_quality_inspector(output_path, started_ns)[0], "No QC warning or failure to override."
        data["ui"]["override"] = True
        _write_quality_sidecar(sidecar, data)
        return render_final_quality_inspector(output_path, started_ns)[0], "Override acknowledged; QC remains " + report.status + ". Export is still available."
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        return render_final_quality_inspector(output_path, started_ns)[0], "Cannot acknowledge QC: " + str(error)


def apply_quality_suggested_settings(output_path, started_ns=0):
    """Apply only allowlisted safe settings for a future render, never edit audio."""
    message = ""
    try:
        _, _, report = _load_render_quality_report(output_path, started_ns)
        if report is None:
            raise ValueError("No quality report is available")
        codes = set(report.failures + report.warnings)
        settings = {}
        if codes & {"VOICE_TOO_QUIET", "MUSIC_MASKING_VOICE", "MUSIC_DOMINATES_VOICE"}:
            settings["auto_balance_levels"] = True
        if codes & {"MUSIC_MASKING_VOICE", "MUSIC_DOMINATES_VOICE"}:
            settings["auto_ducking"] = True
        if codes & {"LOUDNESS_TOO_LOW", "LOUDNESS_TOO_HIGH", "TRUE_PEAK_TOO_HIGH"}:
            settings["normalize_lufs"] = True
        if settings:
            config_manager.update_settings(settings)
        message = ("Saved suggested settings: " + ", ".join(settings) + ". " if settings
                   else "No automatic safe setting change applies; follow the report recommendations. ")
        message += ("Rerender required using the original voice source and music. Re-upload the source if deleted. "
                    "Existing audio and QC result are unchanged; normalization cannot repair clipping.")
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
        message = "Suggested settings not applied: " + str(error)
    return (message, config_manager.get_auto_balance_levels(),
            config_manager.get_auto_ducking(), config_manager.get_normalize_lufs())


def order_voice_segments(voice_files, order_table) -> List[Tuple[str, bool]]:
    """Apply user-defined order and per-track background toggle.

    Args:
        voice_files: Single path or list of paths
        order_table: Data from the order table component (list of rows or DataFrame)

    Returns:
        Ordered list of tuples: (voice_file_path, use_background_music)
    """
    if not voice_files:
        return []

    voice_list = voice_files if isinstance(
        voice_files, list) else [voice_files]

    if not order_table:
        prioritized_list = prioritize_recording_files(
            voice_list,
            config_manager.get_prioritize_recording_filename()
        )
        return [
            (path, should_enable_background_for_filename(os.path.basename(path)))
            for path in prioritized_list
        ]

    order_rows = normalize_voice_order_table(
        order_table, voice_list, apply_move_action=False)

    if not order_rows:
        return [
            (path, should_enable_background_for_filename(os.path.basename(path)))
            for path in voice_list
        ]

    basename_to_paths = {}
    for path in voice_list:
        base = os.path.basename(path)
        basename_to_paths.setdefault(base, []).append(path)

    ordered_entries = []
    for row in order_rows:
        if row is None:
            continue

        try:
            if isinstance(row, dict):
                order_val = row.get("Order", row.get("order", row.get(0)))
                name_val = row.get("File Name", row.get(
                    "file name", row.get("File", row.get(1))))
                use_background_val = row.get(
                    "Use Background Music",
                    row.get("use background music", row.get(
                        "Background Music", row.get("background music", row.get(2, should_enable_background_for_filename(name_val)))))
                )
            else:
                if len(row) < 2:
                    continue
                order_val, name_val = row[0], row[1]
                use_background_val = row[2] if len(
                    row) > 2 else should_enable_background_for_filename(name_val)
        except Exception:
            continue

        try:
            position = float(order_val)
        except (TypeError, ValueError):
            continue

        file_name = str(name_val).strip()
        if not file_name:
            continue

        use_background = parse_background_enabled_value(
            use_background_val, default=True)

        if file_name in basename_to_paths and basename_to_paths[file_name]:
            path = basename_to_paths[file_name].pop(0)
            ordered_entries.append((position, path, use_background))

    if not ordered_entries:
        return [
            (path, should_enable_background_for_filename(os.path.basename(path)))
            for path in voice_list
        ]

    ordered_entries.sort(key=lambda x: (x[0], voice_list.index(x[1])))
    ordered_segments = [(path, use_background)
                        for _, path, use_background in ordered_entries]

    for path in voice_list:
        if path not in [p for p, _ in ordered_segments]:
            ordered_segments.append(
                (path, should_enable_background_for_filename(os.path.basename(path))))

    return ordered_segments


def order_voice_files(voice_files, order_table) -> List[str]:
    """Apply a user-defined order to voice files using an order table.

    Args:
        voice_files: Single path or list of paths
        order_table: Data from the order table component (list of rows or DataFrame)

    Returns:
        Ordered list of voice file paths
    """
    ordered_segments = order_voice_segments(voice_files, order_table)
    return [path for path, _ in ordered_segments]


def update_intro_file(file):
    """Update intro file in configuration."""
    if file is None:
        config_manager.update_intro(None)
        return "No intro file selected", *get_intro_info()

    # Save to audios/intro_audio folder
    # In Gradio 6.0, file is a string path directly
    if isinstance(file, str):
        source_path = file
        original_name = os.path.basename(file)
    elif hasattr(file, 'name'):
        source_path = file.name
        original_name = os.path.basename(file.name)
    else:
        original_name = "intro.mp3"
        source_path = file

    dest_path = os.path.join("audios", "intro_audio", original_name)
    try:
        shutil.copy2(source_path, dest_path)
        config_manager.update_intro(dest_path)
        log_message(f"Intro file saved: {os.path.basename(dest_path)}")
        return f"Intro file saved: {os.path.basename(dest_path)}", *get_intro_info()
    except Exception as e:
        log_message(f"Error saving intro file: {e}")
        return "Error saving intro file", *get_intro_info()


def update_outro_file(file):
    """Update outro file in configuration."""
    if file is None:
        config_manager.update_outro(None)
        return "No outro file selected", *get_outro_info()

    # Save to audios/outro_audio folder
    # In Gradio 6.0, file is a string path directly
    if isinstance(file, str):
        source_path = file
        original_name = os.path.basename(file)
    elif hasattr(file, 'name'):
        source_path = file.name
        original_name = os.path.basename(file.name)
    else:
        original_name = "outro.mp3"
        source_path = file

    dest_path = os.path.join("audios", "outro_audio", original_name)
    try:
        shutil.copy2(source_path, dest_path)
        config_manager.update_outro(dest_path)
        log_message(f"Outro file saved: {os.path.basename(dest_path)}")
        return f"Outro file saved: {os.path.basename(dest_path)}", *get_outro_info()
    except Exception as e:
        log_message(f"Error saving outro file: {e}")
        return "Error saving outro file", *get_outro_info()


def add_background_track(file):
    """Add background music track."""
    global background_tracks_list

    if file is None:
        display_list, _ = get_background_tracks_list()
        return "No file selected", get_background_tracks_display(), gr.update(choices=display_list)

    # Save to audios/background_music folder
    # In Gradio 6.0, file is a string path directly
    if isinstance(file, str):
        source_path = file
        original_name = os.path.basename(file)
    elif hasattr(file, 'name'):
        source_path = file.name
        original_name = os.path.basename(file.name)
    else:
        original_name = "background.mp3"
        source_path = file

    dest_path = os.path.join("audios", "background_music", original_name)
    try:
        shutil.copy2(source_path, dest_path)
        config_manager.add_background_track(dest_path)
        background_tracks_list = config_manager.get_background_tracks()
        log_message(f"Added background track: {os.path.basename(dest_path)}")

        # Get updated list for dropdown
        display_list, _ = get_background_tracks_list()

        return f"Added: {os.path.basename(dest_path)}", get_background_tracks_display(), gr.update(choices=display_list)
    except Exception as e:
        log_message(f"Error saving background file: {e}")
        display_list, _ = get_background_tracks_list()
        return "Error saving file", get_background_tracks_display(), gr.update(choices=display_list)


def get_background_tracks_display():
    """Get formatted list of background tracks."""
    tracks = config_manager.get_background_tracks()
    if not tracks:
        return "No background tracks added yet"

    # Filter out files that don't exist anymore
    valid_tracks = [t for t in tracks if os.path.exists(t)]
    if valid_tracks != tracks:
        config_manager.update_background_tracks(valid_tracks)

    return "\n".join([f"• {os.path.basename(t)}" for t in valid_tracks])


def get_intro_info():
    """Get intro audio file info with duration."""
    intro = config_manager.get_intro()
    if intro and os.path.exists(intro):
        duration = get_audio_duration(intro)
        return f"{duration} - {os.path.basename(intro)}", intro
    return "No intro audio set", None


def get_outro_info():
    """Get outro audio file info with duration."""
    outro = config_manager.get_outro()
    if outro and os.path.exists(outro):
        duration = get_audio_duration(outro)
        return f"{duration} - {os.path.basename(outro)}", outro
    return "No outro audio set", None


def get_background_tracks_list():
    """Get list of background tracks with duration and file paths."""
    tracks = config_manager.get_background_tracks()
    if not tracks:
        return [], []

    valid_tracks = [t for t in tracks if os.path.exists(t)]
    if valid_tracks != tracks:
        config_manager.update_background_tracks(valid_tracks)

    # Return list of (display_name, file_path) tuples
    result = []
    paths = []
    for track in valid_tracks:
        duration = get_audio_duration(track)
        display = f"{duration} - {os.path.basename(track)}"
        result.append(display)
        paths.append(track)

    return result, paths


def delete_intro():
    """Delete intro audio file."""
    intro = config_manager.get_intro()
    if intro and os.path.exists(intro):
        try:
            os.remove(intro)
            config_manager.update_intro(None)
            log_message(f"Deleted intro: {os.path.basename(intro)}")
            return "Intro deleted successfully", *get_intro_info()
        except Exception as e:
            log_message(f"Error deleting intro: {e}")
            return f"Error deleting intro: {e}", *get_intro_info()
    return "No intro to delete", *get_intro_info()


def delete_outro():
    """Delete outro audio file."""
    outro = config_manager.get_outro()
    if outro and os.path.exists(outro):
        try:
            os.remove(outro)
            config_manager.update_outro(None)
            log_message(f"Deleted outro: {os.path.basename(outro)}")
            return "Outro deleted successfully", *get_outro_info()
        except Exception as e:
            log_message(f"Error deleting outro: {e}")
            return f"Error deleting outro: {e}", *get_outro_info()
    return "No outro to delete", *get_outro_info()


def delete_background_track(track_index):
    """Delete a specific background track by index."""
    tracks = config_manager.get_background_tracks()

    if track_index is None or track_index < 0 or track_index >= len(tracks):
        return "Invalid track selection", gr.update(choices=[]), gr.update(value=None)

    track_path = tracks[track_index]

    try:
        if os.path.exists(track_path):
            os.remove(track_path)

        # Remove from config
        tracks.pop(track_index)
        config_manager.update_background_tracks(tracks)

        log_message(
            f"Deleted background track: {os.path.basename(track_path)}")

        # Get updated list
        display_list, paths = get_background_tracks_list()
        choices = display_list if display_list else []

        return "Track deleted successfully", gr.update(choices=choices), gr.update(value=None)
    except Exception as e:
        log_message(f"Error deleting track: {e}")
        display_list, _ = get_background_tracks_list()
        return f"Error deleting track: {e}", gr.update(choices=display_list), gr.update(value=None)


def get_selected_track_audio(track_index, track_choices):
    """Get the audio file path for the selected track."""
    if track_index is None or track_index < 0:
        return None

    tracks = config_manager.get_background_tracks()
    if track_index >= len(tracks):
        return None

    return tracks[track_index]


def clear_background_tracks():
    """Clear all background tracks."""
    global background_tracks_list
    config_manager.update_background_tracks([])
    background_tracks_list = []
    log_message("All background tracks cleared")
    return "All background tracks cleared", get_background_tracks_display(), gr.update(choices=[])


def update_volume(volume):
    """Update background music volume."""
    config_manager.update_volume(int(volume))
    return f"Volume set to {int(volume)}%"


def apply_volume_to_all():
    """Apply current global volume to all tracks."""
    volume = config_manager.get_volume()
    config_manager.apply_volume_to_all_tracks(volume)
    log_message(f"Applied {volume}% volume to all background tracks")
    return f"Applied {volume}% volume to all tracks"


def update_track_volume(track_choice, new_volume):
    """Update volume for a specific track."""
    if track_choice is None:
        return "No track selected", None, None

    # Find the track path
    display_list, paths = get_background_tracks_list()
    try:
        idx = display_list.index(track_choice)
        track_path = paths[idx]

        # Update the volume for this track
        config_manager.set_track_volume(track_path, int(new_volume))
        log_message(
            f"Set volume for {os.path.basename(track_path)} to {int(new_volume)}%")

        # Generate preview audio with new volume
        preview_audio = generate_volume_preview(track_path, int(new_volume))

        return f"Volume for {os.path.basename(track_path)} set to {int(new_volume)}%", preview_audio, preview_audio
    except (ValueError, IndexError):
        return "Track not found", None, None


def generate_volume_preview(track_path: str, volume: int) -> Optional[str]:
    """Generate a preview of the track with applied volume.

    Args:
        track_path: Path to the track
        volume: Volume percentage to apply

    Returns:
        Path to the preview file or None

    Note:
        Generated temporary files persist until system cleanup (temp directory
        is periodically cleaned by OS) or until the application is restarted.
        This is acceptable for preview files as they are small and short-lived.
    """
    try:
        from pydub import AudioSegment
        import tempfile

        # Load the track
        audio = AudioSegment.from_file(track_path)

        # Apply volume
        audio_with_volume = audio_processor.reduce_volume(audio, volume)

        # Save to temp file - persists until OS cleanup or app restart
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".mp3", dir=tempfile.gettempdir())
        audio_with_volume.export(temp_file.name, format="mp3")

        return temp_file.name
    except Exception as e:
        log_message(f"Error generating volume preview: {e}")
        return None


def get_track_volume(track_choice):
    """Get volume setting for the selected track."""
    if track_choice is None:
        return config_manager.get_volume()

    # Find the track path
    display_list, paths = get_background_tracks_list()
    try:
        idx = display_list.index(track_choice)
        track_path = paths[idx]
        return config_manager.get_track_volume(track_path)
    except (ValueError, IndexError):
        return config_manager.get_volume()


def get_current_settings():
    """Get current audio settings as formatted text."""
    intro = config_manager.get_intro()
    outro = config_manager.get_outro()
    bg_tracks = config_manager.get_background_tracks()
    volume = config_manager.get_volume()
    rss_url = config_manager.get_rss_feed_url()
    last_title, next_slug, _ = fetch_rss_episode_info(rss_url)

    settings = []
    settings.append("📋 Current Audio Configuration:")
    settings.append("")
    settings.append(
        f"🎵 Intro: {os.path.basename(intro) if intro and os.path.exists(intro) else 'Not set'}")
    settings.append(
        f"🎵 Outro: {os.path.basename(outro) if outro and os.path.exists(outro) else 'Not set'}")
    settings.append(f"🎵 Background Tracks: {len(bg_tracks)} track(s)")
    if bg_tracks:
        for track in bg_tracks:
            if os.path.exists(track):
                settings.append(f"   • {os.path.basename(track)}")
    settings.append(f"🔊 Background Volume: {volume}%")
    settings.append(f"🔗 RSS Feed: {rss_url}")
    settings.append(
        "🎤 Default upload order: "
        + ("Recording.m4a first" if config_manager.get_prioritize_recording_filename()
           else "Preserve upload order")
    )
    if last_title:
        settings.append(f"   Last episode: {last_title}")
    if next_slug:
        settings.append(f"   Next suggested: {next_slug}")

    return "\\n".join(settings)


def _legacy_progress_html(pct, msg):
    """Generate progress bar HTML with inline display control."""
    return f"""
    <div style="position: fixed; top: 0; left: 0; right: 0; z-index: 9999; background: #2196F3; color: white; padding: 10px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); display: block !important; width: 100%;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="font-weight: bold; display: flex; align-items: center; gap: 10px;">
                <div style="border: 3px solid rgba(255,255,255,0.3); border-radius: 50%; border-top: 3px solid white; width: 20px; height: 20px; animation: spin 1s linear infinite;"></div>
                {msg}
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="font-size: 12px; min-width: 40px;">{int(pct*100)}%</div>
                <div style="background: rgba(255,255,255,0.3); height: 8px; width: 200px; border-radius: 4px; overflow: hidden;">
                    <div style="background: white; height: 100%; width: {pct*100}%; transition: width 0.3s;"></div>
                </div>
            </div>
        </div>
        <style>@keyframes spin {{0% {{transform: rotate(0deg);}} 100% {{transform: rotate(360deg);}}}}</style>
    </div>
    """


def get_audio_autoplay_script(audio_elem_id: str) -> str:
    """Generate a small script to auto-play the audio element when ready."""
    return f"""
    <script>
    (function() {{
        function attemptPlay() {{
            const container = document.getElementById("{audio_elem_id}");
            if (!container) return;
            const audio = container.querySelector("audio");
            if (!audio) return;
            const playPromise = audio.play();
            if (playPromise && typeof playPromise.catch === "function") {{
                playPromise.catch(function() {{}});
            }}
        }}

        setTimeout(attemptPlay, 100);
        setTimeout(attemptPlay, 600);
        setTimeout(attemptPlay, 1200);
    }})();
    </script>
    """


def _render_episode(
    voice_file,
    output_name,
    delete_voice,
    trim_silence,
    denoise_audio,
    denoise_method,
    enhance_voice,
    voice_enhancement_preset,
    normalize_lufs,
    target_lufs,
    intro_voice_overlap,
    voice_outro_overlap,
    generate_transcript,
    whisper_model,
    auto_balance_levels=True,
    auto_ducking=True,
    voice_order_table=None,
    intro_override_file=None,
    progress=gr.Progress(),
    *, snapshot
):
    """Handle podcast creation request with progress tracking.

    Args:
        voice_file: Single file path or list of file paths for voice recording(s)
        output_name: Name for output podcast file
        delete_voice: Whether to delete voice file(s) after processing
        trim_silence: Whether to trim silence
        denoise_audio: Whether to apply denoising
        denoise_method: Denoising method to use
        enhance_voice: Whether to apply voice enhancement
        voice_enhancement_preset: Enhancement preset (podcast, light, aggressive)
        normalize_lufs: Whether to normalize audio levels
        target_lufs: Target LUFS level for normalization
        intro_voice_overlap: Whether to enable intro-voice overlap
        voice_outro_overlap: Whether to enable voice-outro overlap
        generate_transcript: Whether to generate transcript
        whisper_model: Whisper model size to use
        auto_balance_levels: Whether to auto-balance voice and music levels
        auto_ducking: Whether to apply auto-ducking during speech
        voice_order_table: Table for custom voice file ordering
        intro_override_file: Optional one-time custom intro file
        progress: Gradio progress tracker
    """
    import threading
    import queue
    import time

    # Clear the console at start
    global console_log
    console_log.clear()

    # Snapshot once before yielding: changing settings during a render must not
    # change its thresholds, seed, or final QC status.
    quality_started_ns = time.time_ns()
    quality_enabled = bool(snapshot.get("quality_gate_enabled", False))
    quality_config = None
    quality_config_error = None
    music_seed = snapshot.get("music_seed", 0)
    try:
        if snapshot.get("quality_config_error"):
            raise ValueError(snapshot["quality_config_error"])
        quality_config = replace(snapshot["quality_config"],
                                 target_lufs=float(target_lufs))
    except (ValueError, TypeError, AttributeError) as error:
        quality_config_error = str(error)
        log_message(
            f"Quality configuration unavailable: {error}. Using processor defaults.")

    progress(0.0, "🚀 Starting podcast creation...")
    log_message("=" * 50)
    log_message("🎬 Starting new podcast creation")

    # Yield immediately to show progress bar and console
    current_console = get_console_log()
    yield "Starting...", None, None, None, current_console, get_progress_html(0.0, "🚀 Starting podcast creation..."), get_bottom_console_html(current_console)

    if voice_file is None:
        log_message("❌ Error: No voice file provided")
        current_console = get_console_log()
        yield "❌ Error: Please upload a voice recording file", None, None, None, current_console, get_progress_html(0.0, "❌ Error"), get_bottom_console_html(current_console, show_close=True)
        return

    if not output_name or output_name.strip() == "":
        output_name = "podcast_output"

    # Remove extension if provided
    output_name = output_name.replace(".mp3", "")
    log_message(f"📝 Output filename: {output_name}.mp3")

    progress(0.1, "📁 Preparing files...")
    current_console = get_console_log()
    yield "Preparing files...", None, None, None, current_console, get_progress_html(0.1, "Preparing files..."), get_bottom_console_html(current_console)

    # Save voice file(s)
    voice_paths = save_uploaded_files(voice_file, "voice")
    if not voice_paths:
        log_message("❌ Error: Could not save voice file(s)")
        current_console = get_console_log()
        yield "❌ Error: Could not save voice file(s)", None, None, None, current_console, get_progress_html(0.1, "❌ Error"), get_bottom_console_html(current_console, show_close=True)
        return

    # Apply custom ordering/background toggles if provided
    if not voice_order_table:
        voice_order_table = build_voice_order_rows(prioritize_recording_files(
            voice_paths, snapshot.get("prioritize_recording_filename", True)))
    ordered_voice_segments = order_voice_segments(
        voice_paths, voice_order_table)
    voice_background_flags = [use_bg for _, use_bg in ordered_voice_segments]
    ordered_voice_paths = [path for path, _ in ordered_voice_segments]

    if ordered_voice_paths:
        if ordered_voice_paths != voice_paths:
            log_message("🗂️ Applied custom voice order: " +
                        " → ".join([os.path.basename(p) for p in ordered_voice_paths]))
        voice_paths = ordered_voice_paths

    disabled_bg_tracks = sum(
        1 for enabled in voice_background_flags if not enabled)
    if disabled_bg_tracks > 0:
        log_message(
            f"🎵 Background disabled on {disabled_bg_tracks}/{len(voice_background_flags)} uploaded voice track(s)")

    # Build optional background segments for selective background mixing
    background_segments = []
    segment_start_ms = 0
    for path, use_bg in zip(voice_paths, voice_background_flags):
        duration_ms = int(round(get_audio_duration_seconds(path) * 1000))
        segment_end_ms = segment_start_ms + duration_ms
        if use_bg and duration_ms > 0:
            background_segments.append((segment_start_ms, segment_end_ms))
        segment_start_ms = segment_end_ms

    selective_background_segments = background_segments if len(
        voice_paths) > 1 else None

    # Concatenate files if multiple files provided
    voice_path = voice_paths[0]  # Default to first file
    concatenated_file = None

    if len(voice_paths) > 1:
        progress(0.15, "🔗 Concatenating audio files...")
        current_console = get_console_log()
        yield "Concatenating audio files...", None, None, None, current_console, get_progress_html(0.15, "Concatenating audio files..."), get_bottom_console_html(current_console)

        try:
            log_message(f"📎 Concatenating {len(voice_paths)} audio files...")
            concatenated_file = audio_processor.concatenate_audio_files(
                voice_paths,
                output_path=os.path.join(
                    "uploads", f"concatenated_{output_name}.mp3"),
                log_callback=log_message
            )
            voice_path = concatenated_file
            log_message(
                f"✅ Concatenation complete: {os.path.basename(voice_path)}")
        except Exception as e:
            log_message(f"❌ Error concatenating files: {e}")
            current_console = get_console_log()
            yield f"❌ Error: {e}", None, None, None, current_console, get_progress_html(0.15, "❌ Error"), get_bottom_console_html(current_console, show_close=True)
            return

    progress(0.2, "⚙️ Loading configuration...")
    current_console = get_console_log()
    yield "Loading configuration...", None, None, None, current_console, get_progress_html(0.2, "Loading configuration..."), get_bottom_console_html(current_console)

    # Get configuration
    intro_override_path = None
    if intro_override_file:
        intro_override_path = save_uploaded_file(
            intro_override_file, "intro_override")
        if not intro_override_path:
            log_message(
                "⚠️ One-time intro override failed to save. Falling back to default intro.")

    intro_path = intro_override_path or snapshot.get("intro_file")
    outro_path = snapshot.get("outro_file")
    background_tracks = snapshot.get("background_tracks", [])
    volume = snapshot.get("background_volume", 5)
    track_volumes = snapshot.get("track_volumes", {})

    log_message(f"Configuration loaded:")
    if intro_override_path:
        log_message(
            f"  Intro: {intro_path if intro_path else 'None'} (one-time override)")
    else:
        log_message(f"  Intro: {intro_path if intro_path else 'None'}")
    log_message(f"  Outro: {outro_path if outro_path else 'None'}")
    log_message(
        f"  Background tracks: {len(background_tracks) if background_tracks else 0}")
    log_message(f"  Volume: {volume}%")
    log_message(f"  Trim silence: {trim_silence}")
    log_message(f"  Denoise audio: {denoise_audio} (method: {denoise_method})")
    log_message(f"  Normalize LUFS: {normalize_lufs} (target: {target_lufs})")
    log_message(f"  Intro-voice overlap: {intro_voice_overlap}")
    log_message(f"  Voice-outro overlap: {voice_outro_overlap}")
    log_message(f"  Auto-balance levels: {auto_balance_levels}")
    log_message(f"  Auto-ducking: {auto_ducking}")
    log_message(
        f"  Generate transcript: {generate_transcript} (model: {whisper_model})")

    # Create output path
    output_path = os.path.join("outputs", f"{output_name}.mp3")

    # Save output name for next time
    config_manager.update_last_output_name(output_name)

    progress(0.3, "🎬 Starting audio processing...")
    current_console = get_console_log()
    yield "Starting audio processing...", None, None, None, current_console, get_progress_html(0.3, "Starting audio processing..."), get_bottom_console_html(current_console)

    # Queue for logs to enable real-time updates
    log_queue = queue.Queue()
    progress_queue = queue.Queue()

    def threaded_log_callback(message: str):
        log_message(message)
        log_queue.put(message)

        # Update progress based on message content
        pct = 0.3
        msg = "Processing..."

        if "Denoising" in message or "noise" in message.lower():
            pct = 0.4
            msg = "🔧 Removing noise..."
            progress(pct, msg)
        elif "Enhancing" in message or "enhance" in message.lower():
            pct = 0.5
            msg = "✨ Enhancing audio..."
            progress(pct, msg)
        elif "Auto-balance" in message or "balance" in message.lower():
            pct = 0.65
            msg = "🎚️ Balancing levels..."
            progress(pct, msg)
        elif "Mixing" in message or "mixing" in message.lower():
            pct = 0.7
            msg = "🎵 Mixing tracks..."
            progress(pct, msg)
        elif "Normalizing" in message or "LUFS" in message:
            pct = 0.8
            msg = "📊 Normalizing..."
            progress(pct, msg)
        elif "Transcript" in message or "transcrib" in message.lower():
            pct = 0.9
            msg = "📝 Transcribing..."
            progress(pct, msg)
        elif "saved" in message.lower() or "complete" in message.lower():
            pct = 1.0
            msg = "✅ Complete!"
            progress(pct, msg)

        progress_queue.put((pct, msg))

    # Container for result from thread
    result_container = {}

    def capture_quality_report(report):
        # Never read audio_processor.last_quality_report: another request can
        # overwrite it. Snapshot the callback before the worker returns.
        import copy
        result_container['quality_report'] = copy.deepcopy(report)

    def run_process():
        try:
            result_path, denoised_path, transcript_path = audio_processor.create_podcast(
                voice_file=voice_path,
                intro_file=intro_path,
                outro_file=outro_path,
                background_files=background_tracks if (
                    background_tracks and (
                        any(voice_background_flags))
                ) else None,
                background_segments=selective_background_segments,
                background_volume=volume,
                track_volumes=track_volumes if track_volumes else None,
                output_file=output_path,
                trim_silence=trim_silence,
                denoise_audio=denoise_audio,
                denoise_method=denoise_method,
                enhance_voice_enabled=enhance_voice,
                voice_enhancement_preset=voice_enhancement_preset,
                normalize_lufs=normalize_lufs,
                target_lufs=target_lufs,
                intro_voice_overlap=intro_voice_overlap,
                voice_outro_overlap=voice_outro_overlap,
                auto_balance_levels=auto_balance_levels,
                min_voice_music_separation_db=snapshot.get(
                    "min_voice_music_separation_db", 18.0),
                auto_ducking=auto_ducking,
                generate_transcript=generate_transcript,
                whisper_model=whisper_model,
                defer_transcription=True,
                log_callback=threaded_log_callback,
                quality_gate_enabled=quality_enabled,
                quality_config=quality_config,
                music_seed=music_seed,
                quality_report_callback=capture_quality_report
            )
            result_container['result'] = (
                result_path, denoised_path, transcript_path)
        except Exception as e:
            result_container['error'] = str(e)

    # Start processing in a separate thread
    t = threading.Thread(target=run_process)
    t.start()

    # Yield logs while running
    current_logs = get_console_log()
    current_pct = 0.3
    current_msg = "Processing..."

    while t.is_alive():
        # Process any new logs
        logs_updated = False
        while not log_queue.empty():
            msg = log_queue.get()
            logs_updated = True

        # Process progress updates
        while not progress_queue.empty():
            current_pct, current_msg = progress_queue.get()
            logs_updated = True

        if logs_updated:
            current_logs = get_console_log()
            yield "Processing...", None, None, None, current_logs, get_progress_html(current_pct, current_msg), get_bottom_console_html(current_logs)

        time.sleep(0.1)

    # Process any remaining logs
    while not log_queue.empty():
        log_queue.get()

    current_logs = get_console_log()

    # Check result
    if 'error' in result_container:
        error_msg = f"Error creating podcast: {result_container['error']}"
        log_message(error_msg)
        log_message("=" * 50)
        error_console_log = get_console_log()
        yield error_msg, None, None, None, error_console_log, get_progress_html(1.0, "❌ Error"), get_bottom_console_html(error_console_log, visible=True, show_close=True)
    else:
        result_path, denoised_path, transcript_path = result_container['result']

        report = result_container.get(
            'quality_report') if quality_enabled else None
        if quality_enabled and quality_config_error:
            if report is None:
                report = AudioQualityReport(file_path=result_path)
            report.analysis_complete = False
            report.failures.append("INVALID_QUALITY_CONFIG")
            report.analysis_errors.append(quality_config_error)
        qc_status = report.status if report is not None else "UNAVAILABLE"
        try:
            save_render_quality_report(
                result_path, quality_enabled, report, quality_started_ns)
        except (OSError, ValueError, TypeError, AttributeError) as error:
            log_message(
                f"Quality report could not be saved: {error}. Audio export is still available.")
            qc_status = "UNAVAILABLE (report could not be saved)"
        export_status = f"✓ Exported: {output_name}.mp3"
        if quality_enabled:
            export_status += f" — QC: {qc_status}"
            log_message("[AudioQC] RESULT: {}{}".format(
                qc_status, " - " + ", ".join(report.failures + report.warnings)
                if report is not None and (report.failures or report.warnings) else ""))

        # Delete voice recordings if requested
        if delete_voice:
            # Delete all original voice files
            for vpath in voice_paths:
                if vpath and os.path.exists(vpath):
                    try:
                        os.remove(vpath)
                        log_message(
                            f"Deleted voice recording: {os.path.basename(vpath)}")
                    except Exception as e:
                        log_message(
                            f"Warning: Could not delete voice file {vpath}: {e}")

            # Delete concatenated file if it exists and is different from originals
            if concatenated_file and os.path.exists(concatenated_file):
                try:
                    os.remove(concatenated_file)
                    log_message(
                        f"Deleted concatenated file: {os.path.basename(concatenated_file)}")
                except Exception as e:
                    log_message(
                        f"Warning: Could not delete concatenated file: {e}")

        log_message(export_status)
        log_message("=" * 50)

        autoplay_script = ""

        if generate_transcript:
            log_message(export_status)
            current_console = get_console_log()
            yield export_status, result_path, denoised_path, None, current_console, get_progress_html(0.9, "Preparing transcript..."), get_bottom_console_html(current_console)

            log_message("📝 Starting transcription in background...")
            progress(0.95, "📝 Transcribing (background)...")

            def run_background_transcription():
                transcript_path_local = audio_processor.transcribe_podcast(
                    audio_file=result_path,
                    whisper_model=whisper_model,
                    log_callback=log_message
                )

                if transcript_path_local and os.path.exists(transcript_path_local):
                    log_message(
                        f"✓ Background transcript ready: {os.path.basename(transcript_path_local)}")
                else:
                    log_message(
                        "⚠ Background transcription finished without a transcript file.")

            bg_thread = threading.Thread(
                target=run_background_transcription, daemon=True)
            bg_thread.start()

            final_console_log = get_console_log()
            yield export_status, result_path, denoised_path, None, final_console_log, get_progress_html(1.0, "✅ Export complete"), get_bottom_console_html(final_console_log, visible=True, show_close=True, download_path=result_path)
        else:
            final_transcript = transcript_path if transcript_path and os.path.exists(
                transcript_path) else None
            final_console_log = get_console_log()
            yield export_status, result_path, denoised_path, final_transcript, final_console_log, get_progress_html(1.0, "✅ Export complete") + autoplay_script, get_bottom_console_html(final_console_log, visible=True, show_close=True, download_path=result_path)


def create_podcast_handler(voice_file, output_name, delete_voice, trim_silence, denoise_audio, denoise_method, normalize_lufs, target_lufs):
    """Handle podcast creation request.

    Args:
        voice_file: Uploaded voice file
        output_name: Desired output filename
        delete_voice: Whether to delete voice file after creation
        trim_silence: Whether to trim silence from start/end
        denoise_audio: Whether to denoise audio
        denoise_method: Noise reduction method to use
        normalize_lufs: Whether to normalize to target LUFS
        target_lufs: Target LUFS level

    Returns:
        Tuple of (status message, output file path or None, denoised file path or None, transcript file path or None, console log)
    """
    log_message("=" * 50)
    log_message("Starting new podcast creation")

    if voice_file is None:
        log_message("Error: No voice file provided")
        return "Error: Please upload a voice recording file", None, None, None, get_console_log()

    if not output_name or output_name.strip() == "":
        output_name = "podcast_output"

    # Remove extension if provided
    output_name = output_name.replace(".mp3", "")
    log_message(f"Output filename: {output_name}.mp3")

    # Save voice file
    voice_path = save_uploaded_file(voice_file, "voice")
    if not voice_path:
        log_message("Error: Could not save voice file")
        return "Error: Could not save voice file", None, None, None, get_console_log()

    # Get configuration
    intro_path = config_manager.get_intro()
    outro_path = config_manager.get_outro()
    background_tracks = config_manager.get_background_tracks()
    volume = config_manager.get_volume()
    track_volumes = config_manager.get_all_track_volumes()

    log_message(f"Configuration loaded:")
    log_message(f"  Intro: {intro_path if intro_path else 'None'}")
    log_message(f"  Outro: {outro_path if outro_path else 'None'}")
    log_message(
        f"  Background tracks: {len(background_tracks) if background_tracks else 0}")
    log_message(f"  Volume: {volume}%")
    log_message(f"  Trim silence: {trim_silence}")
    log_message(f"  Denoise audio: {denoise_audio} (method: {denoise_method})")
    log_message(f"  Normalize LUFS: {normalize_lufs} (target: {target_lufs})")

    # Create output path
    output_path = os.path.join("outputs", f"{output_name}.mp3")

    # Save output name for next time
    config_manager.update_last_output_name(output_name)

    try:
        # Create podcast
        result_path, denoised_path, transcript_path = audio_processor.create_podcast(
            voice_file=voice_path,
            intro_file=intro_path,
            outro_file=outro_path,
            background_files=background_tracks if background_tracks else None,
            background_volume=volume,
            track_volumes=track_volumes if track_volumes else None,
            output_file=output_path,
            trim_silence=trim_silence,
            denoise_audio=denoise_audio,
            denoise_method=denoise_method,
            normalize_lufs=normalize_lufs,
            target_lufs=target_lufs,
            log_callback=log_message
        )

        # Delete voice recording if requested
        if delete_voice and voice_path and os.path.exists(voice_path):
            try:
                os.remove(voice_path)
                log_message(f"Deleted voice recording: {voice_path}")
            except Exception as e:
                log_message(f"Warning: Could not delete voice file: {e}")

        log_message(f"✓ Podcast created successfully: {output_name}.mp3")
        log_message("=" * 50)
        return f"✓ Podcast created successfully: {output_name}.mp3", result_path, denoised_path, transcript_path, get_console_log()

    except Exception as e:
        error_msg = f"Error creating podcast: {str(e)}"
        log_message(error_msg)
        log_message("=" * 50)
        return error_msg, None, None, None, get_console_log()


def denoise_audio_only_handler(voice_file, delete_after):
    """Run AI Denoiser as a standalone preprocessing step.

    Args:
        voice_file: Uploaded voice file to denoise
        delete_after: Whether to delete the uploaded original after processing

    Returns:
        Tuple of (status message, denoised audio file path or None, console log)
    """
    log_message("=" * 50)
    log_message("Starting standalone AI Denoiser run")

    if voice_file is None:
        log_message("Error: Please upload a voice recording to denoise")
        return "Error: Please upload a voice recording", None, get_console_log()

    saved_voice = save_uploaded_file(voice_file, "denoise")
    if not saved_voice:
        log_message("Error: Could not save uploaded voice file")
        return "Error: Could not save uploaded voice file", None, get_console_log()

    try:
        denoised_path = denoise_audio_file(
            input_file=saved_voice,
            enabled=True,
            log_callback=log_message
        )

        if delete_after and os.path.exists(saved_voice):
            try:
                os.remove(saved_voice)
                log_message(
                    f"Deleted original upload: {os.path.basename(saved_voice)}")
            except Exception as delete_error:
                log_message(
                    f"Warning: Unable to delete original upload: {delete_error}")

        if denoised_path and os.path.exists(denoised_path) and denoised_path != saved_voice:
            log_message(
                f"Standalone denoising ready: {os.path.basename(denoised_path)}")
            log_message("=" * 50)
            return f"✓ Denoised audio ready: {os.path.basename(denoised_path)}", denoised_path, get_console_log()
        elif denoised_path == saved_voice:
            log_message(
                "Audio denoiser skipped processing (not available or file too large)")
            log_message("=" * 50)
            return "Audio denoiser skipped - check console log for details", denoised_path, get_console_log()

        log_message(
            "AI Denoiser returned no file. Please check console log for details.")
        log_message("=" * 50)
        return "Denoising failed. Please check the console log for details.", None, get_console_log()

    except Exception as exc:
        log_message(f"Error denoising audio: {exc}")
        log_message("=" * 50)
        return f"Error denoising audio: {exc}", None, get_console_log()


def export_settings() -> str:
    """Export current settings to a JSON file.

    Returns:
        Path to the exported settings file
    """
    import json
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"podcast_settings_{timestamp}.json"
    filepath = os.path.join("outputs", filename)

    try:
        # Get current configuration
        cfg = saved_settings_snapshot()
        settings = {key: cfg[key] for key in (
            *SETTINGS_FIELDS, "track_volumes", "last_output_name")}
        settings["export_date"] = datetime.datetime.now().isoformat()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)

        log_message(f"Settings exported to: {filename}")
        return filepath
    except Exception as e:
        log_message(f"Error exporting settings: {e}")
        return None


def import_settings(settings_file) -> str:
    """Import settings from a JSON file.

    Args:
        settings_file: Uploaded settings file

    Returns:
        Status message
    """
    import json

    if settings_file is None:
        return "No settings file provided"

    try:
        # Handle Gradio file path
        if isinstance(settings_file, str):
            file_path = settings_file
        elif hasattr(settings_file, 'name'):
            file_path = settings_file.name
        else:
            file_path = str(settings_file)

        # Basic security check - ensure it's a JSON file
        if not file_path.lower().endswith('.json'):
            return "Error: Only JSON files are supported"

        # Check if file exists
        if not os.path.exists(file_path):
            return "Error: Settings file not found"

        # Read settings file with size limit (1MB max)
        file_size = os.path.getsize(file_path)
        if file_size > 1024 * 1024:  # 1MB
            return "Error: Settings file too large (max 1MB)"

        # Validate JSON content
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                settings = json.load(f)
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON format - {str(e)}"

        # Ensure settings is a dictionary
        if not isinstance(settings, dict):
            return "Error: Settings file must contain a JSON object"

        # Validate and import settings
        if "intro_file" in settings:
            intro = settings["intro_file"]
            if intro and os.path.exists(intro):
                config_manager.update_intro(intro)

        if "outro_file" in settings:
            outro = settings["outro_file"]
            if outro and os.path.exists(outro):
                config_manager.update_outro(outro)

        if "background_tracks" in settings:
            tracks = settings["background_tracks"]
            valid_tracks = [t for t in tracks if os.path.exists(t)]
            if valid_tracks:
                config_manager.update_background_tracks(valid_tracks)

        if "background_volume" in settings:
            config_manager.update_volume(settings["background_volume"])

        if "track_volumes" in settings:
            # Import track volumes
            track_volumes = settings["track_volumes"]
            for track, volume in track_volumes.items():
                if os.path.exists(track):
                    config_manager.set_track_volume(track, volume)

        if "last_output_name" in settings:
            config_manager.update_last_output_name(
                settings["last_output_name"])

        if "rss_feed_url" in settings:
            config_manager.set_rss_feed_url(settings["rss_feed_url"])

        if "prioritize_recording_filename" in settings:
            config_manager.set_prioritize_recording_filename(
                bool(settings["prioritize_recording_filename"]))

        # Overlap settings
        if "intro_voice_overlap" in settings:
            config_manager.set_intro_voice_overlap(
                settings["intro_voice_overlap"])

        if "voice_outro_overlap" in settings:
            config_manager.set_voice_outro_overlap(
                settings["voice_outro_overlap"])

        log_message(
            f"Settings imported successfully from {os.path.basename(file_path)}")
        return f"✓ Settings imported successfully from {os.path.basename(file_path)}"

    except json.JSONDecodeError as e:
        error_msg = f"Error: Invalid settings file format - {e}"
        log_message(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error importing settings: {e}"
        log_message(error_msg)
        return error_msg


def save_template_handler(template_name: str) -> tuple[str, str]:
    """Handler to save current settings as a template.

    Args:
        template_name: Name for the new template

    Returns:
        Tuple of (dropdown_choices_json, status_message)
    """
    import json

    if not template_name or not template_name.strip():
        return json.dumps([]), "❌ Please enter a template name"

    try:
        # Get current settings from config manager
        cfg = saved_settings_snapshot()
        settings = {key: cfg[key] for key in (
            *SETTINGS_FIELDS, "track_volumes")}

        # Save template
        success, message = template_manager.save_template(
            template_name, settings)

        if success:
            log_message(f"Template saved: {template_name}")
            config_manager.set_active_template(template_name)

            # Return updated template list
            templates = template_manager.list_templates()
            return json.dumps(templates), f"✅ {message}"
        else:
            log_message(f"Failed to save template: {message}")
            return json.dumps([]), f"❌ {message}"
    except Exception as e:
        log_message(f"Error saving template: {e}")
        return json.dumps([]), f"❌ Error: {str(e)}"


def load_template_handler(template_name: str) -> str:
    """Handler to load settings from a template.

    Args:
        template_name: Name of the template to load

    Returns:
        Status message
    """
    if not template_name or not template_name.strip():
        return "❌ Please select a template"

    try:
        # Load template
        settings, message = template_manager.load_template(template_name)

        if settings:
            # Apply settings to config manager
            config_manager.update_settings(
                dict(settings, active_template=template_name))
            log_message(f"Template loaded: {template_name}")
            return f"✅ {message}"
        else:
            log_message(f"Failed to load template: {message}")
            return f"❌ {message}"
    except Exception as e:
        log_message(f"Error loading template: {e}")
        return f"❌ Error: {str(e)}"


def delete_template_handler(template_name: str) -> tuple[str, str]:
    """Handler to delete a template.

    Args:
        template_name: Name of the template to delete

    Returns:
        Tuple of (dropdown_choices_json, status_message)
    """
    import json

    if not template_name or not template_name.strip():
        return json.dumps([]), "❌ Please select a template to delete"

    try:
        # Delete template
        success, message = template_manager.delete_template(template_name)

        if success:
            log_message(f"Template deleted: {template_name}")

            # Clear active template if it was deleted
            if config_manager.get_active_template() == template_name:
                config_manager.set_active_template(None)

            # Return updated template list
            templates = template_manager.list_templates()
            return json.dumps(templates), f"✅ {message}"
        else:
            log_message(f"Failed to delete template: {message}")
            templates = template_manager.list_templates()
            return json.dumps(templates), f"❌ {message}"
    except Exception as e:
        log_message(f"Error deleting template: {e}")
        return json.dumps([]), f"❌ Error: {str(e)}"


def get_template_choices() -> List[str]:
    """Get list of available templates for dropdown.

    Returns:
        List of template names
    """
    try:
        return template_manager.list_templates()
    except Exception as e:
        log_message(f"Error getting template list: {e}")
        return []


def extract_ntn_number(title: Optional[str]) -> Optional[int]:
    """Extract NTN episode number from a title string."""

    if not title:
        return None

    match = re.search(r"ntn\s*(\d+)", title, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def fetch_rss_episode_info(feed_url: Optional[str], force_refresh: bool = False) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Fetch latest episode info from RSS feed.

    Returns a tuple of (last_title, next_slug, error_message).
    """

    url = (feed_url or DEFAULT_RSS_FEED_URL).strip()

    if not force_refresh and rss_cache.get("url") == url and (rss_cache.get("last_title") or rss_cache.get("error")):
        return rss_cache.get("last_title"), rss_cache.get("next_slug"), rss_cache.get("error")

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read()

        root = ET.fromstring(data)
        title_el = root.find('.//channel/item/title')
        last_title = title_el.text.strip() if title_el is not None and title_el.text else None

        episode_number = extract_ntn_number(last_title)
        next_slug = f"ntn{episode_number + 1}" if episode_number is not None else None

        rss_cache.update({
            "url": url,
            "last_title": last_title,
            "next_slug": next_slug,
            "error": None
        })

        return last_title, next_slug, None
    except Exception as exc:  # pragma: no cover - network errors
        error_message = str(exc)
        rss_cache.update({
            "url": url,
            "last_title": None,
            "next_slug": None,
            "error": error_message
        })
        log_message(f"RSS fetch failed: {error_message}")
        return None, None, error_message


def build_rss_status_html(last_title: Optional[str], next_slug: Optional[str], error: Optional[str] = None) -> str:
    """Render a small HTML snippet showing RSS state."""

    lines = ["<div style=\"font-size:14px; line-height:1.4;\">"]

    if last_title:
        lines.append(f"<div>Last episode: <strong>{last_title}</strong></div>")
    else:
        lines.append("<div>Last episode: <strong>Unavailable</strong></div>")

    if next_slug:
        lines.append(
            f"<div>Next suggested: <strong>{next_slug}</strong></div>")
    else:
        lines.append(
            "<div>Next suggested: <strong>Waiting for feed</strong></div>")

    if error:
        lines.append(f"<div style=\"color:#c00;\">RSS error: {error}</div>")

    lines.append("</div>")
    return "".join(lines)


def suggest_podcast_name(voice_file) -> str:
    """Generate suggested podcast filename using RSS; fallback is a simple default slug."""

    rss_url = config_manager.get_rss_feed_url()
    _, next_slug, _ = fetch_rss_episode_info(rss_url)

    if next_slug:
        return next_slug

    # Minimal fallback to keep the field populated if RSS is unavailable
    return "ntn001"


def refresh_rss_feed_settings(feed_url: Optional[str], current_output_name: Optional[str]) -> Tuple[str, str]:
    """Refresh RSS feed data, persist URL, and produce status + suggested name."""

    rss_url = (feed_url or DEFAULT_RSS_FEED_URL).strip()
    config_manager.set_rss_feed_url(rss_url)

    last_title, next_slug, error = fetch_rss_episode_info(
        rss_url, force_refresh=True)
    status_html = build_rss_status_html(last_title, next_slug, error)

    suggested_name = next_slug or current_output_name or "ntn001"
    return status_html, suggested_name


def get_bottom_console_html(console_text: str, visible: bool = True,
                            show_close: bool = False, download_path=None) -> str:
    """Inline, keyboard-accessible log; exports live in the result DownloadButton."""
    display = "block" if visible and console_text else "none"
    return (f'<details class="episode-log" style="display: {display}">'
            '<summary>Processing log</summary>'
            f'<pre>{html.escape(console_text)}</pre></details>')


def get_progress_html(pct, msg):
    """Compact inline progress, never a floating overlay."""
    percent = max(0, min(100, int(pct * 100)))
    return (f'<div class="episode-progress" role="status" aria-live="polite">'
            f'<span>{html.escape(str(msg))} · {percent}%</span>'
            f'<progress aria-label="Episode progress" max="100" value="{percent}"></progress></div>')


def saved_settings_snapshot():
    """Detached, default-merged values from the atomic configuration API."""
    return config_manager.snapshot()


def _render_snapshot():
    snapshot = saved_settings_snapshot()
    try:
        # Validate the same generation, never a second read of mutable config.
        settings = snapshot["audio_quality"]
        if not isinstance(settings, dict):
            raise ValueError("audio_quality must be a settings object")
        snapshot["quality_config"] = AudioQualityConfig.from_mapping(
            dict(settings, target_lufs=snapshot["target_lufs"]))
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        snapshot["quality_config_error"] = str(error)
    return snapshot


def create_podcast_handler_with_progress(
    voice_file, output_name, delete_voice, trim_silence, denoise_audio,
    denoise_method, enhance_voice, voice_enhancement_preset, normalize_lufs,
    target_lufs, intro_voice_overlap, voice_outro_overlap, generate_transcript,
    whisper_model, auto_balance_levels=True, auto_ducking=True,
    voice_order_table=None, intro_override_file=None, progress=gr.Progress()
):
    """Legacy positional API: explicit processing choices win over saved values."""
    snapshot = _render_snapshot()
    for status, audio, cleaned, transcript, console, bar, log in _render_episode(
        voice_file, output_name, delete_voice, trim_silence, denoise_audio,
        denoise_method, enhance_voice, voice_enhancement_preset, normalize_lufs,
        target_lufs, intro_voice_overlap, voice_outro_overlap, generate_transcript,
        whisper_model, auto_balance_levels, auto_ducking, deepcopy(
            voice_order_table),
        intro_override_file, progress, snapshot=snapshot
    ):
        yield status, audio, cleaned, transcript, console, bar, log


def create_episode_from_saved(voice, name, order, intro_override, progress=gr.Progress()):
    """The main screen accepts episode inputs ONLY, never draft settings controls."""
    snapshot = _render_snapshot()
    yield from _render_episode(
        deepcopy(
            voice), name, snapshot["delete_voice"], snapshot["trim_silence"],
        snapshot["denoise_audio"], snapshot["denoise_method"], snapshot["enhance_voice"],
        snapshot["voice_enhancement_preset"], snapshot["normalize_lufs"], snapshot["target_lufs"],
        snapshot["intro_voice_overlap"], snapshot["voice_outro_overlap"],
        snapshot["generate_transcript"], snapshot["whisper_model"],
        snapshot["auto_balance_levels"], snapshot["auto_ducking"], deepcopy(
            order),
        intro_override, progress, snapshot=snapshot
    )


# One ordered mapping is shared by Save, Discard, template/import refresh, and tests.
SETTINGS_FIELDS = (
    "intro_file", "outro_file", "background_tracks", "background_volume", "delete_voice", "trim_silence",
    "prioritize_recording_filename", "rss_feed_url", "intro_voice_overlap",
    "voice_outro_overlap", "denoise_audio", "denoise_method", "enhance_voice",
    "voice_enhancement_preset", "normalize_lufs", "target_lufs", "auto_balance_levels",
    "min_voice_music_separation_db", "auto_ducking", "generate_transcript", "whisper_model",
    "quality_gate_enabled", "audio_quality", "music_seed",
)


def background_level_description(volume) -> str:
    """Explain the master music percentage using an audible dB reference."""
    try:
        value = float(volume)
    except (TypeError, ValueError, OverflowError):
        return "Choose a background level. Chill (5%) is recommended."
    if not math.isfinite(value) or value <= 0:
        return "**Off** — no background music will be audible."
    gain = 20 * math.log10(value / 100)
    if value <= 3:
        name = "Barely audible"
    elif value <= 7:
        name = "Chill"
    else:
        name = "Present"
    return f"**{name}** — {value:g}% (approximately {gain:.0f} dB below the source track)."


def saved_settings_summary():
    cfg = saved_settings_snapshot()
    parts = [
        f'{len(cfg["background_tracks"])} music tracks · {cfg["background_volume"]}%']
    parts.append("intro " + ("on" if cfg["intro_file"] else "off"))
    parts.append("outro " + ("on" if cfg["outro_file"] else "off"))
    parts.append(
        f'{cfg["target_lufs"]} LUFS' if cfg["normalize_lufs"] else "normalization off")
    parts.append("quality check " +
                 ("on" if cfg["quality_gate_enabled"] else "off"))
    return '<p class="saved-summary"><strong>Saved settings</strong> · ' + html.escape(" · ".join(parts)) + '</p>'


def settings_form_values():
    cfg = saved_settings_snapshot()
    _, raw, _ = quality_settings_values()
    cfg["audio_quality"] = raw
    return tuple(deepcopy(cfg[key]) for key in SETTINGS_FIELDS) + (deepcopy(cfg["track_volumes"]),)


def save_episode_settings(*values):
    """One validated atomic save, with no partial mutation on errors."""
    try:
        if len(values) != len(SETTINGS_FIELDS) + 1:
            raise ValueError("Incomplete settings form")
        settings = dict(zip(SETTINGS_FIELDS, values[:-1]))
        settings["audio_quality"] = json.loads(settings["audio_quality"])
        selected = set(settings["background_tracks"] or [])
        settings["track_volumes"] = {
            path: volume for path, volume in deepcopy(values[-1] or {}).items()
            if path in selected
        }
        config_manager.update_settings(settings)
        return "Settings saved. The next episode will use these settings.", saved_settings_summary()
    except (ValueError, TypeError, OverflowError, OSError) as error:
        return "Settings not saved: " + str(error), saved_settings_summary()


def discard_episode_settings():
    return ("Draft discarded; showing saved settings.", saved_settings_summary(), *settings_form_values())


def stage_track_volume(track, volume, draft):
    """Session-local draft only; selecting a track must not overwrite another."""
    staged = deepcopy(draft or {})
    if track:
        staged[track] = volume
    return staged


def load_episode_template(name):
    status = load_template_handler(name)
    return status, saved_settings_summary(), *settings_form_values()


def import_episode_settings(path):
    try:
        if not path or not str(path).lower().endswith(".json"):
            raise ValueError("Choose a JSON settings file")
        if os.path.getsize(path) > 1024 * 1024:
            raise ValueError("Settings file too large (max 1MB)")
        with open(path, encoding="utf-8") as stream:
            settings = json.load(stream)
        if not isinstance(settings, dict):
            raise ValueError("Settings must be a JSON object")
        # Older exports included this metadata.
        settings.pop("export_date", None)
        config_manager.update_settings(settings)
        status = "Imported settings applied. Draft discarded."
    except (ValueError, TypeError, OSError) as error:
        status = "Settings not imported: " + str(error)
    return status, saved_settings_summary(), *settings_form_values()


def export_episode_settings():
    cfg = saved_settings_snapshot()
    settings = {key: cfg[key] for key in (
        *SETTINGS_FIELDS, "track_volumes")}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", prefix="podcast_settings_",
                                     dir="outputs", delete=False, encoding="utf-8") as stream:
        json.dump(settings, stream, indent=2)
        return stream.name


def episode_marker(state):
    return f'<span data-state="{html.escape(state, quote=True)}" aria-hidden="true"></span>'


def episode_upload_details(voice):
    files = prioritize_recording_files(voice, saved_settings_snapshot()[
                                       "prioritize_recording_filename"])
    rows = build_voice_order_rows(files)
    listing = ''.join(
        f'<li>{html.escape(os.path.basename(path))} · {get_audio_duration(path)}</li>' for path in files)
    return (rows, [row[:2] for row in rows], [[row[1], row[2]] for row in rows],
            f'<ul class="recording-list">{listing}</ul>' if files else "",
            episode_marker("multiple" if len(files) > 1 else "single" if files else "empty"))


def stage_episode_order(table, rows, voice):
    flags = {}
    for _, name, enabled in rows or []:
        flags.setdefault(name, []).append(enabled)
    merged = []
    for position, name in table or []:
        available = flags.get(name, [])
        merged.append([position, name, available.pop(
            0) if available else should_enable_background_for_filename(name)])
    normalized = normalize_voice_order_table(
        merged, voice, apply_move_action=False)
    return normalized, [row[:2] for row in normalized], [[row[1], row[2]] for row in normalized]


def stage_episode_background(table, rows):
    updated = deepcopy(rows or [])
    for index, row in enumerate(updated):
        if table and index < len(table):
            row[2] = parse_background_enabled_value(
                table[index][1], default=row[2])
    return updated


def episode_premix(voice, order, intro_override):
    if not voice:
        return "", "", ""
    ordered = order_voice_segments(voice, order)
    paths, flags = [p for p, _ in ordered], [enabled for _, enabled in ordered]
    cfg = saved_settings_snapshot()
    try:
        analysis = audio_processor.analyze_levels(
            paths, background_files=cfg["background_tracks"], background_volume=cfg["background_volume"],
            track_volumes=cfg["track_volumes"], quality_config=config_manager.get_audio_quality_config())
    except Exception as error:
        analysis = None
        log_message(f"Premix analysis unavailable: {error}")
    alert = ""
    if analysis and analysis.get("overall_status") in {"warning", "danger"}:
        alert = '<p role="status">Review audio balance before creating. See Timeline & premix details.</p>'
    return preview_timeline(paths, intro_override, flags), render_audio_health_card(analysis), alert


def episode_quality_summary(path, started=0):
    if not path:
        return "", episode_marker("empty")
    try:
        _, data, report = _load_render_quality_report(path, started)
        if not data["ui"]["enabled"]:
            return '<p class="qc-neutral">Quality check disabled for this render.</p>', episode_marker("disabled")
        if report is None:
            raise ValueError("No report")
        state = report.status.lower()
        label = {"pass": "Ready to publish", "warn": "Review recommended",
                 "fail": "Quality check failed — review before publishing"}[state]
        override = " · Download override acknowledged" if data["ui"].get(
            "override") else ""
        return f'<p class="qc-{state}" role="status">{label}{override}</p>', episode_marker(state)
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        return '<p class="qc-neutral">Quality check unavailable — export is not certified.</p>', episode_marker("unavailable")


def reset_episode_values(previous_preview=None):
    """Retire only owned temporary previews; never remove an actual export."""
    clear_final_quality_inspector(previous_preview)
    return {"voice": None, "order": [], "intro_override": None,
            "name": suggest_podcast_name(None), "started": 0,
            "preview_receipt": None, "export": None, "cleaned": None,
            "transcript": None, "status": "", "progress": "", "log": "",
            "quality": "", "report": None, "preview": None}


EPISODE_CSS = """
<style>
.gradio-container {max-width: 1080px !important; margin: auto;}
#episode-create {max-width: 800px; margin: auto;}
#episode-hero {border: 2px dashed var(--border-color-primary); border-radius: 16px;}
#episode-summary-row {align-items: center;}
.episode-primary {background: #4f46e5 !important; color: #fff !important; border-color: #4f46e5 !important;}
.saved-summary {font-size: .9rem; color: var(--body-text-color-subdued);}
.sound-card {padding: 1rem; border: 1px solid var(--border-color-primary); border-radius: .75rem; margin-bottom: .75rem;}
.sound-card h3 {margin-top: 0;}
.sound-note {font-size: .9rem; color: var(--body-text-color-subdued);}
.recording-list {padding-inline-start: 1.3rem; overflow-wrap: anywhere;}
.episode-log pre {max-height: 240px; overflow: auto; white-space: pre-wrap; font-size: .85rem;}
.episode-log summary {cursor: pointer; padding: .5rem 0;}
.episode-progress {display: grid; gap: .35rem; font-size: .9rem;}
.episode-progress progress {width: 100%; accent-color: #6366f1;}
#episode-results:not(:has([data-state="ready"])) {display: none !important;}
#episode-create:not(:has(#upload-state [data-state="multiple"])) #episode-order {display: none !important;}
#episode-create:has(#upload-state [data-state="empty"]) #episode-options,
#episode-create:has(#upload-state [data-state="empty"]) #episode-premix {display: none !important;}
.available-only:not(:has([data-state="available"])) {display: none !important;}
#episode-qc-actions:not(:has([data-state="warn"], [data-state="fail"])) {display: none !important;}
.state-marker {display: none !important;}
.qc-pass,.qc-warn,.qc-fail,.qc-neutral {padding: .65rem .9rem; border-radius: .6rem; border-inline-start: 4px solid;}
.qc-pass {color: #065f46; background: #d1fae5;}
.qc-warn {color: #78350f; background: #fef3c7;}
.qc-fail {color: #991b1b; background: #fee2e2;}
.qc-neutral {color: var(--body-text-color); background: var(--background-fill-secondary);}
.dark .qc-pass {color: #a7f3d0; background: #064e3b;}
.dark .qc-warn {color: #fde68a; background: #451a03;}
.dark .qc-fail {color: #fecaca; background: #450a0a;}
button:focus-visible,summary:focus-visible {outline: 3px solid #818cf8; outline-offset: 3px;}
@media(max-width: 640px) {
    .gradio-container {padding: 12px !important;}
    .saved-summary {line-height: 1.6;}
    #episode-summary-row {flex-direction: column; align-items: stretch;}
    #episode-summary-row > * {width: 100%;}
}
</style>
"""


def create_ui():
    """Two destinations: make an episode, or deliberately change saved defaults."""
    cfg = saved_settings_snapshot()
    form_values = dict(zip(SETTINGS_FIELDS, settings_form_values()))

    def audio_choices(folder=None, configured=()):
        """Offer audio files only, including configured files outside the library."""
        paths = {path for path in configured if path}
        if folder:
            directory = os.path.join("audios", folder)
            paths.update(os.path.join(directory, name)
                         for name in os.listdir(directory))
        extensions = {".mp3", ".wav", ".m4a",
                      ".ogg", ".flac", ".aac", ".aiff", ".wma"}
        return [(os.path.basename(path), path) for path in sorted(paths)
                if os.path.splitext(path)[1].lower() in extensions and os.path.isfile(path)]

    with gr.Blocks(title="NTN Podcast Creator") as app:
        gr.HTML(EPISODE_CSS)
        gr.Markdown("# NTN Podcast Creator")
        order = gr.State([])
        exported = gr.State(None)
        cleaned = gr.State(None)
        transcript = gr.State(None)
        console = gr.State("")
        started = gr.State(0)
        preview_receipt = gr.State(None)
        busy = gr.State(False)
        track_draft = gr.State(deepcopy(cfg["track_volumes"]))
        with gr.Tabs(selected="create") as tabs:
            with gr.Tab("Create Episode", id="create"):
                with gr.Column(elem_id="episode-create"):
                    gr.Markdown("### Your next episode starts here")
                    voice = gr.File(label="Upload recordings", file_count="multiple", file_types=["audio"],
                                    type="filepath", elem_id="episode-hero")
                    upload_state = gr.HTML(episode_marker(
                        "empty"), elem_id="upload-state", elem_classes=["state-marker"])
                    recordings = gr.HTML("")
                    with gr.Column(elem_id="episode-order"):
                        order_table = gr.Dataframe(headers=["Order", "Recording"], datatype=["number", "str"],
                                                   value=[], type="array", interactive=True, static_columns=[1], label="Recording order")
                    with gr.Row():
                        name = gr.Textbox(label="Episode name", value=suggest_podcast_name(
                            None), interactive=False, scale=5, min_width=180)
                        edit_name = gr.Button(
                            "Edit", size="sm", scale=0, min_width=64)
                    create = gr.Button("Create Episode", variant="primary", size="lg", elem_classes=[
                                       "episode-primary"])
                    with gr.Row(elem_id="episode-summary-row"):
                        summary = gr.HTML(
                            saved_settings_summary(), min_width=240)
                        change = gr.Button(
                            "Change settings", size="sm", min_width=130)
                    with gr.Accordion("Episode options", open=False, elem_id="episode-options"):
                        background = gr.Dataframe(headers=["Recording", "Background music"], datatype=["str", "bool"],
                                                  value=[], type="array", interactive=True, static_columns=[0], label="Per-recording background")
                        intro_override = gr.File(label="Custom intro for this episode only", file_types=[
                                                 "audio"], type="filepath")
                    alert = gr.HTML("")
                    with gr.Accordion("Timeline & premix details", open=False, elem_id="episode-premix"):
                        timeline = gr.HTML("")
                        health = gr.HTML("")
                    status = gr.Markdown("")
                    progress_html = gr.HTML("")
                    log = gr.HTML("")
                    with gr.Column(elem_id="episode-results"):
                        result_state = gr.HTML(episode_marker(
                            "empty"), elem_classes=["state-marker"])
                        audio = gr.Audio(label="Your episode",
                                         type="filepath", interactive=False)
                        with gr.Row():
                            download = gr.DownloadButton(
                                "Download episode", variant="primary", value=None, elem_classes=["episode-primary"])
                            another = gr.Button("Create another")
                        qc_summary = gr.HTML("")
                        with gr.Column(elem_id="episode-qc-actions"):
                            qc_state = gr.HTML(episode_marker(
                                "empty"), elem_classes=["state-marker"])
                            with gr.Row():
                                override = gr.Button(
                                    "Download anyway — acknowledge warning")
                                fix = gr.Button(
                                    "Apply suggested settings for next render")
                        action_status = gr.Markdown("")
                        with gr.Column(elem_classes=["available-only"]):
                            preview_state = gr.HTML(episode_marker(
                                "empty"), elem_classes=["state-marker"])
                            preview = gr.Audio(
                                label="Preview worst section", type="filepath", interactive=False)
                        with gr.Accordion("Technical details", open=False):
                            raw = gr.HTML(
                                label="Final Audio Quality Inspector", value="")
                            with gr.Column(elem_classes=["available-only"]):
                                report_state = gr.HTML(episode_marker(
                                    "empty"), elem_classes=["state-marker"])
                                report_download = gr.File(
                                    label="Download quality report (JSON)", interactive=False)
                            with gr.Column(elem_classes=["available-only"]):
                                cleaned_state = gr.HTML(episode_marker(
                                    "empty"), elem_classes=["state-marker"])
                                cleaned_download = gr.File(
                                    label="Cleaned voice", interactive=False)
                            with gr.Column(elem_classes=["available-only"]):
                                transcript_state = gr.HTML(episode_marker(
                                    "empty"), elem_classes=["state-marker"])
                                transcript_download = gr.File(
                                    label="Transcript", interactive=False)
                            refresh_transcript = gr.Button(
                                "Check for background transcript", size="sm")
            with gr.Tab("Settings", id="settings"):
                gr.Markdown(
                    "### Saved defaults\nChanges here are drafts until **Save settings**. Episodes always use saved defaults.")
                with gr.Row():
                    save = gr.Button("Save settings", variant="primary")
                    discard = gr.Button("Discard changes")
                settings_status = gr.Markdown("")
                controls = {}
                labels = {
                    "intro_file": "Default intro", "outro_file": "Default outro",
                    "background_tracks": "Background tracks", "background_volume": "Master background level (%)", "delete_voice": "Delete voice recording after creation",
                    "trim_silence": "Trim silence from voice recording", "prioritize_recording_filename": "Prefer Recording.m4a first",
                    "rss_feed_url": "RSS Feed URL", "intro_voice_overlap": "Intro-voice overlap (1 second)",
                    "voice_outro_overlap": "Voice-outro overlap (1 second)", "denoise_audio": "Enable noise reduction",
                    "denoise_method": "Noise Reduction Method", "enhance_voice": "Enable professional voice enhancement",
                    "voice_enhancement_preset": "Enhancement Preset", "normalize_lufs": "Normalize audio to professional LUFS level",
                    "target_lufs": "Target LUFS Level", "auto_balance_levels": "Auto-balance voice & music levels (Recommended)",
                    "min_voice_music_separation_db": "Minimum voice/music separation (dB)", "auto_ducking": "Auto-ducking",
                    "generate_transcript": "Generate transcript with Whisper AI", "whisper_model": "Whisper Model",
                    "quality_gate_enabled": "Final Audio Quality Gate", "audio_quality": "Audio quality thresholds (JSON)",
                    "music_seed": "Music seed",
                }
                enums = {"denoise_method": ["audio_denoiser", "spectral", "rnnoise"],
                         "voice_enhancement_preset": ["podcast", "light", "aggressive"],
                         "whisper_model": ["tiny", "base", "small", "medium", "large"]}
                ranges = {"background_volume": (
                    0, 50), "target_lufs": (-30, -10), "min_voice_music_separation_db": (0, 40)}

                def build_setting(key):
                    value = form_values[key]
                    if key in {"intro_file", "outro_file"}:
                        folder = "intro_audio" if key == "intro_file" else "outro_audio"
                        choices = [("None", None)] + \
                            audio_choices(folder, [value])
                        available = {path for _, path in choices}
                        return gr.Dropdown(choices=choices, label=labels[key],
                                           value=value if value in available else None)
                    elif key == "background_tracks":
                        choices = audio_choices("background_music", value)
                        available = {path for _, path in choices}
                        return gr.Dropdown(
                            choices=choices,
                            value=[path for path in value if path in available],
                            multiselect=True, label=labels[key],
                            info="Select any number of tracks. They share the master level below.")
                    elif key in enums:
                        return gr.Dropdown(
                            enums[key], value=value, label=labels[key])
                    elif key in ranges:
                        low, high = ranges[key]
                        return gr.Slider(
                            low, high, value=value,
                            step=0.5 if key == "background_volume" else 1,
                            label=labels[key])
                    elif key == "audio_quality":
                        return gr.Textbox(
                            value=value, label=labels[key], lines=14)
                    elif key == "music_seed":
                        return gr.Number(
                            value=value, label=labels[key])
                    elif key == "rss_feed_url":
                        return gr.Textbox(
                            value=value, label=labels[key])
                    else:
                        return gr.Checkbox(
                            value=value, label=labels[key])

                with gr.Accordion("Podcast sound", open=True):
                    gr.Markdown(
                        "Choose one intro, one outro, and any number of background tracks.")
                    with gr.Column(elem_classes=["sound-card"]):
                        gr.Markdown(
                            "### Intro\n<span class='sound-note'>One file · original volume (100%) · never treated as background music.</span>")
                        controls["intro_file"] = build_setting("intro_file")
                        intro_preview = gr.Audio(
                            label="Preview intro", value=form_values["intro_file"]
                            if form_values["intro_file"] and os.path.isfile(form_values["intro_file"]) else None,
                            type="filepath", interactive=False)
                        controls["intro_voice_overlap"] = build_setting(
                            "intro_voice_overlap")
                    with gr.Column(elem_classes=["sound-card"]):
                        gr.Markdown(
                            "### Outro\n<span class='sound-note'>One file · original volume (100%) · never treated as background music.</span>")
                        controls["outro_file"] = build_setting("outro_file")
                        outro_preview = gr.Audio(
                            label="Preview outro", value=form_values["outro_file"]
                            if form_values["outro_file"] and os.path.isfile(form_values["outro_file"]) else None,
                            type="filepath", interactive=False)
                        controls["voice_outro_overlap"] = build_setting(
                            "voice_outro_overlap")
                    with gr.Column(elem_classes=["sound-card"]):
                        gr.Markdown(
                            "### Background music\n<span class='sound-note'>Multiple tracks · one intentionally quiet master level · ducked under speech.</span>")
                        controls["background_tracks"] = build_setting(
                            "background_tracks")
                        with gr.Row():
                            barely = gr.Button(
                                "Barely audible · 2.5%", size="sm")
                            chill = gr.Button(
                                "Chill · 5%", size="sm", variant="primary")
                            present = gr.Button("Present · 10%", size="sm")
                        controls["background_volume"] = build_setting(
                            "background_volume")
                        background_level = gr.Markdown(background_level_description(
                            form_values["background_volume"]))

                for title, keys in (
                    ("Voice processing", ("trim_silence", "denoise_audio", "enhance_voice",
                                          "auto_balance_levels", "auto_ducking")),
                    ("Output & quality", ("normalize_lufs", "target_lufs", "quality_gate_enabled",
                                          "generate_transcript", "delete_voice")),
                    ("Naming & RSS", ("prioritize_recording_filename", "rss_feed_url")),
                    ("Advanced", ("denoise_method", "voice_enhancement_preset", "whisper_model",
                                  "min_voice_music_separation_db", "audio_quality", "music_seed")),
                ):
                    with gr.Accordion(title, open=False):
                        for key in keys:
                            controls[key] = build_setting(key)
                with gr.Accordion("Advanced per-track volumes", open=False):
                    gr.Markdown(
                        "Optional: override the master level for one selected background track.")
                    track = gr.Dropdown(choices=audio_choices(
                        configured=cfg["background_tracks"]), label="Fine-tune selected track")
                    track_volume = gr.Slider(
                        0, 50, value=cfg["background_volume"], step=0.5, label="Per-track override (%)")
                    track_preview = gr.Audio(
                        label="Preview track at this level", type="filepath", interactive=False)
                    stage_all = gr.Button(
                        "Reset every selected track to the master level")
                with gr.Accordion("Audio library — actions apply immediately", open=False):
                    gr.Markdown(
                        "Adding an asset updates the library immediately. Select default intro/outro above, then Save settings.")
                    asset_kind = gr.Dropdown(
                        ["intro", "outro", "background"], value="background", label="Asset type")
                    asset_file = gr.File(label="Audio asset", file_types=[
                                         "audio"], type="filepath")
                    add_asset = gr.Button("Add to library now")
                    remove_track = gr.Button(
                        "Remove selected background track now")
                    asset_status = gr.Markdown("")
                with gr.Accordion("Templates & settings files", open=False):
                    template = gr.Dropdown(
                        get_template_choices(), label="Template")
                    with gr.Row():
                        load_template = gr.Button("Load and apply template")
                        delete_template = gr.Button("Delete template")
                    template_name = gr.Textbox(label="Template name")
                    save_template = gr.Button(
                        "Save saved settings as template")
                    import_file = gr.File(label="Settings JSON", file_types=[
                                          ".json"], type="filepath")
                    import_button = gr.Button("Import and apply settings")
                    export_button = gr.Button("Export saved settings")
                    settings_download = gr.File(
                        label="Saved settings download", interactive=False)
                with gr.Accordion("Tools", open=False):
                    tool_voice = gr.File(label="Recording to clean", file_types=[
                                         "audio"], type="filepath")
                    clean_button = gr.Button("Clean audio")
                    tool_status = gr.Markdown("")
                    tool_output = gr.File(
                        label="Cleaned audio download", interactive=False)
                    tool_log = gr.Textbox(label="Tool log", interactive=False)
                with gr.Accordion("Help & appearance", open=False):
                    gr.Markdown("Upload → Create Episode → Download. Review yellow/red quality results before publishing. "
                                "Suggested settings affect the next render only. Keep source recordings if you plan to rerender.")
                    theme = gr.Dropdown(
                        ["System", "Light", "Dark"], value="System", label="Theme")

        form = [controls[key] for key in SETTINGS_FIELDS] + [track_draft]
        refresh_form = [settings_status, summary] + form

        def refresh_asset_controls():
            saved = saved_settings_snapshot()
            return (
                gr.Dropdown(choices=[("None", None)] + audio_choices(
                    "intro_audio", [saved["intro_file"]]), value=saved["intro_file"]),
                saved["intro_file"] if saved["intro_file"] and os.path.isfile(
                    saved["intro_file"]) else None,
                gr.Dropdown(choices=[("None", None)] + audio_choices(
                    "outro_audio", [saved["outro_file"]]), value=saved["outro_file"]),
                saved["outro_file"] if saved["outro_file"] and os.path.isfile(
                    saved["outro_file"]) else None,
                gr.Dropdown(choices=audio_choices("background_music", saved["background_tracks"]),
                            value=saved["background_tracks"], multiselect=True),
                gr.Dropdown(choices=audio_choices(
                    configured=saved["background_tracks"]), value=None),
                saved["background_volume"],
                background_level_description(saved["background_volume"]),
            )

        asset_controls = [controls["intro_file"], intro_preview,
                          controls["outro_file"], outro_preview,
                          controls["background_tracks"], track, track_volume,
                          background_level]
        save.click(save_episode_settings, form, [settings_status, summary])
        discard.click(discard_episode_settings, [], refresh_form).then(
            refresh_asset_controls, [], asset_controls)
        load_template.click(load_episode_template, [template], refresh_form).then(
            refresh_asset_controls, [], asset_controls)
        import_button.click(import_episode_settings, [import_file], refresh_form).then(
            refresh_asset_controls, [], asset_controls)
        export_button.click(export_episode_settings, [], [settings_download])
        change.click(lambda: gr.Tabs(selected="settings"),
                     [], [tabs], queue=False)
        edit_name.click(lambda: gr.Textbox(
            interactive=True), [], [name], queue=False)
        theme.change(None, [theme], [], js="""(theme) => {
            const dark = theme === 'Dark' || (theme === 'System' && matchMedia('(prefers-color-scheme: dark)').matches);
            document.documentElement.classList.toggle('dark', dark);
            document.body.classList.toggle('dark', dark);
        }""")
        controls["intro_file"].change(
            lambda path: path if path and os.path.isfile(path) else None,
            [controls["intro_file"]], [intro_preview])
        controls["outro_file"].change(
            lambda path: path if path and os.path.isfile(path) else None,
            [controls["outro_file"]], [outro_preview])
        controls["background_volume"].input(
            background_level_description, [controls["background_volume"]], [background_level])
        for button, value in ((barely, 2.5), (chill, 5), (present, 10)):
            button.click(lambda selected=value: (
                selected, background_level_description(selected)), [],
                [controls["background_volume"], background_level])

        def stage_background_selection(paths, draft):
            selected = set(paths or [])
            staged = {path: volume for path, volume in (draft or {}).items()
                      if path in selected}
            return gr.Dropdown(choices=audio_choices(
                configured=paths or []), value=None), staged

        controls["background_tracks"].change(
            stage_background_selection,
            [controls["background_tracks"], track_draft], [track, track_draft])

        def select_track_for_preview(path, draft, global_volume):
            volume = (draft or {}).get(path, global_volume)
            return volume, generate_volume_preview(path, volume) if path else None

        track.change(select_track_for_preview,
                     [track, track_draft, controls["background_volume"]],
                     [track_volume, track_preview])

        def stage_track_preview(path, volume, draft):
            return stage_track_volume(path, volume, draft), (
                generate_volume_preview(path, volume) if path else None)

        track_volume.change(stage_track_preview, [
                            track, track_volume, track_draft], [track_draft, track_preview])
        stage_all.click(lambda volume, paths: {path: volume for path in (paths or [])},
                        [controls["background_volume"], controls["background_tracks"]], [track_draft])

        def library_action(kind, path, selected, remove=False):
            try:
                if remove:
                    tracks = saved_settings_snapshot()["background_tracks"]
                    config_manager.update_settings(
                        {"background_tracks": [p for p in tracks if p != selected]})
                    message = "Background track removed from saved defaults. Library file preserved."
                else:
                    if not path:
                        raise ValueError("Choose an audio asset")
                    folder = {"intro": "intro_audio", "outro": "outro_audio",
                              "background": "background_music"}[kind]
                    destination = os.path.join(
                        "audios", folder, os.path.basename(path))
                    if os.path.realpath(path) != os.path.realpath(destination):
                        shutil.copy2(path, destination)
                    message = "Asset added to the library. Select it above, then Save settings."
            except (OSError, ValueError, TypeError) as error:
                message = "Library action failed: " + str(error)
            saved = saved_settings_snapshot()
            # Choice-only updates preserve unsaved selections (including None).
            return (message, saved_settings_summary(),
                    gr.Dropdown(
                        choices=[("None", None)] + audio_choices("intro_audio", [saved["intro_file"]])),
                    gr.Dropdown(
                        choices=[("None", None)] + audio_choices("outro_audio", [saved["outro_file"]])),
                    gr.Dropdown(choices=audio_choices(
                        "background_music", saved["background_tracks"]), multiselect=True),
                    gr.Dropdown(choices=audio_choices(configured=saved["background_tracks"])))

        library_outputs = [asset_status, summary,
                           controls["intro_file"], controls["outro_file"],
                           controls["background_tracks"], track]
        add_asset.click(library_action, [
                        asset_kind, asset_file, track], library_outputs)
        remove_track.click(lambda kind, path, selected: library_action(kind, path, selected, True),
                           [asset_kind, asset_file, track], library_outputs)

        def save_template_ui(value):
            choices, message = save_template_handler(value)
            return gr.Dropdown(choices=json.loads(choices)), message

        def delete_template_ui(value):
            choices, message = delete_template_handler(value)
            return gr.Dropdown(choices=json.loads(choices), value=None), message

        save_template.click(save_template_ui, [template_name], [
                            template, settings_status])
        delete_template.click(delete_template_ui, [template], [
                              template, settings_status])
        clean_button.click(lambda path: denoise_audio_only_handler(path, saved_settings_snapshot()["delete_voice"]),
                           [tool_voice], [tool_status, tool_output, tool_log], concurrency_id="episode-render", concurrency_limit=1)

        result_components = [result_state, audio, download, qc_summary, raw, preview, preview_state,
                             report_download, report_state, cleaned_download, cleaned_state,
                             transcript_download, transcript_state, qc_state, action_status]

        def empty_results():
            empty = episode_marker("empty")
            return [empty, None, None, "", "", None, empty, None, empty, None, empty, None, empty, empty, ""]

        def update_on_voice_upload(files, custom_intro):
            return episode_upload_details(files)

        def update_timeline_with_order_state(files, rows, custom_intro):
            return episode_premix(files, rows, custom_intro)

        voice.change(update_on_voice_upload, [voice, intro_override],
                     [order, order_table, background, recordings, upload_state]).then(
            empty_results, [], result_components)
        order_table.input(stage_episode_order, [order_table, order, voice], [
                          order, order_table, background])
        background.input(stage_episode_background, [
                         background, order], [order])
        order.change(update_timeline_with_order_state, [
                     voice, order, intro_override], [timeline, health, alert])
        intro_override.change(update_timeline_with_order_state, [
                              voice, order, intro_override], [timeline, health, alert])

        def prepare_episode(receipt, is_busy):
            if is_busy:
                raise gr.Error("An episode is already rendering.")
            stamp = clear_final_quality_inspector(receipt)[-1]
            return (*empty_results(), stamp, None, None, None, None, "", "", "", True,
                    gr.Button(interactive=False), gr.Button(
                        interactive=False), gr.File(interactive=False),
                    gr.Button(interactive=False), gr.Dataframe(
                        interactive=False),
                    gr.Dataframe(interactive=False), gr.File(interactive=False), gr.Textbox(interactive=False))

        guard_outputs = [create, another, voice, edit_name,
                         order_table, background, intro_override, name]
        prepare = create.click(prepare_episode, [preview_receipt, busy],
                               result_components + [started, preview_receipt, exported, cleaned, transcript,
                                                    status, progress_html, log, busy] + guard_outputs,
                               queue=False, trigger_mode="once")
        render = prepare.success(create_episode_from_saved, [voice, name, order, intro_override],
                                 [status, exported, cleaned, transcript,
                                     console, progress_html, log],
                                 show_progress="hidden", concurrency_id="episode-render", concurrency_limit=1)

        def finish_episode(path, clean, text, stamp):
            if not path or not os.path.isfile(path):
                return empty_results()
            card, clip, report = render_final_quality_inspector(path, stamp)
            short, state = episode_quality_summary(path, stamp)
            def available(value): return episode_marker(
                "available" if value else "empty")
            clean = clean if clean and os.path.isfile(clean) else None
            text = text if text and os.path.isfile(text) else None
            return [episode_marker("ready"), path, path, short, card, clip, available(clip),
                    report, available(report), clean, available(clean), text, available(text), state, ""]

        finished = render.then(finish_episode, [exported, cleaned, transcript, started], result_components).then(
            remember_quality_preview, [exported, started], [preview_receipt])

        def release_episode():
            return (False, gr.Button(interactive=True), gr.Button(interactive=True), gr.File(interactive=True),
                    gr.Button(interactive=True), gr.Dataframe(
                        interactive=True), gr.Dataframe(interactive=True),
                    gr.File(interactive=True), gr.Textbox(interactive=False))

        finished.then(release_episode, [], [busy] + guard_outputs)

        def reset_episode(receipt):
            values = reset_episode_values(receipt)
            return (*empty_results(), values["voice"], [], [], [], None,
                    gr.Textbox(value=values["name"], interactive=False), "", episode_marker(
                        "empty"),
                    "", "", "", 0, None, None, None, None, "", "", "", "", False)

        another.click(reset_episode, [preview_receipt], result_components +
                      [voice, order, order_table, background, intro_override, name, recordings, upload_state,
                       timeline, health, alert, started, preview_receipt, exported, cleaned, transcript,
                       status, progress_html, log, console, busy], concurrency_id="episode-render", concurrency_limit=1,
                      show_progress="hidden").then(None, [], [], js="""() => {
                          const hero = document.getElementById('episode-hero');
                          hero?.scrollIntoView({block: 'start'});
                          hero?.querySelector('button')?.focus({preventScroll: true});
                      }""")

        def acknowledge_episode(path, stamp):
            card, message = acknowledge_quality_override(path, stamp)
            short, state = episode_quality_summary(path, stamp)
            return card, message, short, state

        override.click(acknowledge_episode, [exported, started], [
                       raw, action_status, qc_summary, qc_state])

        def suggested_episode_settings(path, stamp):
            message, *_ = apply_quality_suggested_settings(path, stamp)
            return message, saved_settings_summary(), *settings_form_values()

        fix.click(suggested_episode_settings, [exported, started], [action_status, summary] + form).then(
            refresh_asset_controls, [], asset_controls)

        def find_transcript(path):
            candidate = os.path.splitext(
                path)[0] + "_transcript.txt" if path else None
            candidate = candidate if candidate and os.path.isfile(
                candidate) else None
            return candidate, episode_marker("available" if candidate else "empty")

        refresh_transcript.click(find_transcript, [exported], [
                                 transcript_download, transcript_state])
    app.queue(default_concurrency_limit=1)
    return app


def _legacy_create_ui():
    """Create Gradio user interface."""

    # Load saved settings
    saved_volume = config_manager.get_volume()
    rss_url = config_manager.get_rss_feed_url()
    rss_last_title, rss_next_slug, rss_error = fetch_rss_episode_info(
        rss_url, force_refresh=True)
    saved_output_name = rss_next_slug or config_manager.get_last_output_name(
    ) or "ntn001"
    rss_status_html_value = build_rss_status_html(
        rss_last_title, rss_next_slug, rss_error)

    with gr.Blocks(title="NTN Podcast Creator") as app:
        gr.HTML("""
        <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #f9f9f9;
            --bg-footer: #f5f5f5;
            --border-color: #e0e0e0;
            --text-primary: #000000;
            --text-secondary: #666666;
            --card-bg: #f9f9f9;
            --card-border: #e0e0e0;
        }

        .dark-theme {
            --bg-primary: #1e1e1e;
            --bg-secondary: #2a2a2a;
            --bg-footer: #1e1e1e;
            --border-color: #444;
            --text-primary: #ffffff;
            --text-secondary: #cccccc;
            --card-bg: #2a2a2a;
            --card-border: #444;
        }

        .dark-theme .gradio-container {
            background: var(--bg-primary) !important;
            color: var(--text-primary) !important;
        }

        .dark-theme {
            background: var(--bg-primary) !important;
            color: var(--text-primary) !important;
        }

        .console-output {
            font-family: 'Courier New', monospace !important;
            background: #1e1e1e !important;
            color: #ffffff !important;
            border: 1px solid #333 !important;
            padding: 10px !important;
        }
        .progress-container {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 9999 !important;
            background: #ffffff !important;
            border-bottom: 2px solid #e0e0e0 !important;
            padding: 5px 20px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            display: none !important;
        }
        .progress-container.visible {
            display: block !important;
        }
        .bottom-console-container {
            position: fixed !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            z-index: 9998 !important;
            background: #1e1e1e !important;
            border-top: 2px solid #333 !important;
            box-shadow: 0 -2px 4px rgba(0,0,0,0.3) !important;
            max-height: 200px !important;
            overflow-y: auto !important;
            display: none !important;
        }
        .bottom-console-container.visible {
            display: block !important;
        }
        .bottom-console-header {
            background: #333 !important;
            color: #ffffff !important;
            padding: 8px 20px !important;
            font-weight: bold !important;
            border-bottom: 1px solid #555 !important;
            font-size: 14px !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
        }
        .bottom-console-content {
            font-family: 'Courier New', monospace !important;
            background: #1e1e1e !important;
            color: #ffffff !important;
            padding: 10px 20px !important;
            font-size: 12px !important;
            line-height: 1.4 !important;
            white-space: pre-wrap !important;
            max-height: 150px !important;
            overflow-y: auto !important;
        }
        .main-container {
            margin-top: 10px !important;
            margin-bottom: 210px !important;
        }
        .compact-row {
            gap: 10px !important;
        }
        .clean-card {
            border: 1px solid var(--card-border) !important;
            border-radius: 8px !important;
            padding: 15px !important;
            margin: 10px 0 !important;
            background: var(--card-bg) !important;
        }
        .footer {
            text-align: center;
            padding: 20px;
            background: var(--bg-footer);
            border-top: 1px solid var(--border-color);
            margin-top: 30px;
            color: var(--text-primary);
        }
        .close-btn {
            cursor: pointer;
            padding: 4px 12px;
            background: #dc3545;
            color: white;
            border-radius: 4px;
            font-size: 12px;
            border: none;
        }
        .close-btn:hover {
            background: #c82333;
        }
        .dark-theme .footer {
            background: var(--bg-footer);
            border-top-color: var(--border-color);
            color: var(--text-primary);
        }
        .dark-theme .clean-card {
            background: var(--card-bg) !important;
            border-color: var(--card-border) !important;
        }
        #voice-order-state {
            display: none !important;
        }
        </style>
        <script>
        // Theme management
        function applyTheme(theme) {
            const root = document.documentElement;
            const body = document.body;
            if (theme === 'Dark') {
                root.classList.add('dark-theme');
                body.classList.add('dark-theme');
                localStorage.setItem('ntn-theme', 'Dark');
            } else if (theme === 'Light') {
                root.classList.remove('dark-theme');
                body.classList.remove('dark-theme');
                localStorage.setItem('ntn-theme', 'Light');
            } else { // System
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                if (prefersDark) {
                    root.classList.add('dark-theme');
                    body.classList.add('dark-theme');
                } else {
                    root.classList.remove('dark-theme');
                    body.classList.remove('dark-theme');
                }
                localStorage.setItem('ntn-theme', 'System');
            }
        }

        // Apply saved theme on load
        window.addEventListener('DOMContentLoaded', function() {
            setTimeout(function() {
                const savedTheme = localStorage.getItem('ntn-theme') || 'System';
                applyTheme(savedTheme);
            }, 100);
        });

        // Also apply theme immediately if DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                setTimeout(function() {
                    const savedTheme = localStorage.getItem('ntn-theme') || 'System';
                    applyTheme(savedTheme);
                }, 100);
            });
        } else {
            setTimeout(function() {
                const savedTheme = localStorage.getItem('ntn-theme') || 'System';
                applyTheme(savedTheme);
            }, 100);
        }

        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function() {
            const savedTheme = localStorage.getItem('ntn-theme') || 'System';
            if (savedTheme === 'System') {
                applyTheme('System');
            }
        });
        </script>
        """)
        # Progress bar container (initially hidden)
        progress_bar = gr.HTML(
            value='<div style="display: none; width: 100%; z-index: 9999;"></div>',
            elem_id="progress-bar-container"
        )

        # Bottom console container (initially hidden)
        bottom_console = gr.HTML(
            value='<div style="display: none; width: 100%; z-index: 9998;"></div>',
            elem_id="bottom-console-container"
        )

        # Title and theme selector
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("# 🎙️ NTN Podcast Creator")
            with gr.Column(scale=1):
                theme_selector = gr.Dropdown(
                    choices=["Light", "Dark", "System"],
                    value="System",
                    label="Theme",
                    info="Select your preferred theme"
                )
                theme_status = gr.HTML(value="")

        # Theme change handler using JavaScript
        def apply_theme_change(theme):
            """Apply theme change via JavaScript."""
            return f"""
            <script>
            (function() {{
                setTimeout(function() {{
                    if (typeof applyTheme === 'function') {{
                        applyTheme('{theme}');
                    }} else {{
                        // Fallback if applyTheme is not available
                        const root = document.documentElement;
                        const body = document.body;
                        if ('{theme}' === 'Dark') {{
                            root.classList.add('dark-theme');
                            body.classList.add('dark-theme');
                            localStorage.setItem('ntn-theme', 'Dark');
                        }} else if ('{theme}' === 'Light') {{
                            root.classList.remove('dark-theme');
                            body.classList.remove('dark-theme');
                            localStorage.setItem('ntn-theme', 'Light');
                        }} else {{
                            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                            if (prefersDark) {{
                                root.classList.add('dark-theme');
                                body.classList.add('dark-theme');
                            }} else {{
                                root.classList.remove('dark-theme');
                                body.classList.remove('dark-theme');
                            }}
                            localStorage.setItem('ntn-theme', 'System');
                        }}
                    }}
                }}, 10);
            }})();
            </script>
            <div style="padding: 5px; font-size: 12px; color: #666;">Theme changed to {theme}</div>
            """

        with gr.Tabs():
            # Main Tab - Podcast Creation
            with gr.Tab("🎙️ Create Podcast"):
                gr.Markdown("""
                ### Upload your voice recording and create your podcast
                Default intro, outro, and background music are automatically applied.
                """)

                with gr.Row():
                    with gr.Column():
                        with gr.Group(elem_classes=["clean-card"]):
                            gr.Markdown("### 📤 Upload & Configure")

                            voice_input = gr.File(
                                label="🎤 Voice Recording(s) (Required)",
                                file_count="multiple",
                                file_types=["audio"],
                                type="filepath",
                                interactive=True,
                                container=True
                            )

                            gr.Markdown("""
                            *Upload one or more audio files. Multiple files will be concatenated in the order you define below.*
                            """)

                            voice_order_editor = gr.HTML(
                                label="Arrange Voice Recordings Order",
                                value=render_voice_order_editor([])
                            )

                            voice_order_state = gr.Textbox(
                                value="[]",
                                visible=True,
                                elem_id="voice-order-state"
                            )

                            gr.Markdown("""
                            Use **⬆️ Up / ⬇️ Down** buttons on each row to reorder your voice tracks.
                            Toggle **Background** per track. Top row can't move up, bottom row can't move down.
                            """)

                            output_name_input = gr.Textbox(
                                label="📝 Podcast Episode Name",
                                value=saved_output_name,
                                placeholder="ntn###",
                                info=f"Auto-suggested from RSS (last: {rss_last_title or 'unavailable'})"
                            )

                        with gr.Accordion("🎵 One-time Intro Override", open=False):
                            gr.Markdown("""
                            Upload a custom intro audio file for this podcast only. This will not change your saved intro settings.
                            """)

                            intro_override_input = gr.Audio(
                                label="Custom Intro Audio (Optional)",
                                type="filepath"
                            )

                        with gr.Accordion("⚙️ Processing Options", open=False):
                            with gr.Row(elem_classes=["compact-row"]):
                                delete_voice_checkbox = gr.Checkbox(
                                    label="Delete voice recording after creation",
                                    value=True,
                                    info="Saves storage space"
                                )

                                trim_silence_checkbox = gr.Checkbox(
                                    label="Trim silence from voice recording",
                                    value=True,
                                    info="Removes silence from start and end"
                                )

                            gr.Markdown("### Audio Transitions")

                            with gr.Row(elem_classes=["compact-row"]):
                                intro_voice_overlap_checkbox = gr.Checkbox(
                                    label="Enable intro-voice overlap (1 second)",
                                    value=config_manager.get_intro_voice_overlap(),
                                    info="Smooth transition from intro to voice"
                                )

                                voice_outro_overlap_checkbox = gr.Checkbox(
                                    label="Enable voice-outro overlap (1 second)",
                                    value=config_manager.get_voice_outro_overlap(),
                                    info="Smooth transition from voice to outro"
                                )

                            gr.Markdown("### Noise Reduction")

                            denoise_audio_checkbox = gr.Checkbox(
                                label="Enable noise reduction",
                                value=config_manager.get_denoise_audio(),
                                info="Remove background noise from your recording"
                            )

                            denoise_method_dropdown = gr.Dropdown(
                                label="Noise Reduction Method",
                                choices=[
                                    ("AI Denoiser (Recommended)", "audio_denoiser"),
                                    ("Spectral Gating (noisereduce)", "spectral"),
                                    ("FFmpeg RNNoise", "rnnoise")
                                ],
                                value=config_manager.get_denoise_method(),
                                info="Choose your preferred noise reduction algorithm"
                            )

                            gr.Markdown("### Voice Enhancement")

                            enhance_voice_checkbox = gr.Checkbox(
                                label="Enable professional voice enhancement",
                                value=config_manager.get(
                                    "enhance_voice", False),
                                info="Apply EQ, compression, and de-essing for clearer voice"
                            )

                            voice_enhancement_preset_dropdown = gr.Dropdown(
                                label="Enhancement Preset",
                                choices=[
                                    ("Podcast (Balanced)", "podcast"),
                                    ("Light (Gentle)", "light"),
                                    ("Aggressive (Strong)", "aggressive")
                                ],
                                value=config_manager.get(
                                    "voice_enhancement_preset", "podcast"),
                                info="Choose enhancement strength: Light for clean recordings, Aggressive for noisy ones"
                            )

                            gr.Markdown("### Volume Normalization")

                            normalize_lufs_checkbox = gr.Checkbox(
                                label="Normalize audio to professional LUFS level",
                                value=config_manager.get_normalize_lufs(),
                                info="Ensures consistent loudness across episodes"
                            )

                            target_lufs_slider = gr.Slider(
                                minimum=-20,
                                maximum=-10,
                                value=config_manager.get_target_lufs(),
                                step=1,
                                label="Target LUFS Level",
                                info="-16 for podcasts (recommended), -14 for louder content"
                            )

                            gr.Markdown(
                                "### 🛡️ Audio Balance & Voice Protection")

                            with gr.Row(elem_classes=["compact-row"]):
                                auto_balance_levels_checkbox = gr.Checkbox(
                                    label="Auto-balance voice & music levels (Recommended)",
                                    value=config_manager.get_auto_balance_levels(),
                                    info="Boosts low voice recordings & ensures background music never overpowers speech"
                                )

                                auto_ducking_checkbox = gr.Checkbox(
                                    label="Auto-ducking",
                                    value=config_manager.get_auto_ducking(),
                                    info="Smoothly lowers music during speech using the shared quality settings"
                                )

                            gr.Markdown("### Final Audio Quality")
                            quality_enabled_value, quality_json_value, quality_seed_value = quality_settings_values()
                            quality_gate_checkbox = gr.Checkbox(
                                label="Final Audio Quality Gate",
                                value=quality_enabled_value,
                                info="Opt-in check of the exact exported audio. Failed QC does not block download."
                            )
                            with gr.Accordion("Advanced quality thresholds", open=False):
                                quality_thresholds_editor = gr.Textbox(
                                    label="Audio quality thresholds (JSON)",
                                    value=quality_json_value, lines=14
                                )
                                music_seed_input = gr.Number(
                                    label="Music seed", value=quality_seed_value, precision=0
                                )
                                gr.Markdown(
                                    "Save edited thresholds and seed before rendering. Target LUFS follows the existing LUFS slider.")
                                save_quality_button = gr.Button(
                                    "Save quality settings")
                            quality_settings_status = gr.Textbox(
                                label="Quality settings status", interactive=False
                            )

                            gr.Markdown("### Transcription")

                            generate_transcript_checkbox = gr.Checkbox(
                                label="Generate transcript with Whisper AI",
                                value=config_manager.get_generate_transcript(),
                                info="Create text transcript from final podcast audio"
                            )

                            whisper_model_dropdown = gr.Dropdown(
                                label="Whisper Model",
                                choices=[
                                    ("Tiny (Fastest)", "tiny"),
                                    ("Base (Recommended)", "base"),
                                    ("Small (Better Quality)", "small"),
                                    ("Medium (High Quality)", "medium"),
                                    ("Large (Best Quality)", "large")
                                ],
                                value=config_manager.get_whisper_model(),
                                info="Larger models are more accurate but slower"
                            )

                        with gr.Group(elem_classes=["clean-card"]):
                            create_button = gr.Button(
                                "🎬 Create Podcast",
                                variant="primary",
                                size="lg",
                                scale=2
                            )

                    with gr.Column():
                        with gr.Group(elem_classes=["clean-card"]):
                            gr.Markdown("### 📊 Preview & Health Check")
                            timeline_html = gr.HTML(
                                label="Timeline Preview",
                                value=preview_timeline(None)
                            )
                            audio_health_html = gr.HTML(
                                label="Audio Balance Health",
                                value=render_audio_health_card(None)
                            )

                        with gr.Group(elem_classes=["clean-card"]):
                            status_output = gr.Textbox(
                                label="📢 Status",
                                interactive=False,
                                lines=2
                            )

                        with gr.Group(elem_classes=["clean-card"]):
                            gr.Markdown("### 🎧 Results")
                            audio_output = gr.Audio(
                                label="🎧 Your Podcast",
                                type="filepath",
                                autoplay=True,
                                elem_id="podcast-audio-player"
                            )

                            with gr.Row():
                                denoised_audio_output = gr.Audio(
                                    label="🎵 Cleaned Voice",
                                    type="filepath",
                                    visible=True,
                                    scale=1
                                )

                                transcript_output = gr.File(
                                    label="📝 Transcript",
                                    visible=True,
                                    scale=1
                                )

                            final_quality_html = gr.HTML(
                                label="Final Audio Quality Inspector", value="")
                            quality_preview = gr.Audio(
                                label="Preview worst section", type="filepath")
                            quality_report_download = gr.File(
                                label="Download quality report (JSON)")
                            quality_override_button = gr.Button(
                                "Override — I acknowledge the QC warning/failure")
                            quality_fix_button = gr.Button(
                                "Apply suggested settings for next render")
                            quality_action_status = gr.Textbox(
                                label="Quality action status", interactive=False)
                            quality_render_started = gr.State(0)
                            quality_preview_state = gr.State(None)
                            gr.Markdown(
                                "Settings fixes require a rerender with the original voice source and music. Keep or re-upload sources if deleted; the current export is never rewritten.")

                        with gr.Accordion("📥 Download & Import Settings", open=False):
                            gr.Markdown("**Podcast RSS Feed**")
                            rss_feed_input = gr.Textbox(
                                label="RSS Feed URL",
                                value=rss_url,
                                placeholder=DEFAULT_RSS_FEED_URL
                            )
                            refresh_rss_button = gr.Button(
                                "🔄 Refresh from RSS",
                                variant="secondary",
                                size="sm"
                            )
                            rss_status_html = gr.HTML(
                                label="RSS Status",
                                value=rss_status_html_value
                            )

                            gr.Markdown("**Export Settings**")
                            export_settings_button = gr.Button(
                                "💾 Download Current Settings",
                                variant="secondary",
                                size="sm"
                            )
                            settings_file_output = gr.File(
                                label="Settings File",
                                visible=True
                            )

                            gr.Markdown("**Import Settings**")
                            import_settings_input = gr.File(
                                label="Upload Settings File (JSON)",
                                file_types=[".json"]
                            )
                            import_status = gr.Textbox(
                                label="Import Status",
                                interactive=False
                            )

                        with gr.Accordion("📋 Templates", open=False):
                            gr.Markdown("""
                            Save and load your podcast settings as templates for quick access.
                            Templates include intro/outro, background music, and processing options.
                            """)

                            # Get available templates
                            available_templates = get_template_choices()
                            active_template = config_manager.get_active_template()

                            with gr.Row():
                                template_dropdown = gr.Dropdown(
                                    label="Select Template",
                                    choices=available_templates,
                                    value=active_template,
                                    interactive=True,
                                    allow_custom_value=False
                                )

                            with gr.Row():
                                load_template_button = gr.Button(
                                    "📂 Load Template",
                                    variant="secondary",
                                    size="sm",
                                    scale=1
                                )
                                delete_template_button = gr.Button(
                                    "🗑️ Delete Template",
                                    variant="secondary",
                                    size="sm",
                                    scale=1
                                )

                            gr.Markdown(
                                "**Save Current Settings as Template**")

                            with gr.Row():
                                template_name_input = gr.Textbox(
                                    label="Template Name",
                                    placeholder="e.g., My Weekly Podcast",
                                    scale=2
                                )
                                save_template_button = gr.Button(
                                    "💾 Save Template",
                                    variant="primary",
                                    size="sm",
                                    scale=1
                                )

                            template_status = gr.Textbox(
                                label="Template Status",
                                interactive=False,
                                lines=2
                            )

                # Hidden component for console log updates
                realtime_console_output = gr.Textbox(
                    value="",
                    visible=False
                )

            # AI Denoiser Tab - Standalone Audio Denoising
            with gr.Tab("🤖 AI Denoiser"):
                gr.Markdown("""
                ### Clean Audio with AI-Based Noise Removal
                Use machine learning to remove background noise from your audio recordings.
                This is a standalone tool - upload audio, clean it, and download the result.
                """)

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("""
                        **How to use:**
                        1. Upload a voice recording below
                        2. Click "Clean Audio"
                        3. Wait for processing (usually under 30 seconds)
                        4. Download the cleaned audio

                        **What it does:**
                        - Removes background noise using AI
                        - Preserves speech quality
                        - **NEW**: Supports files of any size (auto-chunking for large files)
                        - No cloud processing - runs locally
                        """)

                        denoise_tab_voice_input = gr.Audio(
                            label="🎤 Voice Recording to Clean",
                            type="filepath"
                        )

                        denoise_only_delete_checkbox = gr.Checkbox(
                            label="Delete uploaded file after cleaning",
                            value=True,
                            info="Keeps the uploads folder tidy"
                        )

                        denoise_only_button = gr.Button(
                            "🤖 Clean Audio",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column():
                        denoise_only_status = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=3
                        )

                        denoise_only_output = gr.Audio(
                            label="🎧 Cleaned Audio Preview",
                            type="filepath"
                        )

                        with gr.Accordion("📋 Processing Log", open=False):
                            denoise_only_log = gr.Textbox(
                                label="Denoising Log",
                                value=get_console_log(),
                                interactive=False,
                                lines=15,
                                max_lines=30
                            )

                gr.Markdown("""
                ---
                ### 💡 AI Denoiser Tips
                - Processing is very fast, typically under 30 seconds
                - **NEW**: Now supports files of any size with automatic chunking
                - Large files (>10MB) are automatically split into smaller chunks for processing
                - You can also enable automatic denoising in the **🎙️ Create Podcast** tab
                - No internet connection required - everything runs on your machine
                - Install `audio-denoiser` package for this feature to work
                """)

            # Settings Tab - Audio Configuration
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("""
                ### Configure Audio Settings
                Customize intro, outro, and background music for your podcasts.
                """)

                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Intro Audio")
                        gr.Markdown("*Plays before your voice recording*")

                        intro_display = gr.Textbox(
                            label="Current Intro",
                            value=get_intro_info()[0],
                            interactive=False
                        )

                        intro_audio_player = gr.Audio(
                            label="Play Intro",
                            value=get_intro_info()[1],
                            type="filepath"
                        )

                        with gr.Row():
                            intro_input = gr.Audio(
                                label="Upload New Intro",
                                type="filepath"
                            )

                        with gr.Row():
                            delete_intro_button = gr.Button(
                                "🗑️ Delete Intro",
                                variant="stop",
                                size="sm"
                            )

                        intro_status = gr.Textbox(
                            label="Status",
                            interactive=False
                        )

                        gr.Markdown("---")

                        gr.Markdown("#### Outro Audio")
                        gr.Markdown("*Plays after your voice recording*")

                        outro_display = gr.Textbox(
                            label="Current Outro",
                            value=get_outro_info()[0],
                            interactive=False
                        )

                        outro_audio_player = gr.Audio(
                            label="Play Outro",
                            value=get_outro_info()[1],
                            type="filepath"
                        )

                        with gr.Row():
                            outro_input = gr.Audio(
                                label="Upload New Outro",
                                type="filepath"
                            )

                        with gr.Row():
                            delete_outro_button = gr.Button(
                                "🗑️ Delete Outro",
                                variant="stop",
                                size="sm"
                            )

                        outro_status = gr.Textbox(
                            label="Status",
                            interactive=False
                        )

                    with gr.Column():
                        gr.Markdown("#### Background Music")
                        gr.Markdown(
                            "*Tracks are randomly selected and concatenated to match podcast length*")

                        background_input = gr.Audio(
                            label="Upload Background Track",
                            type="filepath"
                        )

                        with gr.Row():
                            add_bg_button = gr.Button(
                                "Add Track",
                                variant="secondary"
                            )
                            clear_bg_button = gr.Button(
                                "Clear All",
                                variant="stop"
                            )

                        background_status = gr.Textbox(
                            label="Status",
                            interactive=False
                        )

                        background_list = gr.Textbox(
                            label="Current Tracks",
                            value=get_background_tracks_display(),
                            interactive=False,
                            lines=6
                        )

                        gr.Markdown("**Manage Tracks**")

                        # Get initial track list
                        initial_tracks, _ = get_background_tracks_list()

                        bg_track_selector = gr.Dropdown(
                            label="Select Track to Play or Delete",
                            choices=initial_tracks,
                            interactive=True
                        )

                        bg_track_player = gr.Audio(
                            label="Play Selected Track",
                            type="filepath"
                        )

                        delete_bg_track_button = gr.Button(
                            "🗑️ Delete Selected Track",
                            variant="stop",
                            size="sm"
                        )

                        bg_track_status = gr.Textbox(
                            label="Track Status",
                            interactive=False
                        )

                        gr.Markdown("---")

                        gr.Markdown("#### Volume Settings")

                        gr.Markdown("**Global Volume Control**")
                        volume_slider = gr.Slider(
                            minimum=0,
                            maximum=50,
                            value=saved_volume,
                            step=1,
                            label="Default Background Music Volume (%)",
                            info="Recommended: 10-12%"
                        )

                        apply_to_all_button = gr.Button(
                            "📢 Apply Volume to All Tracks",
                            variant="primary",
                            size="sm"
                        )

                        volume_status = gr.Textbox(
                            label="Volume Status",
                            interactive=False
                        )

                        gr.Markdown("---")

                        gr.Markdown("**Individual Track Volume**")
                        gr.Markdown(
                            "*Select a track above to adjust its volume individually*")

                        track_volume_slider = gr.Slider(
                            minimum=0,
                            maximum=50,
                            value=saved_volume,
                            step=1,
                            label="Selected Track Volume (%)",
                            info="Volume for the track selected above"
                        )

                        track_volume_status = gr.Textbox(
                            label="Track Volume Status",
                            interactive=False
                        )

                        # Audio player with volume applied
                        bg_track_player_with_volume = gr.Audio(
                            label="Preview Track with Applied Volume",
                            type="filepath"
                        )

                        gr.Markdown("---")

                        gr.Markdown("#### Upload Defaults")

                        prioritize_recording_checkbox = gr.Checkbox(
                            label="Prefer Recording.m4a first",
                            value=config_manager.get_prioritize_recording_filename(),
                            info="When multiple voice files are uploaded, place Recording.m4a at the top of the default order table"
                        )

                gr.Markdown("""
                ---
                ### 💡 Settings Tips
                - Audio files are auto-loaded from `audios/intro_audio/`, `audios/outro_audio/`, and `audios/background_music/`
                - All settings are automatically saved
                - Background music tracks are randomly selected and concatenated to match podcast duration
                - Multiple tracks create variety in your background music
                - Place default audio files in the respective folders and restart to auto-load
                """)

                gr.Markdown("---")

                # Current settings display
                settings_display = gr.Textbox(
                    label="Current Configuration",
                    value=get_current_settings(),
                    interactive=False,
                    lines=10
                )

                refresh_settings_button = gr.Button(
                    "🔄 Refresh Settings",
                    variant="secondary"
                )

            # Tips & Features Tab
            with gr.Tab("💡 Tips & Features"):
                gr.Markdown("""
                ## 💡 Quick Tips

                - Upload your voice recording - the episode name is auto-suggested with today's date
                - Default audio files are automatically loaded from `audios/` folder
                - Background tracks are randomly mixed to match your recording length
                - Generated podcasts are saved in the `outputs/` directory
                - Configure intro, outro, and background music in the **⚙️ Settings** tab
                - Use the **🤖 AI Denoiser** tab to clean audio files with machine learning

                ---

                ## 🎛️ Advanced Features

                ### Multiple Noise Reduction Methods
                Choose between AI Denoiser, Spectral Gating, or FFmpeg RNNoise to remove background noise from your recordings.

                ### LUFS Normalization
                Automatically normalize audio to professional broadcast standards:
                - **-16 LUFS** for podcasts (recommended)
                - **-14 LUFS** for louder streaming content
                - **-23 LUFS** for radio broadcasting

                ### Whisper Transcription
                Generate accurate transcripts with timestamps using OpenAI Whisper:
                - Supports 99+ languages
                - 5 model sizes from Tiny (fast) to Large (best quality)
                - Completely offline after initial model download

                ### Large File Support
                Process audio files of any size with intelligent automatic chunking:
                - No file size limits
                - Large files (>10MB) automatically split into 8MB chunks
                - Seamless reconstruction with perfect audio continuity

                ### Individual Volume Controls
                - Set different volume levels for each background music file
                - Apply global volume to all tracks at once
                - Preview tracks with applied volume before creating

                All advanced features are available in the "Processing Options" section in the **🎙️ Create Podcast** tab.
                """)

            # Console Log Tab
            with gr.Tab("📋 Console Log"):
                gr.Markdown("""
                ### Application Console Log
                View detailed logs of podcast creation process and any errors.
                """)

                console_output = gr.Textbox(
                    label="Console Output",
                    value=get_console_log(),
                    interactive=False,
                    lines=25,
                    max_lines=50
                )

                with gr.Row():
                    refresh_log_button = gr.Button(
                        "🔄 Refresh Log",
                        variant="secondary"
                    )
                    clear_log_button = gr.Button(
                        "🗑️ Clear Log",
                        variant="stop"
                    )

        # Footer
        gr.HTML("""
        <div class="footer">
            <p><strong>Created by: Bruno Capuano</strong></p>
            <p>🔗 <a href="https://aka.ms/elbruno" target="_blank">https://aka.ms/elbruno</a></p>
            <p>🎙️ Podcast: <strong>No Tiene Nombre</strong></p>
            <p>🌐 <a href="https://notienenombre.com/" target="_blank">https://notienenombre.com/</a></p>
        </div>
        """)

        # Event handlers
        # Theme selector
        theme_selector.change(
            fn=apply_theme_change,
            inputs=[theme_selector],
            outputs=[theme_status]
        )

        intro_input.change(
            fn=update_intro_file,
            inputs=[intro_input],
            outputs=[intro_status, intro_display, intro_audio_player]
        )

        delete_intro_button.click(
            fn=delete_intro,
            inputs=[],
            outputs=[intro_status, intro_display, intro_audio_player]
        )

        outro_input.change(
            fn=update_outro_file,
            inputs=[outro_input],
            outputs=[outro_status, outro_display, outro_audio_player]
        )

        delete_outro_button.click(
            fn=delete_outro,
            inputs=[],
            outputs=[outro_status, outro_display, outro_audio_player]
        )

        add_bg_button.click(
            fn=add_background_track,
            inputs=[background_input],
            outputs=[background_status, background_list, bg_track_selector]
        )

        clear_bg_button.click(
            fn=clear_background_tracks,
            inputs=[],
            outputs=[background_status, background_list, bg_track_selector]
        )

        # When user selects a track from dropdown, load it into the player
        def update_bg_player(track_choice):
            if track_choice is None:
                return None
            # Find the index of selected track
            display_list, paths = get_background_tracks_list()
            try:
                idx = display_list.index(track_choice)
                return paths[idx]
            except (ValueError, IndexError):
                return None

        bg_track_selector.change(
            fn=update_bg_player,
            inputs=[bg_track_selector],
            outputs=[bg_track_player]
        )

        # Delete selected background track
        def delete_selected_bg_track(track_choice):
            if track_choice is None:
                display_list, _ = get_background_tracks_list()
                return "No track selected", get_background_tracks_display(), gr.update(choices=display_list), None

            # Find the index of selected track
            display_list, _ = get_background_tracks_list()
            try:
                idx = display_list.index(track_choice)
                status, dropdown_update, player_update = delete_background_track(
                    idx)
                return status, get_background_tracks_display(), dropdown_update, player_update
            except (ValueError, IndexError):
                return "Track not found", get_background_tracks_display(), gr.update(choices=display_list), None

        delete_bg_track_button.click(
            fn=delete_selected_bg_track,
            inputs=[bg_track_selector],
            outputs=[bg_track_status, background_list,
                     bg_track_selector, bg_track_player]
        )

        volume_slider.change(
            fn=update_volume,
            inputs=[volume_slider],
            outputs=[volume_status]
        )

        # Apply volume to all tracks
        apply_to_all_button.click(
            fn=apply_volume_to_all,
            inputs=[],
            outputs=[volume_status]
        )

        # When track is selected, update the track volume slider
        def update_track_volume_slider(track_choice):
            volume = get_track_volume(track_choice)
            return volume

        bg_track_selector.change(
            fn=update_track_volume_slider,
            inputs=[bg_track_selector],
            outputs=[track_volume_slider]
        )

        # When track volume slider changes, update the track volume and generate preview
        track_volume_slider.change(
            fn=update_track_volume,
            inputs=[bg_track_selector, track_volume_slider],
            outputs=[track_volume_status,
                     bg_track_player_with_volume, bg_track_player]
        )

        prioritize_recording_checkbox.change(
            fn=lambda enabled: config_manager.set_prioritize_recording_filename(
                enabled),
            inputs=[prioritize_recording_checkbox],
            outputs=[]
        )

        # Update timeline when voice file is uploaded
        def update_on_voice_upload(voice_file, intro_override_file):
            """Update timeline, suggested filename, order table, and audio health when voice is uploaded."""
            prefer_recording_first = config_manager.get_prioritize_recording_filename()
            ordered_voice_files = prioritize_recording_files(
                voice_file, prefer_recording_first)
            default_bg_flags = [True] * len(ordered_voice_files) if isinstance(
                ordered_voice_files, list) and ordered_voice_files else [True] if ordered_voice_files else []
            timeline = preview_timeline(
                ordered_voice_files, intro_override_file, default_bg_flags)
            suggested_name = suggest_podcast_name(voice_file)
            order_rows = normalize_voice_order_table(
                build_voice_order_rows(ordered_voice_files), ordered_voice_files, apply_move_action=False)

            # Analyze levels for health card
            analysis = None
            if ordered_voice_files:
                try:
                    analysis = audio_processor.analyze_levels(
                        ordered_voice_files,
                        background_files=config_manager.get_background_tracks(),
                        background_volume=config_manager.get_volume(),
                        track_volumes=config_manager.get_all_track_volumes(),
                        quality_config=config_manager.get_audio_quality_config()
                    )
                except Exception:
                    analysis = None
            health_card = render_audio_health_card(analysis)

            return timeline, suggested_name, json.dumps(order_rows), render_voice_order_editor(order_rows), health_card

        voice_input.change(
            fn=update_on_voice_upload,
            inputs=[voice_input, intro_override_input],
            outputs=[timeline_html, output_name_input,
                     voice_order_state, voice_order_editor, audio_health_html]
        )

        def update_timeline_with_intro_override(voice_file, intro_override_file, order_state):
            ordered_segments = order_voice_segments(voice_file, order_state)
            ordered_files = [path for path, _ in ordered_segments]
            bg_flags = [use_bg for _, use_bg in ordered_segments]
            return preview_timeline(ordered_files, intro_override_file, bg_flags)

        intro_override_input.change(
            fn=update_timeline_with_intro_override,
            inputs=[voice_input, intro_override_input, voice_order_state],
            outputs=[timeline_html]
        )

        def update_timeline_with_order_state(voice_file, order_state, intro_override_file):
            normalized_table = normalize_voice_order_table(
                order_state, voice_file, apply_move_action=False)
            ordered_segments = order_voice_segments(
                voice_file, normalized_table)
            ordered_files = [path for path, _ in ordered_segments]
            bg_flags = [use_bg for _, use_bg in ordered_segments]

            # Analyze levels for health card
            analysis = None
            if ordered_files:
                try:
                    analysis = audio_processor.analyze_levels(
                        ordered_files,
                        background_files=config_manager.get_background_tracks(),
                        background_volume=config_manager.get_volume(),
                        track_volumes=config_manager.get_all_track_volumes(),
                        quality_config=config_manager.get_audio_quality_config()
                    )
                except Exception:
                    analysis = None
            health_card = render_audio_health_card(analysis)

            return json.dumps(normalized_table), render_voice_order_editor(normalized_table), preview_timeline(ordered_files, intro_override_file, bg_flags), health_card

        voice_order_state.change(
            fn=update_timeline_with_order_state,
            inputs=[voice_input, voice_order_state, intro_override_input],
            outputs=[voice_order_state, voice_order_editor,
                     timeline_html, audio_health_html]
        )

        clear_quality_event = create_button.click(
            fn=clear_final_quality_inspector,
            inputs=[quality_preview_state],
            outputs=[final_quality_html, quality_preview, quality_report_download,
                     quality_action_status, quality_render_started],
            queue=False
        )
        create_button_event = clear_quality_event.then(
            fn=create_podcast_handler_with_progress,
            inputs=[voice_input, output_name_input,
                    delete_voice_checkbox, trim_silence_checkbox,
                    denoise_audio_checkbox, denoise_method_dropdown,
                    enhance_voice_checkbox, voice_enhancement_preset_dropdown,
                    normalize_lufs_checkbox, target_lufs_slider,
                    intro_voice_overlap_checkbox, voice_outro_overlap_checkbox,
                    generate_transcript_checkbox, whisper_model_dropdown,
                    auto_balance_levels_checkbox, auto_ducking_checkbox,
                    voice_order_state, intro_override_input],
            outputs=[status_output, audio_output,
                     denoised_audio_output, transcript_output, realtime_console_output, progress_bar, bottom_console],
            show_progress='full'
        )

        create_button_event.then(
            fn=render_final_quality_inspector,
            inputs=[audio_output, quality_render_started],
            outputs=[final_quality_html,
                     quality_preview, quality_report_download]
        ).then(
            fn=remember_quality_preview,
            inputs=[audio_output, quality_render_started],
            outputs=[quality_preview_state]
        )
        quality_gate_checkbox.change(
            fn=set_quality_gate_enabled,
            inputs=[quality_gate_checkbox], outputs=[quality_settings_status]
        )
        save_quality_button.click(
            fn=save_quality_settings,
            inputs=[quality_gate_checkbox,
                    quality_thresholds_editor, music_seed_input],
            outputs=[quality_settings_status]
        )
        quality_override_button.click(
            fn=acknowledge_quality_override,
            inputs=[audio_output, quality_render_started],
            outputs=[final_quality_html, quality_action_status]
        )
        quality_fix_button.click(
            fn=apply_quality_suggested_settings,
            inputs=[audio_output, quality_render_started],
            outputs=[quality_action_status, auto_balance_levels_checkbox,
                     auto_ducking_checkbox, normalize_lufs_checkbox]
        )

        # Update the console log tab and other logs whenever processing completes
        create_button_event.then(
            fn=get_console_log,
            inputs=[],
            outputs=[console_output]
        )

        create_button_event.then(
            fn=get_console_log,
            inputs=[],
            outputs=[realtime_console_output]
        )

        # AI Denoiser tab handlers
        denoise_only_button_event = denoise_only_button.click(
            fn=denoise_audio_only_handler,
            inputs=[denoise_tab_voice_input, denoise_only_delete_checkbox],
            outputs=[denoise_only_status,
                     denoise_only_output, denoise_only_log]
        )

        denoise_only_button_event.then(
            fn=get_console_log,
            inputs=[],
            outputs=[console_output]
        )

        refresh_settings_button.click(
            fn=get_current_settings,
            inputs=[],
            outputs=[settings_display]
        )

        refresh_log_event = refresh_log_button.click(
            fn=get_console_log,
            inputs=[],
            outputs=[console_output]
        )

        refresh_log_event.then(
            fn=get_console_log,
            inputs=[],
            outputs=[denoise_only_log]
        )

        clear_log_event = clear_log_button.click(
            fn=clear_console_log,
            inputs=[],
            outputs=[console_output]
        )

        clear_log_event.then(
            fn=get_console_log,
            inputs=[],
            outputs=[denoise_only_log]
        )

        # Save denoise audio setting when changed
        denoise_audio_checkbox.change(
            fn=lambda enabled: config_manager.set_denoise_audio(enabled),
            inputs=[denoise_audio_checkbox],
            outputs=[]
        )

        # Save denoise method when changed
        denoise_method_dropdown.change(
            fn=lambda method: config_manager.set_denoise_method(method),
            inputs=[denoise_method_dropdown],
            outputs=[]
        )

        # Save voice enhancement settings when changed
        enhance_voice_checkbox.change(
            fn=lambda enabled: config_manager.set("enhance_voice", enabled),
            inputs=[enhance_voice_checkbox],
            outputs=[]
        )

        voice_enhancement_preset_dropdown.change(
            fn=lambda preset: config_manager.set(
                "voice_enhancement_preset", preset),
            inputs=[voice_enhancement_preset_dropdown],
            outputs=[]
        )

        # Save overlap settings when changed
        intro_voice_overlap_checkbox.change(
            fn=lambda enabled: config_manager.set_intro_voice_overlap(enabled),
            inputs=[intro_voice_overlap_checkbox],
            outputs=[]
        )

        voice_outro_overlap_checkbox.change(
            fn=lambda enabled: config_manager.set_voice_outro_overlap(enabled),
            inputs=[voice_outro_overlap_checkbox],
            outputs=[]
        )

        # Save audio balance and ducking settings
        auto_balance_levels_checkbox.change(
            fn=lambda enabled: config_manager.set_auto_balance_levels(enabled),
            inputs=[auto_balance_levels_checkbox],
            outputs=[]
        )

        auto_ducking_checkbox.change(
            fn=lambda enabled: config_manager.set_auto_ducking(enabled),
            inputs=[auto_ducking_checkbox],
            outputs=[]
        )

        # Save LUFS normalization settings
        normalize_lufs_checkbox.change(
            fn=lambda enabled: config_manager.set_normalize_lufs(enabled),
            inputs=[normalize_lufs_checkbox],
            outputs=[]
        )

        target_lufs_slider.change(
            fn=lambda target: config_manager.set_target_lufs(target),
            inputs=[target_lufs_slider],
            outputs=[]
        )

        # Save transcript generation settings
        generate_transcript_checkbox.change(
            fn=lambda enabled: config_manager.set_generate_transcript(enabled),
            inputs=[generate_transcript_checkbox],
            outputs=[]
        )

        whisper_model_dropdown.change(
            fn=lambda model: config_manager.set_whisper_model(model),
            inputs=[whisper_model_dropdown],
            outputs=[]
        )

        refresh_rss_button.click(
            fn=refresh_rss_feed_settings,
            inputs=[rss_feed_input, output_name_input],
            outputs=[rss_status_html, output_name_input]
        )

        rss_feed_input.change(
            fn=lambda url: config_manager.set_rss_feed_url(
                (url or DEFAULT_RSS_FEED_URL).strip()),
            inputs=[rss_feed_input],
            outputs=[]
        )

        # Export settings
        export_settings_button.click(
            fn=export_settings,
            inputs=[],
            outputs=[settings_file_output]
        )

        # Import settings
        import_settings_input.change(
            fn=import_settings,
            inputs=[import_settings_input],
            outputs=[import_status]
        )

        # Template management - wrapper functions to handle dropdown updates
        def save_template_and_update(template_name: str):
            """Save template and return updated choices and status."""
            import json
            choices_json, status = save_template_handler(template_name)
            choices = json.loads(choices_json) if choices_json else []
            return choices, status, ""  # Clear the input field

        def delete_template_and_update(template_name: str):
            """Delete template and return updated choices and status."""
            import json
            choices_json, status = delete_template_handler(template_name)
            choices = json.loads(choices_json) if choices_json else []
            return choices, status

        save_template_button.click(
            fn=save_template_and_update,
            inputs=[template_name_input],
            outputs=[template_dropdown, template_status, template_name_input]
        )

        load_template_button.click(
            fn=load_template_handler,
            inputs=[template_dropdown],
            outputs=[template_status]
        ).then(
            fn=quality_settings_values, inputs=[],
            outputs=[quality_gate_checkbox,
                     quality_thresholds_editor, music_seed_input]
        )

        delete_template_button.click(
            fn=delete_template_and_update,
            inputs=[template_dropdown],
            outputs=[template_dropdown, template_status]
        )

    return app


if __name__ == "__main__":
    print("Starting NTN Podcast Creator...")
    print("=" * 50)

    # Check for FFmpeg
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"],
                                capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✓ FFmpeg detected")
        else:
            print("⚠ Warning: FFmpeg may not be properly installed")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠ Warning: FFmpeg not found. Please install FFmpeg for audio processing.")
        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  macOS: brew install ffmpeg")
        print("  Windows: Download from https://ffmpeg.org/download.html")

    print("=" * 50)

    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
