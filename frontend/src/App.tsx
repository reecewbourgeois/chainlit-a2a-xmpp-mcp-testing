import { useEffect, useRef, useState } from "react";
import { Flexbox } from "./shared/Layout";

import styles from "./App.module.scss";

const API_URL = "http://localhost:5000";

// Define the shape of our message
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  reasoning: string;
}

// Define the shape of the SSE JSON chunk
interface StreamResponse {
  reasoning?: string;
  content?: string;
  done?: boolean;
}

interface ImageInput {
  type: "image_url";
  image_url: { url: string };
}

interface AudioInput {
  type: "input_audio";
  input_audio: { data: string; format: string };
}

interface ChatInput {
  message: string;
  vision_input: ImageInput | null;
  audio_input: AudioInput | null;
}

interface SupportedInput {
  audio_input: boolean;
  vision_input: boolean;
}

export function App() {
  const [supportedInput, setSupportedInput] = useState<SupportedInput>({
    audio_input: false,
    vision_input: false,
  });

  useEffect(() => {
    // Fetch model capabilities on mount
    const fetchCapabilities = async () => {
      try {
        const res = await fetch(`${API_URL}/supported_inputs`);
        const data = await res.json();
        setSupportedInput(data);
      } catch (error) {
        console.error("Error fetching model capabilities:", error);
      }
    };

    fetchCapabilities();
  }, []);

  return (
    <Flexbox
      style={{
        width: "100%",
        height: "100%",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <ChatWindow supportedInput={supportedInput} />
    </Flexbox>
  );
}

const ChatWindow = ({ supportedInput }: { supportedInput: SupportedInput }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [selectedImageOrAudioFile, setSelectedImageOrAudioFile] = useState<
    ImageInput | AudioInput | null
  >(null);
  const imageOrAudioFileInputRef = useRef<HTMLInputElement>(null);

  let acceptedFileTypes = "";
  if (supportedInput.vision_input) acceptedFileTypes += "image/*,";
  if (supportedInput.audio_input) acceptedFileTypes += "audio/*,";

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (error) => reject(error);
    });
  };

  const handleAudioOrImageFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];

    const base64 = await fileToBase64(file);

    // Most models don't support audio input, but it is supported in case there is a model that does
    if (file.type.startsWith("audio/")) {
      // alert("Audio upload is not supported in this demo. Please upload an image.");
      setSelectedImageOrAudioFile({
        type: "input_audio",
        input_audio: { data: base64, format: file.type.split("/")[1] || "wav" },
      });
      return;
    }

    if (file.type.startsWith("image/")) {
      setSelectedImageOrAudioFile({
        type: "image_url",
        image_url: { url: base64 },
      });
      return;
    }
  };

  const sendMessage = async () => {
    if (!input.trim() && !selectedImageOrAudioFile) return;

    // 1. Add user message
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      reasoning: "",
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSelectedImageOrAudioFile(null); // Clear image after sending
    if (imageOrAudioFileInputRef.current) imageOrAudioFileInputRef.current.value = "";

    // 2. Add an empty placeholder for the assistant response
    const assistantMsgId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      { id: assistantMsgId, role: "assistant", content: "", reasoning: "" },
    ]);

    try {
      const body: ChatInput = {
        message: input,
        vision_input:
          selectedImageOrAudioFile && selectedImageOrAudioFile.type === "image_url"
            ? (selectedImageOrAudioFile as ImageInput)
            : null,
        audio_input:
          selectedImageOrAudioFile && selectedImageOrAudioFile.type === "input_audio"
            ? (selectedImageOrAudioFile as AudioInput)
            : null,
      };

      const response = await fetch(`${API_URL}/chat/my-session-id`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonText = line.replace("data: ", "");
            if (jsonText === "[DONE]") continue;

            const data: StreamResponse = JSON.parse(jsonText);

            if (data.done) continue;

            // 3. Update the specific assistant message being generated
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMsgId
                  ? {
                      ...msg,
                      reasoning: msg.reasoning + (data.reasoning || ""),
                      content: msg.content + (data.content || ""),
                    }
                  : msg,
              ),
            );
          }
        }
      }
    } catch (e) {
      console.error("Stream error:", e);
    }
  };

  return (
    <div className={styles.chatWindow}>
      {messages.map((msg) => (
        <div key={msg.id}>
          {msg.role === "assistant" && msg.reasoning && (
            <details>
              <summary>Show Reasoning</summary>
              <pre className={styles.message}>{msg.reasoning}</pre>
            </details>
          )}
          <p className={styles.message}>{msg.content}</p>
        </div>
      ))}

      {/* Image Preview Thumbnail */}
      {selectedImageOrAudioFile && (
        <Flexbox className="preview">
          <div>File Uploaded</div>
          <button onClick={() => setSelectedImageOrAudioFile(null)}>X</button>
        </Flexbox>
      )}

      {/* Hidden file input */}
      <input
        type="file"
        ref={imageOrAudioFileInputRef}
        onChange={handleAudioOrImageFileChange}
        accept={acceptedFileTypes}
        style={{ display: "none" }}
      />
      {/* Image Upload Button */}
      <button
        onClick={() => imageOrAudioFileInputRef.current?.click()}
        disabled={acceptedFileTypes.length === 0}
      >
        Upload File
      </button>

      {/* Text Input */}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && sendMessage()}
      />

      <button onClick={sendMessage}>Send</button>
    </div>
  );
};
