import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from google import genai
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

api_key = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key) if api_key else None

CBT_SYSTEM_PROMPT = (
    "You are MindEase, a warm, non-judgmental CBT (Cognitive Behavioral Therapy) companion for students. "
    "Respond casually and warmly to greetings like 'hi' or 'hello' by welcoming them and asking how their day is going. "
    "Validate emotions, help gently identify negative thinking patterns, and offer practical grounding tips. "
    "Never diagnose or prescribe medication. Keep answers concise."
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    is_crisis, crisis_data = scan_for_crisis(payload.message)
    if is_crisis:
        return crisis_data

    async def event_generator():
        if not client:
            fallback = "Hello! I'm here to listen. How has your day been treating you?"
            yield f"data: {json.dumps({'token': fallback, 'is_crisis': False})}\n\n"
            return

        try:
            response = client.models.generate_content_stream(
                model="gemini-1.5-flash",
                contents=payload.message,
                config={"system_instruction": CBT_SYSTEM_PROMPT}
            )
            for chunk in response:
                token = chunk.text or ""
                yield f"data: {json.dumps({'token': token, 'is_crisis': False})}\n\n"
        except Exception as e:
            err_msg = f"Hello! How can I support you today? (Note: {str(e)[:40]})"
            yield f"data: {json.dumps({'token': err_msg, 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
