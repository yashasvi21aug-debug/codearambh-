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
    "You are MindEase, a warm, supportive CBT companion for students. "
    "Respond casually to greetings. For other thoughts, listen with empathy and offer grounding advice."
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
            yield f"data: {json.dumps({'token': 'Error: GEMINI_API_KEY environment variable is empty on Render.', 'is_crisis': False})}\n\n"
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        
        body = {
            "system_instruction": {"parts": [{"text": CBT_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": payload.message}]}]
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=body)
                if res.status_code == 200:
                    data = res.json()
                    bot_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    yield f"data: {json.dumps({'token': bot_text, 'is_crisis': False})}\n\n"
                else:
                    # Print raw error message from Google directly to the chat
                    yield f"data: {json.dumps({'token': f'Google API Error ({res.status_code}): {res.text[:120]}', 'is_crisis': False})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'token': f'Backend Error: {str(e)}', 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
