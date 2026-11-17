# SLA 自举分拆计划（SPLIT_PLAN）

> 性质：测绘与计划文档，不含任何实现代码。用户定调（2026-11-02）：分拆推进——编译器按模块逐件移植、逐件验收，不整体一次性迁移。
> 范围：`sa_plugin_sla`（SLA 前端编译器）用 SLA 重写；sci（SA 工具链：汇编/链接/flattener/verifier/SAB 编码）不在本计划范围，其自举是更后一档的事。

## 0. 测绘口径与素材

- 测绘树：`~/workspace/integ-vt`，HEAD = `962544c9d4ea6b03dfb654101a163508f37db035`（本地 master 口径）。
  - **注意**：该 HEAD 早于远端 master `b8a1eed4`（乙案集成）与在飞的甲案/SAB 修复线——检查层与双后端文件正在被那几条线编辑，模块清单的行数会在阶段 0 开工前按 G7 重测。本次测绘的文件构成与 import 关系不因那几批改变（它们改的是函数体，不是模块边界）。
- 行数：`wc -l src/*.zig` 实测；耦合：逐文件 `grep @import(...)` 实测（去 std/builtin 后）。
- 总量：`src/*.zig` 共 **89,624 行 / 41 文件**；其中测试与驱动 10,999 行（plugin_tests 10,217 + batch_test_runner 670 + test_driver 57 + test_math_driver 55），**产品代码 ≈ 78,625 行**。
- 语料：`tests/*.sla` 310 个 + `tests/diagnostics/*.sla` 16 个 + import_fixtures/；规范门禁口径 = 仓根 cwd + `SLA_NO_FRESHNESS_CACHE=1` + `SA_SLA_FIXTURE_DIR=<仓>/tests/import_fixtures/`，判读只认**失败名字集**。
- 构建事实（build.zig 实测）：插件根模块 = `src/plugin.zig`，产物为动态库（`linkage = .dynamic`，库名 `sla`）；构建期注入三个外部模块：`plugin_api`（本仓 src/plugin_api.zig）、`sci_bridge` 与 `sio`——**后两者不在本仓**，分别位于 sci 树的 `src/plugin_bridge.zig`（298 行，转发 sci 的 flattener/sab/verifier + `encodeSabFromFlat*`）与 `src/sa_io.zig`（749 行，IO 兼容层），经 `resolveRepoRoot` 定位到同级 sci 检出。

## 1. 模块清单（按耦合分层）

职责标注：无标记 = 已读文件头/导出面确认；† = 按文件名与 import 关系推定，未逐行测绘。

### 1.1 纯前端层（词法/语法/AST/源码变换）

| 模块 | 行数 | 职责 |
|---|---|---|
| lexer.zig | 530 | 词法器：字节流→Token 流（Tag/Loc 亦定义于此）；**零本地 import**（仅 std） |
| ast.zig | 517 | AST 节点与类型定义（tagged union Node 全体）；零本地 import |
| parser.zig | 4,597 | 递归下降语法分析，产 AST；import ast/lexer/source_expand/host_paths + **lowering_rules（反向边，见 §2）** |
| contract_parser.zig | 232 | .sai 契约/声明文件解析；零本地 import |
| source_expand.zig | 450 | 源码级展开（元组展开指令等文本-结构变换）；仅 import sio |
| defer_desugar.zig | 366 | defer 语句在 AST 上的去糖；仅 import ast |
| control_flow_rules.zig | 276 | 控制流规则（checker 与 lowering 共享的小规则集）；仅 import ast |
| syntax_lowering.zig | 1,340 | 语法层 lowering（AST→AST/检查前变换）；import ast/contract_parser/type_checker |

### 1.2 检查层

| 模块 | 行数 | 职责 |
|---|---|---|
| type_checker.zig | 7,286 | 类型/所有权检查（含 drop 计划、taint、宏检查等）；import ast/contract_parser/control_flow_rules/parser + lowering_rules |
| lowering_rules.zig | 9,952 | 检查层与双后端共享的语义规则（类型布局、VecAbi 常量、drop/移动规则等）；import ast/control_flow_rules/parser/type_checker——**与 checker、parser 互引，见 §2 SCC** |
| monomorphizer.zig | 1,969 | 泛型单态化；import ast/parser |

