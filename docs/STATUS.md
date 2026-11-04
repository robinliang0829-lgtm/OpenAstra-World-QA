# 当前状态｜v0.1.1｜2026-11-04

归属：世界工坊 → 世界质检工坊。状态仍为 IMPLEMENTING；真实岛未验收、未部署。

- WQA-R01：导出缺证 warning 已进入 JSON／Markdown／HTML，总体至少 blocked；已有明确缺陷仍为 fail。Python 模块修复及反例通过，不代表已实现全场景预期对象覆盖。
- WQA-R02：极大有限整数相减的结果越界转为带字段位置的 ValueError；CLI 返回2，无未处理 traceback。Python 模块修复通过。
- WQA-R03：Godot 增加坏标注拒绝和车辆子树内方向参考拒绝；源码及实机负例已准备，目标 Godot 运行验证未完成。
- 当前 Python：76条通过，0失败。新增实现测试12条、独立复审10条，原有54条保留。
- Godot 合同测试：10条全部跳过，不能计为通过。当前环境没有目标引擎。
- 世界工坊合成试运行单独交付；它不证明真实岛场景、碰撞、性能或生产成本。

本轮证据见 `evidence/verified-v011-20261104/`。旧源码回放证明新反例能捕获问题，不将独立复审的回放说成它在实现前已编写。

## GitHub 首次远端交付｜2026-11-04

- 维护源：[OpenAstra-World-QA](https://github.com/robinliang0829-lgtm/OpenAstra-World-QA)。原 `OpenAstra-QA` 沿用并更名，仓库 ID `1444320089` 不变，仍为公开仓库。
- 所属组织工程：[OpenAstra-World-Workshop](https://github.com/robinliang0829-lgtm/OpenAstra-World-Workshop)，私有独立仓库。
- 本地源提交 `fbc775d13246054da97cffbe7a72f8aa510a38fc` → 首次 API 导入提交 [`f49845efd127ae4bb4773b0852a69da7002dfe49`](https://github.com/robinliang0829-lgtm/OpenAstra-World-QA/commit/f49845efd127ae4bb4773b0852a69da7002dfe49)；两者 tree 核对一致：`9f271f6edf442fc8a762a04c7b17e9bc2125e07f`。
- 首次导入提交的 [CI run 41789455581](https://github.com/robinliang0829-lgtm/OpenAstra-World-QA/actions/runs/41789455581) 已成功；工作流运行 Python 3.10／3.12 测试及合成正常报告，不运行 Godot。此结果只对应上述首次导入 SHA，本次文档更新后的 CI 待单独核查。

首次远端树与本地源树一致，不代表提交历史相同。本轮使用 API 快照导入，原历史的 Git bundle 保留在 `OpenAstra-World-Workshop-Starter-v0.1.zip`。后续开发从 GitHub clone，沿远端提交历史继续；后续文档变更不属于首次导入树。真实岛未验收、Godot 10 条跳过、未部署的结论不变。

以下保留首次 v0.1 交付记录，数字和待办为当时状态；与本节不一致处以本节为准。

## 历史：v0.1 开工回执 / 2026-11-04

状态：**IMPLEMENTING**。第一版 Python 内核与报告已可运行；Godot 适配、真实岛接入、GPU 验收待完成。未部署、未批准上线。

## 本轮已完成

- 五类规则、非法/非有限输入与错误引用拒绝、缺证据阻断。
- 命令行与 JSON/Markdown/HTML 报告，原始输入副本、阈值、SHA256。
- 正常 / 五类故障 / 缺证据三套合成清单。
- 54 条 Python 测试：26 内核 + 8 CLI/报告 + 20 独立反例。
- 独立反例发现3处刚好等于阈值的浮点误报并促成修复：建筑、轨道、列车比例；修后全量通过。
- Godot 只读导出器及示例源码；未在目标引擎运行，不能列为已验证。

## 复现

```bash
python tools/reproduce.py reports/reproduction-001
```

生成 tests.txt、reproduction.json 和三套报告；预期退出码为 0 / 1 / 3。样例报告不是实际岛屿发现。交付包 `evidence/verified-20261104/` 保留本轮命令实测结果。

## 尚未关闭

1. 台式机离线，真实大型 GLB 仅在本机，不能进行真实资产检测。
2. 真实工程标记 DIMENSIONS_UNVERIFIED，尺度基线需确认。
3. 没有目标 Godot 二进制；适配器未完成解析/运行验证。
4. 真实岛脚本动态装配，需要静态展开 QA 快照或后续运行时导出钩子。
5. 自动试玩、截图采集、性能、版本对比、UE、网格/贴图卫生仍在后续工作包。
6. HTML 输出已有转义与结构测试；本环境缺浏览器二进制，未做浏览器截图视觉验收。
7. 本轮交付独立本地 Git 工程和源码包；尚未建立/推送 GitHub 远程仓。

下一里程碑：WQA-03 目标 Godot 示例导出；随后 WQA-05 首批真实模型测量与回执。需要时按 `docs/kickoff.md` 分配后续 Codex 工作包，不借用现有项目的通过状态。
