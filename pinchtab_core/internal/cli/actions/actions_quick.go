package actions

import (
	"fmt"
	"github.com/pinchtab/pinchtab/internal/cli"
	"github.com/pinchtab/pinchtab/internal/cli/apiclient"
	"net/http"
	"net/url"
	"time"
)

func Quick(client *http.Client, base, token string, args []string) {
	if len(args) < 1 {
		cli.Fatal("Usage: pinchtab quick <url>")
	}

	fmt.Println(cli.StyleStdout(cli.HeadingStyle, fmt.Sprintf("Navigating to %s...", args[0])))

	// Navigate
	navBody := map[string]any{"url": args[0]}
	navResult := apiclient.DoPost(client, base, token, "/navigate", navBody)

	// Small delay for page to stabilize
	time.Sleep(1 * time.Second)

	fmt.Println()
	fmt.Println(cli.StyleStdout(cli.HeadingStyle, "Page structure"))

	// Snapshot with interactive filter
	snapParams := url.Values{}
	snapParams.Set("filter", "interactive")
	snapParams.Set("compact", "true")
	apiclient.DoGet(client, base, token, "/snapshot", snapParams)

	// Extract info from navigation result
	if title, ok := navResult["title"].(string); ok {
		fmt.Println()
		fmt.Printf("%s %s\n", cli.StyleStdout(cli.MutedStyle, "Title:"), cli.StyleStdout(cli.ValueStyle, title))
	}
	if urlStr, ok := navResult["url"].(string); ok {
		fmt.Printf("%s %s\n", cli.StyleStdout(cli.MutedStyle, "URL:"), cli.StyleStdout(cli.ValueStyle, urlStr))
	}

	fmt.Println()
	fmt.Println(cli.StyleStdout(cli.HeadingStyle, "Quick actions"))
	fmt.Printf("  %s %s\n", cli.StyleStdout(cli.CommandStyle, "pinchtab click <ref>"), cli.StyleStdout(cli.MutedStyle, "# Click an element (use refs from above)"))
	fmt.Printf("  %s %s\n", cli.StyleStdout(cli.CommandStyle, "pinchtab type <ref> <text>"), cli.StyleStdout(cli.MutedStyle, "# Type into input field"))
	fmt.Printf("  %s %s\n", cli.StyleStdout(cli.CommandStyle, "pinchtab screenshot"), cli.StyleStdout(cli.MutedStyle, "# Take a screenshot"))
	fmt.Printf("  %s %s\n", cli.StyleStdout(cli.CommandStyle, "pinchtab pdf --tab <id> -o output.pdf"), cli.StyleStdout(cli.MutedStyle, "# Save tab as PDF"))
}
