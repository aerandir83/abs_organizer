import os
import shutil
import logging
import zipfile
import tarfile
from src.config import config
import time

logger = logging.getLogger(__name__)

class FileGrouper:
    def __init__(self, callback, window=5):
        self.callback = callback
        self.window = window
        self.groups = {} # dirpath -> {'files': set(), 'last_update': time}

    def add_file(self, filepath):
        dirpath = os.path.dirname(filepath)
        # If the file is in the root INPUT_DIR, we might want to treat it specially,
        # but for now, grouping by directory is the safest bet.
        # If multiple files are in root, they will be grouped together.
        
        if dirpath not in self.groups:
            self.groups[dirpath] = {'files': set(), 'last_update': time.time()}
        
        self.groups[dirpath]['files'].add(filepath)
        self.groups[dirpath]['last_update'] = time.time()
        logger.info(f"Added {os.path.basename(filepath)} to group {dirpath}")

    def check_groups(self):
        current_time = time.time()
        to_emit = []
        
        for dirpath, data in list(self.groups.items()):
            if current_time - data['last_update'] >= self.window:
                to_emit.append(dirpath)
        
        for dirpath in to_emit:
            files = list(self.groups[dirpath]['files'])
            # Verify files still exist
            valid_files = [f for f in files if os.path.exists(f)]
            if valid_files:
                self.callback(dirpath, valid_files)
            del self.groups[dirpath]

    def get_stats(self):
        count = sum(len(data['files']) for data in self.groups.values())
        return {
            "grouping_files_count": count,
            "groups_count": len(self.groups)
        }

class IngestionManager:
    def __init__(self, processing_callback):
        self.processing_callback = processing_callback # Callback to Identification Engine
        self.grouper = FileGrouper(self.on_group_ready)

    def process_file(self, filepath):
        # 1. Archive Handling
        if self.is_archive(filepath):
            self.extract_archive(filepath)
            return

        # 2. Filtering
        if not self.is_valid_file(filepath):
            # logger.debug(f"Ignoring file: {filepath}")
            return

        # 3. Grouping
        self.grouper.add_file(filepath)

    def is_archive(self, filepath):
        return filepath.endswith('.zip') or filepath.endswith('.tar') or filepath.endswith('.tar.gz')

    def extract_archive(self, filepath):
        logger.info(f"Extracting archive: {filepath}")
        try:
            # Extract to a folder with the same name (minus extension)
            # Ensure we are extracting into a subdirectory to prevent dumping into root
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            parent_dir = os.path.dirname(filepath)
            dest_dir = os.path.join(parent_dir, base_name)
            
            if config.DRY_RUN:
                logger.info(f"[DRY RUN] Would create extraction directory: {dest_dir}")
                logger.info(f"[DRY RUN] Would extract archive {filepath} to {dest_dir}")
                logger.info(f"[DRY RUN] Would delete archive {filepath}")
                return

            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            
            if zipfile.is_zipfile(filepath):
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(dest_dir)
            elif tarfile.is_tarfile(filepath):
                with tarfile.open(filepath) as tar_ref:
                    tar_ref.extractall(dest_dir)
            
            # Recursive extraction handled by watchdog detecting new files
            
            # Delete archive after success
            os.remove(filepath)
            logger.info(f"Extracted and deleted archive: {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to extract {filepath}: {e}")

    def is_valid_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        return ext in config.ALLOWED_EXTENSIONS

    def on_group_ready(self, dirpath, files):
        logger.info(f"Group ready: {dirpath} with {len(files)} files")
        self.processing_callback(dirpath, files)
        
    def tick(self):
        self.grouper.check_groups()

    def get_stats(self):
        return self.grouper.get_stats()
