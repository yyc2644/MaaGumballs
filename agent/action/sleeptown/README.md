# 沉眠小镇脚本结构

该目录沿用 `action/mars` 的职责拆分方式：

- `sleeptown_boss.py`：Boss 层策略
- `sleeptown_hp.py`：血量与生存状态
- `sleeptown_title.py`：称号路线
- `sleeptown_periodic.py`：尾数为 9 的楼层检查（活动天赋、消耗品、贵族套装），并在49层读取“退退退”和“吃瓜群众”数量后发送桌面通知
- `sleeptown_special_layer.py`：各层梦境的进入、处理与退出
- `sleeptown_earth_gate.py`：大地之门回层
- `sleeptown_events.py`：梦境交易商、沉睡者之床、月亮秋千等事件
- `sleeptown_settlement.py`：目标层结算
- `sleeptown_divine_forge_sequence.py`：默认禁用的神锻系列测序模板

主流程位于 `action/fight/sleeptown1201.py`。当前版本提供可导入、可注册的长线流程骨架；地图专属识别节点和图片补齐后，应优先在上述对应模块中实现，避免主类再次膨胀。

49层按本次运行中的真实到达次数计数：同层重试不重复计数；大地之门
回退后再次到达49层会递增。第一次确认位面先知，第二次调用恶魔系称号
占位方法，第三次确认大剑师与3级武器大师路线。

当前范围内所有未完成事项统一记录在 `docs/sleeptown_todo.md`，后续按其中
`ST-*` 和 `SDF-*` 编号逐项补充，避免策略信息散落在聊天记录中。
