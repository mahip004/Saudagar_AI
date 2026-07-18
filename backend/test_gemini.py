import google.generativeai as genai
from config import settings

print("GEMINI_API_KEY:", settings.GEMINI_API_KEY)
genai.configure(api_key=settings.GEMINI_API_KEY)
try:
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
    response = model.generate_content("hello")
    print("Success! Response:", response.text)
except Exception as e:
    print("Error calling Gemini API:", e)
