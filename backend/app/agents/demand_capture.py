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
        self.confidence_threshold = 0.80

    def run(self, shop_id: str, transcript: str) -> List[Dict[str, Any]]:
        logger.info(f"[DemandCapture] Starting 7-stage pipeline for shop='{shop_id}'")
        
        # STAGE 1: Conversation Analyst
        stage1_output = gemini_service.analyze_conversation_stage1(transcript)
        if not stage1_output or "events" not in stage1_output:
            logger.warning("[Stage 1] Failed to extract valid JSON. Aborting pipeline.")
            return []
            
        events = stage1_output["events"]
        
        # STAGE 2: Validator
        valid_events = self._validate_events(events)
        
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
                
            # STAGE 4: RapidFuzz Match
            # matching_service now needs to check per-shop aliases first, then catalog
            match_result = matching_service.match_product_stage4(cleaned_phrase, shop_id)
            score = match_result.get("score", 0.0)
            canonical = match_result.get("canonical_name")
            stage_resolved = match_result.get("stage_resolved", "rapidfuzz")
            
            # STAGE 5: Confidence Check
            if score >= self.confidence_threshold and canonical:
                logger.info(f"[Stage 5] Confident match >= {self.confidence_threshold}: {canonical}")
                # Complete event
            else:
                # STAGE 6: Canonical Matcher (LLM)
                logger.info(f"[Stage 6] Score < {self.confidence_threshold}. Escalating to Canonical Matcher.")
                catalog = matching_service.get_catalog_names()
                llm_canonical = gemini_service.canonical_match_stage6(cleaned_product=cleaned_phrase, catalog=catalog)
                
                if llm_canonical != "UNKNOWN" and llm_canonical in catalog:
                    canonical = llm_canonical
                    stage_resolved = "canonical_matcher"
                    logger.info(f"[Stage 6] Resolved to: {canonical}")
                else:
                    # STAGE 7: Ask Shopkeeper
                    logger.info("[Stage 7] UNKNOWN. Triggering shopkeeper WhatsApp escalation.")
                    canonical = None
                    stage_resolved = "shopkeeper"
                    
                    # Need to fetch top candidates for WhatsApp UI
                    candidates = matching_service.get_top_candidates(cleaned_phrase, limit=3)
                    firestore_service.flag_for_shopkeeper_whatsapp(shop_id, raw_phrase, candidates)
            
            # Save the final event to Firestore
            processed_event = self._save_event(
                shop_id=shop_id,
                raw_phrase=raw_phrase,
                canonical_product=canonical,
                availability=availability,
                evidence=evidence,
                stage_resolved=stage_resolved
            )
            processed_events.append(processed_event)
            
        return processed_events

    def _validate_events(self, events: List[Dict]) -> List[Dict]:
        """STAGE 2: Pure deterministic validation."""
        valid = []
        filler_blocklist = {"bhaiya ek", "ek", "haan", "de do", "please", "khatam", "theek hai"}
        negation_cues = {"nahi", "khatam", "out of stock", "nahi hai", "nahin", "nahi milega"}
        
        for event in events:
            raw = event.get("customer_requested", "").strip()
            avail = event.get("availability", "unknown")
            evidence = event.get("evidence", "").lower()
            pronoun = event.get("resolved_from_pronoun", False)
            
            # Rule 1: customer_requested is empty or filler-only
            if not raw or raw.lower() in filler_blocklist:
                logger.info(f"[Stage 2] Rejecting event: empty or filler word '{raw}'")
                continue
                
            # Rule 2: unavailable but evidence has no negation cue
            if avail == "unavailable":
                if not any(cue in evidence for cue in negation_cues):
                    logger.info(f"[Stage 2] Downgrading availability for '{raw}' because evidence lacks negation.")
                    avail = "unknown"
                    event["availability"] = "unknown"
                    
            # Rule 3: resolved_from_pronoun but no earlier event (simplistic check: must not be first event)
            if pronoun and not valid:
                logger.info(f"[Stage 2] Rejecting hallucinated pronoun resolution for '{raw}'.")
                continue
                
            valid.append(event)
        return valid

    def _validate_cleaner_output(self, raw: str, cleaned: str) -> bool:
        """STAGE 3 POST-CHECK: Token subset check."""
        raw_tokens = set(raw.lower().split())
        cleaned_tokens = set(cleaned.lower().split())
        return cleaned_tokens.issubset(raw_tokens)

    def _save_event(self, shop_id: str, raw_phrase: str, canonical_product: Optional[str], 
                    availability: str, evidence: str, stage_resolved: str) -> Dict[str, Any]:
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
