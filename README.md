# 🚀 Antigravity Agents

![UI Concept](https://img.shields.io/badge/Aesthetics-Glassmorphism-purple?style=flat-square) 
![Scalability](https://img.shields.io/badge/Scale-1000%2B%20RPS-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)
![React](https://img.shields.io/badge/React-Vite-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/Python-FastAPI-teal?style=flat-square)

**Antigravity Agents** is an advanced, AI-driven cybersecurity orchestration platform. It features a stunning, real-time dashboard that visualizes high-frequency threat intelligence, payload interception, and autonomous vulnerability scanning at scale.

## ✨ Key Features

- **Live Threat Monitoring:** A high-performance, real-time WebSocket architecture capable of rendering up to 1,000 Requests Per Second (RPS) seamlessly in the browser.
- **Hive AI Orchestrator:** An autonomous, multi-agent artificial intelligence system (**Alpha** for recon, **Beta** for heavy mutation, **Sigma** for payloads) simulating an entirely automated threat ecosystem.
- **Adaptive Telemetry:** Intelligent server-side load balancing ensures that critical security anomalies (SQLi, XSS, Leaks) are always displayed natively, while gracefully handling massive traffic spikes to prevent browser crashes.
- **Resilient Connectivity:** Auto-reconnecting WebSockets ensure the UI automatically recovers from connection drops or backend restarts without losing its state.
- **Forensic Reporting:** Automated, AI-generated intelligence briefings produced seamlessly upon scan completion.

## 🛠️ Architecture

- **Frontend:** React, Vite, Tailwind CSS, Framer Motion
- **Backend:** Python, FastAPI, Uvicorn, Asyncio, WebSockets
- **AI Engine:** Cortex Engine (integrated with locally hosted neural models)

---

## 🚀 Getting Started

Ensure you have **Node.js** and **Python 3.10+** installed on your system.

### 1. Initialize the Backend
```bash
# Clone the repository
git clone https://github.com/sgupta-100/ANTIGRAVITY-AGENTS.git
cd ANTIGRAVITY-AGENTS

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install required dependencies
pip install -r requirements.txt

# Start the AI Engine and WebSocket server
set PYTHONPATH=.
python -m backend.main
```

### 2. Initialize the Frontend
```bash
# Open a new terminal session in the project root
npm install
npm run dev
```

### 3. Launch the System
Navigate to `http://localhost:5173` in your web browser. From the dashboard, you can trigger active scans and watch as the Hive Agents dismantle and dissect incoming targets in real-time.
