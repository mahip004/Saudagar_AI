from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class CaptureDemandRequest(BaseModel):
    shop_id: str = Field(..., description="Unique ID for the kirana shop")
    transcript: str = Field(..., description="Raw text transcript of customer voice recording")

class DemandEventModel(BaseModel):
    shop_id: str
    product: str
    canonical_product: str
    available: bool
    alternative: Optional[str] = None
    purchase_completed: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CaptureDemandResponse(BaseModel):
    event_id: str
    product: str
    canonical_product: str
    available: bool
    alternative: Optional[str] = None
    purchase_completed: bool
    timestamp: str
    needs_confirmation: bool = False
    candidates: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    availability: str = "unknown"

class ConfirmAliasRequest(BaseModel):
    shop_id: str
    canonical_name: str
    new_alias: str

class ProductModel(BaseModel):
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    category: str
    brand: str

class ProductResponse(BaseModel):
    id: str
    canonical_name: str
    aliases: List[str]
    category: str
    brand: str

class DemandSummaryModel(BaseModel):
    shop_id: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    unavailable_counts: Dict[str, int] = Field(default_factory=dict)
    request_frequencies: Dict[str, int] = Field(default_factory=dict)
    demand_scores: Dict[str, float] = Field(default_factory=dict)
    trending_products: List[str] = Field(default_factory=list)

class BusinessInsightsModel(BaseModel):
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    weather: Dict[str, Any] = Field(default_factory=dict)
    trends: Dict[str, Any] = Field(default_factory=dict)
    festivals: List[Dict[str, Any]] = Field(default_factory=list)

class ProcurementRecommendation(BaseModel):
    product: str
    action: str
    reason: str
    percentage_increase: Optional[int] = None
    priority: str  # HIGH, MEDIUM, LOW

class ProcurementModel(BaseModel):
    shop_id: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    recommendations: List[ProcurementRecommendation] = Field(default_factory=list)

class FeedbackRequest(BaseModel):
    shop_id: str
    recommendation_id: str
    feedback: str # e.g. "ACCEPTED", "REJECTED"
    comments: Optional[str] = None
