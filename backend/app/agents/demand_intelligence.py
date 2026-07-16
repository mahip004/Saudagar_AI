import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from app.services.firestore_service import firestore_service
from app.agents.procurement import procurement_agent

logger = logging.getLogger("saudagar_ai.agent.demand_intelligence")

class DemandIntelligenceAgent:
    def process_demand_metrics(self, shop_id: str):
        """
        Triggered when a new demand event is created.
        Gathers recent demand events for the shop, aggregates metrics using Pandas,
        updates the demand_summary in Firestore, and triggers the Procurement Agent.
        """
        logger.info(f"Triggered Demand Intelligence Agent for shop '{shop_id}'")
        
        # 1. Fetch recent events (e.g., last 30 days) from Firestore
        events = firestore_service.get_demand_events(shop_id, limit=500)
        if not events:
            logger.warning(f"No demand events found for shop '{shop_id}' to aggregate.")
            return

        # 2. Load events into a Pandas DataFrame
        df = pd.DataFrame(events)
        
        # Ensure timestamp is datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Calculate Aggregations
        # Group by canonical product
        product_groups = df.groupby("canonical_product")
        
        # Calculate total requests per product
        request_frequencies = product_groups.size().to_dict()
        
        # Calculate unavailable counts
        unavailable_df = df[df["available"] == False]
        if not unavailable_df.empty:
            unavailable_counts = unavailable_df.groupby("canonical_product").size().to_dict()
        else:
            unavailable_counts = {}
            
        # Ensure all requested products have an entry in unavailable counts (default to 0)
        for prod in request_frequencies.keys():
            if prod not in unavailable_counts:
                unavailable_counts[prod] = 0

        # Calculate Demand Score:
        # Higher score for items that are frequently asked for but unavailable (stockout pain points)
        # formula: (unavailable_count * 2.5) + (total_requests * 0.5)
        demand_scores = {}
        for prod in request_frequencies.keys():
            req_freq = request_frequencies[prod]
            unavail = unavailable_counts.get(prod, 0)
            demand_scores[prod] = float((unavail * 2.5) + (req_freq * 0.5))

        # Calculate Trending Products:
        # Products with high volume or positive change in request rate in the last 3 days
        # For simplicity in this offline prototype, we take products with a demand score > 3.0,
        # sorted by recent request counts.
        trending_products = []
        recent_cutoff = datetime.utcnow() - timedelta(days=3)
        recent_df = df[df["timestamp"] >= recent_cutoff]
        
        if not recent_df.empty:
            recent_counts = recent_df.groupby("canonical_product").size().sort_values(ascending=False)
            # Take top 3 as trending
            trending_products = recent_counts.index.tolist()[:3]
        else:
            # Fallback to top overall products by score
            sorted_scores = sorted(demand_scores.items(), key=lambda x: x[1], reverse=True)
            trending_products = [item[0] for item in sorted_scores[:3]]

        # Prepare summary document
        summary_data = {
            "shop_id": shop_id,
            "updated_at": datetime.utcnow().isoformat(),
            "unavailable_counts": unavailable_counts,
            "request_frequencies": request_frequencies,
            "demand_scores": demand_scores,
            "trending_products": trending_products
        }

        # 3. Save summary back to Firestore
        firestore_service.update_demand_summary(shop_id, summary_data)
        logger.info(f"Demand Summary successfully updated for shop '{shop_id}'")

        # 4. Trigger the Procurement Agent to recalculate recommendations
        # Agents communicate only through Firestore — procurement reads demand_summary and writes recommendations.
        procurement_agent.generate_recommendations(shop_id)

demand_intelligence_agent = DemandIntelligenceAgent()
