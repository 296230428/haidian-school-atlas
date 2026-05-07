# 高德地图本地运行

不要直接双击 `海淀小学高德互动地图.html`，`file://` 来源可能触发高德 `INVALID_USER_DOMAIN`，导致底图不显示。

推荐方式：

```bash
export AMAP_KEY="你的高德 Web JS API Key"
export AMAP_SECURITY_CODE="你的 securityJsCode"
python3 scripts/build_amap_school_map.py
python3 scripts/serve_amap_map.py
```

macOS 可双击 `打开高德地图.command`。如果 8765 端口已经有健康服务，它会直接打开页面；如果端口被坏进程占用，会提示先清理旧进程。
