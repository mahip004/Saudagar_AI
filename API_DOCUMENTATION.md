# Saudagar AI - API Documentation

The Saudagar AI backend exposes REST endpoints for capturing demand, accessing aggregated intelligence metrics, and updating product catalogs.

Base URL: `http://localhost:8000` (Local Development)

---

## 1. Capture Demand (Text)
Extracts structured product data from a text transcript and starts the analytics pipeline.

* **Endpoint**: `/capture-demand`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
```json
{
  "shop_id": "shop_001",
  "transcript": "Bhaiya Maggi packet milega kya?"
}
```

* **Response (200 OK)**:
```json
{
  "event_id": "8d3e2a9b-4f5c-4d8a-9e1b-2c3d4e5f6g7h",
  "product": "Maggi",
  "canonical_product": "Maggi Noodles",
  "available": false,
  "alternative": null,
  "purchase_completed": false,
  "timestamp": "2026-07-16T23:15:20.123456"
}
```

---

## 2. Capture Demand (Audio Upload)
Uploads recorded WAV audio, transcribes it via Sarvam AI, and passes the transcript to the capture demand pipeline.

* **Endpoint**: `/upload-audio`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Request Form**:
  - `shop_id` (string): "shop_001"
  - `file` (binary): recorded WAV file

* **Response (200 OK)**:
```json
{
  "transcript": "bhaiya ek amul butter de do aur biscuit",
  "event": {
    "event_id": "7a2b9c8d-3e4f-5g6h-7i8j-9k0l1m2n3o4p",
    "product": "Amul Butter",
    "canonical_product": "Amul Butter 100g",
    "available": true,
    "alternative": null,
    "purchase_completed": true,
    "timestamp": "2026-07-16T23:16:10.789123"
  }
}
```

---

## 3. Get Recommendations
Returns the current AI procurement advice for a shop.

* **Endpoint**: `/recommendations`
* **Method**: `GET`
* **Query Parameters**:
  - `shop_id` (string): "shop_001"

* **Response (200 OK)**:
```json
{
  "shop_id": "shop_001",
  "updated_at": "2026-07-16T23:15:25.654321",
  "recommendations": [
    {
      "product": "Maggi Noodles",
      "action": "Increase stock by 45%",
      "reason": "This product went out-of-stock 3 times recently. Prepare inventory ahead of Raksha Bandhan.",
      "percentage_increase": 45,
      "priority": "HIGH"
    }
  ]
}
```

---

## 4. Get Demand Summary
Returns aggregated analytics computed via Pandas.

* **Endpoint**: `/demand-summary`
* **Method**: `GET`
* **Query Parameters**:
  - `shop_id` (string): "shop_001"

* **Response (200 OK)**:
```json
{
  "shop_id": "shop_001",
  "updated_at": "2026-07-16T23:15:21.098765",
  "unavailable_counts": {
    "Maggi Noodles": 3,
    "Amul Butter 100g": 0
  },
  "request_frequencies": {
    "Maggi Noodles": 5,
    "Amul Butter 100g": 2
  },
  "demand_scores": {
    "Maggi Noodles": 10.0,
    "Amul Butter 100g": 1.0
  },
  "trending_products": [
    "Maggi Noodles"
  ]
}
```

---

## 5. Get Business Insights
Returns the latest local weather conditions, search trend indexes, and upcoming festival schedules.

* **Endpoint**: `/business-insights`
* **Method**: `GET`

* **Response (200 OK)**:
```json
{
  "updated_at": "2026-07-16T23:12:14.000000",
  "weather": {
    "city": "Mumbai",
    "temp": 29.0,
    "condition": "Rainy",
    "humidity": 88,
    "source": "Seasonal Mock (No Key)"
  },
  "trends": {
    "packaged_foods": 85,
    "beverages": 65,
    "hygiene": 50,
    "confectionery": 50
  },
  "festivals": [
    {
      "name": "Raksha Bandhan",
      "date": "2026-08-28",
      "days_away": 42,
      "impact_categories": ["Confectionery", "Chocolates", "Gift Packs", "Pooja Items"],
      "description": "Sisters tie rakhis on brothers' wrists. Heavy demand for premium sweets and chocolate gift packs."
    }
  ]
}
```

---

## 6. Catalog Management (Products)
Allows viewing and inserting catalog templates containing aliases for fuzzy matches.

* **Get Catalog**: `GET /products`
  * **Response**: List of all products.

* **Add Product**: `POST /products`
  * **Request Body**:
```json
{
  "canonical_name": "Lux Soft Touch Soap 100g",
  "aliases": ["lux", "luks", "soap lux", "lux sabun"],
  "category": "Hygiene",
  "brand": "Unilever"
}
```
  * **Response**: Registered Product document with Firestore ID.

---

## 7. Submit Feedback
Records shopkeeper decisions to Accept or Dismiss AI procurement advice.

* **Endpoint**: `/feedback`
* **Method**: `POST`
* **Request Body**:
```json
{
  "shop_id": "shop_001",
  "recommendation_id": "0",
  "feedback": "ACCEPTED",
  "comments": "Accepted recommendation: Order placed."
}
```

* **Response (200 OK)**:
```json
{
  "status": "success",
  "feedback_id": "feedback_doc_id"
}
```
