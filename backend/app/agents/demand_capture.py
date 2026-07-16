import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.models import DemandEventModel
from app.services.firestore_service import firestore_service
from app.services.gemini_service import gemini_service
from app.services.matching_service import matching_service

logger = logging.getLogger("saudagar_ai.agent.demand_capture")

class DemandCaptureAgent:
    def capture_demand_event(self, shop_id: str, transcript: str) -> Dict[str, Any]:
        """
        Orchestrates demand capture:
        1. Extract structured data using Gemini
        2. Perform product alias/canonical matching (RapidFuzz -> Gemini -> Unknown)
        3. Save to Firestore
        """
        logger.info(f"Received capture demand request for shop '{shop_id}'. Transcript: '{transcript}'")
        
        # 1. Extract from transcript
        extracted = gemini_service.extract_demand_from_transcript(transcript)
        raw_product = extracted.get("product", "Unknown")
        available = extracted.get("available", False)
        alternative = extracted.get("alternative")
        purchase_completed = extracted.get("purchase_completed", False)
        
        # 2. Normalize and map product name
        canonical_product = matching_service.find_canonical_match(raw_product)
        
        if not canonical_product:
            # If RapidFuzz doesn't find it, query Gemini to compare with existing canonical items
            logger.info(f"RapidFuzz could not resolve '{raw_product}'. Consulting Gemini...")
            products = firestore_service.get_products()
            canonical_names = [p.get("canonical_name") for p in products if p.get("canonical_name")]
            
            resolved = gemini_service.resolve_unknown_product(raw_product, canonical_names)
            if resolved:
                logger.info(f"Gemini successfully resolved '{raw_product}' to canonical '{resolved}'")
                canonical_product = resolved
            else:
                logger.info(f"Gemini could not resolve '{raw_product}'. Storing as Unknown Product.")
                canonical_product = f"Unknown Product ({raw_product})"
                
        # 3. Create document data
        event = DemandEventModel(
            shop_id=shop_id,
            product=raw_product,
            canonical_product=canonical_product,
            available=available,
            alternative=alternative,
            purchase_completed=purchase_completed,
            timestamp=datetime.utcnow()
        )
        
        event_dict = event.model_dump()
        # Convert datetime to ISO string for Firestore serialization
        event_dict["timestamp"] = event_dict["timestamp"].isoformat()
        
        # Save to Firestore
        event_id = firestore_service.add_demand_event(event_dict)
        logger.info(f"Saved demand event with ID {event_id} for product '{canonical_product}'")
        
        event_dict["event_id"] = event_id
        return event_dict

demand_capture_agent = DemandCaptureAgent()
