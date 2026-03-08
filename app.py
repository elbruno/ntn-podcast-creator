"""Main application for NTN Podcast Creator with Gradio UI."""

import os
import shutil
import datetime
import re
import urllib.request
import xml.etree.ElementTree as ET
import gradio as gr
from typing import Optional, List, Tuple
from features.audio_processor import AudioProcessor
from features.config_manager import ConfigManager, DEFAULT_RSS_FEED_URL
from features.audio_denoiser_processor import denoise_audio_file
from features.template_manager import TemplateManager


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


def get_bottom_console_html(console_text: str, visible: bool = True, show_close: bool = False, download_path: Optional[str] = None) -> str:
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


def build_voice_order_rows(voice_files) -> List[List]:
    """Build default order table rows for uploaded voice files."""
    if not voice_files:
        return []

    if not isinstance(voice_files, list):
        voice_files = [voice_files]

    rows = []
    for idx, vf in enumerate(voice_files, start=1):
        if vf:
            rows.append([idx, os.path.basename(vf), True])
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
        return [(path, True) for path in prioritized_list]

    try:
        if hasattr(order_table, "values"):
            order_rows = order_table.values.tolist()
        elif hasattr(order_table, "tolist"):
            order_rows = order_table.tolist()
        else:
            order_rows = order_table
    except Exception:
        order_rows = order_table

    if not isinstance(order_rows, list):
        return [(path, True) for path in voice_list]

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
                        "Background Music", row.get("background music", row.get(2, True))))
                )
            else:
                if len(row) < 2:
                    continue
                order_val, name_val = row[0], row[1]
                use_background_val = row[2] if len(row) > 2 else True
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
        return [(path, True) for path in voice_list]

    ordered_entries.sort(key=lambda x: (x[0], voice_list.index(x[1])))
    ordered_segments = [(path, use_background)
                        for _, path, use_background in ordered_entries]

    for path in voice_list:
        if path not in [p for p, _ in ordered_segments]:
            ordered_segments.append((path, True))

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


def get_progress_html(pct, msg):
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


