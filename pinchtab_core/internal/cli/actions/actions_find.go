package actions

import (
	"fmt"
	"net/http"

	"github.com/pinchtab/pinchtab/internal/cli"
	"github.com/pinchtab/pinchtab/internal/cli/apiclient"
	"github.com/spf13/cobra"
)

func Find(client *http.Client, base, token string, query string, cmd *cobra.Command) {
	tabID, _ := cmd.Flags().GetString("tab")
	threshold, _ := cmd.Flags().GetString("threshold")
	explain, _ := cmd.Flags().GetBool("explain")
	refOnly, _ := cmd.Flags().GetBool("ref-only")

	body := map[string]any{"query": query}
	if threshold != "" {
		body["threshold"] = threshold
	}
	if explain {
		body["explain"] = true
	}

	path := "/find"
	if tabID != "" {
		path = fmt.Sprintf("/tabs/%s/find", tabID)
	}

	result := apiclient.DoPost(client, base, token, path, body)

	if refOnly {
		if ref, ok := result["best_ref"].(string); ok && ref != "" {
			fmt.Println(ref)
			return
		}
		cli.Fatal("No element found")
	}
}
