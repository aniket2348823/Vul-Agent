# Navigate

Open a new tab and navigate it to a URL, or reuse a tab when a tab ID is provided through the API.

```bash
curl -X POST http://localhost:9867/navigate \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
# CLI Alternative
pinchtab nav https://example.com
# Response
{
  "tabId": "8f9c7d4e1234567890abcdef12345678",
  "url": "https://example.com",
  "title": "Example Domain"
}
```

Useful flags:

- CLI: `--new-tab`, `--block-images`, `--block-ads`
- API body: `tabId`, `newTab`, `timeout`, `blockImages`, `blockAds`, `waitFor`, `waitSelector`

## Related Pages

- [Snapshot](./snapshot.md)
- [Tabs](./tabs.md)