def create_podcast_handler_with_progress(voice_file, output_name, delete_voice, trim_silence, denoise_audio, denoise_method, enhance_voice, voice_enhancement_preset, normalize_lufs, target_lufs, intro_voice_overlap, voice_outro_overlap, generate_transcript, whisper_model, voice_order_table=None, intro_override_file=None, progress=gr.Progress()):
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
        voice_order_table: Table for custom voice file ordering
        progress: Gradio progress tracker
    """
    import threading
    import queue
    import time

    # Clear the console at start
    global console_log
    console_log.clear()

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

    intro_path = intro_override_path or config_manager.get_intro()
    outro_path = config_manager.get_outro()
    background_tracks = config_manager.get_background_tracks()
    volume = config_manager.get_volume()
    track_volumes = config_manager.get_all_track_volumes()

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

    def run_process():
        try:
            result_path, denoised_path, transcript_path = audio_processor.create_podcast(
                voice_file=voice_path,
                intro_file=intro_path,
                outro_file=outro_path,
                background_files=background_tracks if (
                    background_tracks and (
                        len(voice_paths) <= 1 or len(background_segments) > 0)
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
                generate_transcript=generate_transcript,
                whisper_model=whisper_model,
                defer_transcription=True,
                log_callback=threaded_log_callback
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

        log_message(f"✓ Podcast created successfully: {output_name}.mp3")
        log_message("=" * 50)

        autoplay_script = get_audio_autoplay_script("podcast-audio-player")

        if generate_transcript:
            log_message("🎧 Episode audio ready. Auto-playing in browser...")
            current_console = get_console_log()
            yield "🎧 Playing episode audio...", result_path, denoised_path, None, current_console, get_progress_html(0.9, "🎧 Playing episode audio...") + autoplay_script, get_bottom_console_html(current_console)

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
            yield f"✓ Podcast created successfully: {output_name}.mp3", result_path, denoised_path, None, final_console_log, get_progress_html(1.0, "✅ Complete!"), get_bottom_console_html(final_console_log, visible=True, show_close=True, download_path=result_path)
        else:
            final_transcript = transcript_path if transcript_path and os.path.exists(
                transcript_path) else None
            final_console_log = get_console_log()
            yield f"✓ Podcast created successfully: {output_name}.mp3", result_path, denoised_path, final_transcript, final_console_log, get_progress_html(1.0, "✅ Complete!") + autoplay_script, get_bottom_console_html(final_console_log, visible=True, show_close=True, download_path=result_path)


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
        settings = {
            "intro_file": config_manager.get_intro(),
            "outro_file": config_manager.get_outro(),
            "background_tracks": config_manager.get_background_tracks(),
            "background_volume": config_manager.get_volume(),
            "track_volumes": config_manager.get_all_track_volumes(),
            "last_output_name": config_manager.get_last_output_name(),
            "rss_feed_url": config_manager.get_rss_feed_url(),
            "prioritize_recording_filename": config_manager.get_prioritize_recording_filename(),
            "intro_voice_overlap": config_manager.get_intro_voice_overlap(),
            "voice_outro_overlap": config_manager.get_voice_outro_overlap(),
            "export_date": datetime.datetime.now().isoformat()
        }

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
        settings = config_manager.get_template_settings()

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
            config_manager.apply_template_settings(settings)
            config_manager.set_active_template(template_name)
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


def create_ui():
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
                                type="filepath"
                            )

                            gr.Markdown("""
                            *Upload one or more audio files. Multiple files will be concatenated in the order you define below.*
                            """)

                            voice_order_table = gr.Dataframe(
                                label="Arrange Voice Recordings Order",
                                headers=["Order", "File Name",
                                         "Use Background Music"],
                                datatype=["number", "str", "bool"],
                                row_count=(0, "dynamic"),
                                col_count=3,
                                type="array",
                                value=[],
                                interactive=True
                            )

                            gr.Markdown("""
                            Edit the **Order** column to choose playback order (1 = first). Use **Use Background Music** to enable/disable background per uploaded track (default: enabled).
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
                            gr.Markdown("### 📊 Preview")
                            timeline_html = gr.HTML(
                                label="Timeline Preview",
                                value=preview_timeline(None)
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
            """Update timeline, suggested filename, and order table when voice is uploaded."""
            prefer_recording_first = config_manager.get_prioritize_recording_filename()
            ordered_voice_files = prioritize_recording_files(
                voice_file, prefer_recording_first)
            default_bg_flags = [True] * len(ordered_voice_files) if isinstance(
                ordered_voice_files, list) and ordered_voice_files else [True] if ordered_voice_files else []
            timeline = preview_timeline(
                ordered_voice_files, intro_override_file, default_bg_flags)
            suggested_name = suggest_podcast_name(voice_file)
            order_rows = build_voice_order_rows(ordered_voice_files)
            return timeline, suggested_name, order_rows

        voice_input.change(
            fn=update_on_voice_upload,
            inputs=[voice_input, intro_override_input],
            outputs=[timeline_html, output_name_input, voice_order_table]
        )

        def update_timeline_with_intro_override(voice_file, intro_override_file, order_table):
            ordered_segments = order_voice_segments(voice_file, order_table)
            ordered_files = [path for path, _ in ordered_segments]
            bg_flags = [use_bg for _, use_bg in ordered_segments]
            return preview_timeline(ordered_files, intro_override_file, bg_flags)

        intro_override_input.change(
            fn=update_timeline_with_intro_override,
            inputs=[voice_input, intro_override_input, voice_order_table],
            outputs=[timeline_html]
        )

        def update_timeline_with_order(voice_file, order_table, intro_override_file):
            ordered_segments = order_voice_segments(voice_file, order_table)
            ordered_files = [path for path, _ in ordered_segments]
            bg_flags = [use_bg for _, use_bg in ordered_segments]
            return preview_timeline(ordered_files, intro_override_file, bg_flags)

        voice_order_table.change(
            fn=update_timeline_with_order,
            inputs=[voice_input, voice_order_table, intro_override_input],
            outputs=[timeline_html]
        )

        create_button_event = create_button.click(
            fn=create_podcast_handler_with_progress,
            inputs=[voice_input, output_name_input,
                    delete_voice_checkbox, trim_silence_checkbox,
                    denoise_audio_checkbox, denoise_method_dropdown,
                    enhance_voice_checkbox, voice_enhancement_preset_dropdown,
                    normalize_lufs_checkbox, target_lufs_slider,
                    intro_voice_overlap_checkbox, voice_outro_overlap_checkbox,
                    generate_transcript_checkbox, whisper_model_dropdown,
                    voice_order_table, intro_override_input],
            outputs=[status_output, audio_output,
                     denoised_audio_output, transcript_output, realtime_console_output, progress_bar, bottom_console],
            show_progress='full'
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
