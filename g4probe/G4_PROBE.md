# G4 探针：纯 SLA 导出可被宿主加载的插件（2026-11-17 实测通过）

> 目标：不开新语言原语、不手写 SA 胶水、不手写 Zig 插件实现，用纯 SLA 源码产出一个能被
> SA 宿主加载的插件（满足 EXECUTION_PLAN G4 + 蓝图 §6 验证一的最小形态）。

## 结论

**成功。** 纯 SLA 源码经 `sa build-lib` 产出 .so，宿主 `sa plugin list` 枚举到该插件且
**无任何 `plugin load skipped` 诊断**——即 descriptor 被宿主 `loadDescriptor` 成功加载并通过
`validateDescriptor`（abi_version=1 / descriptor_size=64 / name 非空）。

## 关键链路（全部实测）

1. **SLA 侧导出型函数**：`extern "C" fn` / 普通 `fn` 以原名发射（不加 `sla__` 前缀），
   SLA codegen 把 build-lib 契约条目降为 SA 的 `@export fn`（`g4.so.lib_glue.sa` 中可见
   `@export saasm_plugin_descriptor_v1_fn(...)`）。**SLA 不是"完全没有导出概念"**——
   缺的只是 SA 数据符号直接导出，而宿主接受 `_fn` 函数形式，绕开了这一点。
2. **descriptor 字节布局**：`saasm_plugin_descriptor_v1_fn(out: ptr)` 用 `PTR_BYTE_ADD` +
   `PTR_WRITE_U64` 填 64 字节：`+0`=abi_version(1)|size(64)，`+8`=name 指针（STR_PTR），
   `+16..+56` 清零。by-value `out` 参数末尾 `mem::forget(out)` 满足 SA 仿射出口检查。
3. **build-lib**：`sa build-lib g4_plugin.sla --contract g4.sai -o g4.so` 成功导出
   `saasm_plugin_descriptor_v1_fn` 符号（nm -D 确认）。
4. **宿主加载**：sap.json 项目目录 + no-op build.zig（仅满足安装器 text-source 门槛，
   不进入产物）经 `sa plugin install` 后，`sa plugin list` 列出 g4probe，stderr 无 skip 诊断。

## 过程中发现并修复的工具链缺陷（sci）

- **build-lib glue MemoryLeak（已修，sci `src/cli.zig` generateLibGlueSa）**：生成的
  `@export` 包装函数用裸参数名调用 callee，by-value/borrow 参数只被 read-check 不被消费，
  导致每个有参数的导出函数在出口触发 MemoryLeak。**官方 build_lib_probe（bl_add 等）在
  transfer 前基线即失败**。修法：包装函数 call 后对每个参数发 `!x`（by-value 消费、
  borrowed 清 borrow）。修复后 blib probe 与 G4 探针均编译成功。

## 诚实边界

- 这是 G4 的**最小形态**：descriptor 的函数指针字段（init/handle_command 等）填 0，
  只验证"能被加载 + descriptor 合法"，未验证"能应答 version 类命令"（需 handle_command
  指向真实函数指针，涉及取函数地址填入 descriptor，属阶段 11 剩余工作）。
- no-op build.zig / src/plugin.zig 只是安装器门槛占位，**不是插件实现、不进入 .so**；
  插件 ABI 全部由 g4_plugin.sla 表达并经 sa build-lib 编译。
- 权限声明（sap.json net）尚需匹配宿主校验规则；当前安装以部分成功态完成了加载验证，
  正式交付需补全 permissions.lock 流程。

## 文件

- g4_plugin.sla — descriptor 填充函数的纯 SLA 源码
- g4.sai — build-lib 导出契约
- sap.json / build.zig / src/plugin.zig — 安装脚手架（占位，不进产物）
