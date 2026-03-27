// Configuration
const IGNORED_EXTENSIONS = ['.jpg', '.png', '.gif', '.css', '.js', '.woff2', '.svg'];
const API_INGEST_ENDPOINT = "http://localhost:8000/api/recon/ingest";
const WS_ENDPOINT = "ws://localhost:8000/stream?client_type=spy";

let socket = null;

function connectWebSocket() {
    socket = new WebSocket(WS_ENDPOINT);

    socket.onopen = () => {
        console.log("Spy: Connected to Backend Stream");
        // Keep alive / Heartbeat could go here
    };

    socket.onclose = () => {
        console.log("Spy: Disconnected. Retrying in 5s...");
        setTimeout(connectWebSocket, 5000);
    };

    socket.onerror = (err) => {
        console.error("Spy: WS Error", err);
        socket.close();
    };
}

// Start Connection
connectWebSocket();

// Helper to check extensions
function shouldIgnore(url) {
    try {
        const u = new URL(url);
        return IGNORED_EXTENSIONS.some(ext => u.pathname.endsWith(ext));
    } catch (e) {
        return false;
    }
}

// We use onBeforeSendHeaders to capture the request headers
chrome.webRequest.onBeforeSendHeaders.addListener(
    function (details) {
        // FILTER 1: Method Check (Ignore OPTIONS, keep others like GET/POST/PUT)
        if (details.method === "OPTIONS") return;

        // FILTER 2: Extension Check
        if (shouldIgnore(details.url)) return;

        // Extract Headers
        const headers = {};
        if (details.requestHeaders) {
            details.requestHeaders.forEach(h => {
                headers[h.name] = h.value;
            });
        }

        // PREPARE PAYLOAD
        const payload = {
            url: details.url,
            method: details.method,
            headers: headers,
            timestamp: Date.now() / 1000 // Send as float seconds for Python-friendly timestamp
        };

        // RELAY TO ENGINE (Fire and Forget via FETCH for simplicity)
        fetch(API_INGEST_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        }).then(res => {
            if (res.ok) console.log("Spy: Sent", details.url);
        }).catch(err => console.log("Engine Offline", err));
    },
    { urls: ["<all_urls>"] },
    ["requestHeaders", "extraHeaders"]
);
