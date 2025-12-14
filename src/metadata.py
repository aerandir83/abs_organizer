import json
import os
import logging

logger = logging.getLogger(__name__)

class MetadataGenerator:
    def generate_json(self, metadata, output_dir):
        """
        Generates metadata.json in the output directory compliant with Audiobookshelf schema.
        """
        data = {
            "title": metadata.title,
            "authors": [metadata.author] if metadata.author else [],
            "narrators": [metadata.narrator] if metadata.narrator else [],
            "publishedYear": metadata.year,
            "description": getattr(metadata, 'description', ""),
            "isbn": metadata.isbn,
            "asin": metadata.asin,
            # "genres": metadata.genres, # Not yet implemented in IdentificationResult
            # "series": [] # TODO: Series parsing
        }
        
        # Filter None/Empty values
        data = {k: v for k, v in data.items() if v}
        
        filepath = os.path.join(output_dir, "metadata.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Generated metadata.json at {filepath}")
        except Exception as e:
            logger.error(f"Failed to write metadata.json: {e}")
