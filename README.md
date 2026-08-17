# Output-algo

手表日志自动剪切 + 按测试分组整理工具（Windows，打包为 exe）。

## 功能

1. **自动检测手表 U 盘**：按优先级依次检测 E 盘、I 盘上的 `algo` 文件夹
   - 未检测到任何盘符 → 提示「U盘未连接成功」
   - 检测到盘符但无 `algo` 文件夹 → 提示「未检测到」

2. **剪切日志到本地**：将手表上 `algo` 文件夹整个剪切到 `D:\Suunto\Output-algo\algo\`

3. **按测试分组整理**：按文件名「功能_时间戳_序号.ext」解析并分组
   - 按功能名分桶
   - 遇到序号 `0` 开启一个新测试，后续 `1~n` 归入该测试
   - 每个测试生成文件夹：`功能_YYYYMMDD_HHMMSS_测试N`
   - 时间取该测试序号 `0` 文件的时间戳，自动转北京时间
   - 测试文件夹生成在 `algo\` 文件夹内部

4. **误触识别**：若某测试组只有序号 0（无后续文件），且后面还有其他测试组
   - 判定为误触日志开关
   - 该文件不建立文件夹，单独留在 `algo` 根目录
   - 后续真正的测试从「测试1」重新计数

## 使用方式

USB 连接手表后，双击 `D:\Suunto\Output-algo\Output-algo.exe` 即可。

### 目录结构

```
D:\Suunto\Output-algo\
├── Output-algo.exe            # 程序（双击运行）
├── output_algo.py             # 源码备份
└── algo\                      # 剪切过来的日志
    ├── Alg_Ohr_20260817_153128_测试1\   # 分组后的测试文件夹
    │   ├── Alg_Ohr_1786956940_0.sot
    │   ├── Alg_Ohr_1786957000_1.sot
    │   └── ...
    ├── Alg_Ohr_20260817_153400_测试2\
    └── Alg_Ohr_1786956500_0.sot         # 误触的文件（单独序号0，无后续）
```

## 开发 / 打包

环境：Python 3.x（Windows）

```bash
# 安装依赖
pip install pyinstaller

# 打包为单文件 exe（无控制台窗口）
python -m PyInstaller --onefile --noconsole --name "Output-algo" --distpath "D:\Suunto\Output-algo" output_algo.py
```

## 文件名规则

支持的命名格式：`功能名_时间戳_序号.扩展名`

| 部分 | 说明 | 示例 |
|------|------|------|
| 功能名 | 可以包含下划线，会自动拼接 | `Alg_Ohr` |
| 时间戳 | 纯数字，支持 10 位（秒）、13 位（毫秒）、14 位（YYYYMMDDHHMMSS）、17 位（带毫秒） | `1786696940` → `20260814_164220` |
| 序号 | 纯数字，同一测试内从 0 开始递增 | `0`, `1`, `2`, ... |
| 扩展名 | 任意 | `.sot` |

## 安全提示

- **Personal Access Token (PAT)**：向 GitHub 推送代码时，请勿使用账号密码。请在 GitHub 设置中生成 Personal Access Token，在被要求输入密码时粘贴 Token。
- `.gitignore` 已默认忽略日志数据文件（`.sot`）、备份文件夹、打包好的 exe。如需将 exe 纳入仓库，请注释 `.gitignore` 中的对应行。
