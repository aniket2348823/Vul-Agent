# Text

Extract readable text from the current page. Use raw mode when you want `innerText` instead of readability-style extraction.

```bash
curl "http://localhost:9867/text?mode=raw"
# CLI Alternative
pinchtab text --raw
# Response
{
  "url": "https://example.com",
  "title": "Example Domain",
  "text": "Example Domain\nThis domain is for use in illustrative examples in documents.",
  "truncated": false
}
```

Useful flags:

- CLI: `--raw`
- API query: `mode=raw`, `maxChars`, `format=text`

## Related Pages

- [Snapshot](./snapshot.md)
- [PDF](./pdf.md)
