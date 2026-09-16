# Skill-Auto-Eval

## 1. 环境准备


- 推荐 Python **3.12**
- 安装阶段需要访问 Python 包索引及 GitHub Releases。
- 运行效果评测还需要安装并登录 `eval.yaml` 所指定的 Agent Engine，如 Claude Code 或 Codex，并配置其模型服务。
- 单独运行安全静态扫描不需要效果评测的 Engine 或模型密钥。

以下命令使用 Linux Bash 和已有的 `Unlimited-OCR` conda 环境（本机为 Python 3.12.13），无需再创建 `.venv`：

```bash
source /home/quyuan/miniconda3/etc/profile.d/conda.sh
conda activate Unlimited-OCR
cd /home/quyuan/quyuan/auto_eval/Skill-Auto-Eval
# 避免 ~/.local 中其他 Python 环境的包干扰当前环境
export PYTHONNOUSERSITE=1
python --version
python -c 'import sys; print(sys.executable)'
```


## 2. 首次安装

### 安装 Skillspector 和本项目命令

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

`requirements.txt` 当前固定 `skillspector==2.11.2`，从 Python 包索引获取发布包。本项目采用 editable 安装，便于在仓库中开发；两个上游工具不使用源码安装。

如果包索引没有对应版本或缺少当前 Python/平台的可用包，安装会失败；请检查发布情况及 Python 版本，不要把依赖安装失败当作评测失败。

### 安装 skill-up Linux Release

当前 `skill-eval install --tool skill-up`（包括默认的 `--tool all`）只调用 PowerShell 安装脚本，Linux 请使用下面的 Bash 步骤。需要 `curl`、`tar`、`sha256sum` 和 `install`。

固定版本便于复现；安装到当前 conda 环境的 `bin`，不覆盖 `~/.local/bin` 中可能已有的旧版本：

```bash
(
  set -euo pipefail
  : "${CONDA_PREFIX:?请先 conda activate Unlimited-OCR}"
  skill_up_version=0.11.0
  case "$(uname -m)" in
    x86_64) skill_up_arch=amd64 ;;
    aarch64|arm64) skill_up_arch=arm64 ;;
    *) echo "不支持的架构：$(uname -m)" >&2; exit 1 ;;
  esac
  skill_up_archive="skill-up_${skill_up_version}_linux_${skill_up_arch}.tar.gz"
  skill_up_url="https://github.com/alibaba/skill-up/releases/download/v${skill_up_version}"
  skill_up_tmp=$(mktemp -d)
  trap 'rm -rf "$skill_up_tmp"' EXIT
  cd "$skill_up_tmp"
  curl -fL --retry 3 "$skill_up_url/$skill_up_archive" -o "$skill_up_archive"
  curl -fL --retry 3 "$skill_up_url/skill-up_${skill_up_version}_checksums.txt" -o checksums.txt
  awk -v name="$skill_up_archive" '$2 == name {print; found=1} END {if (!found) exit 1}' checksums.txt > selected-checksum.txt
  sha256sum --check selected-checksum.txt
  tar -xzf "$skill_up_archive" skill-up
  install -m 0755 skill-up "$CONDA_PREFIX/bin/skill-up"
)
```

### 配置路径并验证

在已激活 `Unlimited-OCR` 的同一个 Bash 终端设置：

```bash
export SKILL_UP_BIN="$CONDA_PREFIX/bin/skill-up"
export SKILLSPECTOR_BIN="$CONDA_PREFIX/bin/skillspector"
hash -r

python -m skill_eval.cli --help
"$SKILL_UP_BIN" --version
"$SKILLSPECTOR_BIN" --version
```

后文使用 `python -m skill_eval.cli`，确保通过当前 conda Python 运行，避免 PATH 中其他环境的 `skill-eval` 启动脚本干扰。安装成功后也可使用 `"$CONDA_PREFIX/bin/skill-eval"`。

上述环境变量只影响当前终端；新终端需重新激活环境并设置。也可在每次运行时通过 `--skill-up` 和 `--skillspector` 指定绝对路径，命令行参数优先于环境变量。两者均未配置时使用 PATH 中的同名命令。

## 3. 升级和版本管理

### 升级 Skillspector

编辑 `requirements.txt` 中的版本号，再执行：

```bash
python -m pip install --upgrade -r requirements.txt
"$SKILLSPECTOR_BIN" --version
```

CLI 也支持只安装指定版本的 Skillspector：

```bash
python -m skill_eval.cli install --tool skillspector --skillspector-version 2.11.2
```

直接安装不会自动修改 `requirements.txt`，应同步更新该文件。不要在 Linux 上执行不带 `--tool skillspector` 的安装命令，默认流程会调用 Windows 脚本。

### 升级或切换 skill-up

将上方 Linux Release 安装代码中的 `skill_up_version` 改为实际发布的版本号，再执行整段安装代码并检查：

```bash
"$SKILL_UP_BIN" --version
```

升级后建议先运行固定的小样本 Case，核对报告及退出状态，再用于正式提测。

### 更新本项目

更新仓库代码后，在仓库根目录执行：

