import logging
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from typing import List, Optional

# Import configurations & models
from config import settings
from app.models import (
    CaptureDemandRequest, CaptureDemandResponse, 
    ProductModel, ProductResponse, FeedbackRequest
)

# Import services
from app.services.firestore_service import firestore_service
from app.services.sarvam_service import sarvam_service

# Import agents
from app.agents.demand_capture import demand_capture_agent
from app.agents.demand_intelligence import demand_intelligence_agent
from app.agents.business_intelligence import business_intelligence_agent
from app.agents.procurement import procurement_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("saudagar_ai.backend")

# Initialize FastAPI App
app = FastAPI(
    title="Saudagar AI Cloud API",
    description="Production-style backend for Kirana Store Demand & Procurement Intelligence",
    version="1.0.0"
)

# CORS middleware config for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize APScheduler for Business Intelligence Agent
scheduler = BackgroundScheduler()

def run_bi_agent_job():
    try:
        business_intelligence_agent.run_update()
    except Exception as e:
        logger.error(f"Failed to run Business Intelligence scheduler job: {e}")

@app.on_event("startup")
def startup_event():
    # Run the BI update immediately on startup to ensure Firestore has data
    run_bi_agent_job()
    
    # Schedule the BI Agent to run every 6 hours
    scheduler.add_job(run_bi_agent_job, "interval", hours=6)
    scheduler.start()
    logger.info("APScheduler started successfully. Scheduled BI Agent to run every 6 hours.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    logger.info("APScheduler shutdown completed.")

# FastAPI Endpoints

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app": "Saudagar AI Cloud Backend API",
        "api_docs": "/docs"
    }

@app.post("/capture-demand", response_model=CaptureDemandResponse)
def capture_demand(request: CaptureDemandRequest, background_tasks: BackgroundTasks):
    """
    Accepts text transcript, extracts structured info, maps product aliases,
    writes demand event to Firestore, and triggers demand intelligence in background.
    """
    try:
        # Capture and save the event
        event = demand_capture_agent.capture_demand_event(
            shop_id=request.shop_id,
            transcript=request.transcript
        )
        
        # Trigger Demand Intelligence Agent in the background (Pandas metrics calculation)
        background_tasks.add_task(
            demand_intelligence_agent.process_demand_metrics, 
            shop_id=request.shop_id
        )
        
        return CaptureDemandResponse(
            event_id=event["event_id"],
            product=event["product"],
            canonical_product=event["canonical_product"],
            available=event["available"],
            alternative=event["alternative"],
            purchase_completed=event["purchase_completed"],
            timestamp=event["timestamp"]
        )
    except Exception as e:
        logger.error(f"Error capturing demand: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-audio")
async def upload_audio(
    background_tasks: BackgroundTasks,
    shop_id: str = Form(..., description="The shop ID of the kirana store"),
    file: UploadFile = File(..., description="The recorded WAV audio file")
):
    """
    Upload voice recording, transcribe via Sarvam STT API,
    and process the resulting transcript through the capture-demand workflow.
    """
    try:
        # Read file bytes
        audio_bytes = await file.read()
        filename = file.filename or "audio.wav"
        
        # 1. Transcribe audio using Sarvam STT
        logger.info(f"Transcribing audio upload for shop '{shop_id}'...")
        transcript = await sarvam_service.transcribe_audio(audio_bytes, filename)
        
        # 2. Run capture-demand logic
        event = demand_capture_agent.capture_demand_event(
            shop_id=shop_id,
            transcript=transcript
        )
        
        # 3. Trigger Demand Intelligence Agent in background
        background_tasks.add_task(
            demand_intelligence_agent.process_demand_metrics,
            shop_id=shop_id
        )
        
        return {
            "transcript": transcript,
            "event": CaptureDemandResponse(
                event_id=event["event_id"],
                product=event["product"],
                canonical_product=event["canonical_product"],
                available=event["available"],
                alternative=event["alternative"],
                purchase_completed=event["purchase_completed"],
                timestamp=event["timestamp"]
            )
        }
    except Exception as e:
        logger.error(f"Error handling audio upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations")
def get_recommendations(shop_id: str):
    """
    Retrieve current AI recommendations for the specified shop.
    """
    try:
        recs = firestore_service.get_recommendations(shop_id)
        if not recs:
            return {"shop_id": shop_id, "recommendations": [], "updated_at": None}
        return recs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/demand-summary")
def get_demand_summary(shop_id: str):
    """
    Retrieve recent demand intelligence aggregations.
    """
    try:
        summary = firestore_service.get_demand_summary(shop_id)
        if not summary:
            return {
                "shop_id": shop_id,
                "unavailable_counts": {},
                "request_frequencies": {},
                "demand_scores": {},
                "trending_products": [],
                "updated_at": None
            }
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/business-insights")
def get_business_insights():
    """
    Retrieve latest weather, search trends, and upcoming festival insights.
    """
    try:
        return firestore_service.get_business_insights()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products", response_model=List[ProductResponse])
def get_products():
    """
    Retrieve list of canonical products and aliases.
    """
    try:
        products = firestore_service.get_products()
        # Parse into response models
        return [
            ProductResponse(
                id=p.get("id", p.get("canonical_name", "unk")),
                canonical_name=p["canonical_name"],
                aliases=p.get("aliases", []),
                category=p.get("category", "Uncategorized"),
                brand=p.get("brand", "Generic")
            )
            for p in products
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products", response_model=ProductResponse)
def add_product(product: ProductModel):
    """
    Register a new product with its aliases, category, and brand.
    """
    try:
        product_dict = product.model_dump()
        doc_id = firestore_service.add_product(product_dict)
        return ProductResponse(
            id=doc_id,
            canonical_name=product.canonical_name,
            aliases=product.aliases,
            category=product.category,
            brand=product.brand
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def submit_feedback(feedback: FeedbackRequest):
    """
    Submit feedback on generated recommendations (e.g. accepted/rejected actions).
    Saves feedback in Firestore for auditing.
    """
    try:
        feedback_data = feedback.model_dump()
        feedback_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Save directly to custom feedback collection
        doc_id = firestore_service.db.collection("procurement_feedback").add(feedback_data)
        if isinstance(doc_id, tuple):  # If mock DB
            doc_id = doc_id[0]
        else:
            doc_id = doc_id.id if hasattr(doc_id, "id") else str(doc_id)
            
        logger.info(f"Feedback saved for recommendation {feedback.recommendation_id} with reference ID {doc_id}")
        return {"status": "success", "feedback_id": doc_id}
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-bi")
def force_run_bi():
    """
    Manually force trigger the Business Intelligence Agent update.
    """
    try:
        insights = business_intelligence_agent.run_update()
        return {"status": "success", "insights": insights}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
