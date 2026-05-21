from typing import List
from ag_ui.core import Message


def convert_ag_ui_messages_to_openai_format(messages: List[Message]):
    openai_messages = []

    for msg in messages:
        if msg.role in ["user", "system", "assistant"]:
            if isinstance(msg.content, str):
                openai_messages.append({"role": msg.role, "content": msg.content})
            elif isinstance(msg.content, list):
                content_parts = []
                for part in msg.content:
                    # 1. Convert the Pydantic object to a standard Python dict
                    part_dict = part.model_dump()  # Pydantic v2
                    part_type = part_dict.get("type")

                    # 2. Map types to standard OpenAI multimodal format
                    if part_type == "text":
                        # Translate 'content' from React TextPart to 'text' for OpenAI
                        text_val = part_dict.get("content") or ""
                        content_parts.append({"type": "text", "text": text_val})

                    elif part_type in ["image", "image_url"]:
                        source = part_dict.get("source") or {}
                        if source.get("type"):
                            content_parts.append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": source.get("value", ""),
                                        "format": source.get("mimeType", "image/jpeg"),
                                    },
                                }
                            )

                    elif part_type in ["audio", "input_audio"]:
                        audio_data = part_dict.get("source") or {}
                        audio_format = audio_data.get("mimeType") or "audio/wav"
                        audio_format = audio_format.replace(
                            "audio/", ""
                        )  # e.g., "wav", "mp3"

                        if audio_data.get("type"):
                            content_parts.append(
                                {
                                    "type": "input_audio",
                                    "input_audio": {
                                        "data": audio_data,
                                        "format": audio_format,
                                    },
                                }
                            )
                    else:
                        # Pass-through other custom formats as a dictionary
                        content_parts.append(part_dict)

                openai_messages.append({"role": msg.role, "content": content_parts})

    return openai_messages
