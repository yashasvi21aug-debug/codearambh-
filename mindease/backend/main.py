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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

CBT_SYSTEM_PROMPT = (
    "You are MindEase, a warm, non-judgmental CBT (Cognitive Behavioral Therapy) companion for college students. "
    "Respond casually and warmly to greetings like 'hi' or 'hello' by welcoming them and asking how their day is going. "
    "Validate emotions, help gently identify negative thinking patterns, and offer practical grounding tips. "
    "Never diagnose or prescribe medication. Keep answers conversational, empathetic, and concise."
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    is_crisis, crisis_data = scan_for_crisis(payload.message)
    if is_crisis:
        return crisis_data

    async def event_generator():
        if not GEMINI_API_KEY:
            yield f"data: {json.dumps({'token': 'Error: GEMINI_API_KEY is not configured on Render.', 'is_crisis': False})}\n\n"
            return

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Fetch available models for your specific key
            target_model = None
            try:
                list_res = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}")
                if list_res.status_code == 200:
                    models_list = list_res.json().get("models", [])
                    available = [
                        m["name"] for m in models_list 
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    # Select the newest available flash model, or fallback to the first supported model
                    for name in available:
                        if "flash" in name:
                            target_model = name
                            break
                    if not target_model and available:
                        target_model = available[0]
            except Exception:
                pass

            if not target_model:
                target_model = "models/gemini-2.5-flash"

            # 2. Call the active model
            clean_model_name = target_model.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={GEMINI_API_KEY}"
            
            body = {
                "system_instruction": {
                    "parts": [{"text": CBT_SYSTEM_PROMPT}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": payload.message}]
                    }
                ]
            }

            try:
                res = await client.post(url, json=body)
                if res.status_code == 200:
                    data = res.json()
                    bot_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    yield f"data: {json.dumps({'token': bot_text, 'is_crisis': False})}\n\n"
                else:
                    yield f"data: {json.dumps({'token': f'API Error ({res.status_code}): {res.text[:120]}', 'is_crisis': False})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'token': f'Connection error: {str(e)}', 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
