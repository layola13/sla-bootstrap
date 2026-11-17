# stage0 钉版清单

stage0 = tag 0.1.9 的 Zig 版工具链，作为自举全程的对拍裁判，终局后冻结保留、不退役。

## 源码钉（tag 0.1.9，三仓同名 tag）

| 仓 | tag | 提交 |
|---|---|---|
| layola13/sci | 0.1.9 | aad61424 |
| layola13/sa_plugin_sla | 0.1.9 | 42085bb9 |
| layola13/sala | 0.1.9 | c4d6d071 |

移植源钉：sa_plugin_sla 产品模块以开工时 G7 终测的 master 为准（EXECUTION_PLAN §1 G7）；行数盘点基线为 76b4f9af（116,294 行 / 49 文件，产品代码约 104,300 行）。

## 产物冻结（开工早期步，未完成）

本机目前没有冻结的 tag 0.1.9 产物（盘点见 EXECUTION_PLAN §7；cycle-5 era 钉版产物不得冒充 0.1.9）。

冻结规程：

1. 在 8 核机从上表 tag 源码重建 A：宿主 `sa` + 插件 `libsla.so`。
2. 产物 + sha256 清单存入本目录（`stage0/`），并同步主备份（Google Drive）。
3. 冻结后，任何阶段门所称 stage0 均指此产物，不许用现行 master 构建替代。

产物二进制不入 git（见 .gitignore），只以 sha256 清单登记：

| 产物 | sha256 | 状态 |
|---|---|---|
| sa（宿主） | — | 待冻结 |
| libsla.so（stage0 插件） | — | 待冻结 |
