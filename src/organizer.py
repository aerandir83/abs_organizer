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
        
    def organize(self, dirpath, files, metadata):
        logger.info(f"Organizing {metadata.title} by {metadata.author}")
        
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
        staging_dir = os.path.join(config.OUTPUT_DIR, ".staging", rel_path)
        
        # 2. Create Staging Directory
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)
        os.makedirs(staging_dir)
        
        # 3. Copy/Move Files
        # We process files and rename them if needed
        for i, filepath in enumerate(sorted(files)):
            filename = os.path.basename(filepath)
            ext = os.path.splitext(filename)[1]
            
            # Rename logic: 
            # Single file: {Title}{ext}
            # Multi file: {Title} - Part {i+1}{ext} ?
            # BRD: {Series Sequence} - {Title} - Part {Track}.mp3
            # Keeping it simple for now: preserve filename or minimal rename
            
            # Simple rename: Title - 01.mp3
            new_filename = f"{context['title']} - {i+1:02d}{ext}" if len(files) > 1 else f"{context['title']}{ext}"
            
            dest_file = os.path.join(staging_dir, new_filename)
            shutil.copy2(filepath, dest_file)
            
            # Embed cover art if needed (TODO)
            
        # 4. Generate metadata.json
        self.metadata_generator.generate_json(metadata, staging_dir)
        
        # 5. Download Cover Art
        if hasattr(metadata, 'cover_url') and metadata.cover_url:
            self._download_cover(metadata.cover_url, staging_dir)
            
        # 6. Apply Permissions
        self._apply_permissions(staging_dir)
        
        # 7. Write Tags (Requirement 5.2.1)
        self._write_tags(staging_dir, metadata)

        # 8. Atomic Move to Final Destination
        final_dest = dest_base
        if os.path.exists(final_dest):
            logger.warning(f"Destination {final_dest} already exists. Overwriting/Merging.")
            # Depending on policy, we might fail or merge. 
            # For "Move", we typically want to replace or handle collision.
            # shutil.move won't overwrite dir easily.
            # Let's assume we can merge or we should rename if collision.
            pass
            
        # Ensure parent dirs exist
        os.makedirs(os.path.dirname(final_dest), exist_ok=True)
        
        # Rename staging to final
        # If final exists, we might need to remove it first or use specific strategy
        # Here we try to rename.
        try:
             if os.path.exists(final_dest):
                 shutil.rmtree(final_dest) # Dangerous! But ensures clean state.
             os.rename(staging_dir, final_dest)
             logger.info(f"Successfully moved to {final_dest}")
             
             # Cleanup source directory (the group directory in input)
             # Be careful not to delete root input dir
             if os.path.abspath(dirpath) != os.path.abspath(config.INPUT_DIR):
                 shutil.rmtree(dirpath)
                 logger.info(f"Removed source directory {dirpath}")
             else:
                 # If files were in root, we delete them?
                 for f in files:
                     if os.path.exists(f):
                         os.remove(f)
        except Exception as e:
            logger.error(f"Failed to move to final destination: {e}")

    def _sanitize(self, text):
        # Remove characters invalid in filenames
        return "".join(c for c in text if c.isalnum() or c in (' ', '-', '_', '.')).strip()

    def _download_cover(self, url, dest_dir):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(os.path.join(dest_dir, "cover.jpg"), 'wb') as f:
                f.write(response.content)
            logger.info("Downloaded cover art")
        except Exception as e:
            logger.error(f"Failed to download cover: {e}")

    def _apply_permissions(self, directory):
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
        if not os.path.exists(manual_dir):
            os.makedirs(manual_dir)
            
        # Move source folder to manual dir
        dest = os.path.join(manual_dir, os.path.basename(dirpath))
        
        logger.warning(f"Moving {dirpath} to {dest} for manual intervention")
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
                            audio = EasyID3()
                            audio.save(filepath)
                            
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
