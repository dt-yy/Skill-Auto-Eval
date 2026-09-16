# Skill-Auto-Eval

## 1. 环境准备


- 推荐 Python **3.12**
- 安装阶段需要访问 Python 包索引及 GitHub Releases。
- 运行效果评测还需要安装并登录 `eval.yaml` 所指定的 Agent Engine，如 Claude Code 或 Codex，并配置其模型服务。
- 单独运行安全静态扫描不需要效果评测的 Engine 或模型密钥。

进入仓库并创建虚拟环境：

```powershell
cd D:\pdf-bench-v2\Skill-Auto-Eval
python --version
```


## 2. 首次安装

### 安装 Skillspector 和本项目命令

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

`requirements.txt` 当前固定 `skillspector==2.11.2`，从 Python 包索引获取发布包。本项目采用 editable 安装，便于在仓库中开发；两个上游工具不使用源码安装。

如果包索引没有对应版本或缺少当前 Python/平台的可用包，安装会失败；请检查发布情况及 Python 版本，不要把依赖安装失败当作评测失败。

### 安装 skill-up Release

```powershell
skill-eval install --tool skill-up --skill-up-version latest
```


需要复现结果时，应指定已发布的固定版本，例如：

```powershell
skill-eval install --tool skill-up --skill-up-version 0.11.0
```

### 配置路径并验证

在运行评测的同一个 PowerShell 终端设置：

```powershell
$env:SKILL_UP_BIN = "$env:LOCALAPPDATA\skill-eval\bin\skill-up.exe"
$env:SKILLSPECTOR_BIN = "$PWD\.venv\Scripts\skillspector.exe"

skill-eval --help
& $env:SKILL_UP_BIN --version
& $env:SKILLSPECTOR_BIN --version
```

上述环境变量只影响当前终端；新终端需重新设置。也可在每次运行时通过 `--skill-up` 和 `--skillspector` 指定绝对路径，命令行参数优先于环境变量。两者均未配置时使用 PATH 中的同名命令。

## 3. 升级和版本管理

### 升级 Skillspector

编辑 `requirements.txt` 中的版本号，再执行：

```powershell
python -m pip install --upgrade -r requirements.txt
& $env:SKILLSPECTOR_BIN --version
```

为了保持版本锁定，推荐此方式。CLI 也支持直接安装指定版本：

```powershell
skill-eval install --tool skillspector --skillspector-version 2.11.2
```

直接安装不会自动修改 `requirements.txt`，应同步更新该文件。避免直接运行不带版本的 `skill-eval install`：其默认安装两个工具的最新版本，可能覆盖 requirements 中锁定的 Skillspector 版本。

### 升级或切换 skill-up

```powershell
# 更新到最新 Release
skill-eval install --tool skill-up --skill-up-version latest

# 或指定某个已发布版本
skill-eval install --tool skill-up --skill-up-version 0.11.0
& $env:SKILL_UP_BIN --version
```

不传 `--skill-up-version` 时，读取 `SKILL_UP_VERSION` 环境变量；未设置时为 `latest`。升级后建议先运行固定的小样本 Case，核对报告及退出状态，再用于正式提测。

### 更新本项目

更新仓库代码后，在仓库根目录执行：

```powershell
python -m pip install -e .
```

## 4. 准备待评测 Skill

典型目录：

```text
my-skill/
  SKILL.md
  scripts/
  references/
  evals/
    eval.yaml
    cases/
      availability.yaml
      normal-task.yaml
      negative-task.yaml
```

可用性和效果检查均通过 skill-up 的 Case 定义，当前没有单独的 `availability` suite。根据实际需要在 Case 中覆盖基本可用性、正常任务、边界和负向任务，并设定可验证的结果。

`eval.yaml` 必须填写实际使用的 Engine、模型、Case 路径和评分规则。相关凭证通过上游工具支持的环境变量或凭证存储配置，不放进 README、评测 Case 或 Git 仓库。

运行前可直接校验：

```powershell
& $env:SKILL_UP_BIN validate D:\path\to\my-skill\evals\eval.yaml
```

