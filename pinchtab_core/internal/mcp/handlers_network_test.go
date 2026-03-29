package mcp

import (
	"strings"
	"testing"
)

func TestHandleNetwork(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_network", map[string]any{}, srv)
	text := resultText(t, r)
	if !strings.Contains(text, "/network") {
		t.Errorf("expected /network path, got %s", text)
	}
}

func TestHandleNetworkWithFilters(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_network", map[string]any{
		"tabId":  "t1",
		"filter": "api.example",
		"method": "POST",
		"status": "4xx",
		"type":   "xhr",
		"limit":  float64(10),
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "/network") {
		t.Errorf("expected /network path, got %s", text)
	}
	if !strings.Contains(text, "api.example") {
		t.Errorf("expected filter in query, got %s", text)
	}
	if !strings.Contains(text, "POST") {
		t.Errorf("expected method in query, got %s", text)
	}
}

func TestHandleNetworkDetail(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_network_detail", map[string]any{
		"requestId": "req123",
		"tabId":     "t1",
		"body":      true,
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "/network/req123") {
		t.Errorf("expected /network/req123 path, got %s", text)
	}
}

func TestHandleNetworkDetailMissingRequestId(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_network_detail", map[string]any{}, srv)
	if !r.IsError {
		t.Error("expected error for missing requestId")
	}
}

func TestHandleNetworkClear(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_network_clear", map[string]any{}, srv)
	text := resultText(t, r)
	if !strings.Contains(text, "/network/clear") {
		t.Errorf("expected /network/clear path, got %s", text)
	}
}

func TestHandleNetworkClearWithTab(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_network_clear", map[string]any{
		"tabId": "t1",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "/network/clear") {
		t.Errorf("expected /network/clear path, got %s", text)
	}
}
