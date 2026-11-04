"""Deterministic static reports; strings in a manifest are untrusted data."""

from html import escape
import json


LABELS = {
    "grounding": "建筑落地 / Grounding",
    "track_joints": "轨道接缝 / Track joints",
    "spacing": "灯柱间距 / Spacing",
    "train_consistency": "列车朝向与比例 / Train consistency",
    "route_trace": "路线采样覆盖 / Route sample coverage",
}
STATUS = {"pass": "PASS · 已检查通过", "fail": "FAIL · 发现问题",
          "blocked": "BLOCKED · 证据不足", "not_applicable": "N/A · 未适用"}


def _text(value):
    if value is None:
        return "—"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _md(value):
    text = _text(value)
    # Escape link/image/HTML syntax as well as table separators and code spans.
    for char in "\\`*_{}[]()#+-.!|<>":
        text = text.replace(char, "\\" + char)
    return text.replace("\r", " ").replace("\n", " ")


def _counts(report):
    checks = report.get("checks", [])
    return {key: sum(c.get("status") == key for c in checks)
            for key in STATUS}


def _limits(report):
    base = [
        "本报告仅评价声明的检查与输入证据，不构成上线批准。",
        "synthetic 为合成样例；engine_export 为引擎导出声明，两者均不能代替真实岛屿的完整验收。",
        "路线项只核对按序采样覆盖，不证明碰撞净空、连续通行或实际角色可玩性。",
        "默认阈值是演示值，需由岛屿负责人校准。N/A 不计作通过；缺证据必须保留为 BLOCKED。",
        "数值比较另用固定绝对容差 1e-9、相对容差 0；原始测量与业务阈值不改写。",
    ]
    return base


def render_markdown(report):
    lines = ["# OpenAstra 世界质检报告", "",
             f"**场景：** {_md(report['scene_id'])}  ",
             f"**结果：** {_md(STATUS.get(report['summary']['status'], report['summary']['status']))}  ",
             f"**证据类型：** {_md(report['evidence_kind'])}", ""]
    lines.extend("- " + _md(line) for line in _limits(report))
    if report.get("export_warnings"):
        lines += ["", "## 导出缺证 / Export warnings", "",
                  "以下导出告警计入总告警数；即使其余检查通过，总结果仍至少为 BLOCKED。", ""]
        lines.extend("- " + _md(warning) for warning in report["export_warnings"])
    lines += ["", "## 检查覆盖", "", "| 检查 | 状态 | 检查量 | 问题数 |",
              "|---|---|---:|---:|"]
    for check in report["checks"]:
        lines.append("| " + " | ".join(_md(x) for x in (
            LABELS.get(check["id"], check["id"]),
            STATUS.get(check["status"], check["status"]), check["checked"],
            len(check["findings"]))) + " |")
    lines += ["", "## 定位与证据", "",
              "| 检查 / 代码 | 严重度 | 对象 | 位置 (m) | 测量值 | 阈值 | 说明 |",
              "|---|---|---|---|---:|---:|---|"]
    for check in report["checks"]:
        for item in check["findings"]:
            lines.append("| " + " | ".join(_md(x) for x in (
                f"{check['id']} / {item['code']}", item["severity"],
                item.get("object_ids", []), item.get("position"),
                item.get("measured"), item.get("limit"), item["message"])) + " |")
    if not any(c["findings"] for c in report["checks"]):
        lines.append("| — | — | — | — | — | — | 无记录；请同时查看检查覆盖与适用范围 |")
    lines += ["", "## 有效阈值", "", "| 参数 | 值 |", "|---|---:|"]
    lines += [f"| {_md(k)} | {_md(v)} |" for k, v in sorted(report["config"].items())]
    lines += ["", "## 可复现信息", "", "| 字段 | 值 |", "|---|---|"]
    lines += [f"| {_md(k)} | {_md(v)} |" for k, v in sorted(report.get("provenance", {}).items())]
    lines += ["", "同目录包含原始 manifest.input.json、有效阈值 config.effective.json 与 report.json。",
              "若有自定义配置，另存原始 config.input.json。未采集的截图、录像和 GPU 数据不在本报告中推定存在。", ""]
    return "\n".join(lines)


