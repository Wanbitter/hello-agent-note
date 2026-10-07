#     以下为ReAct，PaS,Reflection的互相协作
#                     ┌─ 简单/固定任务 ─→ Planner(PaS) ─→ 按计划执行
# 用户请求 ─→ 调度判断 ┤
#                     └─ 复杂/探索任务 ─→ ReAct 主循环 ─┬─ 需要拆解时 → Planner
#                                                       ├─ 需要外部信息 → Search 等工具
#                                                       └─ 完成后/失败时 → Reflector
#                                                               ↓
#                                                           Memory（存经验）
#                                                               ↓
#                                                           下次规划时带上