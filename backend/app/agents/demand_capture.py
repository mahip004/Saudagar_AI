import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models import DemandEventModel
from app.services.firestore_service import firestore_service
from app.services.gemini_service import gemini_service
from app.services.matching_service import matching_service

logger = logging.getLogger("saudagar_ai.agent.demand_capture")

class DemandCapturePipeline:
    def __init__(self):
        self.verification_threshold = 0.82

    def run(self, shop_id: str, transcript: str) -> List[Dict[str, Any]]:
        logger.info(f"[DemandCapture] Starting 7-stage pipeline for shop='{shop_id}'")
        
        # STAGE 1: Conversation Analyst
        stage1_output = gemini_service.analyze_conversation_stage1(transcript)
        if not stage1_output or "events" not in stage1_output:
            logger.warning("[Stage 1] Failed to extract valid JSON. Aborting pipeline.")
            return []
            
        events = stage1_output["events"]
        
        # STAGE 2: independent Gemini verification plus structural grounding checks.
        valid_events = self._verify_events(events, transcript)
        
        processed_events = []
        
        for event in valid_events:
            raw_phrase = event["customer_requested"]
            availability = event["availability"]
            evidence = event["evidence"]
            
            # STAGE 3: Product Cleaner
            cleaned_phrase = gemini_service.clean_product_stage3(raw_phrase)
            if not self._validate_cleaner_output(raw_phrase, cleaned_phrase):
                logger.warning(f"[Stage 3] Post-check failed for '{cleaned_phrase}'. Falling back to raw phrase.")
                cleaned_phrase = raw_phrase
                
            # STAGE 4: Gemini maps the extracted product to the live catalog; no static word map.
            catalog = matching_service.get_catalog_names()
            llm_canonical = gemini_service.canonical_match_stage6(cleaned_product=cleaned_phrase, catalog=catalog)
            if llm_canonical != "UNKNOWN" and llm_canonical in catalog:
                canonical, stage_resolved = llm_canonical, "gemini_catalog_match"
            else:
                canonical, stage_resolved = gemini_service.identify_product_name(cleaned_phrase), "gemini_identified"
            
            # Save the final event to Firestore
            processed_event = self._save_event(
                shop_id=shop_id,
                raw_phrase=raw_phrase,
                canonical_product=canonical,
                availability=availability,
                evidence=evidence,
                stage_resolved=stage_resolved,
                confidence=event["confidence"]
            )
            processed_events.append(processed_event)
            
        return processed_events

    def _verify_events(self, events: List[Dict], transcript: str) -> List[Dict]:
        """Reject events unless Gemini independently verifies their transcript grounding."""
        valid = []
        for event in events:
            verified = gemini_service.verify_demand_event(transcript, event)
            # A concrete customer request with no shopkeeper answer is still valuable demand.
            # It has no product-to-answer mapping to verify, so use a lower extraction threshold.
            threshold = 0.65 if verified and verified.get("availability") == "unknown" else self.verification_threshold
            if not verified or not verified["verified"] or verified["confidence"] < threshold:
                logger.info("[Stage 2] Gemini rejected or was unsure of proposed event: %s", event)
                continue
            product = verified["customer_requested"].strip()
            evidence = verified["evidence"].strip()
            if not product or product.casefold() not in transcript.casefold():
                logger.info("[Stage 2] Rejected ungrounded product: %s", product)
                continue
            if evidence and evidence.casefold() not in transcript.casefold():
                logger.info("[Stage 2] Rejected ungrounded evidence: %s", evidence)
                continue
            valid.append({**event, **verified})
        return valid

    def _validate_cleaner_output(self, raw: str, cleaned: str) -> bool:
        """STAGE 3 POST-CHECK: Token subset check (supports Devanagari)."""
        if not cleaned or not cleaned.strip():
            return False
        raw_tokens = set(raw.lower().split())
        cleaned_tokens = set(cleaned.lower().split())
        if cleaned_tokens.issubset(raw_tokens):
            return True
        # Allow cleaned phrase if it is a contiguous substring of the raw phrase
        return cleaned.lower().strip() in raw.lower()

    def _save_event(self, shop_id: str, raw_phrase: str, canonical_product: Optional[str], 
                    availability: str, evidence: str, stage_resolved: str, confidence: float) -> Dict[str, Any]:
        """Saves the demand event to Firestore with stage_resolved metric."""
        avail_bool = (availability == "available")
        event = DemandEventModel(
            shop_id=shop_id,
            product=raw_phrase,
            canonical_product=canonical_product or "Unknown",
            available=avail_bool,
            alternative=None,
            purchase_completed=avail_bool,
            timestamp=datetime.utcnow()
        )
        event_dict = event.model_dump()
        event_dict["timestamp"] = event_dict["timestamp"].isoformat()
        event_dict["evidence"] = evidence
        event_dict["confidence"] = confidence
        event_dict["availability"] = availability
        event_dict["stage_resolved"] = stage_resolved
        
        event_id = firestore_service.add_demand_event(event_dict)
        logger.info(f"[Pipeline] 💾 Saved event id={event_id} | canonical='{canonical_product}' | stage='{stage_resolved}'")
        
        event_dict["event_id"] = event_id
        return event_dict
        
    def capture_demand_event(self, shop_id: str, transcript: str) -> Dict[str, Any]:
        # Backwards compatibility stub for old API
        events = self.run(shop_id, transcript)
        return events[0] if events else {}

demand_capture_agent = DemandCapturePipeline()
