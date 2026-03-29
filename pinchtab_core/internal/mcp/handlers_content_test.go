package mcp

import (
	"strings"
	"testing"
)

func TestHandleEval(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_eval", map[string]any{
		"expression": "document.title",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "/evaluate") {
		t.Errorf("expected /evaluate, got %s", text)
	}
}

func TestHandleEvalMissingExpression(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_eval", map[string]any{}, srv)
	if !r.IsError {
		t.Error("expected error for missing expression")
	}
}

func TestHandlePDF(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_pdf", map[string]any{
		"landscape":  true,
		"scale":      float64(0.8),
		"pageRanges": "1-3",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "/pdf") {
		t.Errorf("expected /pdf, got %s", text)
	}
}

func TestHandleFind(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_find", map[string]any{
		"query": "login button",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "/find") {
		t.Errorf("expected /find, got %s", text)
	}
}
