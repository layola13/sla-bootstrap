# sla-bootstrap —  Working Memory

> 本文件是给 AI agent 的持久记忆（随 AGENTS.md 约定自动加载）。更新日期 2026-11-17。
> 目标：用 SLA 重写 sa_plugin_sla 全部产品模块（A=stage0 Zig 裁判 / B=stage1 全 SLA / B'=stage2 自编译）。
> 详细计划在 EXECUTION_PLAN.md、SPLIT_PLAN.md；本文件只记已实测的事实与进度，避免重复踩坑。

## 铁律/口径（用户已裁决）

- **不建支线**：sla-bootstrap 的 `main` 就是主线，直接提交推送，不要新建 branch。
- **stage0 基线 = 含 transfer 的最新 master**（用户裁定，不用旧 tag 0.1.9）：
  - sci `bcafc71f`（transfer IR + emit_c provenance 修复）
  - sa_plugin_sla `f27d2031`（transfer 发射 + 候选修复）
  - sala `0371c49`（transfer 文档）
- **auto-sync**：本仓有外部 auto-sync 进程持续把工作树 checkpoint 提交并推送（日志形如 `checkpoint: auto-sync ... CST`）。HEAD 会在你工作期间增长。**动手前先看 `git log`，成果用显式 commit 固化**（auto-sync 会推）。不要 stash 后快进覆盖别人的 checkpoint。
- 推送方法见根 `/content/sa_all/AGENTS.md` 的 GIT_TOKEN 段（从 /proc 就地取，不落盘）。

## 构建/测试环境（实测可用）

```
export LD_LIBRARY_PATH=/content/tools/llvm14/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
export SA_STD_DIR=/content/sa_all/sci/sa_std
export PATH=/content/sa_all/sci/zig-out/bin:$PATH
SA_PLUGIN_DEV=1 sa check <file.sla>     # 解析+类型检查
SA_PLUGIN_DEV=1 sa test  <file.sla>     # 跑 @test
SA_PLUGIN_DEV=1 sa build-exe <file.sla> -o <out>   # 需 main()；无 main 会在链接期失败但前端通过
```
dev 插件安装（改动插件源码后）：`cd sa_plugin_sla && SA_PLUGIN_DEV=1 sa plugin install --dev .`（可能 >2min，用长 timeout）。
`sa sla <verb>` 已 deprecated，直接用宿主 `sa <verb> <file.sla>`（按扩展名分派）。

## SLA 语法事实（探针实测，别再用 Zig/Python 习惯）

- 逻辑运算 `&&` / `||`（不是 `and`/`or`）。
- 循环 `while i < n { ... }`：**无括号、块后无分号**。
- 条件 `if cond { ... };`：**无括号、块后有分号**；if 体写多行。
- 声明只有 `let`（默认可变，可 `i = i + 1`）；函数体内无 `const`/`var`（`const` 是模块级）。
- struct 字面量 `Type { field: val }`；enum 变体 `Enum::Variant`，构造 `Enum::V { x: 1 }`。
- **struct 的 String 字段不接受字符串字面量**（被推断为 raw_ptr）→ 用 u64 id（字符串池索引）代替。
- 字节缓冲区用固定数组 `[u8; N]` + 显式长度（对齐 demos/rosetta/199、demos/cxu/04），不是 `[]const u8`。
- `@import "rel.sla"` 本地相对导入可用（已验证 ast↔checker 接缝）。

## 障碍登记（探针实测，未裁决的别静默绕过）

- **OBS-1（实质，有规避）**：枚举变体字面量相等比较语义不可靠——`let x=E::A; let y=E::A; x==y` 实测为 **false**（同一变量 `x==x` 为 true）；官方 06_enum_and_match 用 `match` 消费枚举正常。`if e != E::A { panic }` 在 `sa test` 路径报 `expected colon`（check 宽容）。→ **表示策略：用 i32 tag 常量代替 enum 变体比较**（已用于 token.sla/ast.sla/checker.sla）。是否属编译器缺陷待裁决；若修，另立修复线。
- **OBS-2**：`sa check` 与 `sa test` 对同一源码解析路径不一致；阶段门统一走规范口径（test 全套件），check 仅快检。

## 进度（main 主线，均已推送）

- `deb7c83` 阶段 0 探针：token.sla（93 个 tag，对齐 Zig lexer.zig / Rust sla-lexer）、STAGE0_PROBE.md 障碍登记。
- `bef3f1f` 阶段 1 地基：ast.sla（Node 表示）、checker.sla（仿射状态机）。
- `43e8a78` 阶段 1 补全：ast 补齐 58 个 Node tag（声明序对齐 Zig union/Rust node.rs）、checker 加表达式类型推断。
- `fc8454f` 阶段 1 深化：ast 展开全部 84 个 payload struct（543 行）、checker 加调用 ABI 能力与借用释放（@test 4/4）、tools/crosscheck_tags.py 对拍 harness（lexer 93/93、ast 58/58 名集序全等）。
- `c60fbd0` 阶段 0 核心：lexer.sla 完整 next()（关键字 u64 字节打包、hex/浮点/符号/字符串/注释），@test 3/3；crosscheck 增加关键字表 1:1（36/36）。关键字打包坑：len 不能与第8字节重叠，改长度单列判定。
- 验证状态：token/ast/checker 均 `sa check` 通过；checker @test 4/4 PASS、ast 1/1 PASS；本地 @import 接缝可用；对拍 harness PASS。
- 参考架构：layola13/sla Rust 版 11-crate 单向依赖拓扑（sla-abi/lexer/ast/parser/checker/lowering/codegen-text/codegen-sab/plugin/oracle/cli）；token/ast/checker 的 Rust 实现是逐字段镜像规格，可直接对照。

## 下一步（未做，按 EXECUTION_PLAN）

1. ast 通用 payload 槽 → 展开为 Zig 的 84 个真实 payload struct（按 usage 增补，显式登记）。
2. checker 补借用/调用/宏/extern 契约规则（对齐 11,873 行 Zig checker / Rust sla-checker 各模块）。
3. **差分对拍 harness**（阶段出口门核心判据）：A(Zig) 与 B(SLA) 对冻结语料发射 SA text 逐字节相等；行为失败名字集三方相等。当前只有自洽 @test，未对拍。
4. 双探针 A(build-js vs native 计时)/ B(规模) 与 G6/G7 前置门核账尚未执行——不越过入口门宣告阶段 0 正式开工。
