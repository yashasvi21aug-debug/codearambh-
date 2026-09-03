import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI
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

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))

CBT_SYSTEM_PROMPT = (
    "You are MindEase, an empathetic, non-judgmental CBT (Cognitive Behavioral Therapy) companion for students. "
    "Validate the user's emotions, gently guide them through identifying cognitive distortions, "
    "and suggest practical grounding exercises like 4-7-8 breathing. Never provide medical diagnoses or prescriptions."
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(payload: ChatRequest):
    is_crisis, crisis_data = scan_for_crisis(payload.message)
    if is_crisis:
        return crisis_data

    async def event_generator():
        try:
            stream = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CBT_SYSTEM_PROMPT},
                    {"role": "user", "content": payload.message}
                ],
                stream=True
            )
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                yield f"data: {json.dumps({'token': token, 'is_crisis': False})}\n\n"
        except Exception:
            fallback = "I'm listening. Take a gentle breath—tell me more about what's pressing on your mind right now."
            yield f"data: {json.dumps({'token': fallback, 'is_crisis': False})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
