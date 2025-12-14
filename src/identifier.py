import os
import re
import logging
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.id3 import ID3
from mutagen.mp4 import MP4

logger = logging.getLogger(__name__)

class IdentificationResult:
    def __init__(self):
        self.title = None
        self.author = None
        self.year = None
        self.series = None
        self.series_part = None
        self.narrator = None
        self.asin = None
        self.isbn = None
        self.confidence = 0
        self.source = "unknown" # 'tags', 'filename', 'api'

    def __repr__(self):
        return f"<IdentificationResult title='{self.title}' author='{self.author}' asin='{self.asin}'>"

class Identifier:
    def __init__(self):
        # Regex patterns for cleaning and extraction
        self.noise_patterns = [
            r'\[.*?\]', # [MP3], [2022]
            r'\(.*?\)', # (Unabridged)
            r'\d+kbps',
            r'\d+ kbps',
            r'Unabridged',
            r'Abridged',
            r'Audiobook',
        ]
        
    def identify(self, dirpath, files):
        logger.info(f"Identifying content in {dirpath}")
        
        # 1. Try embedded tags
        # We try the first valid audio file
        tag_result = IdentificationResult()
        for f in files:
            if self._is_audio(f):
                tag_result = self._extract_from_tags(f)
                if tag_result.title and tag_result.author:
                    break
        
        # 2. Try filename/dirname parsing
        # Use directory name if available (and not just "Input"), else filename
        # If the files are in the root of input dir, dirpath might be "Input". 
        # But IngestManager groups by parent dir. 
        # If files are /Input/Book/file.mp3, dirpath is /Input/Book.
        # If files are /Input/file.mp3, dirpath is /Input.
        
        # We should decide based on whether dirpath is the root input dir or a subdir.
        # Since we don't know the exact root input dir path here (it's passed as arg to Ingest, but maybe not here),
        # we can assume that if multiple files are grouped, the folder name is likely the book name.
        # If it's a single file, the filename is likely more descriptive if the folder is generic.
        
        path_name = os.path.basename(dirpath)
        if not path_name or path_name in ['.', 'root', 'input']: 
             path_name = os.path.basename(files[0])
             
        filename_result = self._extract_from_string(path_name)

        # 3. Merge (prefer tags for specific fields, fallback to filename)
        final_result = self._merge_results(tag_result, filename_result)
        
        return final_result

    def _is_audio(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return ext in ['.mp3', '.m4b', '.m4a', '.flac', '.opus', '.wma']

    def _extract_from_tags(self, filepath):
        result = IdentificationResult()
        result.source = "tags"
        try:
            audio = mutagen.File(filepath)
            if audio is None:
                return result
            
            # Helper to get first item or string
            def get_val(tags, keys):
                for k in keys:
                    if k in tags:
                        val = tags[k]
                        if isinstance(val, list):
                            return val[0]
                        return str(val)
                return None

            # MP3 (ID3)
            if isinstance(audio.tags, ID3):
                # ID3 keys
                result.title = get_val(audio.tags, ['TIT2', 'nam'])
                result.author = get_val(audio.tags, ['TPE1', 'ART']) # Artist
                result.album = get_val(audio.tags, ['TALB', 'alb'])
                result.year = get_val(audio.tags, ['TDRC', 'TYER', 'day'])
                result.narrator = get_val(audio.tags, ['TCOM']) # Composer is often used for Narrator
                
                # Custom tags for ASIN
                # ID3v2 TXXX frames
                for frame in audio.tags.getall('TXXX'):
                    if frame.desc.lower() == 'asin':
                        result.asin = frame.text[0]
            
            # MP4 (M4B/M4A)
            elif isinstance(audio, MP4):
                 # MP4 atoms
                tags = audio.tags
                if tags:
                    result.title = get_val(tags, ['©nam'])
                    result.author = get_val(tags, ['©ART', 'aART'])
                    result.album = get_val(tags, ['©alb'])
                    result.year = get_val(tags, ['©day'])
                    result.description = get_val(tags, ['desc'])
                    result.narrator = get_val(tags, ['©wrt']) # Composer
                    
                    # Custom atoms for ASIN?
                    # iTunes specific: ----:com.apple.iTunes:ASIN
                    # Mutagen stores freeform as '----:mean:name'
                    asin_key = '----:com.apple.iTunes:ASIN'
                    if asin_key in tags:
                         val = tags[asin_key]
                         if isinstance(val, list):
                            # It's bytes, decode
                            result.asin = val[0].decode('utf-8', errors='ignore')

            # Fallback to EasyID3/EasyMP4 if needed, but manual handling is often better for specific fields like ASIN.
            
            # Normalize
            if result.title: result.title = result.title.strip()
            if result.author: result.author = result.author.strip()

        except Exception as e:
            logger.warning(f"Error parsing tags for {filepath}: {e}")
            
        return result

    def _extract_from_string(self, text):
        result = IdentificationResult()
        result.source = "filename"
        
        # Remove extension
        text = os.path.splitext(text)[0]
        
        # Remove noise
        for pattern in self.noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        text = text.replace('_', ' ').strip()
        
        # Heuristic: "Author - Title" or "Title - Author"
        # If there is a " - " separator
        if ' - ' in text:
            parts = text.split(' - ')
            if len(parts) >= 2:
                # Assume Author - Title usually
                # But could be Series - Title
                # For now, simplistic assignment
                result.author = parts[0].strip()
                result.title = parts[1].strip()
        else:
            # Assume it's just the title
            result.title = text.strip()
            
        return result

    def _merge_results(self, tags, filename):
        # Prefer tags if available
        final = IdentificationResult()
        final.source = "merged"
        
        final.title = tags.title if tags.title else filename.title
        final.author = tags.author if tags.author else filename.author
        final.year = tags.year if tags.year else filename.year
        final.asin = tags.asin # Filename rarely has ASIN unless specifically named
        final.narrator = tags.narrator
        
        return final
