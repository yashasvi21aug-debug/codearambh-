import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import google.generativeai as genai
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
if api_key:
    genai.configure(api_key=api_key)

CBT_SYSTEM_PROMPT = (
    "You are MindEase, an empathetic, supportive CBT companion for students. "
    "Respond warmly to greetings. Listen with compassion, help reframe anxious thoughts, "
    "and suggest practical coping strategies. Keep answers conversational and concise."
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    is_crisis, crisis_data = scan_for_crisis(payload.message)
    if is_crisis:
        return crisis_data

    async def event_generator():
        if not api_key:
            fallback = "Hello! I'm here to listen. How has your day been treating you?"
            yield f"data: {json.dumps({'token': fallback, 'is_crisis': False})}\n\n"
            return

        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=CBT_SYSTEM_PROMPT
            )
            response = model.generate_content(payload.message, stream=True)
            for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps({'token': chunk.text, 'is_crisis': False})}\n\n"
        except Exception as e:
            err_msg = f"Hello! How can I support you today? (Note: {str(e)[:50]})"
            yield f"data: {json.dumps({'token': err_msg, 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
