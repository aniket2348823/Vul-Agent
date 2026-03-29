package engine

import "testing"

func TestCapabilityRule(t *testing.T) {
	r := CapabilityRule{}
	tests := []struct {
		op   Capability
		want Decision
	}{
		{CapScreenshot, UseChrome},
		{CapPDF, UseChrome},
		{CapEvaluate, UseChrome},
		{CapCookies, UseChrome},
		{CapNavigate, Undecided},
		{CapSnapshot, Undecided},
		{CapText, Undecided},
		{CapClick, Undecided},
		{CapType, Undecided},
	}
	for _, tt := range tests {
		if got := r.Decide(tt.op, ""); got != tt.want {
			t.Errorf("CapabilityRule(%s) = %d, want %d", tt.op, got, tt.want)
		}
	}
}

func TestContentHintRule(t *testing.T) {
	r := ContentHintRule{}
	tests := []struct {
		op   Capability
		url  string
		want Decision
	}{
		{CapNavigate, "https://example.com/page.html", UseLite},
		{CapSnapshot, "https://example.com/doc.htm", UseLite},
		{CapText, "https://example.com/feed.xml", UseLite},
		{CapNavigate, "https://example.com/readme.txt", UseLite},
		{CapNavigate, "https://example.com/notes.md", UseLite},
		{CapNavigate, "https://example.com/app", Undecided},
		{CapNavigate, "https://example.com/", Undecided},
		{CapClick, "https://example.com/page.html", Undecided},
		{CapScreenshot, "https://example.com/page.html", Undecided},
	}
	for _, tt := range tests {
		if got := r.Decide(tt.op, tt.url); got != tt.want {
			t.Errorf("ContentHintRule(%s, %q) = %d, want %d", tt.op, tt.url, got, tt.want)
		}
	}
}

func TestDefaultLiteRule(t *testing.T) {
	r := DefaultLiteRule{}
	tests := []struct {
		op   Capability
		want Decision
	}{
		{CapNavigate, UseLite},
		{CapSnapshot, UseLite},
		{CapText, UseLite},
		{CapClick, UseLite},
		{CapType, UseLite},
		{CapScreenshot, Undecided},
		{CapPDF, Undecided},
	}
	for _, tt := range tests {
		if got := r.Decide(tt.op, ""); got != tt.want {
			t.Errorf("DefaultLiteRule(%s) = %d, want %d", tt.op, got, tt.want)
		}
	}
}

func TestDefaultChromeRule(t *testing.T) {
	r := DefaultChromeRule{}
	for _, op := range []Capability{CapNavigate, CapScreenshot, CapClick, CapPDF} {
		if got := r.Decide(op, ""); got != UseChrome {
			t.Errorf("DefaultChromeRule(%s) = %d, want UseChrome", op, got)
		}
	}
}
