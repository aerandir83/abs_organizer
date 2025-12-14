import time
import logging
import sys
import os
import threading
import uvicorn
from src.config import config
from src.monitor import Monitor
from src.ingest import IngestionManager
from src.identifier import Identifier
from src.providers import MetadataAggregator
from src.organizer import Organizer
from src.queue_manager import queue_manager

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

    def start_api(self):
        uvicorn.run("src.web.api:app", host="0.0.0.0", port=config.API_PORT, log_level="info", reload=False)

    def start(self):
        logger.info("Starting AutoLibrarian...")
        logger.info(f"Input Directory: {config.INPUT_DIR}")
        logger.info(f"Output Directory: {config.OUTPUT_DIR}")
        
        if config.WEB_UI_ENABLED:
            logger.info(f"Starting Web API on port {config.API_PORT}")
            api_thread = threading.Thread(target=self.start_api, daemon=True)
            api_thread.start()
        
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
            
            # Web UI Interception
            if config.WEB_UI_ENABLED:
                logger.info("Adding to processing queue for Web UI review")
                queue_manager.add_item(dirpath, files, final_metadata)
                return

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
        url = f"{config.ABS_URL}/api/libraries/scan" 
        headers = {"Authorization": f"Bearer {config.ABS_API_KEY}"} if config.ABS_API_KEY else {}
        
        try:
             # Try simple scan all if supported, or just log if no ID
             logger.info("Triggering ABS Scan...")
             pass 
        except Exception as e:
             logger.error(f"Failed to trigger ABS scan: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AutoLibrarian")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode without modifying files")
    args = parser.parse_args()

    if args.dry_run:
        config.DRY_RUN = True
        logger.info("Dry run mode enabled via CLI")

    app = AutoLibrarian()
    app.start()
