# OpenAstra 世界质检工坊 / World QA

**状态：v0.1.1 工具原型；归属世界工坊下的世界质检工坊；不是创世岛验收报告。**

[项目页与任务状态](https://app.notion.com/p/40e0f164d1a2815882f5d33a567d2752)

本次修复导出缺证告警在报告中丢失、极大整数计算溢出逃逸错误协议两项问题；Godot 增加坏标注拒绝和方向参考独立性校验。Python 修复已本地验证，Godot 代码仍待目标引擎运行。详细状态见 [验证记录](docs/STATUS.md)。

独立于岛屿工程的只读检查工具。首期：建筑支撑高度、显式轨道连接、灯柱间距、列车方向/主体比例、路线采样覆盖。输入是明确标注的场景清单；输出是可以定位对象的 JSON、Markdown、HTML 证据包。

## 立即运行

需要 Python 3.10+，运行本体没有第三方依赖。在解压后的本目录执行：

```bash
python -m unittest discover -s tests -v
python -m worldqa inspect fixtures/good.json --output reports/good-001
python -m worldqa inspect fixtures/five_faults.json --output reports/faults-001
python -m worldqa inspect fixtures/missing_evidence.json --output reports/missing-001
```

第二、第三个检查命令预期返回非零码；这是检出问题/证据缺失，不是程序崩溃。Windows 可用 `py -3` 替代 `python`。每次选择一个新的输出目录，已有目录不覆盖。

| 退出码 | 含义 |
|---|---|
| 0 | 本次已声明且适用的检查通过，不代表整岛或上线通过 |
| 1 | 发现明确问题 |
| 2 | 输入/配置/输出路径无效 |
| 3 | 缺证据，或没有任何适用检查 |

打开输出目录的 `report.html`，不需要启动服务器。`manifest.input.json` 保留输入字节，`config.effective.json` 保留本次阈值，报告含 SHA256，可复现同次检查。不要把合成报告改名为真实验收报告。

## 已实现与尚未实现

- Python：五项规则、严格校验、缺证据阻断、可重复报告、正常/损坏/缺证据样例。
- Godot：显式标注节点的导出适配器源码和独立示例，目标引擎运行验证待完成。
- 尚未实现：真实角色自动驾驶、上下车/进门操作、截图自动采集、GPU 性能测试、版本图像差异、UE 适配、自动几何修复、纹理/拓扑体检。
- 路线 v0.1 只核对依序访问采样点，不证明碰撞正确、无穿墙或真实可通行。
- 默认阈值是样例值。真实岛屿必须先确认尺度、支撑点、轨道端点、车头方向和允许误差。
- 本工具不会创建数字居民、访问记忆、调用模型或修改生产场景。

## 工程组织

```text
worldqa/                检查内核、CLI、报告
fixtures/               合成正常、故障与缺证据清单
tests/                  实现测试与独立反例
adapters/godot/          待目标引擎实测的只读导出器与示例
docs/manifest-contract.md  场景交换契约
docs/kickoff.md          立项范围、工作包、验收与依赖
docs/current-baseline.md 当前已查到的真实岛基线与阻塞
docs/godot-integration.md  操作方接入说明
```

后续施工先读 [开工书](docs/kickoff.md)、[场景契约](docs/manifest-contract.md) 与 [真实工程基线](docs/current-baseline.md)。
