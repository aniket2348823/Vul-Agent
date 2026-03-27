import { useEffect, useState } from "react";

const MAX_ROWS = 400;

export default function LiveMonitor() {
  const [events, setEvents] = useState([]);

  useEffect(() => {
    let reconnectTimer = null;
    let ws = null;
    let eventBuffer = [];

    const connectWs = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const backendHost = window.location.hostname === "localhost" ? "localhost:8000" : "127.0.0.1:8000";
      const wsUrl = `${protocol}//${backendHost}/stream?client_type=ui`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data);
          
          // Handle single event or raw event
          const rawEvents = data.type === "BATCH" ? data.payload : [data];
          
          rawEvents.forEach(e => {
            // Unwrap payload if it's a specific event type
            if (["LIVE_THREAT_LOG", "RECON_PACKET", "LIVE_REQUEST", "LIVE_ATTACK_FEED"].includes(e.type)) {
              eventBuffer.push(e.payload);
            } else if (e.timestamp && e.url) {
              // Already raw format
              eventBuffer.push(e);
            }
          });
        } catch (e) {
          console.error("Invalid WS message", e);
        }
      };

      ws.onclose = () => {
        console.log("LiveMonitor: WS closed. Reconnecting in 3s...");
        reconnectTimer = setTimeout(connectWs, 3000);
      };

      ws.onerror = (err) => {
        console.error("LiveMonitor: WS error", err);
      };
    };

    connectWs();

    // Render Throttling for UI Performance
    const interval = setInterval(() => {
      if (eventBuffer.length > 0) {
        setEvents((prev) => {
          let updated = [...prev, ...eventBuffer];
          eventBuffer = []; // clear buffer

          if (updated.length > MAX_ROWS) {
             // Keep the latest MAX_ROWS
             updated = updated.slice(updated.length - MAX_ROWS);
          }
          return updated;
        });
      }
    }, 50); // 20 FPS

    return () => {
      clearTimeout(reconnectTimer);
      clearInterval(interval);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, []);

  function getSeverityColor(e) {
    const sev = (e.severity || "").toUpperCase();
    if (sev === "CRITICAL") return "#ff4444";
    if (sev === "HIGH") return "#ff8800";
    if (e.anomaly) return "#ff4444";
    if (e.status >= 400) return "#ffbb33";
    if (sev === "MEDIUM") return "#ffbb33";
    if (sev === "INFO" || sev === "LOW") return "#00C851";
    return "#00C851";
  }

  function getSeverityIcon(e) {
    const sev = (e.severity || "").toUpperCase();
    if (sev === "CRITICAL" || e.anomaly) return "🔴";
    if (sev === "HIGH") return "🟠";
    if (sev === "MEDIUM" || (e.status && e.status >= 400)) return "🟡";
    return "🟢";
  }

  return (
    <div className="live-monitor-container" style={{ 
      background: "rgba(0,0,0,0.4)", 
      border: "1px solid rgba(255,255,255,0.08)", 
      borderRadius: "12px", 
      padding: "0",
      fontFamily: "'Space Grotesk', monospace",
      color: "#ddd",
      overflow: "hidden"
    }}>
      <div style={{ 
        padding: "12px 16px", 
        borderBottom: "1px solid rgba(255,255,255,0.08)", 
        display: "flex", 
        justifyContent: "space-between", 
        alignItems: "center",
        background: "rgba(0,0,0,0.3)"
      }}>
        <h3 style={{ margin: 0, color: "#fff", fontSize: "13px", fontWeight: 500, display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ width: "8px", height: "8px", background: "#00C851", borderRadius: "50%", display: "inline-block", boxShadow: "0 0 8px rgba(0,200,81,0.6)", animation: "pulse 2s infinite" }}></span>
          LIVE REQUEST STREAM
        </h3>
        <span style={{ fontSize: "11px", color: "#888", fontFamily: "monospace" }}>
          {events.length > 0 ? `Showing ${events.length} / ${MAX_ROWS} max` : "Waiting for traffic..."}
        </span>
      </div>
      <div style={{ height: "350px", overflowY: "auto", overflowX: "hidden" }}>
        <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse", fontSize: "12px" }}>
          <thead>
            <tr style={{ color: "#666", borderBottom: "1px solid rgba(255,255,255,0.05)", fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              <th style={{ padding: "8px 12px", width: "90px" }}>Time</th>
              <th style={{ padding: "8px 8px", width: "55px" }}>Method</th>
              <th style={{ padding: "8px 8px" }}>Endpoint</th>
              <th style={{ padding: "8px 8px", width: "70px" }}>Status</th>
              <th style={{ padding: "8px 12px" }}>Result</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, i) => (
              <tr key={i} style={{ color: getSeverityColor(e), borderBottom: "1px solid rgba(255,255,255,0.03)", transition: "background 0.15s" }}
                  onMouseEnter={(ev) => ev.currentTarget.style.background = "rgba(255,255,255,0.03)"}
                  onMouseLeave={(ev) => ev.currentTarget.style.background = "transparent"}
              >
                <td style={{ padding: "5px 12px", fontFamily: "monospace", fontSize: "11px", opacity: 0.7 }}>[{e.timestamp}]</td>
                <td style={{ padding: "5px 8px", fontWeight: 600, fontSize: "11px" }}>{e.method || e.action || "GET"}</td>
                <td style={{ padding: "5px 8px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "250px", fontSize: "11px" }}>{e.endpoint || e.url || "N/A"}</td>
                <td style={{ padding: "5px 8px", fontSize: "11px" }}>{e.status || "-"}</td>
                <td style={{ padding: "5px 12px", fontSize: "11px" }}>
                  {getSeverityIcon(e)}{" "}
                  {e.result || e.threat_type || e.arsenal || "OK"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {events.length === 0 && <div style={{textAlign: "center", color: "#444", marginTop: "60px", fontSize: "13px"}}>
          <span className="material-symbols-outlined" style={{fontSize: "32px", display: "block", marginBottom: "8px", opacity: 0.3}}>monitoring</span>
          Waiting for live traffic...
        </div>}
      </div>
    </div>
  );
}
