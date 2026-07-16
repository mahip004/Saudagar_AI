import logging
from typing import Optional, Tuple
from rapidfuzz import process, fuzz
from app.services.firestore_service import firestore_service

logger = logging.getLogger("saudagar_ai.matching")

class MatchingService:
    def __init__(self, threshold: float = 80.0):
        self.threshold = threshold

    def find_canonical_match(self, raw_product_name: str) -> Optional[str]:
        """
        Uses RapidFuzz to find the canonical product name matching the raw product name.
        Looks up both canonical names and aliases.
        """
        if not raw_product_name:
            return None
            
        products = firestore_service.get_products()
        if not products:
            logger.warning("No products found in Firestore to perform matching.")
            return None

        # Build list of candidates. Each candidate is a tuple (candidate_string, canonical_name)
        candidates = []
        for p in products:
            canonical = p.get("canonical_name")
            if canonical:
                candidates.append((canonical.lower(), canonical))
            for alias in p.get("aliases", []):
                candidates.append((alias.lower(), canonical))

        if not candidates:
            return None

        # Search for the best match using the raw name
        search_query = raw_product_name.lower()
        candidate_strings = [c[0] for c in candidates]
        
        # extractOne returns (match_string, score, index) or None
        best_match = process.extractOne(
            search_query, 
            candidate_strings, 
            scorer=fuzz.WRatio
        )
        
        if best_match:
            match_string, score, idx = best_match
            matched_canonical = candidates[idx][1]
            logger.info(f"Fuzzy match result for '{raw_product_name}': best alias/canonical is '{match_string}' matching canonical '{matched_canonical}' with score {score:.2f}")
            if score >= self.threshold:
                return matched_canonical
                
        logger.info(f"No high confidence fuzzy match for '{raw_product_name}' (threshold: {self.threshold})")
        return None

matching_service = MatchingService()
