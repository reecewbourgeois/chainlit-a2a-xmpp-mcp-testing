import { useRef, useState } from "react";
import { Flexbox } from "./shared/ui/Layout";

import styles from "./App.module.scss";
import type { SupportedInput } from "./shared/api/schemas";
import { API } from "./shared/api/api";
import { fetchServerSentEvents, useChat } from "@tanstack/ai-react";
import type { ContentPart, TextPart, AudioPart, ImagePart } from "@tanstack/ai";

export function App() {
  const { data: supportedInput, isFetching, error } = API.useGetSupportedInputs();

  return (
    <Flexbox
      style={{
        width: "100%",
        height: "100%",
        justifyContent: "center",
        alignItems: "center",
        padding: "1rem",
      }}
    >
      {isFetching ? (
        <div>Loading...</div>
      ) : error || supportedInput === undefined ? (
        <div>{error?.message || "Error loading supported inputs"}</div>
      ) : (
        <ChatWindow supportedInput={supportedInput} />
      )}
    </Flexbox>
  );
}

const ChatWindow = ({ supportedInput }: { supportedInput: SupportedInput }) => {
  const [input, setInput] = useState("");
  const [selectedImageOrAudioFile, setSelectedImageOrAudioFile] = useState<
    ImagePart | AudioPart | null
  >(null);
  const imageOrAudioFileInputRef = useRef<HTMLInputElement>(null);

  const { isLoading, messages, sendMessage } = useChat({
    connection: fetchServerSentEvents(`${API.API_URL}/chat`),
  });

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
      setSelectedImageOrAudioFile({
        type: "audio",
        source: {
          type: "data",
          mimeType: file.type,
          value: base64,
        },
      });
      return;
    }

    if (file.type.startsWith("image/")) {
      setSelectedImageOrAudioFile({
        type: "image",
        source: {
          type: "data",
          mimeType: file.type,
          value: base64,
        },
      });
      return;
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim() && !selectedImageOrAudioFile) return;

    const content: ContentPart[] = [];

    content.push({
      type: "text",
      content: input,
    } satisfies TextPart);

    if (selectedImageOrAudioFile && selectedImageOrAudioFile.type === "image") {
      content.push(selectedImageOrAudioFile);
    }

    if (selectedImageOrAudioFile && selectedImageOrAudioFile.type === "audio") {
      content.push(selectedImageOrAudioFile);
    }

    sendMessage({
      content,
    });

    setInput("");
    setSelectedImageOrAudioFile(null); // Clear image after sending
    if (imageOrAudioFileInputRef.current) imageOrAudioFileInputRef.current.value = "";
  };

  return (
    <Flexbox className={styles.chatWindow}>
      <Flexbox style={{ flexDirection: "column", alignItems: "flex-start" }}>
        {messages.map((message) => (
          <div
            key={message.id}
            className={message.role === "assistant" ? styles.assistantMessage : styles.userMessage}
          >
            <div className={styles.messageHeader}>
              {message.role === "assistant" ? "Assistant" : "You"}
            </div>

            <div>
              {message.parts.map((part, idx) => {
                if (part.type === "thinking") {
                  return (
                    <details key={idx}>
                      <summary>💭 Thinking</summary>
                      <pre className={styles.thinkingMessage}>{part.content}</pre>
                    </details>
                  );
                }

                console.log("Rendering content part:", part);

                if (part.type === "tool-call") {
                  return (
                    <details key={idx}>
                      <summary>🛠️ Tool Call: {part.name}</summary>
                      <pre className={styles.toolCallMessage}>{part.arguments}</pre>
                    </details>
                  );
                }

                if (part.type === "tool-result") {
                  return (
                    <details key={idx}>
                      <summary>🔧 Tool Result</summary>
                      <pre className={styles.toolResultMessage}>{part.content}</pre>
                    </details>
                  );
                }

                if (part.type === "text") {
                  return (
                    <div key={idx} className={styles.textMessage}>
                      {part.content}
                    </div>
                  );
                }

                if (part.type === "image") {
                  return (
                    <div key={idx} className={styles.imageMessage}>
                      <img
                        src={part.source.value}
                        alt="Uploaded content"
                        style={{ maxWidth: "200px" }}
                      />
                    </div>
                  );
                }

                console.warn("Unknown content part type:", part);

                return null;
              })}
            </div>
          </div>
        ))}

        {isLoading && <div className={styles.assistantMessage}>Assistant is typing...</div>}
      </Flexbox>

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
        onKeyDown={(e) => e.key === "Enter" && handleSendMessage()}
      />

      <button onClick={handleSendMessage}>Send</button>
    </Flexbox>
  );
};
