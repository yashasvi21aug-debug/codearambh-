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
    "You are MindEase, a warm, non-judgmental CBT (Cognitive Behavioral Therapy) companion for students. "
    "Respond casually and warmly to greetings like 'hi' or 'hello' by welcoming them and asking how their day is going. "
    "Validate emotions, help gently identify negative thinking patterns, and offer practical grounding tips. "
    "Never diagnose or prescribe medication. Keep answers conversational and concise."
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
            fallback = "Hello! I'm here to listen. How has your day been treating you?"
            yield f"data: {json.dumps({'token': fallback, 'is_crisis': False})}\n\n"
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:streamGenerateContent?alt=sse&key={GEMINI_API_KEY}"
        
        request_body = {
            "system_instruction": {
                "parts": [{"text": CBT_SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [{"text": payload.message}]
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, json=request_body) as response:
                    if response.status_code != 200:
                        err_text = await response.aread()
                        yield f"data: {json.dumps({'token': f'Hello! (Service notice: {response.status_code})', 'is_crisis': False})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            raw_data = line.replace("data: ", "").strip()
                            if not raw_data:
                                continue
                            try:
                                parsed = json.loads(raw_data)
                                candidates = parsed.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        token = part.get("text", "")
                                        if token:
                                            yield f"data: {json.dumps({'token': token, 'is_crisis': False})}\n\n"
                            except Exception:
                                continue
        except Exception as e:
            fallback = f"Hello! How can I support you today? (Connection note: {str(e)[:40]})"
            yield f"data: {json.dumps({'token': fallback, 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
