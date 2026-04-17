import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function App() {
  const [health, setHealth] = useState("checking...");

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then((d) => setHealth(d.status ?? "unknown"))
      .catch(() => setHealth("unreachable"));
  }, []);

  return (
    <main
      style={{
        fontFamily: "system-ui, -apple-system, sans-serif",
        maxWidth: 720,
        margin: "80px auto",
        padding: "0 20px",
        color: "#0F172A",
      }}
    >
      <h1 style={{ fontSize: 36, letterSpacing: "-0.02em" }}>
        <span style={{ color: "#0F172A" }}>Chart</span>
        <span style={{ color: "#0B6E79" }}>Nav</span>{" "}
        <span style={{ fontSize: 16, color: "#64748B" }}>Platform</span>
      </h1>
      <p style={{ color: "#475569" }}>
        Ophthalmology-first clinical workflow platform. This is the starter web app.
      </p>
      <p>
        API status:{" "}
        <code style={{ background: "#F1F5F9", padding: "2px 6px", borderRadius: 4 }}>
          {health}
        </code>
      </p>
      <p style={{ color: "#94A3B8", fontSize: 13 }}>API: {API_URL}</p>
    </main>
  );
}
