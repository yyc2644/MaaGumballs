# 91脚本结构

该目录沿用沉眠小镇的职责拆分方式：

- `map91_boss.py`：Boss 层策略
- `map91_hp.py`：血量与生存状态
- `map91_title.py`：称号路线
- `map91_events.py`：普通层搜刮事件
- `map91_special_layer.py`：特殊层或夹层事件
- `map91_earth_gate.py`：大地之门回层
- `map91_settlement.py`：目标层结算

主流程位于 `action/fight/map91.py`。当前版本先提供可注册、可运行的
91-1201 骨架：进图、层数状态、小怪层刷怪/搜刮分离、Boss 分派、下楼和
结算。地图专属事件、Boss 固定解法和特殊层逻辑后续应优先补到本目录的
对应模块中，避免主流程继续膨胀。
