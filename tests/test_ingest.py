import os
import shutil
import pytest
import time
from src.ingest import IngestionManager, FileGrouper
from src.config import config

class TestIngestion:
    @pytest.fixture
    def setup_dirs(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        config.ALLOWED_EXTENSIONS = {'.mp3', '.txt'} # Add txt for easier testing
        return input_dir

    def test_grouping(self, setup_dirs):
        input_dir = setup_dirs
        
        received_groups = []
        def callback(dirpath, files):
            received_groups.append((dirpath, files))
            
        grouper = FileGrouper(callback, window=1)
        
        # Simulate files adding
        f1 = input_dir / "book1" / "ch1.mp3"
        f1.parent.mkdir()
        f1.touch()
        
        grouper.add_file(str(f1))
        
        # Check immediately - should be nothing
        grouper.check_groups()
        assert len(received_groups) == 0
        
        # Wait
        time.sleep(1.1)
        grouper.check_groups()
        
        assert len(received_groups) == 1
        assert received_groups[0][0] == str(f1.parent)
        # FileGrouper converts set to list in check_groups
        assert set(received_groups[0][1]) == {str(f1)}

    def test_archive_extraction(self, setup_dirs):
        # This requires creating a zip file
        import zipfile
        input_dir = setup_dirs
        zip_path = input_dir / "test.zip"
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr('book.mp3', 'audio content')
            
        processed_files = []
        # Mock IngestionManager's callback? No, we test extract_archive directly
        manager = IngestionManager(lambda d, f: None)
        
        assert os.path.exists(zip_path)
        manager.extract_archive(str(zip_path))
        
        assert not os.path.exists(zip_path) # Should be deleted
        extracted_file = input_dir / "test" / "book.mp3"
        assert extracted_file.exists()
