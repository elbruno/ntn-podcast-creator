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


def save_uploaded_file(uploaded_file, prefix: str = "file") -> Optional[str]:
    """Save uploaded file to uploads directory.

    Args:
        uploaded_file: Gradio uploaded file object
        prefix: Prefix for filename

    Returns:
        Path to saved file or None
    """
    if uploaded_file is None:
        return None

    # Get original filename
    if hasattr(uploaded_file, 'name'):
        original_name = os.path.basename(uploaded_file.name)
    else:
        original_name = f"{prefix}.mp3"

    # Create destination path
    dest_path = os.path.join("uploads", original_name)

    # Check if file is already in uploads directory
    if hasattr(uploaded_file, 'name'):
        source_dir = os.path.dirname(os.path.abspath(uploaded_file.name))
        target_dir = os.path.abspath("uploads")

        # Only copy if not already in uploads directory
        if source_dir != target_dir:
            try:
                shutil.copy2(uploaded_file.name, dest_path)
            except Exception as e:
                print(f"Error saving file: {e}")
                return None
        else:
            # File is already in uploads, verify it exists
            if not os.path.exists(dest_path):
                print(f"Warning: Expected file not found: {dest_path}")
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


def create_podcast_handler(voice_file, output_name, delete_voice):
    """Handle podcast creation request.

    Args:
        voice_file: Uploaded voice file
        output_name: Desired output filename
        delete_voice: Whether to delete voice file after creation

    Returns:
        Tuple of (status message, output file path or None)
    """
    if voice_file is None:
        return "Error: Please upload a voice recording file", None

    if not output_name or output_name.strip() == "":
        output_name = "podcast_output"

    # Remove extension if provided
    output_name = output_name.replace(".mp3", "")

    # Save voice file
    voice_path = save_uploaded_file(voice_file, "voice")
    if not voice_path:
        return "Error: Could not save voice file", None

    # Get configuration
    intro_path = config_manager.get_intro()
    outro_path = config_manager.get_outro()
    background_tracks = config_manager.get_background_tracks()
    volume = config_manager.get_volume()

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
            output_file=output_path
        )

        # Delete voice recording if requested
        if delete_voice and voice_path and os.path.exists(voice_path):
            try:
                os.remove(voice_path)
                print(f"Deleted voice recording: {voice_path}")
            except Exception as e:
                print(f"Warning: Could not delete voice file: {e}")

        return f"✓ Podcast created successfully: {output_name}.mp3", result_path

    except Exception as e:
        error_msg = f"Error creating podcast: {str(e)}"
        print(error_msg)
        return error_msg, None


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
                            "*One track is randomly selected and looped*")

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
                - Background music is randomly selected and looped to match podcast duration
                - Place default audio files in the respective folders and restart to auto-load
                """)

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
            inputs=[voice_input, output_name_input, delete_voice_checkbox],
            outputs=[status_output, audio_output]
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
