package bridge

import "testing"

func TestIsCFChallenge(t *testing.T) {
	tests := []struct {
		title string
		want  bool
	}{
		{"Just a moment...", true},
		{"JUST A MOMENT...", true},
		{"Attention Required | Cloudflare", true},
		{"Checking your browser before accessing...", true},
		{"Google", false},
		{"", false},
		{"My Cool Website", false},
		{"just a moment", true},
		{"Please wait - Checking Your Browser", true},
	}
	for _, tt := range tests {
		got := isCFChallenge(tt.title)
		if got != tt.want {
			t.Errorf("isCFChallenge(%q) = %v, want %v", tt.title, got, tt.want)
		}
	}
}

func TestCloudflareSolverName(t *testing.T) {
	s := &CloudflareSolver{}
	if s.Name() != "cloudflare" {
		t.Errorf("expected name 'cloudflare', got %q", s.Name())
	}
}
