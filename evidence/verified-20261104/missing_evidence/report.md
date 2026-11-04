# OpenAstra 世界质检报告

**场景：** synthetic\-terrace\-train\-missing\-evidence  
**结果：** BLOCKED · 证据不足  
**证据类型：** synthetic

- 本报告仅评价声明的检查与输入证据，不构成上线批准。
- synthetic 为合成样例；engine\_export 为引擎导出声明，两者均不能代替真实岛屿的完整验收。
- 路线项只核对按序采样覆盖，不证明碰撞净空、连续通行或实际角色可玩性。
- 默认阈值是演示值，需由岛屿负责人校准。N/A 不计作通过；缺证据必须保留为 BLOCKED。
- 数值比较另用固定绝对容差 1e\-9、相对容差 0；原始测量与业务阈值不改写。

## 检查覆盖

| 检查 | 状态 | 检查量 | 问题数 |
|---|---|---:|---:|
| 建筑落地 / Grounding | BLOCKED · 证据不足 | 0 | 1 |
| 轨道接缝 / Track joints | BLOCKED · 证据不足 | 0 | 1 |
| 灯柱间距 / Spacing | BLOCKED · 证据不足 | 1 | 1 |
| 列车朝向与比例 / Train consistency | BLOCKED · 证据不足 | 3 | 1 |
| 路线采样覆盖 / Route sample coverage | BLOCKED · 证据不足 | 0 | 1 |

## 定位与证据

| 检查 / 代码 | 严重度 | 对象 | 位置 (m) | 测量值 | 阈值 | 说明 |
|---|---|---|---|---:|---:|---|
| grounding / MISSING\_EVIDENCE | warning | \["/Synthetic/WelcomeStation"\] | \[0, 12\.03, 0\] | — | — | /Synthetic/WelcomeStation: missing support\_y; not checked\. |
| track\_joints / MISSING\_EVIDENCE | warning | \["/Synthetic/TrackB"\] | \[10\.015, 12, 10\] | — | — | /Synthetic/TrackB: missing endpoints\.a, endpoints\.b; not checked\. |
| spacing / MISSING\_EVIDENCE | warning | \["/Synthetic/LampB"\] | \[5, 12, 20\] | — | — | /Synthetic/LampB: missing spacing\_group; not checked\. |
| train\_consistency / MISSING\_EVIDENCE | warning | \["/Synthetic/Train/Head"\] | \[2, 12, 10\] | — | — | /Synthetic/Train/Head: missing expected\_forward; not checked\. |
| route\_trace / MISSING\_EVIDENCE | warning | \["synthetic\-welcome\-walk"\] | — | — | — | Route synthetic\-welcome\-walk: missing trace; not checked\. |

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
| manifest\_sha256 | b42ef91cae2ea898597803bdd625767f30a2addabde6a4d09a878bc07448af2d |
| tool | OpenAstra\-World\-QA |
| tool\_version | 0\.1\.0 |

同目录包含原始 manifest.input.json、有效阈值 config.effective.json 与 report.json。
若有自定义配置，另存原始 config.input.json。未采集的截图、录像和 GPU 数据不在本报告中推定存在。
