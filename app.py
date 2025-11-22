"""Main application for NTN Podcast Creator with Gradio UI."""

import os
import shutil
import gradio as gr
from typing import Optional, List
from audio_processor import AudioProcessor
from config_manager import ConfigManager


# Initialize components
config_manager = ConfigManager()
audio_processor = AudioProcessor()

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


# Global variable for console log
console_log = []


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


def generate_timeline_chart(voice_file: Optional[str], intro_file: Optional[str],
                            outro_file: Optional[str], has_background: bool, 
                            background_tracks: Optional[List[str]] = None,
                            track_volumes: Optional[dict] = None) -> str:
    """Generate a visual timeline chart showing how audio segments are organized.

    Args:
        voice_file: Path to voice recording
        intro_file: Path to intro audio
        outro_file: Path to outro audio
        has_background: Whether background music will be applied
        background_tracks: List of background track paths
        track_volumes: Dictionary mapping track paths to volumes

    Returns:
        HTML string with timeline visualization
    """
    if not voice_file:
        return "<div style='padding: 20px; text-align: center; color: #666;'>Upload a voice recording to preview timeline</div>"

    # Get durations
    intro_duration = get_audio_duration_seconds(
        intro_file) if intro_file else 0.0
    voice_duration = get_audio_duration_seconds(
        voice_file) if voice_file else 0.0
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

    # Add voice segment with background indicator
    if voice_duration > 0:
        html += f"""
                    <div style="width: {voice_percent}%; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                         display: flex; align-items: center; justify-content: center; color: white;
                         font-size: 12px; font-weight: bold; border-right: 2px solid white; position: relative;">
                        <div style="text-align: center; padding: 5px;">
                            <div>VOICE</div>
                            <div style="font-size: 10px; opacity: 0.9;">{format_time(voice_duration)}</div>
                        </div>
                        {"<div style='position: absolute; left: -10px; top: 0; bottom: 0; width: 20px; background: rgba(255,255,255,0.3); z-index: 10;'></div>" if intro_duration > 0 else ""}
                        {"<div style='position: absolute; right: -10px; top: 0; bottom: 0; width: 20px; background: rgba(255,255,255,0.3); z-index: 10;'></div>" if outro_duration > 0 else ""}
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
        # Calculate position and width for background music overlay
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
        html += "<div style='margin: 3px 0;'>🔴 <strong>VOICE</strong> - Your recording"
        if has_background:
            html += " (see background music layer above)"
        html += "</div>"
    if outro_duration > 0:
        html += "<div style='margin: 3px 0;'>🔵 <strong>OUTRO</strong> - Plays last (no background music)</div>"
    if has_background and voice_duration > 0:
        html += "<div style='margin: 3px 0;'>🎵 <strong>BACKGROUND MUSIC</strong> - Plays only during voice recording</div>"
        
        # Show background tracks with volumes
        if background_tracks and len(background_tracks) > 0:
            html += "<div style='margin-top: 10px; padding: 8px; background: #f8f9fa; border-radius: 3px;'>"
            html += "<div style='font-size: 12px; font-weight: bold; margin-bottom: 5px;'>🎼 Background Tracks:</div>"
            for track in background_tracks:
                if os.path.exists(track):
                    track_name = os.path.basename(track)
                    volume = track_volumes.get(track, config_manager.get_volume()) if track_volumes else config_manager.get_volume()
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
    """Add message to console log."""
    global console_log
    console_log.append(message)
    print(message)


def get_console_log() -> str:
    """Get console log as string."""
    global console_log
    return "\n".join(console_log) if console_log else "No logs yet"


def clear_console_log():
    """Clear console log."""
    global console_log
    console_log = []
    return "Console log cleared"


def preview_timeline(voice_file: Optional[str]) -> str:
    """Generate timeline preview.

    Args:
        voice_file: Path to voice recording

    Returns:
        HTML timeline chart
    """
    intro_file = config_manager.get_intro()
    outro_file = config_manager.get_outro()
    background_tracks = config_manager.get_background_tracks()
    track_volumes = config_manager.get_all_track_volumes()
    has_background = background_tracks is not None and len(
        background_tracks) > 0

    return generate_timeline_chart(voice_file, intro_file, outro_file, has_background, background_tracks, track_volumes)


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
        log_message(f"Set volume for {os.path.basename(track_path)} to {int(new_volume)}%")
        
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
    """
    try:
        from pydub import AudioSegment
        import tempfile
        
        # Load the track
        audio = AudioSegment.from_file(track_path)
        
        # Apply volume
        audio_with_volume = audio_processor.reduce_volume(audio, volume)
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
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

    return "\\n".join(settings)


