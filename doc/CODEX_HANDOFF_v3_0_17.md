# CODEX HANDOFF v3.0.17

## 当前交付

- 仓库：`x18055868223-png/Neutral-Loop-Execution-Layer`
- 本地路径：`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`
- 当前版本：`3.0.17-manual-gate`
- FMZ 最新交付：`artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_17.py`
- 通用 artifact：`artifacts/spm_manual_gate_execution_fmz.py`
- 源码 bundle：`realsrc/spm_manual_gate_execution_fmz.py`
- SHA256：`03DAA34761D89DA38B773546BD460E38BD4FDB9F79844D213D31FB34025F0B35`

## 本轮结论

用户在 FMZ v3.0.16 截图中指出两个显示问题：

1. 固定备选方案库里三个方案都显示为 `次日备选`。
2. 固定备选方案库未直接标记确认码。

定位：

- 确认码已在 `run_cycle()` 中通过 `_annotate_menu_lock_state()` 写入菜单行的 `_confirm_code`，但 `disp_menu_table()` 没有恢复 v3.0.10 的 `确认码/锁定状态` 列，导致状态栏表格看不到确认码。
- `expiry_role` 原本按原始到期选择标记。若近 24h 到期没有候选进入最终展示库，最终只剩后一个到期时，整表会继续显示 `次日备选`。对交易员阅读面板而言，最终展示库的最早到期应显示为 `最近可用`，避免把全部可选方案都标成备选。

v3.0.17 修复点：

1. 固定备选方案库恢复 `确认码/锁定状态` 列，优先显示 `_confirm_code` / `confirm_code`；无确认码但不可锁定时显示 `不可锁定:<reason>`。
2. `disp_menu_table()` 改为最终展示库语义：如果当前展示菜单没有任何 `TARGET_24H` 行，则把最早展示到期标记为 `最近可用`，其余仍可标为备选。
3. 不改确认码生成、锁定、预提交或下单路径；本轮只修正状态栏展示语义。

## 验证证据

已运行：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
```

结果：

- `249 passed, 0 failed`

新增/更新回归覆盖：

- `test_panel_restores_full_plan_and_order_status_tabs`
- `test_menu_promotes_earliest_displayed_backup_to_nearest_available`

交付前继续运行：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_17.py
```

## 下一步 FMZ 复测重点

1. 固定备选方案库应出现 `确认码/锁定状态` 列，行内可直接看到确认码。
2. 若最终展示的方案全来自更晚到期，期号角色应显示 `最近可用`，不应全是 `次日备选`。
3. 交互控制台和完整主链模块仍应显示同一批确认码。
