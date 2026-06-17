"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

type Source = {
  filename: string;
  source_type: string;
  similarity: number;
  rerank_score?: number;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  webSources?: { title?: string; url?: string }[];
};

const API_BASE_URL = "http://127.0.0.1:8001";
const SESSION_STORAGE_KEY = "regulor_session_id";

function getOrCreateSessionId() {
  if (typeof window === "undefined") return "";

  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;

  const nextId =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `regulor-${Date.now()}-${Math.random().toString(16).slice(2)}`;

  window.localStorage.setItem(SESSION_STORAGE_KEY, nextId);
  return nextId;
}

export default function HomePage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Bonjour. Je suis Regulor, votre assistant IA interne. Posez-moi une question sur vos procédures internes, la conformité réglementaire, les documents RH ou les textes officiels.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [sessionId, setSessionId] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    setSessionId(getOrCreateSessionId());
  }, []);

  const resetSession = async () => {
    const currentSessionId = sessionId || getOrCreateSessionId();

    if (currentSessionId) {
      try {
        const formData = new FormData();
        formData.append("session_id", currentSessionId);

        await fetch(`${API_BASE_URL}/chat/context/reset`, {
          method: "POST",
          body: formData,
        });
      } catch (error) {
        console.error("[FRONTEND] Erreur reset contexte :", error);
      }
    }

    window.localStorage.removeItem(SESSION_STORAGE_KEY);
    const freshSessionId = getOrCreateSessionId();
    setSessionId(freshSessionId);
    setAttachedFile(null);
    setMessages([
      {
        role: "assistant",
        content:
          "Bonjour. Je suis Regulor, votre assistant IA interne. Posez-moi une question sur vos procédures internes, la conformité réglementaire, les documents RH ou les textes officiels.",
      },
    ]);
  };

  const buildCleanHistory = (items: Message[]) => {
    return items.map((msg) => ({
      role: msg.role,
      content: msg.content,
    }));
  };

  const sendMessage = async () => {
    const currentInput = input.trim();

    if (!currentInput || loading) return;

    const userMessage: Message = {
      role: "user",
      content: attachedFile
        ? `${currentInput} [Fichier joint : ${attachedFile.name}]`
        : currentInput,
    };

    const previousMessages = [...messages];

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      let response: Response;

      if (attachedFile) {
        const formData = new FormData();

        formData.append("file", attachedFile);
        formData.append("question", currentInput);
        formData.append("session_id", sessionId || getOrCreateSessionId());
        formData.append(
          "history",
          JSON.stringify(buildCleanHistory(previousMessages)),
        );

        response = await fetch(`${API_BASE_URL}/chat/upload`, {
          method: "POST",
          body: formData,
        });

        setAttachedFile(null);
      } else {
        response = await fetch(`${API_BASE_URL}/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: currentInput,
            history: buildCleanHistory(previousMessages),
            session_id: sessionId || getOrCreateSessionId(),
          }),
        });
      }

      let data: {
        response?: string;
        sources?: Source[];
        web_sources?: { title?: string; url?: string }[];
        found?: boolean;
        session_id?: string;
        detail?: string;
        error?: string;
      };

      try {
        data = await response.json();
      } catch {
        throw new Error("Le backend a répondu, mais pas avec du JSON valide.");
      }

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || `Erreur backend HTTP ${response.status}`,
        );
      }

      const assistantMessage: Message = {
        role: "assistant",
        content:
          data.response ||
          "Je n'ai pas reçu de réponse exploitable du backend.",
        sources: data.sources || [],
        webSources: data.web_sources || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("[FRONTEND] Erreur chat :", error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            error instanceof Error
              ? `Erreur : ${error.message}`
              : "Erreur : impossible de contacter le backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-zinc-950 via-slate-950 to-black text-white flex">
      <aside className="w-[260px] border-r border-white/10 bg-white/5 backdrop-blur-xl p-6 flex flex-col justify-between">
        <div>
          <div className="mb-10">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">
              Regulor
            </h1>
            <p className="text-zinc-400 mt-2 text-sm">AI Compliance Platform</p>
          </div>

          <nav className="space-y-3">
            <button className="w-full text-left px-4 py-3 rounded-xl bg-cyan-500/10 border border-cyan-400/20 hover:bg-cyan-500/20 transition">
              Chat
            </button>
            <button
              onClick={() => router.push("/documents")}
              className="w-full text-left px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 transition"
              type="button"
            >
              Documents
            </button>
            <button className="w-full text-left px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 transition" type="button">
              Alerts
            </button>
            <button
              onClick={() => router.push("/admin")}
              className="w-full text-left px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 transition"
              type="button"
            >
              Admin
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <span className="h-2 w-2 rounded-full bg-green-400 shadow-[0_0_8px_rgba(0,255,120,0.8)]" />
          Connected locally
        </div>
      </aside>

      <section className="flex-1 flex items-center justify-center p-10">
        <div className="w-full max-w-5xl h-[85vh] rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-[0_0_60px_rgba(0,180,255,0.08)] flex flex-col overflow-hidden">
          <div className="border-b border-white/10 px-8 py-5 flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">AI Internal Assistant</h2>
              <p className="text-sm text-zinc-400 mt-1">
                Ask questions about internal procedures and regulations
              </p>
            </div>
            <div className="h-3 w-3 rounded-full bg-green-400 shadow-[0_0_15px_rgba(0,255,120,0.8)]" />
          </div>

          <div className="flex-1 overflow-y-auto p-8 space-y-6">
            {messages.map((msg, index) => (
              <div key={index}>
                <div
                  className={`max-w-2xl rounded-2xl p-5 ${
                    msg.role === "assistant"
                      ? "bg-cyan-500/10 border border-cyan-400/20"
                      : "ml-auto bg-white/10 border border-white/10"
                  }`}
                >
                  <p className="leading-7 text-zinc-100 whitespace-pre-wrap">
                    {msg.content}
                  </p>
                </div>

                {msg.role === "assistant" &&
                  msg.sources &&
                  msg.sources.length > 0 && (
                    <div className="max-w-2xl mt-2 flex flex-wrap gap-2">
                      {msg.sources.map((source, i) => (
                        <span
                          key={`${source.filename}-${i}`}
                          className="text-xs px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/20 text-blue-300"
                        >
                          SOURCE {i + 1} — {source.filename} (
                          {Math.round(source.similarity * 100)}% pertinent)
                        </span>
                      ))}
                    </div>
                  )}

                {msg.role === "assistant" &&
                  msg.webSources &&
                  msg.webSources.length > 0 && (
                    <div className="max-w-2xl mt-2 flex flex-wrap gap-2">
                      {msg.webSources.map((source, i) => (
                        <span
                          key={`${source.title || "web"}-${i}`}
                          className="text-xs px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-400/20 text-emerald-300"
                        >
                          WEB {i + 1} — {source.title || source.url || "source web"}
                        </span>
                      ))}
                    </div>
                  )}
              </div>
            ))}

            {loading && (
              <div className="max-w-2xl rounded-2xl p-5 bg-cyan-500/10 border border-cyan-400/20">
                <p className="text-zinc-400 animate-pulse">
                  Regulor analyse les documents...
                </p>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="border-t border-white/10 p-6">
            {attachedFile && (
              <div className="mb-3 flex items-center gap-2 text-sm text-cyan-300">
                <span className="px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-400/20">
                  {attachedFile.name}
                </span>
                <button
                  onClick={() => setAttachedFile(null)}
                  className="text-zinc-500 hover:text-red-400 transition"
                >
                  Retirer
                </button>
              </div>
            )}

            <div className="mb-3 text-xs text-zinc-500">
              {sessionId
                ? "Le contexte d’un fichier uploadé peut être réutilisé dans cette session."
                : "Initialisation de la session en cours..."}
            </div>

            <div className="mb-4 flex flex-wrap gap-3">
              <button
                onClick={resetSession}
                type="button"
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-zinc-200 hover:bg-white/10 transition"
              >
                Nouveau sujet
              </button>
              {attachedFile && (
                <button
                  onClick={resetSession}
                  type="button"
                  className="rounded-xl border border-cyan-400/20 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200 hover:bg-cyan-500/20 transition"
                >
                  Sortir du contexte du fichier
                </button>
              )}
            </div>

            <div className="flex gap-4">
              <input
                type="file"
                ref={fileInputRef}
                accept=".pdf,.png,.jpg,.jpeg"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];

                  if (file) {
                    setAttachedFile(file);
                  }

                  event.target.value = "";
                }}
              />

              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-4 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition text-zinc-400"
                title="Joindre un fichier"
                type="button"
              >
                +
              </button>

              <input
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Posez votre question..."
                className="flex-1 bg-black/30 border border-white/10 rounded-2xl px-5 py-4 outline-none focus:border-cyan-400/40 transition"
              />

              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="px-6 rounded-2xl bg-gradient-to-r from-cyan-400 to-blue-500 font-semibold text-black hover:scale-[1.02] transition disabled:opacity-50"
                type="button"
              >
                {loading ? "..." : "Envoyer"}
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
