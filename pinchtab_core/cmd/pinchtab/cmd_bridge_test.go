package main

import "testing"

func TestResolveBridgeEngine(t *testing.T) {
	tests := []struct {
		name      string
		flagValue string
		cfgValue  string
		want      string
		wantErr   bool
	}{
		{name: "config default", cfgValue: "lite", want: "lite"},
		{name: "flag overrides config", flagValue: "auto", cfgValue: "chrome", want: "auto"},
		{name: "empty falls back to chrome", want: "chrome"},
		{name: "invalid", flagValue: "bogus", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := resolveBridgeEngine(tt.flagValue, tt.cfgValue)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got != tt.want {
				t.Fatalf("got %q want %q", got, tt.want)
			}
		})
	}
}
