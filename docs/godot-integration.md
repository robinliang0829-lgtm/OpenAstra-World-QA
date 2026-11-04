# Godot 接入：标记与导出原型

## 状态与边界

本包包含可供 Godot 4 执行的 `SceneTree` 导出脚本及独立合成场景。当前开发环境没有 Godot 可执行程序，因此 **尚未通过 Godot 解析、导出或物理射线实机验证**。目标创世岛钉定 `4.7.2-stable`；不能把 Python 单元测试或其他 Godot 小版本的结果当作该版本通过。

开工时读取的真实工程基线为 `OpenAstra-Godot` 的 `fded0ca7ba65c24bc35dd6a707ce6002e3c2745e`。`scenes/genesis_island/main.tscn` 根节点声明 `DIMENSIONS_UNVERIFIED=true`，坐标假设为 `TEMP_PLAN_TO_GODOT_V0`；因此目前不能把该工程的数值当作已校准米制。导出器检查整个被检节点层级，发现任一 `DIMENSIONS_UNVERIFIED=true` 就错误退出，优先于 `meters_per_unit`。**不可为通过检查而删除标记**；必须先由建设方校准基线并提供证据。大 GLB 不在该仓库中，仅远程源码也不够完成实岛质量验收。

适配器只写新 JSON 文件，不保存或改写源场景。它并非不可信工程的沙箱：Godot 加载项目和实例化场景时可能运行 autoload 或脚本 `_init`。只在经过检查的、无业务自动加载的隔离 QA 工程副本中运行，使用其副本的环境与数据。脚本在加入场景树前移除节点脚本并关闭 process/physics_process 回调；这不抹去此前发生的初始化副作用，也不保证停止所有原生动画。它不设置整树 PROCESS_MODE_DISABLED，以免碰撞体被移出物理空间。不要直接指向正在运营的世界工程。

## 本地执行

先建立工程外的新输出路径。以下命令在仓库根目录执行，替换 `godot` 为已核对版本的程序：

```bash
godot --version
godot --headless --path adapters/godot --script res://export_worldqa.gd -- --scene res://demo.tscn --output /tmp/worldqa-demo/scene.json
python -m worldqa inspect /tmp/worldqa-demo/scene.json --output /tmp/worldqa-demo/report
```

Windows 的输出示例为 `D:/worldqa-evidence/run-001/scene.json`。导出器拒绝已有文件，复跑须换目录。退出码 `0` 只说明 JSON 导出成功；后续 Python 检查独立决定 pass/fail/blocked。示例应包含悬空站、0.3 米轨道缝、1 米灯间距、反向车头和大小不一致车厢；路线没有物理轨迹，必须 blocked。**这些是故意构造的演示数据，不是创世岛缺陷实证。**

## 场景标注

节点元数据统一使用 `qainfo: Dictionary`，不依赖名称模糊匹配。

显式 `qainfo` 不是 Dictionary 时，导出以退出码 2 失败，不产生输出文件。根节点的 `qainfo` 可以只包含场景设置；其他显式标注节点必须是 Node3D，并具有受支持的非空字符串 `role`（building、track、lamp、column、train_head、train_car）。缺角色、错类型、拼错或不受支持的角色都会拒绝导出，不能静默漏掉对象。没有 `qainfo` 的辅助节点仍允许存在，但不属于已检查的对象覆盖范围。

已识别对象缺少测量数据时，原有缺证会以 `export_warnings: string[]` 保留，并由 Python 报告阻断通过；该机制不同于上面导致整个导出失败的标注错误。

| 标注对象 | 所需字段 | 解释 |
|---|---|---|
| 场景根 | `scene_id`, `meters_per_unit`, `revision` | 单位转换必须显式指定；版本应填写实际工程 SHA。演示场景另写 `synthetic: true` |
| 全部被检节点 | `id`, `role` | ID 稳定且唯一；未提供 id 时使用场景树路径，跨版本比较建议明确 ID |
| 建筑 | `base_marker`, `support_probe`, `support_collision_mask` | 前两项为相对该建筑的 Marker3D 路径。支撑高度来自独立物理射线，不以 origin 假装地面 |
| 轨道 | `endpoint_a`, `endpoint_b` | 端点 Marker3D 路径；根节点 `track_links` 按 manifest 契约写真实连接，不猜最近点 |
| 路灯／柱子 | `spacing_group` | 同角色且同组内比较距离；两条相邻道路应按实际需求分组 |
| 车头／车厢 | `consist_id` | 归入同一列车；车头角色 `train_head`，车厢 `train_car` |
| 车辆方向 | `forward_origin`, `forward_tip`, `expected_forward_origin`, `expected_forward_tip` | 四个 Marker3D 路径；实际方向标记随车，期望方向标记属于独立路线，不可随车一同旋转 |
| 车体尺度 | `body_left`, `body_right`, `body_bottom`, `body_top` | 主体边界 Marker3D，排除后视镜、天线等装饰。宽高用世界距离测量，包含祖先缩放 |
| 路线 | 根节点 `routes: [{id, waypoint_markers: [...]}]` | 只导出途经点；v1 不生成或假冒 physics trace |

