# Saudagar AI - API Documentation

Local base URL: `http://localhost:8001`.

## Capture text demand

`POST /capture-demand`

```json
{"shop_id":"shop_001","transcript":"Bhaiya Maggi packet milega kya?"}
```

A successful `200` response includes `event_id`, `product`, `canonical_product`, `available`, `purchase_completed`, `timestamp`, `confidence`, and `availability`.

If the extraction cannot produce a verified event, the endpoint returns `503` with a `detail` message. This could mean inference is unavailable, quota-limited, malformed, or that the transcript is insufficient; `503` does not distinguish these causes.

## Upload audio

`POST /upload-audio` uses `multipart/form-data`: `shop_id` (string) and `file` (WAV audio). A successful `200` response contains `transcript` and `event`. Empty audio and Sarvam/provider failures currently surface as generic request errors unless no verified event is extracted, in which case the response is `503`.

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | Basic backend liveness response |
| GET/POST | `/products` | Read or add product catalogue items |
| POST | `/confirm-product-alias` | Confirm an alias mapping |
| GET | `/recommendations?shop_id=shop_001` | Get recommendations |
| GET | `/demand-summary?shop_id=shop_001` | Get demand counts, scores, and trends |
| GET | `/business-insights` | Get weather, trend scores, and festivals |
| POST | `/feedback` | Save recommendation feedback |
| POST | `/run-bi` | Trigger an immediate business-insights update |

## Errors and limits

| Status | Current meaning |
| --- | --- |
| `200` | Request succeeded |
| `404` | Alias confirmation could not find the canonical product |
| `422` | Invalid or missing request fields |
| `503` | No verified demand event could be extracted |
| `500` | Unexpected processing, database, or external-service error |

The active inference service is **Groq**, configured with `GROQ_API_KEY` and `GROQ_MODEL` (default: `llama-3.3-70b-versatile`). `gemini_service.py` is a legacy filename only.

There is no stable provider-error format yet: rate limits (`429`), quota exhaustion, invalid credentials, timeouts, and upstream `5xx` responses are not mapped to distinct client-facing codes or `Retry-After` values. Clients should treat non-`200` responses as failures and allow the user to retry.