### 1.3 发射层（双后端）

| 模块 | 行数 | 职责 |
|---|---|---|
| codegen.zig | 17,317 | text 后端：AST+检查结果→SA 文本；import ast/contract_parser/lowering_rules/parser/type_checker |
| sab_codegen.zig | 20,644 | SAB 后端：构造 flat 指令列，经 `sci_bridge` 调 sci 的 verifier 校验并由 `encodeSabFromFlatUnchecked` 编码为 SAB 字节——**字节级编码不在本模块、在 sci**；import 上列 + host_paths/sci_bridge/sla_build_options |

### 1.4 宿主耦合层（插件入口/ABI/导入系统/编排/文件与进程面）

| 模块 | 行数 | 职责 |
|---|---|---|
| plugin_api.zig | 119 | 宿主 ABI 契约类型：Context（含 log/broker 函数指针）、PluginDescriptor、HostStream、extern 结构体；仅 std |
| plugin.zig | 271 | .so 根：导出 `saasm_plugin_descriptor_v1`（数据符号）与 `saasm_plugin_descriptor_v1_fn`，描述符内嵌 `handle_command = runSlaCommandAbi`（C 调用约定）；import 几乎全部模块 |
| plugin_handler.zig | 169 | 导出 `sla_compile_handler` / `sla_compile_handler_result_free`（handler 编译 ABI） |
| handler_bridge.zig | 363 | handler ABI 到完整编译管线的桥；import 前端+检查+单态化全链 |
| plugin_compile.zig | 1,046 | 编译管线编排：read→source expand→parse→import expand→monomorphize→check→codegen（管线序据 plugin_freshness.zig 文件头注释） |
| plugin_commands.zig | 626 | 插件命令分发（runSlaCommandImpl 本体）† |
| plugin_cli.zig | 502 | 独立 CLI 入口面 † |
| local_cli.zig | 104 | 本地 `sla` 命令入口（import plugin.zig/plugin_api） |
| plugin_imports.zig | 446 | 导入解析（路径/包）† |
| plugin_import_expand.zig | 1,447 | 导入展开（被导入文件的展开与宏索引缓存面）† |
| plugin_imported_macros.zig | 401 | 导入宏的登记与展开 † |
| plugin_module_table.zig | 943 | 模块表（已加载模块的登记/查询）† |
| plugin_reachability.zig | 2,628 | 可达性分析（模块/声明级）† |
| plugin_emit_reachability.zig | 333 | 发射期可达性收集（plugin.zig 直接取用其 collect* 函数） |
| plugin_project_shortcuts.zig | 1,678 | 工程级快捷路径（项目形态的编译捷径）† |
| plugin_freshness.zig | 319 | 全编译新鲜度门：依赖闭包内容哈希→产物缓存复用，经宿主 broker cache 运算（plugin_api broker_op 5/6） |
| workspace.zig | 705 | 工作区/包解析（manifest 读取、成员枚举、源路径选择） |
| host_paths.zig | 108 | 宿主路径：home 目录、路径规范化、sa 可执行文件定位 |
| plugin_sab_paths.zig | 220 | SAB 产物路径解析 † |
| plugin_output_paths.zig | 101 | 输出路径解析 † |
| stability_metadata.zig | 386 | 稳定性元数据（被 plugin_cli/plugin.zig 引用）† |
| plugin_skills.zig | 153 | 插件技能描述（描述符 skills 数组来源）† |
| plugin_compile_options.zig | 36 | 编译选项类型（SlaCompileOptions） |
| sla_rt.zig | 45 | 进程级 Io 单例 + 环境变量读取（Zig 0.17 无环境文件访问的适配层） |

### 1.5 不移植（验收裁判，显式登记为非目标）

| 模块 | 行数 | 理由 |
|---|---|---|
| plugin_tests.zig | 10,217 | 语料/单测裁判：被测对象与裁判同体移植会使门禁失效，留 Zig |
| batch_test_runner.zig | 670 | 分批/监督测试运行器，同上 |
| test_driver.zig / test_math_driver.zig | 57 / 55 | 独立冒烟驱动，同上 |

### 1.6 外部依赖（sci 树，非本计划范围但构成边界）

