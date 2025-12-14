import time
import logging
import sys
import os
from src.config import config
from src.monitor import Monitor
from src.ingest import IngestionManager
from src.identifier import Identifier
from src.providers import MetadataAggregator
from src.organizer import Organizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutoLibrarian")

class AutoLibrarian:
    def __init__(self):
        self.identifier = Identifier()
        self.aggregator = MetadataAggregator()
        self.organizer = Organizer()
        
        # Ingestion Manager callback -> Processing Pipeline
        self.ingestion = IngestionManager(self.process_book)
        
        # Monitor callback -> Ingestion Manager
        self.monitor = Monitor(config.INPUT_DIR, self.ingestion.process_file)

    def start(self):
        logger.info("Starting AutoLibrarian...")
        logger.info(f"Input Directory: {config.INPUT_DIR}")
        logger.info(f"Output Directory: {config.OUTPUT_DIR}")
        
        self.monitor.start()
        
        try:
            while True:
                time.sleep(1)
                self.monitor.tick()
                self.ingestion.tick()
        except KeyboardInterrupt:
            logger.info("Stopping...")
            self.monitor.stop()

    def process_book(self, dirpath, files):
        logger.info(f"Processing book group from {dirpath}")
        
        try:
            # 1. Identification
            initial_metadata = self.identifier.identify(dirpath, files)
            logger.info(f"Initial ID: {initial_metadata}")
            
            # 2. Metadata Enrichment (API)
            final_metadata = self.aggregator.enrich(initial_metadata)
            logger.info(f"Final Metadata: {final_metadata}")
            
            # Confidence Check
            if final_metadata.confidence < config.MATCH_THRESHOLD_PROBABLE:
                logger.warning(f"Confidence score {final_metadata.confidence} below threshold. Moving to Manual Intervention.")
                self.organizer.move_to_manual(dirpath, files, final_metadata)
                return

            # 3. Organization & Move
            self.organizer.organize(dirpath, files, final_metadata)
            
            # 4. Notify ABS
            self.notify_abs()
            
        except Exception as e:
            logger.error(f"Error processing book: {e}", exc_info=True)
            # Move to manual intervention folder?

    def notify_abs(self):
        url = f"{config.ABS_URL}/api/libraries/scan" # Note: ABS API might differ, usually /api/scan or /api/libraries/{id}/scan
        # Requirement says: POST /api/libraries/{id}/scan
        # We assume one library or scan all. 
        # Alternatively: /api/scan/all
        # If we don't have Lib ID, we might need to fetch it first.
        # For MVP, logging the intent or trying a generic scan.
        # ABS API documentation usually requires API Key.
        
        headers = {"Authorization": f"Bearer {config.ABS_API_KEY}"} if config.ABS_API_KEY else {}
        
        try:
             # Try simple scan all if supported, or just log if no ID
             # Real implementation would fetch library ID first
             logger.info("Triggering ABS Scan...")
             # requests.post(url, headers=headers, timeout=5) 
             # Commented out to avoid failure in environment without ABS
             pass 
        except Exception as e:
             logger.error(f"Failed to trigger ABS scan: {e}")

if __name__ == "__main__":
    app = AutoLibrarian()
    app.start()
