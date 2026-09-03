"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { Send, ShieldAlert, PhoneCall, Heart, Sparkles, CheckCircle2, EyeOff } from "lucide-react";

interface Message {
  sender: "user" | "bot";
  text: string;
}

interface Resource {
  name: string;
  contact: string;
}

interface MoodEntry {
  score: number;
  emoji: string;
  label: string;
  trigger: string;
  timestamp: string;
}

const MOOD_OPTIONS = [
  { score: 1, emoji: "😞", label: "Very Low" },
  { score: 2, emoji: "🙁", label: "Struggling" },
  { score: 3, emoji: "😐", label: "Okay" },
  { score: 4, emoji: "🙂", label: "Good" },
  { score: 5, emoji: "😊", label: "Thriving" },
];

const COMMON_TRIGGERS = ["Exams", "Sleep", "Friends", "Deadlines", "Burnout"];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    { sender: "bot", text: "Hello friend. I'm MindEase, an anonymous and private space. How are you feeling today?" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isMasked, setIsMasked] = useState(false);

  const [crisisAlert, setCrisisAlert] = useState<{ active: boolean; text: string; resources: Resource[] }>({
    active: false,
    text: "",
    resources: []
  });

  const [selectedMood, setSelectedMood] = useState<typeof MOOD_OPTIONS[0] | null>(null);
  const [selectedTrigger, setSelectedTrigger] = useState<string>("");
  const [moodSubmitted, setMoodSubmitted] = useState<boolean>(false);
  const [recentLogs, setRecentLogs] = useState<MoodEntry[]>([]);

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Instant Quick Exit handler
  const triggerQuickExit = useCallback(() => {
    setIsMasked(true);
    setMessages([]);
    setInput("");
    // Replace URL history so back button cannot restore the chat
    window.location.replace("https://www.google.com");
  }, []);

  // Global keydown listener for Esc or Alt+Q
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" || (e.altKey && e.key.toLowerCase() === "q")) {
        e.preventDefault();
        triggerQuickExit();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [triggerQuickExit]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleMoodSubmit = () => {
    if (!selectedMood) return;

    const entry: MoodEntry = {
      score: selectedMood.score,
      emoji: selectedMood.emoji,
      label: selectedMood.label,
      trigger: selectedTrigger || "General",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setRecentLogs((prev) => [entry, ...prev.slice(0, 4)]);
    setMoodSubmitted(true);

    const promptMessage = `I just logged my mood as ${selectedMood.label} (${selectedMood.emoji}) due to ${entry.trigger}.`;
    setMessages((prev) => [...prev, { sender: "user", text: promptMessage }]);

    fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: promptMessage })
    })
      .then(async (res) => {
        const reader = res.body?.getReader();
        const decoder = new TextDecoder();
        let botResponse = "";

        setMessages((prev) => [...prev, { sender: "bot", text: "" }]);

        while (reader) {
          const { value, done } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const parsed = JSON.parse(line.replace("data: ", ""));
                botResponse += parsed.token;
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1].text = botResponse;
                  return updated;
                });
              } catch (err) {}
            }
          }
        }
      })
      .catch(() => {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: "Thank you for checking in with yourself. Acknowledging how you feel is always the first step." }
        ]);
      });
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userText = input;
    setInput("");
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText })
      });

      if (!res.ok) throw new Error("Network error");

      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const data = await res.json();
        if (data.is_crisis) {
          setCrisisAlert({ active: true, text: data.response, resources: data.resources });
          setMessages((prev) => [...prev, { sender: "bot", text: data.response }]);
          setLoading(false);
          return;
        }
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let botResponse = "";

      setMessages((prev) => [...prev, { sender: "bot", text: "" }]);

      while (reader) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const parsed = JSON.parse(line.replace("data: ", ""));
              botResponse += parsed.token;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1].text = botResponse;
                return updated;
              });
            } catch (err) {}
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [...prev, { sender: "bot", text: "Take a deep breath. I ran into a connection issue, but I am still here for you." }]);
    } finally {
      setLoading(false);
    }
  };

  // Instant Blank Screen Mask to prevent visual leakage before navigation fires
  if (isMasked) {
    return (
      <main className="h-screen w-screen bg-white flex flex-col items-center justify-center font-sans text-slate-700">
        <h1 className="text-4xl font-semibold mb-3">Google</h1>
        <div className="w-80 h-10 border border-slate-300 rounded-full shadow-sm"></div>
      </main>
    );
  }

  return (
    <main className="flex h-screen bg-slate-50 text-slate-800 relative">
      {crisisAlert.active && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="max-w-md w-full rounded-2xl bg-white p-6 shadow-2xl border-t-8 border-rose-500">
            <div className="flex items-center gap-3 text-rose-600 mb-3">
              <ShieldAlert className="w-8 h-8" />
              <h2 className="text-xl font-bold">Immediate Support Available</h2>
            </div>
            <p className="text-sm text-slate-600 mb-4">{crisisAlert.text}</p>
            <div className="space-y-2 mb-6">
              {crisisAlert.resources.map((res, i) => (
                <a
                  key={i}
                  href={`tel:${res.contact}`}
                  className="flex justify-between items-center p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 font-medium hover:bg-rose-100 transition"
                >
                  <span>{res.name}</span>
                  <span className="flex items-center gap-1 font-mono font-bold">
                    <PhoneCall className="w-4 h-4" /> {res.contact}
                  </span>
                </a>
              ))}
            </div>
            <button
              onClick={() => setCrisisAlert((prev) => ({ ...prev, active: false }))}
              className="w-full py-2.5 rounded-xl bg-slate-800 text-white font-semibold hover:bg-slate-700"
            >
              Return to Chat
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-col flex-1 max-w-3xl mx-auto h-full bg-white shadow-sm border-x border-slate-200 relative">
        <header className="p-4 border-b border-slate-200 flex justify-between items-center bg-white/80 backdrop-blur sticky top-0 z-10">
          <div>
            <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              MindEase <Sparkles className="w-4 h-4 text-teal-500" />
            </h1>
            <p className="text-xs text-slate-400">Anonymous & Encrypted Student Space</p>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={triggerQuickExit}
              title="Instantly exit to Google (Press ESC)"
              className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 px-2.5 py-1.5 rounded-full font-medium flex items-center gap-1.5 transition"
            >
              <EyeOff className="w-3.5 h-3.5 text-slate-500" />
              <span>Quick Exit</span>
              <kbd className="bg-white border border-slate-300 px-1 py-0.2 text-[10px] rounded font-mono text-slate-500 shadow-2xs">ESC</kbd>
            </button>

            <button
              onClick={() => setCrisisAlert({
                active: true,
                text: "You don't need to carry heavy burdens alone. Tap to connect right now.",
                resources: [
                  {"name": "Tele-MANAS (Govt Free Hotline)", "contact": "14416"},
                  {"name": "KIRAN Mental Health Support", "contact": "1800-599-0019"}
                ]
              })}
              className="text-xs bg-rose-50 text-rose-600 border border-rose-200 px-3 py-1.5 rounded-full font-semibold hover:bg-rose-100 flex items-center gap-1"
            >
              <Heart className="w-3.5 h-3.5 fill-rose-500" /> Immediate Help
            </button>
          </div>
        </header>

        <section className="bg-slate-50 border-b border-slate-200 p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Daily Anonymous Check-In
            </span>
            {moodSubmitted && (
              <span className="text-xs text-teal-600 flex items-center gap-1 font-medium">
                <CheckCircle2 className="w-3.5 h-3.5" /> Checked In
              </span>
            )}
          </div>

          <div className="flex justify-between gap-2 mb-3">
            {MOOD_OPTIONS.map((item) => (
              <button
                key={item.score}
                onClick={() => {
                  setSelectedMood(item);
                  setMoodSubmitted(false);
                }}
                className={`flex-1 py-2 rounded-xl flex flex-col items-center justify-center text-xs transition border ${
                  selectedMood?.score === item.score
                    ? "bg-teal-50 border-teal-500 scale-105 shadow-sm"
                    : "bg-white border-slate-200 hover:bg-slate-100"
                }`}
              >
                <span className="text-xl mb-1">{item.emoji}</span>
                <span className="text-[11px] font-medium text-slate-600">{item.label}</span>
              </button>
            ))}
          </div>

          {selectedMood && !moodSubmitted && (
            <div className="flex items-center gap-2 pt-1">
              <div className="flex gap-1.5 overflow-x-auto py-1 flex-1">
                {COMMON_TRIGGERS.map((tag) => (
                  <button
                    key={tag}
                    onClick={() => setSelectedTrigger(tag)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition whitespace-nowrap ${
                      selectedTrigger === tag
                        ? "bg-slate-800 text-white border-slate-800"
                        : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
              <button
                onClick={handleMoodSubmit}
                className="text-xs bg-teal-600 hover:bg-teal-700 text-white font-semibold px-3 py-1.5 rounded-lg transition shrink-0"
              >
                Save
              </button>
            </div>
          )}

          {recentLogs.length > 0 && (
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-200/60 overflow-x-auto">
              <span className="text-[10px] text-slate-400 font-semibold uppercase">Recent:</span>
              {recentLogs.map((log, i) => (
                <span key={i} className="text-xs bg-white border border-slate-200 rounded-md px-2 py-0.5 text-slate-600 flex items-center gap-1 shrink-0">
                  <span>{log.emoji}</span>
                  <span className="font-medium text-slate-700">{log.trigger}</span>
                  <span className="text-[10px] text-slate-400">({log.timestamp})</span>
                </span>
              ))}
            </div>
          )}
        </section>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m, idx) => (
            <div key={idx} className={`flex ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  m.sender === "user"
                    ? "bg-teal-600 text-white rounded-br-none"
                    : "bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200"
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <footer className="p-4 border-t border-slate-200 bg-white">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              sendMessage();
            }}
            className="flex gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type what you are experiencing..."
              className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 text-sm"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2.5 rounded-xl flex items-center justify-center transition disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </footer>
      </div>
    </main>
  );
}
