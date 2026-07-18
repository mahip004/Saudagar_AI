import os
import json
import logging
import re
from typing import Optional, List, Dict, Any
import httpx
from config import settings

logger = logging.getLogger("saudagar_ai.groq")

class GeminiService:
    def __init__(self):
        self.client_enabled = False
        self._initialize_client()

    def _initialize_client(self):
        api_key = settings.GROQ_API_KEY
        if api_key:
            self.client_enabled = True
            logger.info("Configured Groq inference client using model '%s'.", settings.GROQ_MODEL)
        else:
            logger.warning("Groq inference disabled (no GROQ_API_KEY).")

    def _generate(self, prompt: str, json_mode: bool = False) -> str:
        """Call Groq's OpenAI-compatible chat endpoint."""
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not content:
            raise ValueError("Groq returned an empty completion")
        return content.strip()
 
    _NEGATION_CUES = (
        r"nahi|nahin|nahi hai|khatam|out of stock|nahi milega|nahi hoga|kabhi nahi"
        r"|नहीं|नही|खत्म|मिलेगा नहीं|नहीं है|नहीं मिलेगा"
    )
    _FILLER_PATTERN = (
        r"\b(bhaiya|uncle|auntie|please|sir|madam|ok|okbhay|theek|milega|milegi|ek|de|do|pack|packet|kya|ki|ka|hai|hain|dena|dijiye)\b"
        r"|(?:भैया|क्या|है|हैं|दे|दो|एक|पैक|पैकेट|सर|मैडम|ठीक)"
    )

    def _contains_negation(self, text: str) -> bool:
        return bool(re.search(self._NEGATION_CUES, text, re.IGNORECASE))

    def _strip_fillers(self, text: str) -> str:
        cleaned = re.sub(self._FILLER_PATTERN, " ", text, flags=re.IGNORECASE).strip()
        return re.sub(r"\s+", " ", cleaned).strip(" ?।")

    def _fallback_stage1(self, transcript: str) -> Optional[Dict[str, Any]]:
        """Fallback stage 1 extraction when Gemini is unavailable or quota-limited."""
        if not transcript or not transcript.strip():
            return None

        transcript = transcript.strip()
        sentences = [s.strip() for s in re.split(r"[,?.!।]", transcript) if s.strip()]
        events = []
        transcript_has_negation = self._contains_negation(transcript)

        for sent in sentences:
            if self._contains_negation(sent) and len(sent) <= 12:
                continue

            cleaned = self._strip_fillers(sent)
            if not cleaned or len(cleaned) < 2:
                continue

            product_name = cleaned
            has_negation = self._contains_negation(sent)

            if has_negation:
                availability = "unavailable"
                evidence = sent
            elif transcript_has_negation and len(sentences) <= 2:
                availability = "unavailable"
                evidence = next((s for s in sentences if self._contains_negation(s)), transcript)
            else:
                availability = "available"
                evidence = sent

            events.append({
                "customer_requested": product_name,
                "availability": availability,
                "evidence": evidence,
                "resolved_from_pronoun": False,
                "confidence": 0.4,
            })

        if not events:
            return None

        return {"events": events}
 
    def analyze_conversation_stage1(self, transcript: str) -> Optional[Dict[str, Any]]:
        """Stage 1: Conversation Analyst"""
        prompt = f"""You are reading a shopkeeper-customer conversation at an Indian kirana store.
The transcript may be in Devanagari Hindi, Latin-script Hinglish, or English.

For every distinct product the CUSTOMER asked about:
1. Identify the product exactly as spoken (do not clean, translate, or normalize it).
2. Find the SHOPKEEPER's availability answer for that product — usually in the next 1-2 turns.
   If a later turn uses a pronoun ("wo", "vo bhi", "ye", "voh", "वो") referring back to an
   earlier product, resolve it to that product.
3. Classify availability as one of: "available", "unavailable", "unknown".
4. Quote the exact shopkeeper phrase you used to decide — this is "evidence". If no
   resolving turn exists, availability = "unknown" and evidence = "".
5. Give a confidence score from 0 to 1 for how sure you are of this mapping.

Availability rules (critical):
- Customer questions like "है क्या?", "hai kya?", "milega?", "milta hai?" are REQUESTS, not
  availability answers. Do NOT mark these as "available".
- Shopkeeper denials like "नहीं", "nahi", "nahin", "nahi hai", "khatam", "खत्म" mean
  "unavailable". Use the denial phrase as evidence.
- Shopkeeper confirmations like "haan", "hai", "है", "milega", "le lo" mean "available".
- In short Q&A exchanges, link the product question to the shopkeeper's next reply even
  if they are in separate sentences.

Examples:
Input: "भैया बाल्टी है क्या? नहीं।"
Output: {{"events": [{{"customer_requested": "बाल्टी", "availability": "unavailable", "evidence": "नहीं", "resolved_from_pronoun": false, "confidence": 0.95}}]}}

Input: "Bhaiya maggi hai? Haan hai."
Output: {{"events": [{{"customer_requested": "maggi", "availability": "available", "evidence": "Haan hai", "resolved_from_pronoun": false, "confidence": 0.95}}]}}

Other rules:
- Do not merge two different products into one event.
- Do not invent a product the customer never mentioned.
- Do not resolve a pronoun unless there is a real prior product mention to point to.
- If the turn is filler only (e.g. "haan", "de do", "please", "ek") with no product,
  do not emit an event for it.

Return ONLY valid JSON, no other text, in this exact schema:
{{"events": [{{"customer_requested": "string", "availability": "available"|"unavailable"|"unknown", "evidence": "string", "resolved_from_pronoun": true|false, "confidence": 0.0}}]}}

Transcript:
{transcript}"""
        if self.client_enabled:
            for attempt in range(2): # 1 bounded retry
                try:
                    data = json.loads(self._generate(prompt, json_mode=True))
                     
                    # Validate schema
                    if "events" not in data or not isinstance(data["events"], list):
                        raise ValueError("Missing 'events' array")
                         
                    for event in data["events"]:
                        keys = ["customer_requested", "availability", "evidence", "resolved_from_pronoun", "confidence"]
                        if not all(k in event for k in keys):
                            raise ValueError(f"Missing keys in event: {event}")
                        if event["availability"] not in ["available", "unavailable", "unknown"]:
                            raise ValueError(f"Invalid availability: {event['availability']}")
                        if not isinstance(event["confidence"], (int, float)) or not (0 <= event["confidence"] <= 1):
                            raise ValueError(f"Invalid confidence: {event['confidence']}")
                             
                    return data
                except Exception as e:
                    logger.warning(f"Stage 1 attempt {attempt+1} failed: {e}")
            logger.error("Stage 1 failed after retry.")
 
        # Do not replace model reasoning with keyword heuristics. A failed model call must
        # produce no event so incorrect stockout data never reaches demand analytics.
        logger.error("Gemini extraction unavailable; refusing heuristic extraction.")
        return None

    def verify_demand_event(self, transcript: str, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use an independent Gemini pass to verify a product-to-reply association."""
        prompt = f"""You are the verification gate for a kirana-store demand system.
Audit the proposed extraction against the transcript. Reason about speaker turns, reply
scope, and pronouns. Verify the exact association between the requested product and the
shopkeeper reply; do not use a fixed keyword list. A customer question is never evidence
that an item is available. Reject any unsupported or ambiguous association.

Transcript:
{transcript}

Proposed extraction:
{json.dumps(event, ensure_ascii=False)}

Return ONLY this JSON:
{{"verified": true|false, "customer_requested": "exact product phrase", "availability": "available"|"unavailable"|"unknown", "evidence": "exact transcript quote or empty", "confidence": 0.0}}

For available or unavailable, set verified=false below 0.82 confidence. For unknown, a
concrete product request with no decisive shopkeeper answer is valid: set verified=true and
use 0.65-0.80 confidence for the product extraction. customer_requested and non-empty evidence
must be verbatim substrings of the transcript."""
        if not self.client_enabled:
            return None
        try:
            result = json.loads(self._generate(prompt, json_mode=True))
            required = {"verified", "customer_requested", "availability", "evidence", "confidence"}
            if not required.issubset(result) or not isinstance(result["verified"], bool):
                raise ValueError("Invalid verification schema")
            if result["availability"] not in {"available", "unavailable", "unknown"}:
                raise ValueError("Invalid verified availability")
            if not isinstance(result["confidence"], (int, float)) or not 0 <= result["confidence"] <= 1:
                raise ValueError("Invalid verified confidence")
            return result
        except Exception as exc:
            logger.warning("Demand event verification failed: %s", exc)
            return None

    def clean_product_stage3(self, customer_requested: str) -> str:
        """Stage 3: Product Cleaner"""
        prompt = f"""Clean this retail product name extracted from a customer conversation.
The name may be in Devanagari Hindi, Hinglish, or English.

Rules:
- Remove duplicated words (e.g. "cream cream" -> "cream").
- Remove filler words and honorifics (e.g. "bhaiya", "भैया", "wala", "packet", "hai kya").
- Keep the core product noun (e.g. "बाल्टी" stays "बाल्टी", "maggi packet" -> "maggi").
- Do NOT invent, guess, or add a brand name that wasn't in the input.
- Do NOT translate the product name to a different language.
- Return ONLY the cleaned product name as a single line of plain text. No JSON,
  no explanation, no punctuation beyond what the product name itself needs.

Input: "{customer_requested}"
"""
        if self.client_enabled:
            for attempt in range(2):
                try:
                    return self._generate(prompt)
                except Exception as e:
                    logger.warning(f"Stage 3 attempt {attempt+1} failed: {e}")
            logger.error("Stage 3 failed after retry.")
        # Fallback to raw input if LLM fails
        return customer_requested

    def identify_product_name(self, product_phrase: str) -> str:
        """Identify the retail product from a customer phrase when catalog matching fails."""
        prompt = f"""A customer at an Indian kirana store asked for this product:
"{product_phrase}"

Identify the core retail product being requested.
- Keep Devanagari Hindi as-is if that is how it was spoken (e.g. "बाल्टी").
- For Hinglish, keep the common spoken form (e.g. "balti", "maggi").
- Do NOT add a brand unless the customer mentioned one.
- Do NOT explain or add punctuation.

Return ONLY the product name as plain text."""
        if self.client_enabled:
            try:
                identified = self._generate(prompt).strip('"').strip("'")
                if identified:
                    return identified
            except Exception as e:
                logger.error(f"Product identification failed: {e}")
        return product_phrase.strip()

    def canonical_match_stage6(self, cleaned_product: str, catalog: List[str]) -> str:
        """Stage 6: Canonical Matcher"""
        bullet_list = "\n".join(f"- {item}" for item in catalog)
        prompt = f"""A customer asked for a product in a retail shop. The exact phrase they used could
not be confidently matched to the shop's catalog automatically.

Extracted product phrase: "{cleaned_product}"

Existing catalog products for this shop:
{bullet_list}

Choose the ONE catalog product that the phrase most likely refers to. If none of
them are a reasonable match, return exactly: UNKNOWN

Return ONLY the exact catalog product name as written above, or UNKNOWN. No other text.
"""
        if self.client_enabled:
            try:
                return self._generate(prompt)
            except Exception as e:
                logger.error(f"Stage 6 failed: {e}")
        return "UNKNOWN"

    def generate_procurement_recommendations(self, demand_summary: Dict[str, Any], business_insights: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Takes demand statistics and external market insights, and generates intelligent procurement actions.
        """
        prompt = f"""
You are Saudagar AI's Procurement Agent, an expert inventory and purchasing advisor for small offline Indian retail (kirana) stores.
Based on the following aggregated customer demand (missing items) and business insights (weather, trends, festivals), generate procurement recommendations.

Demand Summary (Recent Store Requests & Stockouts):
{json.dumps(demand_summary, indent=2)}

Business Insights (External Factors):
{json.dumps(business_insights, indent=2)}

Generate recommendations to replenish out-of-stock items, capitalize on trending items, and stock up for upcoming festivals or weather changes.
Provide your response strictly as a JSON array of objects, where each object represents a recommendation with these keys:
- "product": string, the product name
- "action": string, the recommended action (e.g. "Increase inventory by 30%", "Order premium packs")
- "reason": string, explanation cross-referencing demand and insights (e.g., "Maggi is unavailable frequently and noodles are trending in current cold weather")
- "percentage_increase": integer, recommended stock increase percentage, or null
- "priority": string, either "HIGH", "MEDIUM", or "LOW"

Example Output:
[
  {{
    "product": "Cadbury Dairy Milk 100g",
    "action": "Increase stock by 50% and display gift packs near checkout",
    "reason": "High frequency of out-of-stock events coupled with Raksha Bandhan festival coming in 6 weeks.",
    "percentage_increase": 50,
    "priority": "HIGH"
  }}
]
"""
        if self.client_enabled:
            try:
                data = json.loads(self._generate(prompt, json_mode=True))
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "recommendations" in data:
                    return data["recommendations"]
                logger.info("Procurement Agent returned an unexpected JSON shape.")
            except Exception as e:
                logger.error(f"Gemini generate_procurement_recommendations failed, falling back: {e}")

        # Hardcoded realistic mockup response based on inputs
        recommendations = []
        unavailable_counts = demand_summary.get("unavailable_counts", {})
        
        # Build logical mock suggestions
        for prod, count in unavailable_counts.items():
            if count > 0:
                priority = "HIGH" if count >= 3 else "MEDIUM"
                pct = 30 + (count * 10)
                reason = f"This product went out-of-stock {count} times recently. "
                
                # Cross reference with business insights
                festivals = business_insights.get("festivals", [])
                if festivals:
                    fest_name = festivals[0].get("name", "")
                    reason += f"Prepare inventory ahead of {fest_name} to capture festival demand."
                    pct += 20
                else:
                    reason += "Replenish safety stock to meet steady consumer demand."

                recommendations.append({
                    "product": prod,
                    "action": f"Increase stock by {pct}%",
                    "reason": reason,
                    "percentage_increase": pct,
                    "priority": priority
                })
                
        # If no unavailable items, add some based on festival insights
        if not recommendations:
            festivals = business_insights.get("festivals", [])
            for fest in festivals:
                fest_name = fest.get("name", "")
                recommendations.append({
                    "product": "Cadbury Gift Packs",
                    "action": "Procure 40% more inventory of premium chocolate packs",
                    "reason": f"Upcoming festival {fest_name} drives high gifting confectionary sales.",
                    "percentage_increase": 40,
                    "priority": "HIGH"
                })
                recommendations.append({
                    "product": "Pooja Materials & Ghee",
                    "action": "Increase stock of cow ghee and incense sticks by 25%",
                    "reason": f"Anticipated rise in daily rituals and offerings during {fest_name}.",
                    "percentage_increase": 25,
                    "priority": "MEDIUM"
                })

        return recommendations

gemini_service = GeminiService()
