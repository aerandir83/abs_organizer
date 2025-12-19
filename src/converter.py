import os
import subprocess
import logging
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from src.config import config

logger = logging.getLogger(__name__)

class AudioConverter:
    def __init__(self):
        self.ffmpeg_path = config.FFMPEG_PATH

    def merge_files(self, input_files, metadata, output_dir):
        """
        Merges multiple audio files into a single M4B with chapters.
        Returns the path to the created M4B file.
        """
        if not input_files:
            return None

        # Sanitize title for filename
        sanitized_title = "".join(c for c in metadata.title if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        output_filename = f"{sanitized_title}.m4b"
        output_path = os.path.join(output_dir, output_filename)
        
        logger.info(f"Starting conversion/merge for {metadata.title} ({len(input_files)} files) -> {output_path}")

        # 1. Create file list for ffmpeg concat
        list_file_path = os.path.join(output_dir, "files.txt")
        self._create_concat_list(input_files, list_file_path)

        # 2. Generate Chapter Metadata
        metadata_file_path = os.path.join(output_dir, "ffmetadata.txt")
        self._create_metadata_file(input_files, metadata, metadata_file_path)

        # 3. Determine Encoder Flags
        audio_codec = "aac"
        if config.FFMPEG_HW_ACCEL == "aac_at":
             audio_codec = "aac_at" # macOS hardware acceleration
        
        # 4. Run FFMPEG
        # Command: ffmpeg -f concat -safe 0 -i files.txt -i ffmetadata.txt -map_metadata 1 -c:a aac -b:a 128k -vn output.m4b
        # -map_metadata 1 tells ffmpeg to use the global metadata from the second input (ffmetadata.txt)
        
        cmd = [
            self.ffmpeg_path,
            "-y", # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", list_file_path,
            "-i", metadata_file_path,
            "-map_metadata", "1",
            "-c:a", audio_codec,
            "-b:a", "128k", # Standard audiobook bitrate
            "-vn", # No video
            output_path
        ]

        logger.info(f"Running ffmpeg: {' '.join(cmd)}")
        
        try:
            # Run ffmpeg (blocking for now - parallel processing handled at book level)
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info("Conversion complete.")
            
            # Cleanup temp files
            if os.path.exists(list_file_path):
                os.remove(list_file_path)
            if os.path.exists(metadata_file_path):
                os.remove(metadata_file_path)
                
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg failed: {e.stderr.decode('utf-8', errors='ignore')}")
            raise Exception("FFmpeg conversion failed")

    def _create_concat_list(self, files, list_path):
        with open(list_path, 'w', encoding='utf-8') as f:
            for filepath in sorted(files):
                # FFmpeg concat demuxer requires escaping:
                # 1. Backslashes can be problematic, better to use forward slashes
                # 2. Single quotes must be escaped
                safe_path = filepath.replace("\\", "/").replace("'", "'\\''") 
                f.write(f"file '{safe_path}'\n")

    def _create_metadata_file(self, files, metadata, output_path):
        # Header
        content = [
            ";FFMETADATA1",
            f"title={metadata.title}",
            f"artist={metadata.author}",
            f"album={metadata.title}",
            f"date={metadata.year}",
            f"genre=Audiobook",
            f"description={getattr(metadata, 'description', '')}"
        ]

        # Chapters
        current_time = 0
        timebase = 1000 # milliseconds

        for i, filepath in enumerate(sorted(files)):
            duration_ms = self._get_duration_ms(filepath)
            
            start = current_time
            end = current_time + duration_ms
            
            # Use filename as chapter title if no better source (could use metadata providers later)
            chapter_title = os.path.splitext(os.path.basename(filepath))[0]
            
            content.append("[CHAPTER]")
            content.append(f"TIMEBASE=1/{timebase}")
            content.append(f"START={int(start)}")
            content.append(f"END={int(end)}")
            content.append(f"title={chapter_title}")
            
            current_time = end

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))

    def _get_duration_ms(self, filepath):
        try:
            ext = os.path.splitext(filepath)[1].lower()
            if ext == '.mp3':
                audio = MP3(filepath)
                return audio.info.length * 1000
            elif ext in ['.m4a', '.m4b', '.mp4']:
                audio = MP4(filepath)
                return audio.info.length * 1000
            elif ext == '.flac':
                audio = FLAC(filepath)
                return audio.info.length * 1000
            else:
                # Fallback or error?
                # Assume 0 or try ffmpeg probe if mutagen fails
                return 0 
        except Exception as e:
            logger.warning(f"Could not get duration for {filepath}: {e}")
            return 0
