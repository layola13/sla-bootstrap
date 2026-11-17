# sla-bootstrap

以 SLA 重写 SLA 编译器自身（`sa_plugin_sla` 的全部产品模块，约 104,300 行；裁判组不移植）。

- **A（stage0）** = Zig 构建的现行插件，取 tag 0.1.9 版，冻结为对拍裁判。
- **B（stage1）** = 全部产品模块由 SLA 构建的插件，作为 SA 宿主的 sla 插件运行。
- **B'（stage2）** = 用 B 编译编译器自身的 SLA 源码产出的插件。

## 验收口径（蓝图 §6）

1. **自编译**：B 能被宿主加载、描述符 ABI 逐字段相等，并能编译编译器自身的全部 SLA 源码产出 B'。
2. **发射对拍（核心判据）**：A、B、B' 对冻结语料全集（tests/** + demos/**）做 text 后端发射，SA 文本产物逐字节相等。
3. **行为对拍**：三者跑规范口径全套件，失败名字集三方相等；诊断类用例的诊断名与文本相等。

不追求 .so 字节相等；不追求后端独立——产品输出恒为 SA text，宿主负责 native 路。

## 文档

- [EXECUTION_PLAN.md](EXECUTION_PLAN.md) — 执行计划：前置门 G1–G7、双探针（build-js 计时 / 规模）、12 阶段表、规模墙对策、完成定义、待裁决点。
- [SPLIT_PLAN.md](SPLIT_PLAN.md) — 分拆蓝图（2026-11-02 定调，含 §9 JS/Bun 快验变体）：12 阶段划分、§6 验收、§7 登记式回退 R1–R7。
- [docs/BOOTSTRAP_AUDIT_VERIFY.md](docs/BOOTSTRAP_AUDIT_VERIFY.md) — 外部自举审计的逐条对源核实（2026-11-17）：哪些障碍属实、哪些已被证伪。
- [stage0/PIN.md](stage0/PIN.md) — stage0 源码钉版与产物冻结规程。
- [registry/STAY_IN_ZIG.md](registry/STAY_IN_ZIG.md) — 留 Zig 登记表：未自举面必须在此显式登记，不许静默缺席。

## 开发约定

- 路线按 EXECUTION_PLAN 的 12 阶段推进，一阶段一交付，阶段出口门以名字集对拍为准（只看计数不算过）。
- 任一模块留 Zig，当轮同步更新 registry/STAY_IN_ZIG.md（模块名、行数、原因、边界接缝）。自举完成度以登记清单为准：已自举 X 行 / 登记留 Zig Y 行。
- 单文件不超过 700 行；Zig 大模块移植时拆为多个 SLA 文件，拆分图先写入阶段接缝说明。
- 编译器改动验证前清四面缓存：`.sla-cache`、`~/.cache/sa/frontend`、`.zig-cache`/`zig-out`、各测试目录 `.sa_cache`。
- JS/Bun 只作开发期快验（必须经 SA 宿主 build-js 路，不许 SLA 直出 JS 绕过验证）；产品与收官门恒为 native。
- 提交后由仓库所有者安排审核；审核口径 = 本仓验收三条 + 阶段出口门证据。
