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
    
    # Create unique filename
    dest_path = os.path.join("uploads", original_name)
    
    # Copy file if it's not already in uploads
    if hasattr(uploaded_file, 'name') and uploaded_file.name != dest_path:
        try:
            shutil.copy2(uploaded_file.name, dest_path)
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    return dest_path


def update_intro_file(file):
    """Update intro file in configuration."""
    if file is None:
        config_manager.update_intro(None)
        return "No intro file selected"
    
    saved_path = save_uploaded_file(file, "intro")
    config_manager.update_intro(saved_path)
    return f"Intro file saved: {os.path.basename(saved_path)}"


def update_outro_file(file):
    """Update outro file in configuration."""
    if file is None:
        config_manager.update_outro(None)
        return "No outro file selected"
    
    saved_path = save_uploaded_file(file, "outro")
    config_manager.update_outro(saved_path)
    return f"Outro file saved: {os.path.basename(saved_path)}"


def add_background_track(file):
    """Add background music track."""
    global background_tracks_list
    
    if file is None:
        return "No file selected", get_background_tracks_display()
    
    saved_path = save_uploaded_file(file, "background")
    if saved_path:
        config_manager.add_background_track(saved_path)
        background_tracks_list = config_manager.get_background_tracks()
        return f"Added: {os.path.basename(saved_path)}", get_background_tracks_display()
    
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


def create_podcast_handler(voice_file, output_name):
    """Handle podcast creation request.
    
    Args:
        voice_file: Uploaded voice file
        output_name: Desired output filename
        
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
    
    with gr.Blocks(title="NTN Podcast Creator", theme=gr.themes.Soft()) as app:
        gr.Markdown("""
        # 🎙️ NTN Podcast Creator
        
        Create professional podcasts by combining your voice recording with intro/outro audio and background music.
        All settings are automatically saved for your next session.
        """)
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 1. Upload Your Podcast Voice Recording")
                voice_input = gr.Audio(
                    label="Main Voice Recording",
                    type="filepath"
                )
                
                gr.Markdown("### 2. Optional: Set Intro Audio")
                intro_input = gr.Audio(
                    label="Intro Audio (plays before your voice)",
                    type="filepath"
                )
                intro_status = gr.Textbox(label="Intro Status", interactive=False)
                
                gr.Markdown("### 3. Optional: Set Outro Audio")
                outro_input = gr.Audio(
                    label="Outro Audio (plays after your voice)",
                    type="filepath"
                )
                outro_status = gr.Textbox(label="Outro Status", interactive=False)
            
            with gr.Column():
                gr.Markdown("### 4. Optional: Add Background Music")
                gr.Markdown("Upload one or more tracks. A random track will be selected and looped.")
                background_input = gr.Audio(
                    label="Upload Background Music Track",
                    type="filepath"
                )
                add_bg_button = gr.Button("Add Background Track", variant="secondary")
                background_status = gr.Textbox(label="Upload Status", interactive=False)
                
                background_list = gr.Textbox(
                    label="Current Background Tracks",
                    value=get_background_tracks_display(),
                    interactive=False,
                    lines=5
                )
                clear_bg_button = gr.Button("Clear All Background Tracks", variant="stop")
                
                gr.Markdown("### 5. Configure Background Volume")
                volume_slider = gr.Slider(
                    minimum=0,
                    maximum=50,
                    value=saved_volume,
                    step=1,
                    label="Background Music Volume (%)",
                    info="Recommended: 10-12%"
                )
                volume_status = gr.Textbox(label="Volume Status", interactive=False)
        
        gr.Markdown("---")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 6. Create Your Podcast")
                output_name_input = gr.Textbox(
                    label="Output Filename (without .mp3)",
                    value=saved_output_name,
                    placeholder="my_podcast"
                )
                create_button = gr.Button("🎬 Create Podcast", variant="primary", size="lg")
                
                status_output = gr.Textbox(label="Status", interactive=False)
                audio_output = gr.Audio(label="Download Your Podcast", type="filepath")
        
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
            inputs=[voice_input, output_name_input],
            outputs=[status_output, audio_output]
        )
        
        gr.Markdown("""
        ---
        ### 💡 Tips
        - All uploaded files are saved in the `uploads/` directory
        - Generated podcasts are saved in the `outputs/` directory  
        - Your settings (intro, outro, background tracks, volume) are automatically saved
        - Background music is randomly selected and looped to match your podcast duration
        - Recommended background volume: 10-12% for clear voice quality
        """)
    
    return app


if __name__ == "__main__":
    print("Starting NTN Podcast Creator...")
    print("=" * 50)
    
    # Check for FFmpeg
    try:
        import subprocess
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
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
        share=True,
        show_error=True
    )
