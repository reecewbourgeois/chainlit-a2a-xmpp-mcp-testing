import uuid
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    ReasoningMessageStartEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from litellm import CustomStreamWrapper, acompletion

from app.helpers import convert_ag_ui_messages_to_openai_format


MODEL = "ollama_chat/gemma4:e2b"  # TODO: Env

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Env
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_main():
    return {"message": "Hello World from main app"}


@app.get("/supported_inputs")
async def supported_inputs():
    # Was initially going to make this dynamic using litellm's functions, but it they are incorrect
    return {
        "audio_input": False,
        "vision_input": True,
    }


@app.post("/chat")
async def chat(run_input: RunAgentInput, request: Request):
    accept_header = request.headers.get("accept") or ""
    encoder = EventEncoder(accept=accept_header)

    async def event_generator():
        # Send run started event
        yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=run_input.thread_id,
                run_id=run_input.run_id,
            )
        )

        # Convert AG-UI messages to OpenAI messages format
        openai_messages = convert_ag_ui_messages_to_openai_format(run_input.messages)

        # stream=True will always return this CustomStreamWrapper
        stream: CustomStreamWrapper = await acompletion(
            model=MODEL, messages=openai_messages, stream=True
        )  # type: ignore

        # Generate a message ID for the assistant's response
        message_id = str(uuid.uuid4())

        # Send reasoning start event
        yield encoder.encode(
            ReasoningMessageStartEvent(
                type=EventType.REASONING_MESSAGE_START,
                message_id=message_id,
                role="reasoning",
            )
        )

        # Send text message start event
        yield encoder.encode(
            TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant",
            )
        )

        # Process the streaming response and send content events
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta:
                delta = chunk.choices[0].delta

                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_content = delta.reasoning_content
                    yield encoder.encode(
                        ReasoningMessageContentEvent(
                            type=EventType.REASONING_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=reasoning_content,
                        )
                    )
                elif hasattr(delta, "content") and delta.content:
                    content = delta.content
                    yield encoder.encode(
                        TextMessageContentEvent(
                            type=EventType.TEXT_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=content,
                        )
                    )

        # Send reasoning end event
        yield encoder.encode(
            ReasoningMessageEndEvent(
                type=EventType.REASONING_MESSAGE_END,
                message_id=message_id,
            )
        )

        # Send text message end event
        yield encoder.encode(
            TextMessageEndEvent(type=EventType.TEXT_MESSAGE_END, message_id=message_id)
        )

        # Send run finished event
        yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=run_input.thread_id,
                run_id=run_input.run_id,
            )
        )

    return StreamingResponse(event_generator(), media_type=encoder.get_content_type())


# Note: This should be for development purposes only. In production, this will use Gunicorn with Uvicorn workers.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