配置格式参考 [skill-up 编写评测文档](https://alibaba.github.io/skill-up/guide/writing-evals.html)。

## 5. 发起提测

先替换以下路径为真实 Skill 目录；建议每次使用独立的输出目录，并放在被扫描的 Skill 目录之外。

```powershell
$skillPath = "D:\path\to\my-skill"
$evalPath = Join-Path $skillPath "evals\eval.yaml"
$outputPath = Join-Path $PWD ("results\" + (Get-Date -Format "yyyyMMdd-HHmmss"))
```

### 完整评测

```powershell
skill-eval run `
  --skill $skillPath `
  --eval $evalPath `
  --suite all `
  --output $outputPath
```

先执行 skill-up，再执行 Skillspector。已启动的效果评测即使返回非零，仍继续安全扫描；输入路径或必要参数校验失败时不会开始完整流程。

### 只评可用性和效果

```powershell
skill-eval run `
  --skill $skillPath `
  --eval $evalPath `
  --suite effectiveness `
  --output $outputPath
```

### 只评安全性

```powershell
skill-eval run `
  --skill $skillPath `
  --suite security `
  --format json `
  --output $outputPath
```

安全扫描当前固定传递 `--no-llm`、`--fail-on-findings`，无需额外添加；暂未提供开启 LLM 或关闭风险门禁的参数。静态扫描不等于完全离线，上游工具可能查询依赖漏洞数据库。检测结果不能保证覆盖所有密钥或恶意行为。

### 常用参数

| 参数 | 说明 |
| --- | --- |
| `--skill` | 必填，待评测 Skill 目录；安全扫描会以此目录为工作目录 |
| `--eval` | skill-up 配置路径，`all`、`effectiveness` 必填 |
| `--suite` | `all`（默认）、`effectiveness`、`security` |
| `--skill-up` | skill-up 可执行文件路径，推荐绝对路径 |
| `--skillspector` | Skillspector 可执行文件路径，推荐绝对路径 |
| `--output` | 输出根目录，建议每次使用新目录 |
| `--format` | 仅影响安全报告：`json`（默认）、`terminal`、`markdown`、`sarif` |

更多参数：`skill-eval run --help`、`skill-eval install --help`。

## 6. 查看报告与退出码

指定 `--output` 后，输出结构示例：

```text
results/<本次运行>/
  security.json
  skill-up/
    iteration-N/
      result.json
      ...
```

skill-up 产物以实际版本和 `eval.yaml` 的报告配置为准。安全报告文件名为 `security.<format>`，例如 `security.markdown`。终端先显示子工具输出，最后显示包含各工具 `returncode` 的 JSON 摘要；stdout 不是单独的纯 JSON 文档，摘要目前不会自动保存为文件。

`skill-eval run` 的退出码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 所选评测工具全部返回 0 |
| `1` | 至少一个评测器失败或无法启动；查看摘要和原始报告 |
| `2` | 参数、输入路径等前置校验错误 |

工具无法启动时，该工具摘要中的 `returncode` 为 `127`，外层 `skill-eval run` 返回 `1`。`install` 子命令则返回安装进程的失败码。安全报告可能包含源码片段或敏感信息，不要自动提交原始扫描报告。

## 7. CI 使用

在安装好 Python 3.12、Engine、凭证的 Windows Runner 上，可使用固定版本：

```powershell
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pip install -e .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
skill-eval install --tool skill-up --skill-up-version 0.11.0
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$env:SKILL_UP_BIN = "$env:LOCALAPPDATA\skill-eval\bin\skill-up.exe"
$env:SKILLSPECTOR_BIN = (Get-Command skillspector).Source
skill-eval run --skill D:\path\to\my-skill --eval D:\path\to\my-skill\evals\eval.yaml --suite all --output .\results\ci
exit $LASTEXITCODE
```

按 CI 平台的 secret 注入机制配置凭证。使用全新的工作目录或输出目录，保留原始报告作为受控访问的产物。

## 8. 常见问题

- **找不到 skill-eval**：确认已在当前 Python 环境执行 `python -m pip install -e .`；也可用 `.\.venv\Scripts\skill-eval.exe`。
- **Skillspector 安装失败**：检查 Python 是否为 3.12–3.14、固定版本是否已发布，以及依赖包在当前平台是否可安装。
- **找不到评测器**：检查 `SKILL_UP_BIN`、`SKILLSPECTOR_BIN` 或显式可执行文件路径；skill-up 安装脚本不会自动配置 PATH。
- **GitHub Release 下载失败**：检查版本、网络、代理和 GitHub API 限额；重新安装前先确认下载错误原因。
- **效果评测报模型或鉴权错误**：检查 `eval.yaml` 和对应 Agent Engine 的登录/模型配置。工具安装成功不等于模型服务已配置。
- **安全评测非零退出**：查看安全报告区分实际风险与扫描执行错误，不要仅凭退出码判定 Skill 恶意。

## 9. 开发测试

```powershell
python -m pip install pytest
python -m pytest -q
```

