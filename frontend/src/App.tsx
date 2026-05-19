import { useRef, useState } from "react";
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

export function App() {
  return (
    <Flexbox
      style={{
        width: "100%",
        height: "100%",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <ChatWindow />
    </Flexbox>
  );
}

const ChatWindow = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (error) => reject(error);
    });
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const base64 = await fileToBase64(e.target.files[0]);
      setSelectedImage(base64);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() && !selectedImage) return;

    // 1. Add user message
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      reasoning: "",
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSelectedImage(null); // Clear image after sending
    if (fileInputRef.current) fileInputRef.current.value = "";

    // 2. Add an empty placeholder for the assistant response
    const assistantMsgId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      { id: assistantMsgId, role: "assistant", content: "", reasoning: "" },
    ]);

    try {
      const response = await fetch(`${API_URL}/chat/my-session-id`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input, image_url: selectedImage }),
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
      {selectedImage && (
        <div className="preview">
          <img src={selectedImage} alt="Preview" style={{ width: "50px" }} />
          <button onClick={() => setSelectedImage(null)}>X</button>
        </div>
      )}

      {/* Hidden file input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/*"
        style={{ display: "none" }}
      />
      {/* Image Upload Button */}
      <button onClick={() => fileInputRef.current?.click()}>Upload Image</button>

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
