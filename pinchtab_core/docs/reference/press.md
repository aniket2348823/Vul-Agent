# Press

Send a keyboard key to the current tab.

```bash
curl -X POST http://localhost:9867/action \
  -H "Content-Type: application/json" \
  -d '{"kind":"press","key":"Enter"}'
# CLI Alternative
pinchtab press Enter
# Response
{
  "success": true,
  "result": {
    "success": true
  }
}
```

Common keys include `Enter`, `Tab`, and `Escape`.

## Related Pages

- [Click](./click.md)
- [Focus](./focus.md)
