# 真实工程接入基线与阻塞

核对日期：2026-11-04（Asia/Shanghai），只读查询。

## 已证实

- GitHub：`robinliang0829-lgtm/OpenAstra-Godot`。
- 当次 main 完整 SHA：`fded0ca7ba65c24bc35dd6a707ce6002e3c2745e`。这是远程代码快照，**不是本机当前工作树或正在运行版本的证明**。
- README 和 project.godot 声明目标 `Godot 4.7.2-stable`，Forward Plus。
- 主场景 `scenes/genesis_island/main.tscn`，脚本 `scripts/main_island.gd` 动态放置对象。
- 主场景明确 `metadata/DIMENSIONS_UNVERIFIED = true` 和 `TEMP_PLAN_TO_GODOT_V0`。
- README 说明大 GLB 未入 Git，需现有本机资产；仓库里占位/回退可运行不等于真实模型到位。
- Notion 精修 CURRENT 记录最新 Blender 工作树 qbI，G 盘旧 Landscape 包不是当前权威精修版本。
- 本轮 Desktop Commander 报 PC-20260807LEIE 离线，不能声称在台式机上操作或检查过模型。
- 本轮执行环境没有 `godot` / `godot4` 可执行文件；Python 检查内核可运行。适配器源码尚未在目标引擎解析/实测。

## 直接来源

- [固定代码提交](https://github.com/robinliang0829-lgtm/OpenAstra-Godot/commit/fded0ca7ba65c24bc35dd6a707ce6002e3c2745e)
- [README](https://github.com/robinliang0829-lgtm/OpenAstra-Godot/blob/fded0ca7ba65c24bc35dd6a707ce6002e3c2745e/README.md)
- [主场景](https://github.com/robinliang0829-lgtm/OpenAstra-Godot/blob/fded0ca7ba65c24bc35dd6a707ce6002e3c2745e/scenes/genesis_island/main.tscn)
- [精修 CURRENT](https://app.notion.com/p/40d0f164d1a281248574f0a588357cc7)

## 阻塞与处理

| 阻塞 | 当前结论 | 解除材料 |
|---|---|---|
| 尺度未校准 | 不能将工程距离当作正式米制验收 | island-baseline 与轴向/比例实测 |
| 大型真实资产未取得 | 不能宣称检查了真实建筑/轨道 | 带 hash 的可访问模型清单 |
| 台式机离线 | GPU 实测/截图未执行 | 已授权设备在线及对应工程路径 |
| 无目标 Godot 二进制 | 导出器运行未验证 | 目标版解析、示例导出和反例回执 |
| 尚无新 GitHub 远程仓 | 当前为独立本地工程交付，未推送 | 建仓后上传同一源码，不向其他项目硬塞目录 |

首期工具默认只对测量结果做判断；它不自动解除 DIMENSIONS_UNVERIFIED，也不把桩数据升级为真实采样。
