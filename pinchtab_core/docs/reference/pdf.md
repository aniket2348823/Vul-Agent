# PDF

Render the current page as a PDF.

```bash
curl "http://localhost:9867/pdf?output=file"
# CLI Alternative
pinchtab pdf -o page.pdf
# Response
{
  "path": "/path/to/state/pdfs/page-20260308-120001.pdf",
  "size": 48210
}
```

Useful flags:

- CLI: `-o`, `--tab`, `--landscape`, `--scale`
- API query: `output=file`, `raw`, `landscape`, `scale`, `paperWidth`, `paperHeight`

## Related Pages

- [Text](./text.md)
- [Screenshot](./screenshot.md)