```bash
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

```bash
"$SKILL_UP_BIN" validate /path/to/my-skill/evals/eval.yaml
```

配置格式参考 [skill-up 编写评测文档](https://alibaba.github.io/skill-up/guide/writing-evals.html)。

## 5. 发起提测

先替换以下路径为真实 Skill 目录；建议每次使用独立的输出目录，并放在被扫描的 Skill 目录之外。

```bash
skill_path="/path/to/my-skill"
eval_path="$skill_path/evals/eval.yaml"
mkdir -p "$PWD/results"
output_path=$(mktemp -d "$PWD/results/$(date +%Y%m%d-%H%M%S)-XXXXXX")
```

### 完整评测

```bash
python -m skill_eval.cli run \
  --skill "$skill_path" \
  --eval "$eval_path" \
  --suite all \
  --output "$output_path"
```

先执行 skill-up，再执行 Skillspector。已启动的效果评测即使返回非零，仍继续安全扫描；输入路径或必要参数校验失败时不会开始完整流程。

### 只评可用性和效果

```bash
python -m skill_eval.cli run \
  --skill "$skill_path" \
  --eval "$eval_path" \
  --suite effectiveness \
  --output "$output_path"
```

### 只评安全性

```bash
python -m skill_eval.cli run \
  --skill "$skill_path" \
  --suite security \
  --format json \
  --output "$output_path"
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

在已有 `Unlimited-OCR` conda 环境的 Linux Runner 上，先按第 2 节安装固定版本 skill-up，再使用以下 Bash 脚本（按 Runner 实际位置调整路径）：

```bash
#!/usr/bin/env bash
set -euo pipefail
source /home/quyuan/miniconda3/etc/profile.d/conda.sh
conda activate Unlimited-OCR
export PYTHONNOUSERSITE=1
cd /home/quyuan/quyuan/auto_eval/Skill-Auto-Eval
python -m pip install -r requirements.txt
python -m pip install -e .
export SKILL_UP_BIN="$CONDA_PREFIX/bin/skill-up"
export SKILLSPECTOR_BIN="$CONDA_PREFIX/bin/skillspector"
"$SKILL_UP_BIN" --version
"$SKILLSPECTOR_BIN" --version
mkdir -p "$PWD/results"
ci_output=$(mktemp -d "$PWD/results/ci-XXXXXX")
python -m skill_eval.cli run \
  --skill /path/to/my-skill \
  --eval /path/to/my-skill/evals/eval.yaml \
  --suite all \
  --output "$ci_output"
```

完整评测还需事先安装并配置 `eval.yaml` 指定的 Engine 和模型凭证。`set -e` 会让安装或评测失败时保留非零退出状态。

按 CI 平台的 secret 注入机制配置凭证。使用全新的工作目录或输出目录，保留原始报告作为受控访问的产物。

## 8. 常见问题

- **找不到 skill-eval**：确认已在当前 Python 环境执行 `python -m pip install -e .`；优先使用 `python -m skill_eval.cli`，或 `"$CONDA_PREFIX/bin/skill-eval"`。若出现 `bad interpreter`，检查是否误用了 `~/.local/bin` 中属于其他环境的旧脚本。
- **Skillspector 安装失败**：检查 Python 是否为 3.12–3.14、固定版本是否已发布，以及依赖包在当前平台是否可安装。
- **找不到评测器**：检查 `SKILL_UP_BIN`、`SKILLSPECTOR_BIN` 或显式可执行文件路径；确认路径位于当前 `$CONDA_PREFIX/bin`，且文件有执行权限。
- **GitHub Release 下载失败**：检查版本、网络、代理和 GitHub API 限额；重新安装前先确认下载错误原因。
- **效果评测报模型或鉴权错误**：检查 `eval.yaml` 和对应 Agent Engine 的登录/模型配置。工具安装成功不等于模型服务已配置。
- **安全评测非零退出**：查看安全报告区分实际风险与扫描执行错误，不要仅凭退出码判定 Skill 恶意。

## 9. 开发测试

在仓库根目录、已激活的 `Unlimited-OCR` 环境中运行：

```bash
python -m pip install pytest
python -m pytest -q
```

### 安全扫描冒烟测试

下面创建临时 Skill，并调用真实 Skillspector；无需模型密钥。输出保留在打印的临时目录中，便于检查：

```bash
smoke_root=$(mktemp -d /tmp/skill-auto-eval-smoke-XXXXXX)
mkdir -p "$smoke_root/skill"
cat > "$smoke_root/skill/SKILL.md" <<'EOF'
---
name: greeting-smoke
description: Return a short greeting when the user asks for a greeting.
---
When asked for a greeting, reply with "Hello!". No tools or file access are needed.
EOF
set +e
python -m skill_eval.cli run \
  --skill "$smoke_root/skill" \
  --suite security \
  --format json \
  --output "$smoke_root/results"
smoke_status=$?
set -e
printf '退出码：%s\n报告目录：%s\n' "$smoke_status" "$smoke_root/results"
python -m json.tool "$smoke_root/results/security.json"
exit "$smoke_status"
```

开发测试验证 CLI 基本行为；安全冒烟测试验证真实扫描和报告生成。效果评测需另备真实 `eval.yaml` 和模型服务，以上测试不代表效果评测已通过。
