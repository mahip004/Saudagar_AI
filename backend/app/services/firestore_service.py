import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from config import settings

logger = logging.getLogger("saudagar_ai.firestore")

class MockDocument:
    def __init__(self, doc_id: str, data: Dict[str, Any]):
        self.id = doc_id
        self._data = data

    def to_dict(self) -> Dict[str, Any]:
        return self._data

class MockCollection:
    def __init__(self, name: str, memory_db: Dict[str, Dict[str, Any]]):
        self.name = name
        self.memory_db = memory_db

    def document(self, doc_id: str):
        return MockDocumentReference(self.name, doc_id, self.memory_db)

    def stream(self):
        docs = []
        for doc_id, data in self.memory_db.get(self.name, {}).items():
            docs.append(MockDocument(doc_id, data))
        return docs

    def add(self, document_data: Dict[str, Any]):
        import uuid
        doc_id = str(uuid.uuid4())
        if self.name not in self.memory_db:
            self.memory_db[self.name] = {}
        self.memory_db[self.name][doc_id] = document_data
        return doc_id, MockDocumentReference(self.name, doc_id, self.memory_db)

class MockDocumentReference:
    def __init__(self, collection_name: str, doc_id: str, memory_db: Dict[str, Dict[str, Any]]):
        self.collection_name = collection_name
        self.id = doc_id
        self.memory_db = memory_db

    def get(self):
        data = self.memory_db.get(self.collection_name, {}).get(self.id)
        if data:
            return MockDocument(self.id, data)
        return MockDocument(self.id, {})

    def set(self, document_data: Dict[str, Any], merge: bool = False):
        if self.collection_name not in self.memory_db:
            self.memory_db[self.collection_name] = {}
        if merge and self.id in self.memory_db[self.collection_name]:
            self.memory_db[self.collection_name][self.id].update(document_data)
        else:
            self.memory_db[self.collection_name][self.id] = document_data

    def delete(self):
        if self.collection_name in self.memory_db and self.id in self.memory_db[self.collection_name]:
            del self.memory_db[self.collection_name][self.id]

class MockFirestoreClient:
    def __init__(self):
        self.memory_db: Dict[str, Dict[str, Any]] = {
            "products": {
                "prod_1": {"canonical_name": "Maggi Noodles", "aliases": ["maggi", "maggie", "migi", "maggie noodles"], "category": "Packaged Foods", "brand": "Nestle"},
                "prod_2": {"canonical_name": "Amul Butter 100g", "aliases": ["amul butter", "butter amul", "makkhan"], "category": "Dairy", "brand": "Amul"},
                "prod_3": {"canonical_name": "Colgate Strong Teeth 150g", "aliases": ["colgate", "toothpaste colgate", "colgat"], "category": "Personal Care", "brand": "Colgate-Palmolive"},
                "prod_4": {"canonical_name": "Cadbury Dairy Milk 100g", "aliases": ["dairy milk", "chocolate dairy milk", "dary milk", "cadbury chocolate", "chocolate"], "category": "Confectionery", "brand": "Cadbury"},
            },
            "demand_events": {},
            "demand_summary": {},
            "business_insights": {
                "latest": {
                    "updated_at": datetime.utcnow().isoformat(),
                    "weather": {"temp": 32.5, "condition": "Sunny", "humidity": 65},
                    "trends": {"chocolate": 75, "noodles": 80, "toothpaste": 50},
                    "festivals": [{"name": "Raksha Bandhan", "date": "2026-08-28", "days_away": 43}]
                }
            },
            "recommendations": {}
        }
        logger.warning(
            "\n"
            "==================================================\n"
            "MOCK FIRESTORE INITIALIZED (IN-MEMORY)\n"
            "service-account.json was not found at specified path.\n"
            "To connect to Google Cloud Firestore, please perform:\n"
            "========================\n"
            "MANUAL STEP REQUIRED\n"
            "========================\n"
            "1. Download your service account JSON file from Firebase Console.\n"
            "2. Place it at: " + os.path.abspath(settings.FIREBASE_CREDENTIALS_PATH) + "\n"
            "3. Restart the FastAPI server.\n"
            "=================================================="
        )

    def collection(self, name: str):
        return MockCollection(name, self.memory_db)

