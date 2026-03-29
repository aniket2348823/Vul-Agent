package actions

import (
	"github.com/pinchtab/pinchtab/internal/cli/apiclient"
	"github.com/spf13/cobra"
	"net/http"
	"net/url"
)

func Text(client *http.Client, base, token string, cmd *cobra.Command) {
	params := url.Values{}
	if v, _ := cmd.Flags().GetBool("raw"); v {
		params.Set("mode", "raw")
		params.Set("format", "text")
	}
	if v, _ := cmd.Flags().GetString("tab"); v != "" {
		params.Set("tabId", v)
	}
	apiclient.DoGet(client, base, token, "/text", params)
}
