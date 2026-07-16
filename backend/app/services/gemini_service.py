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
            logger.warning(
                "\n"
                "==================================================\n"
                "MOCK GEMINI SERVICE ENABLED (NO API KEY)\n"
                "GEMINI_API_KEY was not found in environment or .env file.\n"
                "Gemini calls will return mock/heuristic responses.\n"
                "To use real Gemini LLM capabilities, please perform:\n"
                "========================\n"
                "MANUAL STEP REQUIRED\n"
                "========================\n"
                "1. Generate an API Key from Google AI Studio.\n"
                "2. Add 'GEMINI_API_KEY=<your_key>' in saudagar_ai/backend/.env\n"
                "3. Restart the FastAPI server.\n"
                "=================================================="
            )

    def extract_demand_from_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Extracts structured demand info from a transcript.
        Returns: {
            "product": str,
            "available": bool,
            "alternative": Optional[str],
            "purchase_completed": bool
        }
        """
        prompt = f"""
You are an AI that analyzes transcripts of conversations between CUSTOMERS and SHOPKEEPERS at Indian kirana (grocery) stores.
The transcript may contain dialogue from MULTIPLE speakers — typically a customer asking for a product and the shopkeeper responding.
Your job is to determine:
1. What product was the customer looking for?
2. Did the shopkeeper have it in stock? (available = true/false)
3. Was an alternative product offered by the shopkeeper?
4. Did the customer actually buy something? (purchase_completed = true/false)

IMPORTANT RULES:
- If the customer asks "X hai kya?" and the shopkeeper says "nahi" or "khatam" → available = false
- If the shopkeeper says "haan" or hands over the product → available = true
- If the shopkeeper suggests a different brand → that's the alternative
- If the customer pays or says "de do" / "pack karo" → purchase_completed = true
- The conversation might be in Hindi, Hinglish, Marathi, or English

Provide your response strictly as a JSON object with keys:
"product": (string, name of the product the customer asked for, e.g. "Maggi", "Dairy Milk", "Amul Butter")
"available": (boolean, was the product available at the shop?)
"alternative": (string or null, any alternative product suggested by the shopkeeper)
"purchase_completed": (boolean, did the customer end up buying something?)

Examples:

Transcript: "Bhaiya Maggi hai kya?"
Output: {{"product": "Maggi", "available": false, "alternative": null, "purchase_completed": false}}

Transcript: "Chocolate hai kya? Nahi bhai khatam ho gaya"
Output: {{"product": "Chocolate", "available": false, "alternative": null, "purchase_completed": false}}

Transcript: "Uncle Cadbury chocolate de do. Haan ye lijiye, 50 rupaye."
Output: {{"product": "Cadbury", "available": true, "alternative": null, "purchase_completed": true}}

Transcript: "Ata hai Aashirvaad? Nahi beta, Aashirvaad nahi hai. Fortune hai. Achha wahi de do."
Output: {{"product": "Aashirvaad Ata", "available": false, "alternative": "Fortune Ata", "purchase_completed": true}}

Transcript: "Bhaiya Surf Excel hai? Haan hai. Chhota wala de do. Ye lo."
Output: {{"product": "Surf Excel", "available": true, "alternative": null, "purchase_completed": true}}

Transcript: "Amul butter milega? Nahi butter khatam hai. Achha chodo phir."
Output: {{"product": "Amul Butter", "available": false, "alternative": null, "purchase_completed": false}}

Transcript: "Maggi do packet de do. Sorry bhai Maggi nahi hai, Yippee rakh lu? Haan chalo Yippee de do."
Output: {{"product": "Maggi", "available": false, "alternative": "Yippee", "purchase_completed": true}}

Transcript to analyze: "{transcript}"
"""
        if self.client_enabled:
            try:
                # Use Gemini 2.5 Flash (gemini-2.0-flash)
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                data = json.loads(response.text.strip())
                logger.info(f"Gemini raw response: {response.text}")
                return data
            except Exception as e:
                logger.error(f"Gemini API call failed, falling back to mock: {e}")
                
        # Mock / Heuristic logic fallback
        text = transcript.lower()
        product = "Unknown Product"
        available = False
        alternative = None
        purchase_completed = False

        # Simple heuristic parser
        if "maggi" in text or "maggie" in text:
            product = "Maggi"
        elif "butter" in text or "amul" in text:
            product = "Amul Butter"
        elif "colgate" in text:
            product = "Colgate toothpaste"
        elif "chocolate" in text or "cadbury" in text or "dairy milk" in text:
            product = "Dairy Milk"
        elif "surf excel" in text or "surf" in text:
            product = "Surf Excel"
        elif "lux" in text:
            product = "Lux Soap"
        else:
            # Extract whatever is after "hai" or "de do" or similar, or just use the first few words
            words = transcript.split()
            if len(words) > 0:
                product = words[-1].replace("?", "").replace(".", "")
                if len(words) > 1 and product in ["hai", "de", "do", "bhaiya", "uncle"]:
                    product = words[0]

        # Determine availability/purchase
        if "de do" in text or "le lo" in text or "pack kar" in text or "de" in text:
            available = True
            purchase_completed = True
        if "nahi hai" in text or "khatam" in text or "out of stock" in text:
            available = False
            purchase_completed = False
            if "yippee" in text or "fortune" in text or "alternativ" in text:
                alternative = "Yippee"
                available = False
                purchase_completed = True
                
        logger.info(f"Mock Gemini extracted: product='{product}', available={available}, alternative='{alternative}', purchase_completed={purchase_completed}")
        return {
            "product": product,
            "available": available,
            "alternative": alternative,
            "purchase_completed": purchase_completed
        }

    def resolve_unknown_product(self, raw_product_name: str, existing_canonical_names: List[str]) -> Optional[str]:
        """
        Uses Gemini to check if a raw product name is a semantic variant of existing canonical products.
        Returns the canonical name if yes, otherwise None.
        """
        if not existing_canonical_names:
            return None

        prompt = f"""
We have a list of canonical products in our system:
{json.dumps(existing_canonical_names)}

A customer asked for: "{raw_product_name}".
Is this name a clear spelling variation, translation, or variant of one of the canonical products in the list?
If yes, return the exact canonical product name from the list.
If it is a completely different product, return null.

Provide your response strictly as a JSON object with a single key:
"matched_canonical": (string or null)
"""
        if self.client_enabled:
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                data = json.loads(response.text.strip())
                return data.get("matched_canonical")
            except Exception as e:
                logger.error(f"Gemini resolve_unknown_product failed: {e}")

        # Basic fallback matching (simple lower case substring matching)
        for canon in existing_canonical_names:
            if raw_product_name.lower() in canon.lower() or canon.lower() in raw_product_name.lower():
                return canon
        return None

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
