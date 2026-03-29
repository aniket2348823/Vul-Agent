package mcp

import (
	"context"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
)

func handleAction(c *Client, kind string) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, r mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		payload := map[string]any{"kind": kind}

		if tabID := optString(r, "tabId"); tabID != "" {
			payload["tabId"] = tabID
		}

		resolveSelector := func(required bool) error {
			sel := optString(r, "selector")
			ref := optString(r, "ref")
			if sel != "" {
				payload["selector"] = sel
			} else if ref != "" {
				payload["selector"] = ref
			} else if required {
				return fmt.Errorf("required parameter 'selector' is missing")
			}
			return nil
		}

		switch kind {
		case "click", "hover", "focus":
			if err := resolveSelector(true); err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			if kind == "click" {
				if waitNav, ok := optBool(r, "waitNav"); ok && waitNav {
					payload["waitNav"] = true
				}
			}

		case "type":
			if err := resolveSelector(true); err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			text, err := r.RequireString("text")
			if err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			payload["text"] = text

		case "press":
			key, err := r.RequireString("key")
			if err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			payload["key"] = key

		case "select":
			if err := resolveSelector(true); err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			value, err := r.RequireString("value")
			if err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			payload["value"] = value

		case "scroll":
			_ = resolveSelector(false)
			if px, ok := optFloat(r, "pixels"); ok {
				payload["scrollY"] = int(px)
			}

		case "fill":
			if err := resolveSelector(true); err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			value, err := r.RequireString("value")
			if err != nil {
				return mcp.NewToolResultError(err.Error()), nil
			}
			payload["value"] = value
		}

		body, code, err := c.Post(ctx, "/action", payload)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return resultFromBytes(body, code)
	}
}

func handleKeyboardText(c *Client, kind string) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, r mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		text, err := r.RequireString("text")
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		payload := map[string]any{"kind": kind, "text": text}
		if tabID := optString(r, "tabId"); tabID != "" {
			payload["tabId"] = tabID
		}
		body, code, err := c.Post(ctx, "/action", payload)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return resultFromBytes(body, code)
	}
}

func handleKeyboardKey(c *Client, kind string) func(context.Context, mcp.CallToolRequest) (*mcp.CallToolResult, error) {
	return func(ctx context.Context, r mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		key, err := r.RequireString("key")
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		payload := map[string]any{"kind": kind, "key": key}
		if tabID := optString(r, "tabId"); tabID != "" {
			payload["tabId"] = tabID
		}
		body, code, err := c.Post(ctx, "/action", payload)
		if err != nil {
			return mcp.NewToolResultError(err.Error()), nil
		}
		return resultFromBytes(body, code)
	}
}
