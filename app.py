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
        return "No intro file selected"

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
        return f"Intro file saved: {os.path.basename(dest_path)}"
    except Exception as e:
        print(f"Error saving intro file: {e}")
        return "Error saving intro file"


def update_outro_file(file):
    """Update outro file in configuration."""
    if file is None:
        config_manager.update_outro(None)
        return "No outro file selected"

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
        return f"Outro file saved: {os.path.basename(dest_path)}"
    except Exception as e:
        print(f"Error saving outro file: {e}")
        return "Error saving outro file"


def add_background_track(file):
    """Add background music track."""
    global background_tracks_list

    if file is None:
        return "No file selected", get_background_tracks_display()

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
        return f"Added: {os.path.basename(dest_path)}", get_background_tracks_display()
    except Exception as e:
        print(f"Error saving background file: {e}")
        return "Error saving file", get_background_tracks_display()


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


def clear_background_tracks():
    """Clear all background tracks."""
    global background_tracks_list
    config_manager.update_background_tracks([])
    background_tracks_list = []
    return "All background tracks cleared", get_background_tracks_display()


def update_volume(volume):
    """Update background music volume."""
    config_manager.update_volume(int(volume))
    return f"Volume set to {int(volume)}%"


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
                        status_output = gr.Textbox(
                            label="Status",
                            interactive=False,
                            lines=3
                        )
                        audio_output = gr.Audio(
                            label="Your Podcast",
                            type="filepath"
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
                        intro_input = gr.Audio(
                            label="Upload Intro Audio",
                            type="filepath"
                        )
                        intro_status = gr.Textbox(
                            label="Status",
                            interactive=False
                        )

                        gr.Markdown("---")

                        gr.Markdown("#### Outro Audio")
                        gr.Markdown("*Plays after your voice recording*")
                        outro_input = gr.Audio(
                            label="Upload Outro Audio",
                            type="filepath"
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

                        gr.Markdown("---")

                        gr.Markdown("#### Volume Settings")
                        volume_slider = gr.Slider(
                            minimum=0,
                            maximum=50,
                            value=saved_volume,
                            step=1,
                            label="Background Music Volume (%)",
                            info="Recommended: 10-12%"
                        )
                        volume_status = gr.Textbox(
                            label="Volume Status",
                            interactive=False
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
            outputs=[intro_status]
        )

        outro_input.change(
            fn=update_outro_file,
            inputs=[outro_input],
            outputs=[outro_status]
        )

        add_bg_button.click(
            fn=add_background_track,
            inputs=[background_input],
            outputs=[background_status, background_list]
        )

        clear_bg_button.click(
            fn=clear_background_tracks,
            inputs=[],
            outputs=[background_status, background_list]
        )

        volume_slider.change(
            fn=update_volume,
            inputs=[volume_slider],
            outputs=[volume_status]
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