class FirestoreService:
    def __init__(self):
        self.db = None
        self._initialize_firebase()

    def _initialize_firebase(self):
        service_account_json = settings.FIREBASE_SERVICE_ACCOUNT
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        if service_account_json:
            try:
                # Avoid duplicate app initialization
                if not firebase_admin._apps:
                    cred = credentials.Certificate(json.loads(service_account_json))
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                logger.info("Successfully connected to live Firebase Firestore using environment credentials!")
            except Exception as e:
                logger.error(f"Error initializing Firebase with environment credentials: {e}")
                self.db = MockFirestoreClient()
        elif os.path.exists(cred_path):
            try:
                # Local development path only; production should use FIREBASE_SERVICE_ACCOUNT.
                if not firebase_admin._apps:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                logger.info("Successfully connected to live Firebase Firestore using credentials file!")
            except Exception as e:
                logger.error(f"Error initializing Firebase with credentials file: {e}")
                self.db = MockFirestoreClient()
        else:
            self.db = MockFirestoreClient()

    def seed_products_if_empty(self):
        """
        Populates a default product catalog in Firestore if it is currently empty.
        """
        try:
            if isinstance(self.db, MockFirestoreClient):
                return
            
            # Check if products collection is empty
            docs = self.db.collection("products").limit(1).stream()
            if not list(docs):
                logger.info("Live Firestore 'products' collection is empty. Seeding default product catalog...")
                default_products = [
                    {"canonical_name": "Maggi Noodles", "aliases": ["maggi", "maggie", "migi", "maggie noodles"], "category": "Packaged Foods", "brand": "Nestle"},
                    {"canonical_name": "Amul Butter 100g", "aliases": ["amul butter", "butter amul", "makkhan"], "category": "Dairy", "brand": "Amul"},
                    {"canonical_name": "Colgate Strong Teeth 150g", "aliases": ["colgate", "toothpaste colgate", "colgat"], "category": "Personal Care", "brand": "Colgate-Palmolive"},
                    {"canonical_name": "Cadbury Dairy Milk 100g", "aliases": ["dairy milk", "chocolate dairy milk", "dary milk", "cadbury chocolate", "chocolate"], "category": "Confectionery", "brand": "Cadbury"},
                ]
                for p in default_products:
                    # Insert directly without triggering refresh cache on each one to avoid recursion
                    self.db.collection("products").add(p)
                logger.info("Successfully seeded default catalog in Firestore!")
        except Exception as e:
            logger.error(f"Failed to seed products: {e}", exc_info=True)

    def get_products(self) -> List[Dict[str, Any]]:
        docs = self.db.collection("products").stream()
        products = []
        for doc in docs:
            d = doc.to_dict()
            d["id"] = doc.id
            products.append(d)
        return products

    def add_product(self, product_data: Dict[str, Any]) -> str:
        # Check if already has ID
        doc_id = product_data.get("id")
        if doc_id:
            self.db.collection("products").document(doc_id).set(product_data)
        else:
            ref = self.db.collection("products")
            # If using mock DB
            if isinstance(self.db, MockFirestoreClient):
                doc_id, _ = ref.add(product_data)
            else:
                _, doc_ref = ref.add(product_data)
                doc_id = doc_ref.id

        # Trigger cache refresh in matching service (import locally to avoid circular dependency)
        try:
            from app.services.matching_service import matching_service
            matching_service.refresh_cache()
        except Exception as ex:
            logger.error(f"Error refreshing matching service cache after adding product: {ex}")

        return doc_id

    def add_product_alias(self, canonical_name: str, new_alias: str) -> bool:
        """ Legacy global alias mechanism. Kept for backwards compatibility but shouldn't be used by new pipeline. """
        pass

    def get_shop_aliases(self, shop_id: str) -> Dict[str, str]:
        """
        Returns a dict mapping raw_phrase -> canonical_product_id for a specific shop.
        Schema: shops/{shop_id}/aliases/{alias_id}
        """
        aliases = {}
        try:
            if isinstance(self.db, MockFirestoreClient):
                # Simple in-memory mock for local testing
                if "shops" not in self.db.memory_db:
                    return aliases
                shop_data = self.db.memory_db["shops"].get(shop_id, {})
                for k, v in shop_data.get("aliases", {}).items():
                    aliases[v.get("raw_phrase", "").lower()] = v.get("canonical_product_id")
            else:
                docs = self.db.collection("shops").document(shop_id).collection("aliases").stream()
                for doc in docs:
                    d = doc.to_dict()
                    aliases[d.get("raw_phrase", "").lower()] = d.get("canonical_product_id")
        except Exception as e:
            logger.error(f"Error fetching shop aliases: {e}")
        return aliases

    def add_shop_alias(self, shop_id: str, raw_phrase: str, canonical_product_id: str) -> None:
        """ Adds a confirmed alias directly to the shop's subcollection """
        import uuid
        alias_id = str(uuid.uuid4())
        data = {
            "raw_phrase": raw_phrase.lower(),
            "canonical_product_id": canonical_product_id,
            "confidence_at_creation": 1.0,
            "created_by": "shopkeeper",
            "created_at": datetime.utcnow().isoformat()
        }
        
        if isinstance(self.db, MockFirestoreClient):
            if "shops" not in self.db.memory_db:
                self.db.memory_db["shops"] = {}
            if shop_id not in self.db.memory_db["shops"]:
                self.db.memory_db["shops"][shop_id] = {"aliases": {}}
            self.db.memory_db["shops"][shop_id]["aliases"][alias_id] = data
        else:
            self.db.collection("shops").document(shop_id).collection("aliases").document(alias_id).set(data)
            
        # Trigger cache refresh in matching service
        try:
            from app.services.matching_service import matching_service
            matching_service.refresh_cache()
        except Exception as ex:
            logger.error(f"Error refreshing matching service cache after adding shop alias: {ex}")

    def flag_for_shopkeeper_whatsapp(self, shop_id: str, raw_phrase: str, candidates: List[str]) -> None:
        """
        Writes a special document that acts as a trigger for an external WhatsApp bot.
        """
        import uuid
        trigger_id = str(uuid.uuid4())
        data = {
            "shop_id": shop_id,
            "raw_phrase": raw_phrase,
            "candidates": candidates,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        if isinstance(self.db, MockFirestoreClient):
            if "whatsapp_triggers" not in self.db.memory_db:
                self.db.memory_db["whatsapp_triggers"] = {}
            self.db.memory_db["whatsapp_triggers"][trigger_id] = data
        else:
            self.db.collection("whatsapp_triggers").document(trigger_id).set(data)
        logger.info(f"Triggered WhatsApp flow for '{raw_phrase}' with candidates: {candidates}")

    def add_demand_event(self, event_data: Dict[str, Any]) -> str:
        ref = self.db.collection("demand_events")
        if isinstance(self.db, MockFirestoreClient):
            doc_id, _ = ref.add(event_data)
            return doc_id
        else:
            _, doc_ref = ref.add(event_data)
            return doc_ref.id

    def get_demand_events(self, shop_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        ref = self.db.collection("demand_events")
        # In a real app we might query: ref.where("shop_id", "==", shop_id).order_by("timestamp", direction=Query.DESCENDING).limit(limit)
        # To avoid complex composite index issues in prototype, we can fetch and filter in python if mock/simple,
        # or do a basic list and filter.
        docs = ref.stream()
        events = []
        for doc in docs:
            d = doc.to_dict()
            if d.get("shop_id") == shop_id:
                d["id"] = doc.id
                events.append(d)
        # Sort by timestamp desc
        events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return events[:limit]

    def update_demand_summary(self, shop_id: str, summary_data: Dict[str, Any]):
        self.db.collection("demand_summary").document(shop_id).set(summary_data)

    def get_demand_summary(self, shop_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection("demand_summary").document(shop_id).get()
        if doc and doc.to_dict():
            return doc.to_dict()
        return None

    def update_business_insights(self, insights_data: Dict[str, Any]):
        self.db.collection("business_insights").document("latest").set(insights_data)

    def get_business_insights(self) -> Dict[str, Any]:
        doc = self.db.collection("business_insights").document("latest").get()
        if doc and doc.to_dict():
            return doc.to_dict()
        return {}

    def update_recommendations(self, shop_id: str, recommendations_data: Dict[str, Any]):
        self.db.collection("recommendations").document(shop_id).set(recommendations_data)

    def get_recommendations(self, shop_id: str) -> Dict[str, Any]:
        doc = self.db.collection("recommendations").document(shop_id).get()
        if doc and doc.to_dict():
            return doc.to_dict()
        return {}

# Instantiate global service
firestore_service = FirestoreService()
