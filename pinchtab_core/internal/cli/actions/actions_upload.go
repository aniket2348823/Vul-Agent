package actions

import (
	"encoding/base64"
	"net/http"
	"os"

	"github.com/pinchtab/pinchtab/internal/cli"
	"github.com/pinchtab/pinchtab/internal/cli/apiclient"
)

func Upload(client *http.Client, base, token string, args []string, selector string) {
	if len(args) < 1 {
		cli.Fatal("Usage: pinchtab upload <file-path> [--selector <css>]")
	}

	var files []string
	for _, path := range args {
		data, err := os.ReadFile(path)
		if err != nil {
			cli.Fatal("Failed to read %s: %v", path, err)
		}
		files = append(files, base64.StdEncoding.EncodeToString(data))
	}

	body := map[string]any{
		"files": files,
	}
	if selector != "" {
		body["selector"] = selector
	}

	apiclient.DoPost(client, base, token, "/upload", body)
}
