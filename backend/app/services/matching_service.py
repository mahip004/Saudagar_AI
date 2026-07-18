import logging
import threading
from typing import Optional, List, Tuple, Dict, Any
from rapidfuzz import process, fuzz
from app.services.firestore_service import firestore_service

logger = logging.getLogger("saudagar_ai.matching")

class MatchingService:
    def __init__(self):
        self._canonical_catalog: List[str] = []
        self._alias_map: Dict[str, str] = {}  # Maps alias to canonical_name
        self._lock = threading.Lock()
        self._initialized = False

    def refresh_cache(self) -> None:
        """ Fetches the master list of canonical product names and aliases from Firestore. """
        try:
            logger.info("Refreshing product catalog from Firestore...")
            products = firestore_service.get_products()
            new_catalog = []
            new_alias_map = {}
            
            for p in products:
                canonical = p.get("canonical_name")
                if canonical:
                    new_catalog.append(canonical)
                    # Also add canonical name as an alias to itself
                    new_alias_map[canonical.lower()] = canonical
                    # Map all aliases to the canonical name
                    for alias in p.get("aliases", []):
                        new_alias_map[alias.lower()] = canonical
            
            with self._lock:
                self._canonical_catalog = new_catalog
                self._alias_map = new_alias_map
                self._initialized = True
            
            logger.info(f"Catalog refreshed. Loaded {len(new_catalog)} canonical products and {len(new_alias_map)} aliases.")
        except Exception as e:
            logger.error(f"Failed to refresh catalog: {e}", exc_info=True)

    def get_catalog_names(self) -> List[str]:
        if not self._initialized:
            self.refresh_cache()
        with self._lock:
            return list(self._canonical_catalog)

    def get_top_candidates(self, phrase: str, limit: int = 3) -> List[str]:
        catalog = self.get_catalog_names()
        if not catalog:
            return []
        results = process.extract(phrase.lower(), catalog, scorer=fuzz.WRatio, limit=limit)
        return [r[0] for r in results]

    def match_product_stage4(self, cleaned_phrase: str, shop_id: str) -> Dict[str, Any]:
        """
        STAGE 4: RapidFuzz Match + Alias Check.
        First checks shop-specific aliases. Then searches both canonical names and product aliases.
        Returns: {"score": float (0-1), "canonical_name": str, "stage_resolved": str}
        """
        if not cleaned_phrase:
            return {"score": 0.0, "canonical_name": None, "stage_resolved": "rapidfuzz"}

        search_query = cleaned_phrase.lower().strip()
        
        # 1. Exact lookup in shop-specific aliases
        shop_aliases = firestore_service.get_shop_aliases(shop_id)
        if search_query in shop_aliases:
            canonical = shop_aliases[search_query]
            logger.info(f"[Stage 4] Shop alias exact match: '{search_query}' -> '{canonical}'")
            return {
                "score": 1.0,
                "canonical_name": canonical,
                "stage_resolved": "alias_table"
            }

        # 2. RapidFuzz against both canonical names and aliases
        if not self._initialized:
            self.refresh_cache()
        
        with self._lock:
            # Build a list of all searchable strings (canonical names + aliases)
            all_searchable = list(self._canonical_catalog) + list(self._alias_map.keys())
        
        if not all_searchable:
            return {"score": 0.0, "canonical_name": None, "stage_resolved": "rapidfuzz"}

        best_match = process.extractOne(search_query, all_searchable, scorer=fuzz.WRatio)
        if best_match:
            matched_string, raw_score, idx = best_match
            normalized_score = raw_score / 100.0  # Normalize to 0-1
            
            # Resolve matched_string to canonical name
            with self._lock:
                canonical_name = self._alias_map.get(matched_string.lower(), matched_string)
            
            logger.info(f"[Stage 4] RapidFuzz best match for '{cleaned_phrase}': '{matched_string}' (canonical: '{canonical_name}') with score {normalized_score:.2f}")
            return {
                "score": normalized_score,
                "canonical_name": canonical_name,
                "stage_resolved": "rapidfuzz"
            }

        return {"score": 0.0, "canonical_name": None, "stage_resolved": "rapidfuzz"}

    # Legacy method for backwards compatibility
    def find_canonical_match(self, raw_product_name: str) -> Optional[str]:
        res = self.match_product_stage4(raw_product_name, "default_shop")
        if res.get("score", 0) >= 0.8:
            return res.get("canonical_name")
        return None

matching_service = MatchingService()
