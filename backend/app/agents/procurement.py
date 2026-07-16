import logging
from datetime import datetime
from app.services.firestore_service import firestore_service
from app.services.gemini_service import gemini_service

logger = logging.getLogger("saudagar_ai.agent.procurement")

class ProcurementAgent:
    def generate_recommendations(self, shop_id: str):
        """
        Gathers demand summary and business insights,
        uses Gemini to generate procurement recommendations,
        and saves them back to Firestore.
        """
        logger.info(f"Triggered Procurement Agent for shop '{shop_id}'")
        
        # 1. Read demand summary
        demand_summary = firestore_service.get_demand_summary(shop_id)
        if not demand_summary:
            logger.warning(f"No demand summary found for shop '{shop_id}'. Cannot generate recommendations.")
            return

        # 2. Read business insights
        business_insights = firestore_service.get_business_insights()
        
        # 3. Call Gemini service to perform cross-reference and generate recommendations
        recommendations = gemini_service.generate_procurement_recommendations(
            demand_summary, 
            business_insights
        )
        
        # 4. Save recommendations to Firestore
        recommendations_data = {
            "shop_id": shop_id,
            "updated_at": datetime.utcnow().isoformat(),
            "recommendations": recommendations
        }
        
        firestore_service.update_recommendations(shop_id, recommendations_data)
        logger.info(f"Procurement recommendations updated in Firestore for shop '{shop_id}'")

procurement_agent = ProcurementAgent()