| 模块 | 行数 | 职责 |
|---|---|---|
| sci_bridge（sci/src/plugin_bridge.zig） | 298 | 转发 sci 的 flattener/sab/verifier + SAB 编码入口 |
| sio（sci/src/sa_io.zig） | 749 | IO 兼容层（cwd/Child/args/stdout 垫片）；本仓 27 个文件引用 `sio.`，plugin_tests 内 374 处、sab_codegen 44 处、plugin_compile 24 处为最重 |

## 2. 依赖序与阶段划分

### 2.1 import 图的关键事实

- **叶子集**（零本地 import 或仅 ast/sio）：lexer、ast、contract_parser、source_expand、defer_desugar、control_flow_rules、sla_rt、plugin_api。
- **强连通分量 SCC-1 = {parser, lowering_rules, type_checker}，合计 21,835 行**：parser→lowering_rules、lowering_rules→{parser, type_checker}、type_checker→{lowering_rules, parser} 三向互引。Zig 靠惰性声明解析容忍互引；移植到 SLA 时这是必须先处理的一团。
- SCC 的对外依赖只有 ast、contract_parser、control_flow_rules、lexer、source_expand、host_paths——全部位于叶子/前端层，即 SCC 之下无未移植依赖，SCC 之上（syntax_lowering、双后端、handler_bridge）都单向依赖它。
- 管线方向：plugin_compile 串起 source_expand→parser→import_expand→monomorphizer→type_checker→{codegen, sab_codegen}；plugin.zig/plugin_handler 是最外层壳。

### 2.2 无环化处理（SCC-1 的边怎么切）

阶段 3 开工前先做一次**边审计**（只审计、不移植）：统计 parser 对 lowering_rules、lowering_rules 对 parser/type_checker、type_checker 对 lowering_rules 各自实际引用的符号数与种类。
- 若某条边的引用面是少数类型/常量（如布局常量、枚举）→ 把被引符号下沉到 ast 相邻的叶子模块（或 ast 本体），边即切断，被切模块可先行独立移植，原 Zig 侧同步改引新位置（双确认：编译+名集门）。
- 若引用面是函数级互调（如检查器回调规则函数）→ 以**接口桩**切：定义只含签名与类型的前置声明模块，Zig 侧与 SLA 侧各自实现/引用，运行时经现有 @import 接缝对接。
- 审计结论若显示边密不可切 → SCC-1 整体作为**一个阶段**移植（阶段 5 扩大版），不许硬拆出半成品。此判定点写进阶段 3 的交付物。

### 2.3 阶段划分（每阶段 = 独立交付 + 独立验收）

| 阶段 | 内容 | 依赖 | 备注 |
|---|---|---|---|
| **0（探针）** | **lexer** | 无 | 见 §3 |
| 1 | ast + contract_parser + control_flow_rules + defer_desugar | 0 | AST 在 SLA 侧的表示形态在本阶段定型（tagged union↔SLA 枚举、递归经 Vec/Box 间接）；后续所有阶段的地基 |
| 2 | source_expand + host_paths + sla_rt 对应面 | 1 | IO 相邻叶子；sio 引用在此阶段首次跨界（见 §4） |
| 3 | SCC 边审计（交付物=审计报告+切边清单）→ parser | 0,1,2 + 边审计 | parser 对 lowering_rules 的边按审计结论切/桩 |
| 4 | monomorphizer | 1,3 | |
| 5 | lowering_rules + type_checker（同阶段，或按阶段 3 审计结论拆二） | 1,3,4 | 全仓最重的一团（17,238 行）；深 drop 与集合面在此压满 |
| 6 | syntax_lowering | 1,5 | |
| 7 | codegen（text 后端） | 1,5 | 产物是文本，逐字节对拍最容易 |
| 8 | sab_codegen | 1,5 + sci_bridge 边界裁定（§7 R2） | flat IR 构造在本模块；编码在 sci |
| 9 | 导入系统组：plugin_imports + plugin_import_expand + plugin_imported_macros + plugin_module_table | 2,3,5 | 宏展开层在此组与阶段 5 交叉（§7 R3） |
| 10 | 编排组：plugin_compile + plugin_commands + workspace + plugin_reachability + plugin_emit_reachability + plugin_project_shortcuts + plugin_freshness + plugin_sab_paths + plugin_output_paths + stability_metadata + plugin_skills + plugin_compile_options | 4–9 | 文件/进程/缓存面集中于此组 |
| 11 | ABI 壳：plugin_api（类型）+ plugin_handler + handler_bridge + plugin_cli + local_cli + plugin.zig（描述符/命令入口） | 全部 + 前置门 G4 | 最薄但最受 build-lib 契约约束；可能含手写 SA 胶水（若有，显式登记） |
| — | plugin_tests 等裁判组 | — | 不移植（§1.5） |

