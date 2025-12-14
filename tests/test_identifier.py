import pytest
from src.identifier import Identifier, IdentificationResult

class TestIdentifier:
    def test_filename_parsing(self):
        identifier = Identifier()
        
        # Test case 1: Author - Title
        res = identifier._extract_from_string("Andy Weir - The Martian.mp3")
        assert res.author == "Andy Weir"
        assert res.title == "The Martian"
        
        # Test case 2: Title only
        res = identifier._extract_from_string("The Martian.mp3")
        assert res.title == "The Martian"
        
        # Test case 3: Noise removal
        res = identifier._extract_from_string("Andy Weir - The Martian [Unabridged] [MP3].mp3")
        assert res.author == "Andy Weir"
        assert res.title.strip() == "The Martian"
        
    def test_merge(self):
        identifier = Identifier()
        tags = IdentificationResult()
        tags.title = "Tag Title"
        
        filename = IdentificationResult()
        filename.title = "Filename Title"
        filename.author = "Filename Author"
        
        merged = identifier._merge_results(tags, filename)
        assert merged.title == "Tag Title"
        assert merged.author == "Filename Author"
