import os
import json
import logging
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from config import settings

logger = logging.getLogger("saudagar_ai.gemini")

class GeminiService:
    def __init__(self):
        self.client_enabled = False
        self._initialize_client()

    def _initialize_client(self):
        api_key = settings.GEMINI_API_KEY
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.client_enabled = True
                logger.info("Successfully configured Google Generative AI (Gemini) API client.")
            except Exception as e:
                logger.error(f"Error configuring Gemini client: {e}")
        else:
            logger.warning("MOCK GEMINI SERVICE ENABLED (NO API KEY)")

    def analyze_conversation_stage1(self, transcript: str) -> Optional[Dict[str, Any]]:
        """Stage 1: Conversation Analyst"""
        prompt = f"""You are reading a shopkeeper-customer conversation (Hindi/English/Hinglish,
transliterated to Latin script).

For every distinct product the CUSTOMER asked about:
1. Identify the product exactly as spoken (do not clean, translate, or normalize it).
2. Find the availability signal for that product - usually in the shopkeeper's next
   1-2 turns. If a later turn uses a pronoun ("wo", "vo bhi", "ye", "voh") that refers
   back to an earlier product, resolve it to that product.
3. Classify availability as one of: "available", "unavailable", "unknown".
4. Quote the exact shopkeeper phrase you used to decide - this is "evidence". If no
   resolving turn exists, availability = "unknown" and evidence = "".
5. Give a confidence score from 0 to 1 for how sure you are of this mapping.

Rules:
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
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                    data = json.loads(response.text.strip())
                    
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
        return None

    def clean_product_stage3(self, customer_requested: str) -> str:
        """Stage 3: Product Cleaner"""
        prompt = f"""Clean this retail product name extracted from a customer conversation.

Rules:
- Remove duplicated words (e.g. "cream cream" -> "cream").
- Remove filler words and honorifics (e.g. "bhaiya", "wala", "packet").
- Do NOT invent, guess, or add a brand name that wasn't in the input.
- Do NOT translate the product name.
- Return ONLY the cleaned product name as a single line of plain text. No JSON,
  no explanation, no punctuation beyond what the product name itself needs.

Input: "{customer_requested}"
"""
        if self.client_enabled:
            for attempt in range(2):
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content(prompt)
                    return response.text.strip()
                except Exception as e:
                    logger.warning(f"Stage 3 attempt {attempt+1} failed: {e}")
            logger.error("Stage 3 failed after retry.")
        # Fallback to raw input if LLM fails
        return customer_requested

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
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(prompt)
                return response.text.strip()
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
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                data = json.loads(response.text.strip())
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "recommendations" in data:
                    return data["recommendations"]
                logger.info(f"Procurement Agent response: {response.text}")
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