阶段总数：**12 个移植阶段（0–11）**，外加阶段 3 内的边审计子交付。

## 3. 探针阶段（阶段 0）：lexer

**选择理由**（全部为实测事实）：
- 耦合最低：530 行，本地 import 为零（仅 std），输入=字节切片、输出=Token 流，不触 AST 所有权、不触集合、不触 IO。
- 链路最全：parser 的每个文件解析都过 lexer，语料 310+16 个文件全量敏感——任何 token 化差异都会在规范套件里以名字集变化显形，不存在「移植了但没被测到」。
- 边界最便宜：Token 是（tag, start, end）平坦三元组，可走「调用方缓冲填充」式 ABI 跨 Zig↔SLA 界，不需要把深层结构的所有权送过边界——探针验证的是**全链**（SLA 源码→旧编译器编译→产物接回 Zig 主体→跑套件），不是深水区。
- 次选 contract_parser（232 行、零 import）链路覆盖太窄（仅契约路径），落选；其落选理由本身写入本节以备复核。

**探针的接回形态**：SLA 版 lexer 经现行工具链编译为目标单元，由 build.zig 链入插件构建；parser.zig 在既有 `lexer.Lexer` 类型接缝后切换实现（Token 类型定义权在本阶段仍属 Zig 侧 lexer.zig 的类型声明，SLA 侧按三元组填充）——若该接缝在实施时被证明不可行，按 §7 回退形态处理并登记，不许另开静默通道。

