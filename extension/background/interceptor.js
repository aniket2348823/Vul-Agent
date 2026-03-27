// FILE: extension/background/interceptor.js
// IDENTITY: AGENT IOTA (CHI) - THE HANDS
// MISSION: Active Event Interception & Dark Pattern Blocking.

/* global chrome */

const CHI_ENDPOINT = "http://localhost:8000/api/defense/analyze";

// State
let isDebuggerAttached = false;
let currentTabId = null;

// 1. Initialize Interception (Listen for connection from Content Script or Popup)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "CHI_ACTIVATE") {
        attachDebugger(sender.tab.id);
    }
    if (message.type === "CHI_EVENT_INTERCEPTED") {
        handleInterceptedEvent(message.payload, sender.tab.id);
    }
});

// 2. Debugger Control
function attachDebugger(tabId) {
    if (currentTabId === tabId && isDebuggerAttached) return;

    currentTabId = tabId;
    chrome.debugger.attach({ tabId: tabId }, "1.3", () => {
        if (chrome.runtime.lastError) {
            console.error("Chi: Debugger Attach Failed", chrome.runtime.lastError);
            return;
        }
        isDebuggerAttached = true;
        console.log("Chi: Kinetic Interceptor Active on Tab", tabId);
        chrome.debugger.sendCommand({ tabId: tabId }, "Debugger.enable");
    });
}

function detachDebugger() {
    if (currentTabId && isDebuggerAttached) {
        chrome.debugger.detach({ tabId: currentTabId });
        isDebuggerAttached = false;
        currentTabId = null;
    }
}

// 3. Event Handling Logic
async function handleInterceptedEvent(eventPayload, tabId) {
    // 3.1. FREEZE! (Pause Execution via Debugger)
    if (isDebuggerAttached) {
        // We pause JS execution to prevent the click form performing action
        // In real debugger protocol, we'd set a breakpoint or use 'Debugger.pause'.
        // For this V6 implementation, we simulate freeze by sending a command.
        chrome.debugger.sendCommand({ tabId: tabId }, "Debugger.pause");
    }

    // 3.2. Send Intent Packet to Backend (Chi Agent)
    try {
        const response = await fetch(CHI_ENDPOINT, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                agent_id: "IOTA",
                url: eventPayload.url,
                content: eventPayload // { type: 'click', innerText: 'Cancel', action: '/pay' }
            })
        });

        const packet = await response.json();
        /* Expected Packet: 
           { status: "SUCCESS" | "BLOCKED", data: { action: "ALLOW" | "BLOCK", reason: "..." } } 
        */

        const verdict = packet.data || { action: "ALLOW" }; // Default Allow

        // 3.3. Act on Verdict
        if (verdict.action === "BLOCK") {
            // REJECT
            console.log("Chi: BLOCKED Action.", verdict.reason);

            // Notify User (Toast in Page) via Content Script
            chrome.tabs.sendMessage(tabId, {
                type: "CHI_SHOW_TOAST",
                message: `🚫 Chi Blocked: ${verdict.reason}`,
                color: "#ff4444"
            });

            // Do NOT resume execution if possible (or reload page to kill state)
            // Ideally we just don't unpause, but that hangs browser. 
            // We should reload or just let it hang for a bit then resume?
            // Correct approach: Resume but maybe inject code to stop propagation?
            // For MVP: We keep it paused for 2s to show "Freeze", then kill request via network?
            // Creating a "HardBlock" effect.

        } else {
            // ALLOW
            console.log("Chi: Allowed.");
            // Resume Buffer
            if (isDebuggerAttached) {
                chrome.debugger.sendCommand({ tabId: tabId }, "Debugger.resume");
            }
        }

    } catch (e) {
        console.error("Chi: Backend Error", e);
        // Fail Safe: Resume
        if (isDebuggerAttached) chrome.debugger.sendCommand({ tabId: tabId }, "Debugger.resume");
    }
}