def create_podcast_handler(voice_file, output_name, delete_voice, trim_silence):
    """Handle podcast creation request.

    Args:
        voice_file: Uploaded voice file
        output_name: Desired output filename
        delete_voice: Whether to delete voice file after creation
        trim_silence: Whether to trim silence from start/end

    Returns:
        Tuple of (status message, output file path or None, console log)
    """
    log_message("=" * 50)
    log_message("Starting new podcast creation")

    if voice_file is None:
        log_message("Error: No voice file provided")
        return "Error: Please upload a voice recording file", None, get_console_log()

    if not output_name or output_name.strip() == "":
        output_name = "podcast_output"

    # Remove extension if provided
    output_name = output_name.replace(".mp3", "")
    log_message(f"Output filename: {output_name}.mp3")

    # Save voice file
    voice_path = save_uploaded_file(voice_file, "voice")
    if not voice_path:
        log_message("Error: Could not save voice file")
        return "Error: Could not save voice file", None, get_console_log()

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

    # Create output path
    output_path = os.path.join("outputs", f"{output_name}.mp3")

    # Save output name for next time
    config_manager.update_last_output_name(output_name)

    try:
        # Create podcast
        result_path = audio_processor.create_podcast(
            voice_file=voice_path,
            intro_file=intro_path,
            outro_file=outro_path,
            background_files=background_tracks if background_tracks else None,
            background_volume=volume,
            track_volumes=track_volumes if track_volumes else None,
            output_file=output_path,
            trim_silence=trim_silence,
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
        return f"✓ Podcast created successfully: {output_name}.mp3", result_path, get_console_log()

    except Exception as e:
        error_msg = f"Error creating podcast: {str(e)}"
        log_message(error_msg)
        log_message("=" * 50)
        return error_msg, None, get_console_log()


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
        
        # Read settings file
        with open(file_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
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
            config_manager.update_last_output_name(settings["last_output_name"])
        
        log_message(f"Settings imported successfully from {os.path.basename(file_path)}")
        return f"✓ Settings imported successfully from {os.path.basename(file_path)}"
        
    except json.JSONDecodeError as e:
        error_msg = f"Error: Invalid settings file format - {e}"
        log_message(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error importing settings: {e}"
        log_message(error_msg)
        return error_msg



def create_ui():
    """Create Gradio user interface."""

    # Load saved settings
    saved_volume = config_manager.get_volume()
    saved_output_name = config_manager.get_last_output_name()

    with gr.Blocks(title="NTN Podcast Creator") as app:
        gr.Markdown("""
        # 🎙️ NTN Podcast Creator

        Create professional podcasts with intro, outro, and background music.
        """)

        with gr.Tabs():
            # Main Tab - Podcast Creation
            with gr.Tab("Create Podcast"):
                gr.Markdown("""
                ### Upload your voice recording and create your podcast
                Default intro, outro, and background music are automatically applied.
                """)

                with gr.Row():
                    with gr.Column():
                        voice_input = gr.Audio(
                            label="Voice Recording (Required)",
                            type="filepath"
                        )

                        output_name_input = gr.Textbox(
                            label="Podcast Filename (without .mp3)",
                            value=saved_output_name,
                            placeholder="my_podcast"
                        )

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

                        create_button = gr.Button(
                            "🎬 Create Podcast",
                            variant="primary",
                            size="lg"
                        )

                    with gr.Column():
                        timeline_html = gr.HTML(
                            label="Timeline Preview",
                            value=preview_timeline(None)
                        )

                        status_output = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=3
                        )
                        audio_output = gr.Audio(
                            label="Your Podcast",
                            type="filepath"
                        )
                        
                        gr.Markdown("**Download Options**")
                        with gr.Row():
                            export_settings_button = gr.Button(
                                "💾 Download Settings",
                                variant="secondary",
                                size="sm"
                            )
                            settings_file_output = gr.File(
                                label="Settings File",
                                visible=True
                            )
                        
                        gr.Markdown("**Import Settings**")
                        with gr.Row():
                            import_settings_input = gr.File(
                                label="Upload Settings File (JSON)",
                                file_types=[".json"]
                            )
                            import_status = gr.Textbox(
                                label="Import Status",
                                interactive=False
                            )


                gr.Markdown("""
                ---
                ### 💡 Quick Tips
                - Upload your voice recording and click "Create Podcast"
                - Default audio files are automatically loaded from `audios/` folder
                - Background tracks are randomly selected and mixed to match your recording length
                - Generated podcasts are saved in the `outputs/` directory
                - Configure intro, outro, and background music in the Settings tab
                """)

            # Settings Tab - Audio Configuration
            with gr.Tab("Settings"):
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
                        gr.Markdown("*Select a track above to adjust its volume individually*")
                        
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

            # Console Log Tab
            with gr.Tab("Console Log"):
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

        # Event handlers
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
            outputs=[track_volume_status, bg_track_player_with_volume, bg_track_player]
        )


        # Update timeline when voice file is uploaded
        voice_input.change(
            fn=preview_timeline,
            inputs=[voice_input],
            outputs=[timeline_html]
        )

        create_button.click(
            fn=create_podcast_handler,
            inputs=[voice_input, output_name_input,
                    delete_voice_checkbox, trim_silence_checkbox],
            outputs=[status_output, audio_output, console_output]
        )

        refresh_settings_button.click(
            fn=get_current_settings,
            inputs=[],
            outputs=[settings_display]
        )

        refresh_log_button.click(
            fn=get_console_log,
            inputs=[],
            outputs=[console_output]
        )

        clear_log_button.click(
            fn=clear_console_log,
            inputs=[],
            outputs=[console_output]
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