**验收门**（缺一不算过）：
1. 规范口径全套件：仓根 cwd + `SLA_NO_FRESHNESS_CACHE=1` + `SA_SLA_FIXTURE_DIR=<仓>/tests/import_fixtures/`，失败**名字集**与阶段开工时冻结的基线逐一相等（当前已知基线 = import-scan 三件 {#59,#110,#111}，阶段 0 开工时按 G6 在当时 master 上重冻）。
2. 差分对拍：SLA lexer 与 Zig lexer 对 `tests/**` + `demos/**` 全部源文件的 Token 流逐项相等（tag/start/end 三元组全等），零容忍。
3. zig 单测名集不变（plugin_tests 裁判组在 Zig 侧原样运行）。

## 4. 每阶段的 SLA 侧需求映射

图例：●已具备（有实测/在役证据）◐部分具备/有替代面 ○未备（挂在修批次）

| 需求面 | 状态 | 用到的阶段 | 说明 |
|---|---|---|---|
| 字节/字符串切片处理 | ● | 全部 | sa_std 字符串面在役（三台服务器与 CXU 后端实证） |
| Vec 动态数组（含嵌套） | ●（语义收口中） | 全部 | 容器本身在役；**深层嵌套 drop 的正确性**见下行 |
| 深层嵌套 drop（Vec<结构体含 Vec 字段> 的赋值替换/释放） | ○ | 1,3,4,5,7,8,9 | **挂在修批次**：甲案 replace（实现中）、SAB walker 计数偏移修复（在跑）、deep_struct DS2（Jev 已定形 0.59，候甲案后）。AST 恰是此类负载的最深形态——阶段 1 的 AST 表示定型必须等 G1/G3 关账或给出经审计的表示规避（规避须登记，不许静默） |
| 递归（递归下降/递归数据） | ● | 1,3,5 | SLA 递归在役；递归类型经 Vec/Box 间接，Box/Rc 面有 §8.3 未覆盖项登记（深 drop 未覆盖面清单），阶段 1 需逐项核对所用间接形态不在未覆盖清单内 |
| tagged union / 枚举 payload | ● | 1 起全部 | SLA 枚举/match 在役（语料与三台实证）；Bend2 图谱中的「部分」评级针对设备面与 Bend 纪律，宿主侧 SLA 枚举是日常面 |
| 通用哈希表（符号表/驻留） | ○ | 3,5,9,10 | **已知缺口**：sa_std 集合以 BTreeMap/Set 为主，通用 HashMap 面薄（slaredis 成员索引手写开放寻址为旁证）。Zig 侧实测用量：type_checker 内 List/Map 类站点 100、codegen 225、sab_codegen 165、plugin_reachability 113（`grep -c` 量级）。替代=BTree（语义等价、性能交税，须给阶段 5 定编译时间预算）；正解=std 补通用哈希面（G5） |
| 大量字符串构建（ArrayList(u8) 等价面） | ◐ | 7,8 | Vec<u8> append 在役；**原生批量 append 原语缺**（GAP-BULKAPPEND，已登记，候 sci 批）——影响发射层性能，不影响正确性 |
| 格式化输出/诊断（allocPrint 等价面） | ◐ | 3,5,7,10 | Zig 侧 `std.fmt` 用量未单独测绘（**未测绘**）；SLA 侧格式化面存在但与 Zig fmt 的逐字一致性未验——诊断文本是名字集之外还要对拍的面（诊断语料 16 件 + test_error* 系列按名+诊断判读） |
| 文件 IO / 目录遍历 | ● | 2,9,10 | sa_std 文件面在役（服务器/CXU 实证） |
| 进程 spawn / 子进程 | ◐ | 10 | sa_std 进程面存在（三台与 CXU 编排在役）；新鲜度缓存与测试驱动的细粒度进程控制是否全覆盖**未测绘** |
| 内容哈希（新鲜度闭包哈希） | ◐ | 10 | std 第四批加密套件已落（哈希面存在）；plugin_freshness 实际所用算法与调用形态**未测绘** |
| 函数指针表 / extern 结构体 / 导出数据符号 | ○ | 11 | **挂 G4**：build-lib 契约文法实测仅标量+ptr（见 §5），描述符是「含函数指针的结构体数据符号」导出，不在契约文法直射范围内 |
| comptime/泛型元编程（Zig 习语） | ○ | 散布 | Zig 侧 anytype/comptime 习语（如 sio.ForwardWriter 泛型）在 SLA 无直接对应；逐模块审计，撞墙模块按 §7 回退 |
| 宏系统（被移植对象本身含宏检查/展开） | ◐ | 5,9 | 宏的检查在 type_checker、导入宏在 plugin_imported_macros、展开在 source_expand/import_expand；移植是数据变换问题，不依赖 SLA 自身宏设施——但移植后编译器处理宏重语料（.sla-cache 宏索引格式兼容）的行为对拍须进阶段 5/9 的门（见 §7 R3） |

## 5. 前置门清单（自举开工前必须先关）

| # | 事项 | 出处/状态 |
|---|---|---|
| G1 | 深 drop 甲案（句柄域 replace 语义）落地 master | 在飞实现线（基点 b8a1eed4，审计 AUDIT.md 已过门）；**未关** |
| G2 | SAB walker 计数偏移修复落地（emitVecElementDrops 改 VecAbi 常量、删静默兜底） | 在飞修复线；**未关**——其未关意味着规范口径下语料 SAB 腿仍红，任何阶段门都会被它污染 |
| G3 | deep_struct 场所读出 DS2 批（响亮拒绝+显式 take）落地 | Jev 已定形（DS2 0.59），排甲案后；**未关**——阶段 1 AST 表示定型依赖它 |
| G4 | build-lib ↔ 插件 ABI 对接实证 | `sa build-lib` 已在 sci 实现（cli.zig 7696 行起：契约 .sai 式 @export 清单→C 头+API 表+链接导出控制，.sla 源自动生成转发单元；目标 goal_69ea6e930fc7 的 GOAL.md 仅立项描述）。**但**：其实测契约类型文法仅 `i8..u64/f32/f64/ptr/void`，而宿主 ABI 需要导出数据符号 `saasm_plugin_descriptor_v1`（含函数指针字段的结构体）、`sla_compile_handler` 的 extern 结构体参数、Context 内的 broker 回调——能否经 build-lib 契约+SA 胶水表达，**未实证**。须以最小探针（一个只含描述符+空命令的 SLA 插件被 SA 宿主成功加载并应答 version 类命令）关账；**未关** |
| G5 | 通用哈希面裁定：std 补 HashMap 面，或正式接受 BTree 替代+阶段 5 编译时间预算 | 缺口已登记（§4）；**未关** |
| G6 | 基线冻结：在开工时 master 上以规范口径重跑并冻结语料失败名字集 + zig 单测名字集 | 程序性事项；当前已知语料基线为 import-scan 三件 {#59,#110,#111}（乙案集成记录口径）；**未执行** |
| G7 | 按开工时 master 重测模块清单（行数/import 图） | 本计划测绘树 962544c9 落后于在飞批次；**未执行** |

**未关计数：7 项**（实质 5 项 G1–G5 + 程序性 2 项 G6–G7）。

**每阶段的进入条件**（通用）：① 前置阶段已落地且其名字集门绿；② 本阶段 §4 映射中标 ○ 的需求面已关账或已按 §7 显式登记回退形态；③ 若 master 已移动，先按 G6 重冻基线再开工；④ 本阶段的跨界接缝（Zig↔SLA ABI 形状）在开工前写成一页接缝说明并经评审（后续阶段评审主体按主会话规程）。

## 6. 终局形态：stage 自举验证

终局在**阶段 11 落地时**成立，判法如下（适配经典 stage0/1/2 固定点到本仓现实）：

- 设 A = Zig 构建的现行插件 .so（stage0），B = 全部产品模块由 SLA 构建的插件 .so（stage1）。
- **验证一（自编译）**：用 B 作为 SA 宿主的 sla 插件，编译编译器自身的全部 SLA 源码，产出 B′（stage2）。B′ 必须能被宿主加载且描述符 ABI 逐字段相等（abi_version/descriptor_size/name/函数指针非空性）。
- **验证二（发射对拍，本判法的核心）**：A、B、B′ 三者分别对冻结语料全集（tests/** + demos/**）做 text 后端发射，**SA 文本产物逐字节相等**；SAB 后端经同一 sci 编码器，flat 构造确定性成立时 .sab 亦逐字节相等（若 flat 构造存在合法非确定序，以「解码后指令列相等」替代并登记理由）。
- **验证三（行为对拍）**：三者跑规范口径全套件，失败名字集三方相等；诊断类用例（test_error* + diagnostics/）的诊断名与文本相等。
- **不要求** .so 字节相等：A 与 B 的代码生成路径不同（Zig vs SLA 发射），.so 字节必然不同；固定点判据是「发射产物字节相等 + 行为名集相等」，不是镜像字节。B 与 B′ 同为 SLA 发射，若发射确定性成立，二者的发射产物（对任意输入，含编译器自身源码）逐字节相等即构成固定点——这是验证二在输入=编译器源码时自然给出的结论，无需另设判据。

## 7. 风险与止损

| # | 风险 | 撞墙形态与回退 |
|---|---|---|
| R1 | **SCC-1 互引团**（parser/lowering_rules/type_checker，21,835 行）：边审计证明不可切 | 阶段 5 按整团移植；若整团亦 stalls，该团**留 Zig**，自举状态显式降级登记为「前端+发射已自举、检查团未自举」，不许以「基本完成」含糊 |
| R2 | **sci_bridge 边界**：flattener/verifier/SAB 编码是 sci 的 Zig 内部 API，SLA 侧无 SA 级绑定面 | sab_codegen 的 flat 构造可移植，但其对 sci_bridge 的 5 处调用（校验+编码）需要 SA 级 extern 面；该面不存在或不完备时，sab_codegen **留 Zig** 并登记为未自举面（text 后端自举不受影响）。此项须在阶段 8 进入前以接缝说明裁定 |
| R3 | **宏展开层**：宏检查（checker 内）、导入宏登记/展开、.sla-cache 宏索引格式 | 移植后若宏重语料行为漂移（索引格式/展开序），按名字集门定位到阶段 5 或 9 回滚该阶段交付；宏索引二进制格式若必须变更，属格式版本事项，须单独评审，不许在移植批内顺手改 |
| R4 | **发射器字节级操作**：text 后端是字符串构建（风险低）；SAB 字节编码已在 sci（不在范围，风险已隔离）；残余风险在诊断/数字格式化逐字一致性 | 阶段 7 门含诊断语料文本对拍；不一致项逐项登记为格式化面缺口回 std 批，不许在发射器里手写补丁凑对拍 |
| R5 | **性能塌方**：BTree 替代 HashMap + SLA 发射开销使自举编译器显著变慢 | 阶段 5/7 各设编译时间预算（具体倍率在阶段进入时按当时基线定，写入接缝说明）；超预算先走 G5 正解（std 哈希面）与 GAP-BULKAPPEND，不许以放松对拍/名集门换速度 |
| R6 | **Zig 习语不可译**：comptime 泛型、anytype writer、错误集推断在个别模块深度使用 | 逐模块审计；不可译模块**留 Zig**，边界保持原 @import 接缝（Zig 侧继续提供同名模块实现），逐个登记进 §1.5 式「未自举面」清单 |
| R7 | **插件 ABI 表达力**（G4 探针失败）：build-lib 契约表达不了描述符数据符号 | ABI 壳（阶段 11）以**手写 SA 胶水单元**承载描述符与导出（build-lib 对 .sa 源直绑 @export 的路径已存在），SLA 侧只出实现体；胶水文件显式登记为未自举面，并在 sala/计划内标注其行数与形状——这是显式形态，不是静默降级 |

**止损通则**：任一模块留 Zig，必须在交付时同步更新本计划的未自举面登记（模块名、行数、原因、边界接缝）；终局验证（§6）只对「已自举面」宣称成立，未自举面清单随终局报告一并交付。自举完成度以登记清单为准，不以口头比例为准。

## 8. 未测绘（如实登记）

- plugin_commands / plugin_cli / plugin_imports / plugin_import_expand / plugin_imported_macros / plugin_module_table / plugin_reachability / plugin_project_shortcuts / plugin_sab_paths / plugin_output_paths / stability_metadata / plugin_skills 十二个文件的内部结构未逐行读（职责按文件名+import 图推定，标 †）；阶段 9/10 进入前须补测。
- Zig 侧 `std.fmt` 的逐文件用量未统计；sio 的逐文件用途分类未做（仅统计引用次数）。
- lowering_rules 中 VecAbi 之外被 parser/checker 跨引的具体符号清单未统计（即 §2.2 边审计本体，留作阶段 3 子交付）。
- build-lib 在盒上/CI 的实跑验收状态未核（仅核源码存在与设计注释）；G4 探针即为此设。

## 9. 2026-11-16 增补：JS/Bun 开发运行时变体（用户定，tag 后路线）

> 背景：Zig 与 Rust 两版编译器都慢——慢有两笔：① 编译器本体每次改动要重编原生插件/cargo（分钟级）；② 语料验证每文件付一遍 LLVM+链接（冷编剖析约 85% 在宿主后端）。本增补给自举加一个开发运行时变体，两笔都省。

- **形态**：自举开发期，SLA 编译器发射 JS、在 Bun 下运行作开发运行时。改一处只重新发射文本，不再重编原生插件；语料快验走 JS 发射顶替 LLVM+链接。
- **运行时选 Bun 不选 Node（用户定）**：Bun 支持 FFI（bun:ffi），extern 面可经 FFI 直调本地库——补上此前 JS 路「extern/FFI 验不了」缺口的大半。残余照不出：i64 精度语义、原生 codegen 本身，仍须 native 路验。
- **铁律**：JS 必须经 SA 宿主 build-js 路（照样过展平 + 所有权验证，检查一分不少，只是换发射目标）；禁止 SLA 直出 JS 绕过 SA 验证——否则 MemoryLeak 1012 类缺陷在 JS 路不可见，属静默降级。
- **定位**：JS/Bun 只是开发期快验运行时，不是产品目标；产品输出恒为 SA text → native，收官门仍为 native 全量。JS 的 goroutine 协作式运行时已接线在役，可直接复用。
- **终局衔接（§6）**：全部模块移植完成后，由 stage0（打 tag 的 Zig 版）把 SLA 编译器编成原生二进制——一次性慢编译可接受；验收 = 双编译对拍（Bun 版与原生版对冻结语料的发射产物逐字节相等 + 失败名字集相等），并入 §6 验证二/三。
- **顺序不变**：先收官打 tag、把语义用语料钉成合同，再开自举；本增补不改期、不挤当前清零工作。
- **开工第一步（探针）**：同一批语料 build-js 对 native 计时对拍，先证快再全面推——SAB 教训：未实测不宣称提速。
