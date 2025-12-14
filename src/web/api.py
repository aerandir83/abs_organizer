from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
from src.queue_manager import queue_manager
from src.providers import MetadataAggregator
from src.organizer import Organizer
from src.identifier import IdentificationResult

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("WebAPI")

# Models
class MetadataUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    series: Optional[str] = None
    year: Optional[str] = None
    isbn: Optional[str] = None
    asin: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    author: Optional[str] = None

# Services
aggregator = MetadataAggregator()
organizer = Organizer()

@app.get("/api/queue")
def get_queue():
    return queue_manager.get_items()

@app.get("/api/queue/{item_id}")
def get_item(item_id: str):
    item = queue_manager.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item.to_dict()

@app.post("/api/queue/{item_id}/search")
def search_metadata(item_id: str, query: SearchQuery):
    item = queue_manager.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Create a temporary identification result for searching
    temp_res = IdentificationResult()
    temp_res.title = query.query
    temp_res.author = query.author
    
    # We cheat a bit and use enrich logic or just access providers directly?
    # Aggregator.enrich expects an initial result and returns a best match.
    # But here we want a list of candidates.
    # MetadataAggregator helpers are private but providers are in self.providers
    
    results = []
    for provider in aggregator.providers:
        try:
            res = provider.search(query.query, query.author)
            # Convert to dict
            for r in res:
                results.append(r.__dict__)
        except Exception as e:
            logger.error(f"Provider error: {e}")
            
    return results

@app.post("/api/queue/{item_id}/update")
def update_metadata(item_id: str, updates: MetadataUpdate):
    item = queue_manager.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update the metadata object
    if not item.metadata:
        item.metadata = IdentificationResult()
        
    for k, v in updates.dict(exclude_unset=True).items():
        setattr(item.metadata, k, v)
        
    queue_manager.update_item(item_id) # Signal update if needed (lock is already handled if we just modify object reference, but update_item is safer if we replace)
    return item.to_dict()

@app.post("/api/queue/{item_id}/process")
def process_item(item_id: str, background_tasks: BackgroundTasks):
    item = queue_manager.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if not item.metadata:
         raise HTTPException(status_code=400, detail="No metadata for item")

    # Set status to processing
    item.status = "processing"
    
    background_tasks.add_task(run_organizer, item_id, item.dirpath, item.files, item.metadata)
    return {"status": "started"}

def run_organizer(item_id, dirpath, files, metadata):
    try:
        organizer.organize(dirpath, files, metadata)
        queue_manager.remove_item(item_id)
    except Exception as e:
        logger.error(f"Failed to organize {item_id}: {e}")
        queue_manager.update_item(item_id, status="error", error=str(e))

@app.delete("/api/queue/{item_id}")
def remove_item(item_id: str):
    queue_manager.remove_item(item_id)
    return {"status": "removed"}
