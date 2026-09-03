import os
import json
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from crisis_detector import scan_for_crisis

load_dotenv()

app = FastAPI(title="MindEase API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

CBT_SYSTEM_PROMPT = (
    "You are MindEase, a supportive CBT companion for students. "
    "Respond warmly to greetings. Listen with empathy, validate feelings, "
    "and give practical grounding steps. Keep answers concise."
)

class ChatRequest(BaseModel):
    message: str

def smart_fallback(text: str) -> str:
    msg = text.lower().strip()
    if any(g in msg for g in ["hi", "hello", "hey"]):
        return "Hello! I'm here for you. How are you feeling today?"
    if any(w in msg for w in ["exam", "stress", "anxious", "worry", "panic", "study"]):
        return "Take a slow, deep breath. Academic pressure is tough, but you are not alone. What part is feeling the most heavy right now?"
    if any(w in msg for w in ["sad", "depressed", "lonely", "tired", "burnout"]):
        return "I hear you, and your feelings are completely valid. It is okay to take things one moment at a time. What's been on your mind?"
    return "I'm listening closely. Please tell me more about what you are experiencing."

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    is_crisis, crisis_data = scan_for_crisis(payload.message)
    if is_crisis:
        return crisis_data

    async def event_generator():
        if not GEMINI_API_KEY:
            yield f"data: {json.dumps({'token': smart_fallback(payload.message), 'is_crisis': False})}\n\n"
            return

        bot_reply = None
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Query available models for this specific API key
            model_to_use = "gemini-1.5-flash"
            try:
                list_res = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}")
                if list_res.status_code == 200:
                    models_data = list_res.json().get("models", [])
                    generate_models = [
                        m["name"] for m in models_data 
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    # Pick gemini-1.5-flash if present, otherwise first viable model
                    for candidate in ["models/gemini-1.5-flash", "models/gemini-pro", "models/gemini-1.0-pro"]:
                        if candidate in generate_models:
                            model_to_use = candidate.replace("models/", "")
                            break
                    else:
                        if generate_models:
                            model_to_use = generate_models[0].replace("models/", "")
            except Exception:
                pass

            # 2. Call the resolved model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_to_use}:generateContent?key={GEMINI_API_KEY}"
            body = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{CBT_SYSTEM_PROMPT}\n\nStudent: {payload.message}"}]
                    }
                ]
            }

            try:
                res = await client.post(url, json=body)
                if res.status_code == 200:
                    result = res.json()
                    candidates = result.get("candidates", [])
                    if candidates:
                        bot_reply = candidates[0]["content"]["parts"][0]["text"]
            except Exception:
                pass

        # 3. Always guarantee a clean, helpful answer
        if not bot_reply:
            bot_reply = smart_fallback(payload.message)

        yield f"data: {json.dumps({'token': bot_reply, 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
