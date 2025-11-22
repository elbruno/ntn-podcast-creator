"""Audio processing for podcast creation."""

import os
import random
from typing import List, Optional
from pydub import AudioSegment


class AudioProcessor:
    """Handles audio mixing and processing for podcast creation."""
    
    def __init__(self):
        """Initialize audio processor."""
        pass
    
    def load_audio(self, file_path: str) -> AudioSegment:
        """Load audio file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            AudioSegment object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            Exception: If file cannot be loaded
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        try:
            # Try to load the audio file
            audio = AudioSegment.from_file(file_path)
            return audio
        except Exception as e:
            raise Exception(f"Error loading audio file {file_path}: {e}")
    
    def reduce_volume(self, audio: AudioSegment, volume_percent: int) -> AudioSegment:
        """Reduce audio volume.
        
        Args:
            audio: AudioSegment to process
            volume_percent: Target volume as percentage (0-100)
            
        Returns:
            AudioSegment with reduced volume
        """
        if volume_percent >= 100:
            return audio
        
        if volume_percent <= 0:
            # Silence
            return audio - 60
        
        # Convert percentage to dB using logarithmic scaling
        # volume_percent of 100 = 0 dB, 50 = -6 dB, 10 = -20 dB
        import math
        db_change = 20 * math.log10(volume_percent / 100)
        return audio + db_change
    
    def create_looped_background(
        self, 
        background_files: List[str], 
        target_duration_ms: int,
        volume_percent: int = 10
    ) -> Optional[AudioSegment]:
        """Create looped background music from random track.
        
        Args:
            background_files: List of background music file paths
            target_duration_ms: Target duration in milliseconds
            volume_percent: Volume percentage for background (0-100)
            
        Returns:
            AudioSegment with looped background music or None if no files
        """
        if not background_files:
            return None
        
        # Filter out files that don't exist
        valid_files = [f for f in background_files if os.path.exists(f)]
        if not valid_files:
            print("Warning: No valid background music files found")
            return None
        
        # Randomly select a background track
        selected_file = random.choice(valid_files)
        print(f"Selected background music: {os.path.basename(selected_file)}")
        
        try:
            background = self.load_audio(selected_file)
        except Exception as e:
            print(f"Error loading background music: {e}")
            return None
        
        # Reduce volume
        background = self.reduce_volume(background, volume_percent)
        
        # Loop the background music to match target duration
        background_duration_ms = len(background)
        if background_duration_ms < target_duration_ms:
            # Calculate how many times to loop
            loops_needed = (target_duration_ms // background_duration_ms) + 1
            background = background * loops_needed
        
        # Trim to exact duration
        background = background[:target_duration_ms]
        
        return background
    
    def mix_audio(
        self,
        main_audio: AudioSegment,
        background: Optional[AudioSegment] = None
    ) -> AudioSegment:
        """Mix main audio with background music.
        
        Args:
            main_audio: Main audio track
            background: Background music (optional)
            
        Returns:
            Mixed audio
        """
        if background is None:
            return main_audio
        
        # Overlay background music on main audio
        return main_audio.overlay(background)
    
    def create_podcast(
        self,
        voice_file: str,
        intro_file: Optional[str] = None,
        outro_file: Optional[str] = None,
        background_files: Optional[List[str]] = None,
        background_volume: int = 10,
        output_file: str = "output.mp3"
    ) -> str:
        """Create complete podcast with intro, outro, and background music.
        
        Args:
            voice_file: Path to main voice recording
            intro_file: Path to intro audio (optional)
            outro_file: Path to outro audio (optional)
            background_files: List of background music files (optional)
            background_volume: Volume percentage for background (0-100)
            output_file: Path for output file
            
        Returns:
            Path to output file
            
        Raises:
            Exception: If processing fails
        """
        print("Starting podcast creation...")
        
        # Load main voice recording
        print(f"Loading main voice: {os.path.basename(voice_file)}")
        voice = self.load_audio(voice_file)
        
        # Build the podcast sequence
        podcast = AudioSegment.empty()
        
        # Add intro if provided
        if intro_file and os.path.exists(intro_file):
            print(f"Adding intro: {os.path.basename(intro_file)}")
            intro = self.load_audio(intro_file)
            podcast += intro
        
        # Add main voice
        print("Adding main voice recording")
        podcast += voice
        
        # Add outro if provided
        if outro_file and os.path.exists(outro_file):
            print(f"Adding outro: {os.path.basename(outro_file)}")
            outro = self.load_audio(outro_file)
            podcast += outro
        
        # Add background music if provided
        if background_files:
            print(f"Creating background music (volume: {background_volume}%)")
            background = self.create_looped_background(
                background_files,
                len(podcast),
                background_volume
            )
            if background:
                print("Mixing background music with podcast")
                podcast = self.mix_audio(podcast, background)
        
        # Export final podcast
        print(f"Exporting to: {output_file}")
        podcast.export(output_file, format="mp3")
        print("Podcast creation complete!")
        
        return output_file
