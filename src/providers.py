import requests
import logging
from src.identifier import IdentificationResult
from src.config import config
from thefuzz import fuzz

logger = logging.getLogger(__name__)

class MetadataProvider:
    def search(self, query, author=None):
        raise NotImplementedError

class OpenLibraryProvider(MetadataProvider):
    def search(self, query, author=None):
        logger.info(f"Searching OpenLibrary for: {query}, author: {author}")
        base_url = "https://openlibrary.org/search.json"
        params = {'q': query}
        if author:
            params['author'] = author
            
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if 'docs' in data:
                for doc in data['docs'][:5]: # Limit to top 5
                    results.append(self._parse_doc(doc))
            return results
        except Exception as e:
            logger.error(f"OpenLibrary search failed: {e}")
            return []

    def _parse_doc(self, doc):
        res = IdentificationResult()
        res.source = "openlibrary"
        res.title = doc.get('title')
        res.author = doc.get('author_name', [None])[0]
        res.year = str(doc.get('first_publish_year', ''))
        res.isbn = doc.get('isbn', [None])[0]
        # OpenLibrary ID as identifier
        res.openlibrary_id = doc.get('key')
        
        if 'id_amazon' in doc:
             res.asin = doc['id_amazon'][0]
             
        return res

class GoogleBooksProvider(MetadataProvider):
    def search(self, query, author=None):
        logger.info(f"Searching Google Books for: {query}, author: {author}")
        base_url = "https://www.googleapis.com/books/v1/volumes"
        q = query
        if author:
            q += f"+inauthor:{author}"
            
        params = {'q': q, 'maxResults': 5}
        # if config.GOOGLE_BOOKS_API_KEY:
        #    params['key'] = config.GOOGLE_BOOKS_API_KEY
            
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if 'items' in data:
                for item in data['items']:
                    results.append(self._parse_volume(item))
            return results
        except Exception as e:
            logger.error(f"Google Books search failed: {e}")
            return []

    def _parse_volume(self, item):
        res = IdentificationResult()
        res.source = "googlebooks"
        info = item.get('volumeInfo', {})
        res.title = info.get('title')
        res.author = info.get('authors', [None])[0]
        res.year = info.get('publishedDate', '')[:4]
        res.description = info.get('description')
        res.publisher = info.get('publisher')
        
        # Identifiers
        identifiers = info.get('industryIdentifiers', [])
        for ident in identifiers:
            if ident['type'] == 'ISBN_13':
                res.isbn = ident['identifier']
            elif ident['type'] == 'ISBN_10' and not res.isbn:
                res.isbn = ident['identifier']
                
        # Image links
        if 'imageLinks' in info:
            res.cover_url = info['imageLinks'].get('extraLarge') or \
                            info['imageLinks'].get('large') or \
                            info['imageLinks'].get('medium') or \
                            info['imageLinks'].get('thumbnail')
                            
        return res

class AudibleProvider(MetadataProvider):
    def search(self, query, author=None):
        logger.info(f"Searching Audible for: {query}, author: {author}")
        base_url = "https://api.audible.com/1.0/catalog/products"
        
        q = query
        if author:
            q += f" {author}"
            
        params = {
            "title": q,
            "num_results": 5,
            "products_sort_by": "Relevance",
            "response_groups": "media,product_attrs,product_desc,product_extended_attrs,series,contributors"
        }
            
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            if 'products' in data:
                for item in data['products']:
                    results.append(self._parse_product(item))
            return results
        except Exception as e:
            logger.error(f"Audible search failed: {e}")
            return []

    def _parse_product(self, item):
        res = IdentificationResult()
        res.source = "audible"
        res.title = item.get('title')
        res.asin = item.get('asin')
        
        # Authors
        authors = item.get('authors', [])
        if authors:
            res.author = authors[0].get('name')
            
        # Narrators
        narrators = item.get('narrators', [])
        if narrators:
            res.narrator = narrators[0].get('name')
            
        # Year
        date_str = item.get('issue_date') or item.get('release_date')
        if date_str:
            res.year = date_str[:4]
            
        # Description
        res.description = item.get('publisher_summary')
        
        # Cover
        if 'product_images' in item:
            try:
                images = item['product_images']
                if images:
                    # Filter for numeric keys only to avoid errors
                    numeric_keys = [k for k in images.keys() if k.isdigit()]
                    if numeric_keys:
                        max_key = max(numeric_keys, key=int)
                        res.cover_url = images[max_key]
                    else:
                        # Fallback to any value
                        res.cover_url = list(images.values())[0]
            except Exception as e:
                logger.debug(f"Error parsing audible images: {e}")
                pass
                
        res.publisher = item.get('publisher_name')
        
        return res

class MetadataAggregator:
    def __init__(self):
        self.providers = []
        if 'openlibrary' in config.METADATA_PROVIDERS:
            self.providers.append(OpenLibraryProvider())
        if 'googlebooks' in config.METADATA_PROVIDERS:
            self.providers.append(GoogleBooksProvider())
        if 'audible' in config.METADATA_PROVIDERS:
            self.providers.append(AudibleProvider())
            
    def enrich(self, initial_result):
        # Use initial result (from filename/tags) to query providers
        query = initial_result.title
        author = initial_result.author
        
        if not query:
            logger.warning("No title to search for")
            return initial_result
            
        best_match = initial_result
        highest_score = 0
        
        for provider in self.providers:
            results = provider.search(query, author)
            
            for res in results:
                # Calculate match score
                score = self._calculate_score(initial_result, res)
                res.confidence = score
                
                if score > highest_score:
                    highest_score = score
                    best_match = self._merge(best_match, res)
        
        return best_match

    def _calculate_score(self, target, candidate):
        # Fuzzy match title and author
        title_score = fuzz.ratio(target.title.lower(), candidate.title.lower())
        author_score = 0
        if target.author and candidate.author:
            author_score = fuzz.ratio(target.author.lower(), candidate.author.lower())
            return (title_score + author_score) / 2
        return title_score

    def _merge(self, base, new):
        # Merge logic: Prefer new (provider data) for metadata fields if high confidence
        # But keep base info if new is missing it
        
        # If new result has description, cover, etc., take it.
        if hasattr(new, 'description') and new.description:
            base.description = new.description
        if hasattr(new, 'year') and new.year:
            base.year = new.year
        if hasattr(new, 'isbn') and new.isbn:
            base.isbn = new.isbn
        if hasattr(new, 'asin') and new.asin:
            base.asin = new.asin
        if hasattr(new, 'cover_url') and new.cover_url: # dynamic attribute
            base.cover_url = new.cover_url
        if hasattr(new, 'narrator') and new.narrator:
            base.narrator = new.narrator
            
        # Update title/author to official ones from API if score is high enough?
        # Maybe safer to keep what we found unless it was really bad.
        # But API usually has better formatting (capitalization etc).
        if new.confidence > 90:
            base.title = new.title
            base.author = new.author
            
        return base
