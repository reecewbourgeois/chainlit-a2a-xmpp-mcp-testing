import json
from typing import Literal, Optional

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from litellm import CustomStreamWrapper, acompletion
from pydantic import BaseModel

MODEL = "ollama_chat/gemma4:e2b"  # TODO: Env

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Env
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO: Database or Redis
# Global memory store (for demonstration)
chat_sessions: dict[str, list[dict]] = {}


@app.get("/")
def read_main():
    return {"message": "Hello World from main app"}


class ImageURLInput(BaseModel):
    url: str


class ImageInput(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: ImageURLInput


class AudioURLInput(BaseModel):
    data: str  # Base64 string
    format: str  # e.g., "wav", "mp3"


class AudioInput(BaseModel):
    type: Literal["input_audio"] = "input_audio"
    input_audio: AudioURLInput


class Chat(BaseModel):
    message: str
    # Format: https://docs.litellm.ai/docs/completion/vision#quick-start
    vision_input: Optional[ImageInput] = None
    # Format: https://docs.litellm.ai/docs/completion/audio#audio-input-to-a-model
    audio_input: Optional[AudioInput] = None


@app.get("/supported_inputs")
async def supported_inputs():
    # Was initially going to make this dynamic using litellm's functions, but it they are incorrect
    return {
        "audio_input": False,
        "vision_input": True,
    }


@app.post("/chat/{session_id}")
async def chat(session_id: str, body: Chat):
    # Construct the multimodal message
    user_content: list[dict] = [{"type": "text", "text": body.message}]

    # Handle image if provided.
    if body.vision_input:
        print(body.vision_input.model_dump(mode="json"))
        user_content.append(body.vision_input.model_dump(mode="json"))

    # Handle audio if provided. Note that most models don't support audio input.
    if body.audio_input and False:  # Audio input not supported
        print(body.audio_input.model_dump(mode="json"))
        user_content.append(body.audio_input.model_dump(mode="json"))

    # Initialize history for this session if it doesn't exist
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    # Append to history, but note the change to a LIST of dicts for 'content'
    chat_sessions[session_id].append({"role": "user", "content": user_content})

    # Create the generator for streaming
    async def generate():
        ai_reasoning_content = ""
        ai_response_content = ""

        # stream=True will always return this CustomStreamWrapper
        stream: CustomStreamWrapper = await acompletion(
            model=MODEL, messages=chat_sessions[session_id], stream=True
        )  # type: ignore

        async for chunk in stream:
            delta = chunk.choices[0].delta

            # Safely extract parts
            reasoning = delta.get("reasoning_content", "") or ""
            content = delta.get("content", "") or ""

            # Accumulate for history
            ai_reasoning_content += reasoning
            ai_response_content += content

            # Yield for the typing effect instead of waiting for the full response
            payload = {"reasoning": reasoning, "content": content, "done": False}

            # Apparently SSE requires this format: "data: <payload>\n\n"
            yield f"data: {json.dumps(payload)}\n\n"

        # Save to history AFTER the stream is finished
        # Note: If you want to store reasoning, add it to the message schema
        chat_sessions[session_id].append(
            {"role": "assistant", "content": ai_response_content}
        )

        # Send final signal
        yield f"data: {json.dumps({'done': True})}\n\n"

    # Simple history trimming
    if len(chat_sessions[session_id]) > 20:
        # Keep system prompt (index 0) and last 19 messages
        chat_sessions[session_id] = [chat_sessions[session_id][0]] + chat_sessions[
            session_id
        ][-19:]

    return StreamingResponse(generate(), media_type="text/event-stream")


# Note: This should be for development purposes only. In production, this will use Gunicorn with Uvicorn workers.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
