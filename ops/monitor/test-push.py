#!/usr/bin/env python3
"""钉钉推送连通性自测：发一条测试消息，验证 webhook 与签名配置是否可用。

用法（与 monitor.py 同目录）：python3 test-push.py
"""
import sys

from monitor import load_config, send_dingtalk

TEXT = """### EZLove 监控接入成功

- 探测对象：后端健康接口（宿主机 nginx + 公网）
- 采集内容：每分钟请求量、5xx 比例、响应耗时
- 告警策略：同类告警指数退避（900s 起，封顶 3600s），每小时最多 6 条
- 随时关闭：`python3 monitor.py --pause`，恢复用 `--resume`
- 当前状态：监控已生效，后续异常会推送到本群"""


def main() -> int:
    cfg = load_config()
    webhook = cfg.get("dingtalk_webhook") or ""
    if not webhook:
        print("config.json 里没有 dingtalk_webhook")
        return 1
    err = send_dingtalk(webhook, TEXT, cfg.get("dingtalk_secret") or "")
    if err:
        print(f"推送失败：{err}")
        return 1
    print("推送成功，请到钉钉群确认")
    return 0


if __name__ == "__main__":
    sys.exit(main())