package actions

import (
	"encoding/json"
	"testing"

	"github.com/spf13/cobra"
)

func newNavigateCmd() *cobra.Command {
	cmd := &cobra.Command{}
	cmd.Flags().Bool("new-tab", false, "")
	cmd.Flags().Bool("block-images", false, "")
	cmd.Flags().Bool("block-ads", false, "")
	cmd.Flags().String("tab", "", "")
	return cmd
}

func TestNavigate(t *testing.T) {
	m := newMockServer()
	defer m.close()
	client := m.server.Client()

	cmd := newNavigateCmd()
	Navigate(client, m.base(), "", "https://pinchtab.com", cmd)
	if m.lastMethod != "POST" {
		t.Errorf("expected POST, got %s", m.lastMethod)
	}
	if m.lastPath != "/navigate" {
		t.Errorf("expected /navigate, got %s", m.lastPath)
	}
	var body map[string]any
	_ = json.Unmarshal([]byte(m.lastBody), &body)
	if body["url"] != "https://pinchtab.com" {
		t.Errorf("expected url=https://pinchtab.com, got %v", body["url"])
	}
}

func TestNavigateWithAllFlags(t *testing.T) {
	m := newMockServer()
	defer m.close()
	client := m.server.Client()

	cmd := newNavigateCmd()
	_ = cmd.Flags().Set("new-tab", "true")
	_ = cmd.Flags().Set("block-images", "true")
	Navigate(client, m.base(), "", "https://pinchtab.com", cmd)
	var body map[string]any
	_ = json.Unmarshal([]byte(m.lastBody), &body)
	if body["newTab"] != true {
		t.Error("expected newTab=true")
	}
	if body["blockImages"] != true {
		t.Error("expected blockImages=true")
	}
}

func TestNavigateWithBlockAds(t *testing.T) {
	m := newMockServer()
	defer m.close()
	client := m.server.Client()

	cmd := newNavigateCmd()
	_ = cmd.Flags().Set("block-ads", "true")
	Navigate(client, m.base(), "", "https://pinchtab.com", cmd)
	var body map[string]any
	_ = json.Unmarshal([]byte(m.lastBody), &body)
	if body["blockAds"] != true {
		t.Error("expected blockAds=true")
	}
}
