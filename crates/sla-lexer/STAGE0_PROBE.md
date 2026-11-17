# 阶段 0 可行性探针报告（lexer 移植前置）

> 日期：2026-11-17。性质：实测探针（非静态推理），遵循 EXECUTION_PLAN §2「未实测不宣称」。
> 基线：sci `bcafc71f`（含 transfer）× sa_plugin_sla `f27d2031`（含 transfer + 候选修复），dev 插件重装。
> 目标：在写阶段 0 正式代码前，实测「SLA 能否表达词法器并经宿主验证」，以及表示策略的可用性。

## 一、通过的结论（可行性成立）

实测一个最小词法器切片（enum/struct/可变局部状态扫描/span 记录/`@test`），经 `sa check` 与 `sa test` 两条路径：

- `sa check <file.sla>`：成功解析并验证语法与类型。
- `sa build-exe`：前端成功编译到 `.sa`（仅因无 `main` 在链接期失败，前端路径全通）。
- 最小整数-tag 词法器：`sa test` **PASS**。

**结论：SLA 具备表达词法器的能力，阶段 0（lexer 移植，530 行）在语言层面可行。** 字节缓冲区惯例为固定数组 `[u8; N]` + 显式长度（实测可用，对齐 `demos/rosetta/199` 与 `demos/cxu/04` 的既有写法）；`while i < n { ... }`（无括号、块后无分号）、`if cond { ... };`（无括号、块后有分号）、`let`（默认可变，可直接重赋值）为实测正确语法。

## 二、发现的障碍（须登记，供裁决）

### OBS-1：枚举变体字面量的相等比较语义不可靠（实质，有规避路径）

最小复现（均已实测）：

```
enum E { A, B }
// 用例一：同一变量自比较 → PASS
let x = E::A; if !(x == x) { panic(2); }
// 用例二：两个独立初始化的 E::A 比较 → FAIL（panic）
let x = E::A; let y = E::A; if !(x == y) { panic(1); }
```

- `E::A == E::A` 在两支独立 `let` 上求值为 **false**；同一变量 `x == x` 为 true。
- 对照：官方 `demos/rosetta/06_enum_and_match`（用 `match` 消费枚举）**通过**。
- 另一处解析层怪象：`if e != E::A { panic(1); }` 在 `sa test` 路径报 `Syntax Error: expected colon` 于 `panic(`，疑为 `::` 路径表达式未正确终结；把比较提到独立 `let is_a = e == E::A;` 后可解析（但语义仍为 false）。`sa check` 对同一写法宽容。

**影响**：Zig lexer 用 `Token.Tag` enum，移植后 tag 比较是最高频操作。若照搬 enum + `==`，会静默产出错误 Token 流，直接击穿阶段 0 出口门（Token 流逐项全等，零容忍）。

**规避路径（已采用，见 token.sla）**：用 `i32` tag 常量 + `@const` 表达 `Token.Tag`，逐项对齐 Zig 声明序；整数比较实测稳定（最小整数-tag 用例 PASS）。每条 tag 常量的数值映射写入 token.sla 注释，供发射逐字节对拍按名核对。**这是一条显式登记的表示策略，不是静默降级**——Zig→SLA 的 enum 变体在此改形为整数常量，需在阶段 1「AST 表示形态定型文书」中一并追认（AST 的 enum 也有同类比较风险）。

**待裁决**：这是编译器缺陷（enum 相等应可靠）还是既定语义（enum 只能 match 消费）？若属前者，应另立修复线而非仅在本项目规避；本项目当前按「有规避路径的障碍」登记，不阻塞阶段 0。

### OBS-2：`sa test` 与 `sa check` 解析路径不一致（同一源码不同判定）

上述 OBS-1 的 `!= E::A` 用例在 `sa check` 通过、`sa test` 报语法错。两条命令经同一 dev 插件，但对注解/类型表达式的解析面不同。**影响**：以 `sa check` 为门禁的模块可能在 `sa test` 暴露解析分歧；阶段出口门若混用二者需统一。建议阶段门统一走规范口径（EXECUTION_PLAN 已规定全套件用 test/规范口径），check 仅作快检。

## 三、产物

- `crates/sla-lexer/src/token.sla`：Token/Token.Loc/Token.Tag 的 SLA 表示（整数 tag 策略），已 `sa check` 通过。声明序与 Zig `lexer.zig:3-114` 及 Rust `sla-lexer/src/token.rs` 一一对应。
- 本文件：探针发现登记。

## 四、下一步（阶段 0 正式入口条件）

EXECUTION_PLAN §3 阶段 0 的入口为「双探针结论已出；G6/G7 完成」。本报告只完成前置可行性探针（语言能力 + 表示策略），**双探针 A（build-js 计时）/ B（规模）与 G6/G7 尚未执行**。按既定纪律，不越过入口门直接宣告阶段 0 开工；本报告作为双探针之前的技术侦察归档。