字段中的节点路径都相对其标注节点，路线标记路径相对场景根。所有位置均读取 `global_transform.origin`，乘根节点 `meters_per_unit`，输出米制右手 Y 向上坐标。旋转和祖先缩放通过世界变换计算，禁止再次在 Python 中重复变换。

### 列车方向参考的独立性

导出前先扫描完整节点树，收集全部已标注车头和车厢。`expected_forward_origin` 与 `expected_forward_tip` 均不得与实际 `forward` 的任一标记为同一节点，也不得位于任何已标注车辆自身或其子树内。即使车厢在车头之后才出现在场景树中，也会拒绝从该车厢取期望方向。违反时退出码 2，不产生输出文件。

该检查仅验证静态节点引用与层级关系；它不能证明动画轨道、约束或未标注的共同运动父节点不会同时改变列车和路线参考。场景操作者仍须把期望方向放在独立的路线坐标系中。此轮未获得 Godot 运行证据，不能据此关闭真实列车朝向验收。

### 目标引擎反例套件

`adapters/godot/tests/test_export_contract.py` 包含10条调用真实 Godot 的导出反例／正常例：坏 qainfo、缺角色、非字符串／未知角色、非空间节点、实际与期望标记重用、期望点位于本车或后序车厢，以及独立路线参考正常导出。每例复制独立合成工程到临时目录，输出放在该工程之外，不打开正式岛屿。

```bash
WORLDQA_GODOT_BIN=/absolute/path/to/godot python adapters/godot/tests/test_export_contract.py -v
```

Windows PowerShell 可先设置 `$env:WORLDQA_GODOT_BIN = 'C:\path\to\Godot.exe'`，再执行上述 Python 命令。先单独记录该程序的 `--version` 输出；只有核对目标版本后，结果才能用于对应版本的接入验收。

没有可用 Godot 程序时，这10条全部明确跳过；跳过不计为通过。当前仅确认测试脚本可被 Python 编译与发现，GDScript解析、物理同步和实际导出结果仍待目标引擎运行。

## 建筑射线细节

`base_marker` 位于建筑真正的底面，不是任意模型 origin。`support_probe` 指定需要核对的支撑点横向位置；射线默认从该点上方 2 米至下方 20 米，可用 `probe_up_m`、`probe_down_m` 配置。脚本排除建筑子树内 CollisionObject3D，按显式碰撞 mask 命中支撑层。两次 physics_frame 后读取射线；目标引擎中是否满足同步要求仍须实机验证。

射线无命中、没有碰撞、缺失标记都保留为缺证，不能输出零高度来伪装通过。单个支撑点不能证明整块底面支撑，斜坡、桥、悬挑建筑须后续增加多点采样及例外配置。命中水面或装饰层属于标注错误，应先修 mask。

## 正式接入交接

**当前真实主场景由脚本动态装配。**本版导出器会移除场景节点脚本再挂入树，因此不能直接用 `main.tscn` 证明完整岛屿已导出。操作方须先准备已展开、实例化且显式标注的静态 QA 场景快照；运行时快照/导出钩子尚未实现。应对照资产清单核验对象覆盖率，零标注会退出报错。

输出文件存在性检查只保护单任务正常运行，不提供跨进程独占提交协议；不同任务必须使用各自独立的输出目录，不要并发写同一路径。

1. 固定真实 Godot 小版本、工程 SHA、资产哈希、单位及坐标原点。
2. 制作脱离正式数据的 QA 场景副本，验证 autoload 和脚本无业务副作用。
3. 从站台、两段铁轨、一组灯和一列车开始标注，不批量猜语义。
4. 执行导出，保存命令、标准输出和 JSON。逐项用 Godot 现场测量核对数值。
5. 由岛屿 Owner 校准阈值。演示默认值没有施工验收授权效力。
6. 后续接入真实 CharacterBody3D 物理行走录制器，再交付路线轨迹与录像。当前只有途经点，不能声称自动试玩成功。

## 官方 API 参考

- https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html
- https://docs.godotengine.org/en/stable/classes/class_scenetree.html
- https://docs.godotengine.org/en/stable/classes/class_physicsrayqueryparameters3d.html

参考 API 不代替目标版本实测。
