# OpenAstra 世界质检报告

**场景：** synthetic\-terrace\-train\-five\-faults  
**结果：** FAIL · 发现问题  
**证据类型：** synthetic

- 本报告仅评价声明的检查与输入证据，不构成上线批准。
- synthetic 为合成样例；engine\_export 为引擎导出声明，两者均不能代替真实岛屿的完整验收。
- 路线项只核对按序采样覆盖，不证明碰撞净空、连续通行或实际角色可玩性。
- 默认阈值是演示值，需由岛屿负责人校准。N/A 不计作通过；缺证据必须保留为 BLOCKED。
- 数值比较另用固定绝对容差 1e\-9、相对容差 0；原始测量与业务阈值不改写。

## 检查覆盖

| 检查 | 状态 | 检查量 | 问题数 |
|---|---|---:|---:|
| 建筑落地 / Grounding | FAIL · 发现问题 | 1 | 1 |
| 轨道接缝 / Track joints | FAIL · 发现问题 | 1 | 1 |
| 灯柱间距 / Spacing | FAIL · 发现问题 | 2 | 1 |
| 列车朝向与比例 / Train consistency | FAIL · 发现问题 | 4 | 3 |
| 路线采样覆盖 / Route sample coverage | FAIL · 发现问题 | 1 | 2 |

## 定位与证据

| 检查 / 代码 | 严重度 | 对象 | 位置 (m) | 测量值 | 阈值 | 说明 |
|---|---|---|---|---:|---:|---|
| grounding / BUILDING\_FLOATING | error | \["/Synthetic/WelcomeStation"\] | \[0, 13, 0\] | 1\.0 | 0\.15 | Building base is above its declared measured support\. |
| track\_joints / TRACK\_GAP | error | \["/Synthetic/TrackA", "/Synthetic/TrackB"\] | \[10, 12, 10\] | 1\.0 | 0\.03 | Declared track connection track\-a\-to\-b exceeds the gap limit\. |
| spacing / OBJECTS\_TOO\_CLOSE | error | \["/Synthetic/LampA", "/Synthetic/LampB"\] | \[0, 12, 20\] | 1\.0 | 4\.0 | lamp objects in spacing group 'outer\-walk' are too close\. |
| train\_consistency / TRAIN\_WRONG\_DIRECTION | error | \["/Synthetic/Train/Head"\] | \[2, 12, 10\] | 180\.0 | 15\.0 | Vehicle forward direction differs from the declared travel direction\. |
| train\_consistency / TRAIN\_BODY\_RATIO | error | \["/Synthetic/Train/Head", "/Synthetic/Train/CarA"\] | \[\-5, 12, 10\] | 0\.5 | 0\.15 | Car body\_width differs from the reference head body\. |
| train\_consistency / TRAIN\_BODY\_RATIO | error | \["/Synthetic/Train/Head", "/Synthetic/Train/CarA"\] | \[\-5, 12, 10\] | 0\.4999999999999998 | 0\.15 | Car body\_height differs from the reference head body\. |
| route\_trace / ROUTE\_INCOMPLETE | error | \["synthetic\-welcome\-walk"\] | — | — | — | The recorded route explicitly reports incomplete execution\. |
| route\_trace / ROUTE\_WAYPOINT\_MISSED | error | \["synthetic\-welcome\-walk"\] | \[8, 12, 0\] | — | 0\.75 | Waypoint 2 is not reached by successive trace samples in the declared order\. |

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
| manifest\_sha256 | 76f06167c785bd0652bafce854299e2613646aa7abb1cd797f75991a94e8a6da |
| tool | OpenAstra\-World\-QA |
| tool\_version | 0\.1\.1 |

同目录包含原始 manifest.input.json、有效阈值 config.effective.json 与 report.json。
若有自定义配置，另存原始 config.input.json。未采集的截图、录像和 GPU 数据不在本报告中推定存在。
