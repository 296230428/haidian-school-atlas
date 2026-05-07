# Contributing

Contributions should keep the project reproducible and safe to publish.

## Rules

- Do not commit real API keys, local `.env` files, cookies, browser profiles or credentials.
- Keep raw third-party pages and downloaded images out of Git unless their redistribution rights are clear.
- Prefer derived JSON data and scripts over opaque manual edits.
- Add source notes when introducing new data fields.
- Verify generated workbooks and maps after changing processing scripts.

## Local Checks

```bash
python3 -m py_compile scripts/*.py
zsh -n outputs/amap_map/打开高德地图.command
rg -n "AMAP_KEY=.*[a-f0-9]{20}|securityJsCode: \\"[a-f0-9]{20}" .
```

If the final command finds a real credential, remove it before publishing.
