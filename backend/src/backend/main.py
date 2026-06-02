import os
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
    ToolCallStartEvent,
    ToolCallArgsEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
    ToolCallEndEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from litellm import CustomStreamWrapper, acompletion
from sqlalchemy import text
import json

from .util.api_utils import convert_ag_ui_messages_to_openai_format
from .util.db_utils import DB_ENGINE, EMBEDDINGS, EMBEDDINGS_CONFIG_NAME


PRIMARY_MODEL = "ollama_chat/gemma4:e2b"  # TODO: Env
SUBAGENT_MODEL = "ollama_chat/qwen3:0.6b"  # TODO: Env

TOOLS = [
    {
        "type": "function",
        "function": {
            "id": "delegate_to_subagent",
            "name": "delegate_to_subagent",
            "description": "Call a specialized sub-agent for simple queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The message for the sub-agent.",
                    }
                },
                "required": ["prompt"],
            },
        },
    }
]

# Sample data for RAG
SAMPLE_DATA = [
    "Python is a high-level, interpreted programming language.",
    "FastAPI is a modern, fast (high-performance) web framework for building APIs with Python.",
    "LiteLLM is a lightweight library that allows you to call various LLM APIs using the OpenAI format.",
    "txtai is an enterprise-grade library for semantic search, RAG, and more.",
    "The AG-UI protocol is used for streaming structured events to UIs.",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    need_to_index = False
    try:
        with DB_ENGINE.connect() as conn:
            # Query default txtai document tracking table
            result = conn.execute(text("SELECT COUNT(*) FROM sections")).scalar()

            # If no results, or the config file doesn't exist, we need to index the data.
            if (
                result is None
                or result == 0
                or not os.path.exists(EMBEDDINGS_CONFIG_NAME)
            ):
                need_to_index = True
    except Exception:
        # If the table doesn't exist, we also need to index
        need_to_index = True

    if need_to_index:
        print("Seeding initial data into txtai...")
        EMBEDDINGS.index(SAMPLE_DATA)
        EMBEDDINGS.save(EMBEDDINGS_CONFIG_NAME)  # Save to database
        EMBEDDINGS.close()  # Close the connection after seeding. We don't need to keep the data in memory

    print("Loading index...")
    EMBEDDINGS.load(
        EMBEDDINGS_CONFIG_NAME
    )  # Should only initialize the database connection and not load any data into memory

    yield

    # Any extra shutdown logic here


app = FastAPI(lifespan=lifespan)

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

        # RAG Step: Extract the last user message for context retrieval
        user_query = ""
        for msg in reversed(run_input.messages):
            if msg.role == "user":
                user_query = msg.content
                break

        context_text = ""
        if user_query and EMBEDDINGS:
            # Search for top 3 relevant sentences
            # Output shape seems dependent on options used in the Embeddings contructor. With content=True and objects=True, we get a list of dicts with 'id', 'text', and 'score'.
            results: list[dict] = EMBEDDINGS.search(user_query, limit=3)  # type: ignore | The exported types from this function are horrendous and incorrect
            context_text = "\n".join([r["text"] for r in results])

        # Convert AG-UI messages to OpenAI messages format
        openai_messages = convert_ag_ui_messages_to_openai_format(run_input.messages)

        if context_text:
            # Inject context as a system message at the beginning
            rag_prompt = (
                "You are a helpful assistant. Use the following retrieved context "
                "to answer the user's question. If the context doesn't contain "
                "the answer, use your general knowledge but mention you are "
                "relying on it.\n\n"
                f"CONTEXT:\n{context_text}"
            )
            openai_messages.insert(
                len(openai_messages) - 1, {"role": "system", "content": rag_prompt}
            )

        # stream=True will always return this CustomStreamWrapper
        stream: CustomStreamWrapper = await acompletion(
            model=PRIMARY_MODEL, messages=openai_messages, stream=True, tools=TOOLS
        )  # type: ignore

        # Generate a message ID for the assistant's response
        message_id = str(uuid.uuid4())

        # Flags for events
        is_reasoning = False
        is_messaging = False

        # Helper functions for setting flags and sending events
        def start_reasoning():
            nonlocal is_reasoning
            is_reasoning = True
            return encoder.encode(
                ReasoningMessageStartEvent(
                    type=EventType.REASONING_MESSAGE_START,
                    message_id=message_id,
                    role="reasoning",
                )
            )

        def start_messaging():
            nonlocal is_messaging
            is_messaging = True
            return encoder.encode(
                TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=message_id,
                    role="assistant",
                )
            )

        def end_reasoning():
            nonlocal is_reasoning

            result = ""
            if is_reasoning:
                result = encoder.encode(
                    ReasoningMessageEndEvent(
                        type=EventType.REASONING_MESSAGE_END,
                        message_id=message_id,
                    )
                )

            is_reasoning = False
            return result

        def end_messaging():
            nonlocal is_messaging

            result = ""
            if is_messaging:
                result = encoder.encode(
                    TextMessageEndEvent(
                        type=EventType.TEXT_MESSAGE_END,
                        message_id=message_id,
                    )
                )

            is_messaging = False
            return result

        # TODO: Need to rework this to support looping in the event of a tool call
        # TODO: open_ai_messages will need to be updated with tool call results to maintain context for the main stream after tool calls
        # Process the streaming response and send content events
        async for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta:
                delta = chunk.choices[0].delta

                if delta.tool_calls is not None and len(delta.tool_calls) > 0:
                    tool_calls = delta.tool_calls

                    print(f"Received tool calls: {tool_calls}")  # ! DEBUGGING

                    for tool_call in tool_calls:
                        if tool_call.type == "function" and tool_call.function:
                            function = tool_call.function
                            tool_call_id = tool_call.id or "unknown_tool_call_id"
                            tool_call_name = function.name or "unknown_tool_call_name"

                            # Send start event
                            yield encoder.encode(
                                ToolCallStartEvent(
                                    type=EventType.TOOL_CALL_START,
                                    tool_call_id=tool_call_id,
                                    tool_call_name=tool_call_name,
                                )
                            )

                            # Send args event
                            yield encoder.encode(
                                ToolCallArgsEvent(
                                    type=EventType.TOOL_CALL_ARGS,
                                    tool_call_id=tool_call_id,
                                    delta=function.arguments,
                                )
                            )

                            sub_stream: CustomStreamWrapper = await acompletion(
                                model=SUBAGENT_MODEL,
                                messages=[
                                    {
                                        "role": "user",
                                        "content": json.loads(function.arguments).get(
                                            "prompt", ""
                                        ),  # type: ignore
                                    }
                                ],
                                stream=True,
                            )  # type: ignore

                            result = ""
                            async for sub_chunk in sub_stream:
                                if (
                                    sub_chunk.choices
                                    and len(sub_chunk.choices) > 0
                                    and sub_chunk.choices[0].delta
                                ):
                                    sub_delta = sub_chunk.choices[0].delta

                                    if (
                                        hasattr(sub_delta, "content")
                                        and sub_delta.content
                                    ):
                                        content = sub_delta.content
                                        result += content

                            # Result event
                            yield encoder.encode(
                                ToolCallResultEvent(
                                    type=EventType.TOOL_CALL_RESULT,
                                    message_id=str(uuid.uuid4()),
                                    tool_call_id=tool_call_id,
                                    content=result,
                                )
                            )

                            # End event
                            yield encoder.encode(
                                ToolCallEndEvent(
                                    type=EventType.TOOL_CALL_END,
                                    tool_call_id=tool_call_id,
                                )
                            )

                            # Add tool result to the main stream's context
                            openai_messages.append(
                                {
                                    "role": "system",
                                    "content": f"Tool call '{tool_call_name}' returned the following result: {result}",
                                }
                            )

                    continue

                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_content = delta.reasoning_content

                    # Send reasoning start event
                    if not is_reasoning:
                        yield end_messaging()
                        yield start_reasoning()

                    yield encoder.encode(
                        ReasoningMessageContentEvent(
                            type=EventType.REASONING_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=reasoning_content,
                        )
                    )

                    continue

                if hasattr(delta, "content") and delta.content:
                    content = delta.content

                    # Send text message start event
                    if not is_messaging:
                        yield end_reasoning()
                        yield start_messaging()

                    yield encoder.encode(
                        TextMessageContentEvent(
                            type=EventType.TEXT_MESSAGE_CONTENT,
                            message_id=message_id,
                            delta=content,
                        )
                    )

                    continue  # Just here for consistency, but not really needed

        # End any open events
        yield end_reasoning()
        yield end_messaging()

        # Send run finished event
        yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=run_input.thread_id,
                run_id=run_input.run_id,
            )
        )

    return StreamingResponse(event_generator(), media_type=encoder.get_content_type())


def main():
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=5000, reload=True)
