import os
import shutil
import logging
import requests
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4, MP4Tags
from jinja2 import Template
from src.config import config
from src.metadata import MetadataGenerator

logger = logging.getLogger(__name__)

class Organizer:
    def __init__(self):
        self.metadata_generator = MetadataGenerator()
        # Template for directory structure
        self.dir_template = Template("{{ author }}/{{ series }}/{{ title }}") 
        # Default simple template if series missing: {{ author }}/{{ title }}
        
    def organize(self, dirpath, files, metadata, mode="copy"):
        logger.info(f"Organizing {metadata.title} by {metadata.author} (Mode: {mode})")
        
        dest_base, rel_path = self.calculate_destination(metadata)
        staging_dir = os.path.join(config.OUTPUT_DIR, ".staging", rel_path)
        
        # 1. Create Staging Directory
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Would create staging directory: {staging_dir}")
        else:
            if os.path.exists(staging_dir):
                shutil.rmtree(staging_dir)
            os.makedirs(staging_dir)
        
        # 2. Copy/Process Files to Staging
        context = {
            "title": self._sanitize(metadata.title or "Unknown Title"),
        }
        
        for i, filepath in enumerate(sorted(files)):
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1]
            
            # Simple rename: Title - 01.mp3 if multi-file, else Title.mp3
            new_filename = f"{context['title']} - {i+1:02d}{ext}" if len(files) > 1 else f"{context['title']}{ext}"
            
            dest_file = os.path.join(staging_dir, new_filename)
            if config.DRY_RUN:
                logger.info(f"[DRY RUN] Would copy {filepath} to {dest_file}")
            else:
                shutil.copy2(filepath, dest_file)
            
        # 3. Generate metadata.json
        if config.DRY_RUN:
             logger.info(f"[DRY RUN] Would generate metadata.json in {staging_dir}")
        else:
             self.metadata_generator.generate_json(metadata, staging_dir)
        
        # 4. Download Cover Art
        if hasattr(metadata, 'cover_url') and metadata.cover_url:
            self._download_cover(metadata.cover_url, staging_dir)
            
        # 5. Apply Permissions
        self._apply_permissions(staging_dir)
        
        # 6. Write Tags
        self._write_tags(staging_dir, metadata)

        # 7. Move Staging to Final Destination
        final_dest = dest_base
        
        if config.DRY_RUN:
             logger.info(f"[DRY RUN] Would move {staging_dir} to {final_dest}")
             if mode == 'move':
                 logger.info(f"[DRY RUN] Would remove original files from {dirpath}")
        else:
            os.makedirs(os.path.dirname(final_dest), exist_ok=True)
            try:
                 if os.path.exists(final_dest):
                     # If exists, merge/overwrite
                     shutil.rmtree(final_dest) 
                 
                 os.rename(staging_dir, final_dest)
                 logger.info(f"Successfully moved processed files to {final_dest}")
                 
                 # 8. Cleanup Original Files (If Move Mode)
                 if mode == 'move':
                     self._cleanup_source(dirpath, files)
                     
            except Exception as e:
                logger.error(f"Failed to move to final destination: {e}")
                raise e

    def calculate_destination(self, metadata):
        # 1. Determine Destination Path
        # Handle missing fields gracefully for template
        context = {
            "author": self._sanitize(metadata.author or "Unknown Author"),
            "title": self._sanitize(metadata.title or "Unknown Title"),
            "series": self._sanitize(metadata.series or ""),
            "year": metadata.year or ""
        }
        
        # Logic to choose template based on available data
        if metadata.series:
            rel_path = f"{context['author']}/{context['series']}/{context['title']}"
        else:
             rel_path = f"{context['author']}/{context['title']}"
             
        # Support user-defined template later?
        # For now, hardcoded structure: Author/Series/Book or Author/Book
        
        dest_base = os.path.join(config.OUTPUT_DIR, rel_path)
        return dest_base, rel_path

    def _cleanup_source(self, dirpath, files):
        logger.info(f"Cleaning up source files in {dirpath}")
        try:
             # Delete the processed files
             for f in files:
                 if os.path.exists(f):
                     os.remove(f)
             
             # Attempt to remove the directory if empty
             # If dirpath differs from specific input root check? 
             # We should only remove if it's a subdirectory of input, not input root itself.
             if os.path.abspath(dirpath) != os.path.abspath(config.INPUT_DIR):
                 try:
                     os.rmdir(dirpath) # Only removes if empty
                     logger.info(f"Removed empty source directory {dirpath}")
                 except OSError:
                     pass # Directory not empty
        except Exception as e:
            logger.warning(f"Failed to cleanup source: {e}")


    def _sanitize(self, text):
        # Remove characters invalid in filenames
        return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_', '.')).strip()

    def _download_cover(self, url, dest_dir):
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Would download cover from {url} to {dest_dir}")
            return
            
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(os.path.join(dest_dir, "cover.jpg"), 'wb') as f:
                f.write(response.content)
            logger.info("Downloaded cover art")
        except Exception as e:
            logger.error(f"Failed to download cover: {e}")

    def _apply_permissions(self, directory):
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Would apply permissions {config.PUID}:{config.PGID} to {directory}")
            return

        uid = config.PUID
        gid = config.PGID
        logger.info(f"Applying permissions {uid}:{gid} to {directory}")
        try:
            for root, dirs, files in os.walk(directory):
                os.chown(root, uid, gid)
                os.chmod(root, 0o775)
                for f in files:
                    filepath = os.path.join(root, f)
                    os.chown(filepath, uid, gid)
                    os.chmod(filepath, 0o664)
            # Apply to the directory itself if not covered by walk (it usually is if we walk it)
            os.chown(directory, uid, gid)
            os.chmod(directory, 0o775)
        except Exception as e:
            logger.error(f"Failed to apply permissions: {e}")

    def move_to_manual(self, dirpath, files, metadata):
        manual_dir = os.path.join(config.OUTPUT_DIR, "Manual_Intervention")
        if not config.DRY_RUN:
            if not os.path.exists(manual_dir):
                os.makedirs(manual_dir)
            
        # Move source folder to manual dir
        dest = os.path.join(manual_dir, os.path.basename(dirpath))
        
        logger.warning(f"Moving {dirpath} to {dest} for manual intervention")
        
        if config.DRY_RUN:
            logger.info(f"[DRY RUN] Would move {dirpath} to {dest}")
            if os.path.abspath(dirpath) == os.path.abspath(config.INPUT_DIR):
                 logger.info(f"[DRY RUN] Would move individual files to {dest}")
            # Simulate metadata generation in dry run
            logger.info(f"[DRY RUN] Would generata metadata.json in {dest}")
            return

        try:
             # Ideally we move the whole dir
             # If files are isolated, move files.
             if os.path.exists(dest):
                  shutil.rmtree(dest)
             
             # If dirpath is not root input
             if os.path.abspath(dirpath) != os.path.abspath(config.INPUT_DIR):
                 shutil.move(dirpath, dest)
             else:
                 # Move individual files
                 os.makedirs(dest, exist_ok=True)
                 for f in files:
                     shutil.move(f, os.path.join(dest, os.path.basename(f)))
                     
             # Write metadata.json with what we found anyway to help
             self.metadata_generator.generate_json(metadata, dest)
             
        except Exception as e:
            logger.error(f"Failed to move to manual intervention: {e}")

    def _write_tags(self, directory, metadata):
        if config.DRY_RUN:
             logger.info(f"[DRY RUN] Would write tags to files in {directory}")
             return

        logger.info(f"Writing tags to files in {directory}")
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                
                try:
                    if ext == '.mp3':
                        try:
                            audio = EasyID3(filepath)
                        except mutagen.id3.ID3NoHeaderError:
                            # Create a new tag and verify it's saved
                            audio = EasyID3()
                            audio.save(filepath, v2_version=3)
                            # Reload so valid filename is associated
                            audio = EasyID3(filepath)
                            
                        audio['title'] = metadata.title
                        audio['artist'] = metadata.author
                        if metadata.year:
                            audio['date'] = metadata.year
                        audio.save()
                        
                    elif ext in ['.m4b', '.m4a']:
                        audio = MP4(filepath)
                        # Mutagen MP4 tags are complex, using standard keys
                        if audio.tags is None:
                            audio.add_tags()
                        
                        audio.tags['\xa9nam'] = metadata.title # Title
                        audio.tags['\xa9ART'] = metadata.author # Artist
                        audio.tags['\xa9alb'] = metadata.title # Album (often same as title for Audiobooks)
                        if metadata.year:
                            audio.tags['\xa9day'] = metadata.year
                        if hasattr(metadata, 'description') and metadata.description:
                            audio.tags['desc'] = metadata.description
                        
                        audio.save()
                except Exception as e:
                    logger.warning(f"Failed to write tags for {filepath}: {e}")
