# OpenAstra 世界质检报告

**场景：** synthetic\-terrace\-train\-good  
**结果：** PASS · 已检查通过  
**证据类型：** synthetic

- 本报告仅评价声明的检查与输入证据，不构成上线批准。
- synthetic 为合成样例；engine\_export 为引擎导出声明，两者均不能代替真实岛屿的完整验收。
- 路线项只核对按序采样覆盖，不证明碰撞净空、连续通行或实际角色可玩性。
- 默认阈值是演示值，需由岛屿负责人校准。N/A 不计作通过；缺证据必须保留为 BLOCKED。
- 数值比较另用固定绝对容差 1e\-9、相对容差 0；原始测量与业务阈值不改写。

## 检查覆盖

| 检查 | 状态 | 检查量 | 问题数 |
|---|---|---:|---:|
| 建筑落地 / Grounding | PASS · 已检查通过 | 1 | 0 |
| 轨道接缝 / Track joints | PASS · 已检查通过 | 1 | 0 |
| 灯柱间距 / Spacing | PASS · 已检查通过 | 2 | 0 |
| 列车朝向与比例 / Train consistency | PASS · 已检查通过 | 4 | 0 |
| 路线采样覆盖 / Route sample coverage | PASS · 已检查通过 | 1 | 0 |

## 定位与证据

| 检查 / 代码 | 严重度 | 对象 | 位置 (m) | 测量值 | 阈值 | 说明 |
|---|---|---|---|---:|---:|---|
| — | — | — | — | — | — | 无记录；请同时查看检查覆盖与适用范围 |

## 有效阈值

| 参数 | 值 |
|---|---:|
| max\_body\_ratio\_error | 0\.15 |
| max\_embed\_m | 0\.15 |
| max\_float\_m | 0\.15 |
| max\_forward\_angle\_deg | 15\.0 |
| max\_track\_gap\_m | 0\.03 |
| min\_column\_spacing\_m | 2\.0 |
| min\_lamp\_spacing\_m | 4\.0 |
| route\_tolerance\_m | 0\.75 |

## 可复现信息

| 字段 | 值 |
|---|---|
| config\_input\_sha256 | — |
| effective\_config\_sha256 | a9c38639c8fd420e698c5a2bbbc70ba4f71d0a69f30cbbe563ec25907995563f |
| manifest\_sha256 | c26f589520801377f6cbf4710034186556721e723866ec726330d7b85e2a86cc |
| tool | OpenAstra\-World\-QA |
| tool\_version | 0\.1\.0 |

同目录包含原始 manifest.input.json、有效阈值 config.effective.json 与 report.json。
若有自定义配置，另存原始 config.input.json。未采集的截图、录像和 GPU 数据不在本报告中推定存在。
