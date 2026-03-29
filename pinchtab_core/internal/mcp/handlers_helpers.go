package mcp

import (
	"encoding/json"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
)

func optString(r mcp.CallToolRequest, key string) string {
	v, _ := r.GetArguments()[key].(string)
	return v
}

func optFloat(r mcp.CallToolRequest, key string) (float64, bool) {
	v, ok := r.GetArguments()[key].(float64)
	return v, ok
}

func optBool(r mcp.CallToolRequest, key string) (bool, bool) {
	v, ok := r.GetArguments()[key].(bool)
	return v, ok
}

func optNumber(r mcp.CallToolRequest, key string) float64 {
	v, _ := r.GetArguments()[key].(float64)
	return v
}

func formatInt(v float64) string {
	return fmt.Sprintf("%d", int(v))
}

func resultFromBytes(body []byte, code int) (*mcp.CallToolResult, error) {
	if code >= 400 {
		return mcp.NewToolResultError(fmt.Sprintf("HTTP %d: %s", code, string(body))), nil
	}
	return mcp.NewToolResultText(string(body)), nil
}

type profileInstanceStatus struct {
	Name    string `json:"name"`
	Running bool   `json:"running"`
	Status  string `json:"status"`
	Port    string `json:"port"`
	ID      string `json:"id"`
	Error   string `json:"error"`
}

func jsonResult(v any) (*mcp.CallToolResult, error) {
	body, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return mcp.NewToolResultError(fmt.Sprintf("encode response: %v", err)), nil
	}
	return mcp.NewToolResultText(string(body)), nil
}