def render_html(report):
    e = lambda value: escape(_text(value), quote=True)
    status = report["summary"]["status"]
    css_status = status if status in STATUS else "blocked"
    counts = _counts(report)
    cards = "".join(f'<div class="card"><strong>{counts[k]}</strong><span>{e(STATUS[k])}</span></div>'
                    for k in STATUS)
    coverage = "".join(
        f'<tr><td>{e(LABELS.get(c["id"], c["id"]))}</td>'
        f'<td>{e(STATUS.get(c["status"], c["status"]))}</td>'
        f'<td>{e(c["checked"])}</td><td>{len(c["findings"])}</td></tr>'
        for c in report["checks"])
    details = []
    for check in report["checks"]:
        for item in check["findings"]:
            details.append("<tr>" + "".join(f"<td>{e(x)}</td>" for x in (
                f"{check['id']} / {item['code']}", item["severity"],
                item.get("object_ids", []), item.get("position"), item.get("measured"),
                item.get("limit"), item["message"])) + "</tr>")
    if not details:
        details.append('<tr><td colspan="7">无问题记录；仍须查看未适用项及证据限制。</td></tr>')
    params = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>"
                     for k, v in sorted(report["config"].items()))
    provenance = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>"
                         for k, v in sorted(report.get("provenance", {}).items()))
    limits = "".join(f"<li>{e(line)}</li>" for line in _limits(report))
    export_notice = ""
    if report.get("export_warnings"):
        warnings = "".join(f"<li>{e(warning)}</li>" for warning in report["export_warnings"])
        export_notice = ('<h2>导出缺证 / Export warnings</h2><aside class="notice">'
                         '<strong>导出告警计入总告警数；其余检查通过也不能消除缺证。</strong>'
                         f'<ul>{warnings}</ul></aside>')
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>OpenAstra 世界质检 · {e(report['scene_id'])}</title>
<style>
:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f2f5f7;color:#14283b;font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1320px;margin:0 auto;padding:38px 24px 60px}}header{{background:#15374c;color:#fff;padding:28px;border-radius:16px}}h1{{margin:4px 0 12px;font-size:30px}}h2{{margin:32px 0 12px;font-size:21px}}.eyebrow{{font-size:12px;letter-spacing:.2em;color:#9bd2cf}}.sub{{overflow-wrap:anywhere;color:#d4e6ef}}.badge{{display:inline-block;padding:5px 12px;border-radius:99px;font-weight:700;background:#e2ebef;color:#173447}}.badge.fail{{background:#ffceca;color:#762b24}}.badge.pass{{background:#c9f0df;color:#155342}}.badge.blocked{{background:#ffe4ad;color:#674400}}
.cards{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0}}.card{{background:white;padding:15px 20px;border:1px solid #dce4e9;border-radius:12px}}.card strong{{display:block;font-size:26px}}.card span{{font-size:13px}}.notice{{background:#fff5dd;border-left:4px solid #c6902c;padding:12px 18px;border-radius:6px}}.notice ul{{margin:6px 0;padding-left:22px}}.scroll{{overflow:auto;border:1px solid #dce4e9;border-radius:12px;background:#fff}}table{{width:100%;border-collapse:collapse;font-size:13px}}th{{text-align:left;background:#e7eff3;color:#294657;white-space:nowrap}}th,td{{padding:12px 14px;border-bottom:1px solid #e5ebef;vertical-align:top}}td{{overflow-wrap:anywhere;max-width:460px}}tr:last-child td{{border-bottom:0}}.fine{{font-size:13px;color:#596c78}}a{{color:#24607c}}@media(max-width:700px){{.cards{{grid-template-columns:repeat(2,minmax(0,1fr))}}main{{padding:18px 12px}}header{{padding:20px}}h1{{font-size:24px}}}}@media print{{body{{background:white}}main{{padding:0}}.scroll{{overflow:visible}}header{{color:#14283b;background:white;border:1px solid #ccc}}.sub{{color:#294657}}}}
</style></head><body><main>
<header><div class="eyebrow">OPENASTRA / WORLD QA LAB</div><h1>世界质检报告</h1><span class="badge {css_status}">{e(STATUS.get(status, status))}</span>
<p class="sub">场景：{e(report['scene_id'])}<br>证据类型：{e(report['evidence_kind'])}</p></header>
<div class="cards">{cards}</div><aside class="notice"><strong>证据边界</strong><ul>{limits}</ul></aside>
{export_notice}
<h2>检查覆盖</h2><div class="scroll"><table><thead><tr><th>检查</th><th>状态</th><th>检查量</th><th>问题数</th></tr></thead><tbody>{coverage}</tbody></table></div>
<h2>定位与测量</h2><div class="scroll"><table><thead><tr><th>检查 / 代码</th><th>严重度</th><th>对象</th><th>位置 (m)</th><th>测量值</th><th>阈值</th><th>说明</th></tr></thead><tbody>{''.join(details)}</tbody></table></div>
<h2>有效阈值</h2><div class="scroll"><table><thead><tr><th>参数</th><th>值</th></tr></thead><tbody>{params}</tbody></table></div>
<h2>可复现信息</h2><div class="scroll"><table><tbody>{provenance}</tbody></table></div>
<p class="fine">本目录保存输入原始字节、有效配置及报告。未采集的截图、录像、GPU 数据不在这里推定存在。<br>
<a href="report.json">JSON 报告</a> · <a href="report.md">Markdown 报告</a> · <a href="manifest.input.json">输入副本</a> · <a href="config.effective.json">有效配置</a></p>
</main></body></html>\n'''
