package mcp

import (
	"strings"
	"testing"
)

func TestHandleClick(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_click", map[string]any{
		"ref": "e5",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "click") {
		t.Errorf("expected click in response, got %s", text)
	}
}

func TestHandleClickWaitNav(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_click", map[string]any{
		"ref":     "e5",
		"waitNav": true,
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, `"waitNav":true`) {
		t.Errorf("expected waitNav in action payload, got %s", text)
	}
}

func TestHandleClickMissingRef(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_click", map[string]any{}, srv)
	if !r.IsError {
		t.Error("expected error for missing ref")
	}
}

func TestHandleType(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_type", map[string]any{
		"ref":  "e12",
		"text": "hello world",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "type") {
		t.Errorf("expected type in response, got %s", text)
	}
	if !strings.Contains(text, "hello world") {
		t.Errorf("expected text in response, got %s", text)
	}
}

func TestHandlePress(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_press", map[string]any{
		"key": "Enter",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "Enter") {
		t.Errorf("expected Enter in response, got %s", text)
	}
}

func TestHandleSelect(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_select", map[string]any{
		"ref":   "e3",
		"value": "option2",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "select") {
		t.Errorf("expected select, got %s", text)
	}
}

func TestHandleScroll(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_scroll", map[string]any{
		"pixels": float64(500),
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "scroll") {
		t.Errorf("expected scroll, got %s", text)
	}
}

func TestHandleFill(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_fill", map[string]any{
		"ref":   "e7",
		"value": "test@example.com",
	}, srv)

	text := resultText(t, r)
	if !strings.Contains(text, "fill") {
		t.Errorf("expected fill, got %s", text)
	}
}

func TestHandleHover(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_hover", map[string]any{"ref": "e3"}, srv)
	text := resultText(t, r)
	if !strings.Contains(text, "hover") {
		t.Errorf("expected hover, got %s", text)
	}
}

func TestHandleFocus(t *testing.T) {
	srv := mockPinchTab()
	defer srv.Close()

	r := callTool(t, "pinchtab_focus", map[string]any{"ref": "e1"}, srv)
	text := resultText(t, r)
	if !strings.Contains(text, "focus") {
		t.Errorf("expected focus, got %s", text)
	}
}
