# Fusion Workflow

A multi-model Claude Code workflow where GPT-5.5 High manages the project and chooses the cheapest implementation agent likely to reach a verified result efficiently.

```text
GPT-5.5 High — technical lead / router
├── DeepSeek V4 Flash — abundant bounded implementation
├── MiMo-V2.5 — abundant alternate / race challenger
├── Qwen3.7 Plus — default implementation workhorse
├── MiniMax M3 — large-context specialist
├── Kimi K2.7 Code — long-horizon specialist
├── GLM-5.2 — terminal/debugging specialist
├── Sonnet 5 Low — premium closer
└── Sonnet 5 Medium — high-risk judgment-heavy implementation
```

Everything appears inside Claude Code. A local Anthropic-compatible gateway maps Fusion's fixed model aliases to Codex, OpenCode Go, and Claude.

The core rule:

> Route by expected total cost to a verified result, not by vague task difficulty and not by first-attempt price.

A hard parser with exhaustive tests may go to DeepSeek Flash. A small authentication change with weak verification may start on Sonnet.

## What the manager does

GPT-5.5 High:

- inspects the repository and resolves design ambiguity
- turns broad requests into explicit implementation contracts
- scores specification ambiguity, verification strength, coupling, blast radius, autonomy horizon, and context burden
- chooses a worker using task shape, relative scarcity, and learned history
- can race the two abundant models on low-risk objectively verifiable tasks
- reviews worker commits before integration
- repairs or escalates when the expected future value of the current route turns negative
- learns aggregate per-model outcomes in persistent agent memory

The manager does not normally write substantial features itself.

## Requirements

- Claude Code 2.1.200 or newer
- Python 3.9 or newer
- Git projects for isolated implementation worktrees
- an Anthropic-compatible gateway that routes the model aliases in `config/model-aliases.json`

For the first experiment, [Claude Code Router](https://github.com/musistudio/claude-code-router) is the recommended gateway. The wizard generates a CCR-oriented alias/profile bundle automatically.

## Install on macOS / Linux

```bash
mkdir -p ~/.local/share ~/.local/bin
git clone https://github.com/pikalover6/fusion-workflow.git ~/.local/share/fusion-workflow
chmod +x ~/.local/share/fusion-workflow/bin/fusion-flow
ln -sf ~/.local/share/fusion-workflow/bin/fusion-flow ~/.local/bin/fusion-flow
```

Make sure `~/.local/bin` is on your `PATH`. For zsh:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
exec zsh
```

Then:

```bash
fusion-flow wizard
fusion-flow doctor
```

## Install on Windows

Open PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.local\share", "$HOME\.local\bin" | Out-Null
git clone https://github.com/pikalover6/fusion-workflow.git "$HOME\.local\share\fusion-workflow"
Copy-Item "$HOME\.local\share\fusion-workflow\bin\fusion-flow.cmd" "$HOME\.local\bin\fusion-flow.cmd" -Force
```

Add `~\.local\bin` to your user `PATH` if needed:

```powershell
$bin = "$HOME\.local\bin"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (($userPath -split ';') -notcontains $bin) {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$bin", "User")
}
$env:Path += ";$bin"
```

Then:

```powershell
fusion-flow wizard
fusion-flow doctor
```

## First-run wizard

Run:

```bash
fusion-flow wizard
```

The wizard:

- checks whether a Claude Code Router executable is already available
- prints the official CCR release page if it is not installed yet
- asks for the local Anthropic-compatible gateway URL, defaulting to `http://127.0.0.1:8080`
- optionally records provider base URLs for GPT/Codex, OpenCode Go, and Claude
- writes Fusion's local launcher config
- generates a complete gateway profile bundle under your Fusion config directory

Generated files:

```text
~/.config/fusion-workflow/gateway-profile/fusion-gateway-profile.json
~/.config/fusion-workflow/gateway-profile/fusion-ccr-aliases.md
~/.config/fusion-workflow/gateway-profile/CCR_QUICKSTART.md
~/.config/fusion-workflow/gateway-profile/.env.example
```

On Windows these live under `%APPDATA%\fusion-workflow\gateway-profile`.

`fusion-ccr-aliases.md` is the easiest file to keep open while creating the CCR routing rules. `fusion-gateway-profile.json` is a stable machine-readable profile for future import tooling.

For noninteractive setup:

```bash
fusion-flow wizard --non-interactive --skip-install
```

## Configure the proxy

Fusion uses fixed incoming model names so the plugin never needs provider credentials or provider-specific model IDs.

```text
fusion-gpt-5.5-high
fusion-deepseek-v4-flash
fusion-mimo-v2.5
fusion-qwen3.7-plus
fusion-minimax-m3
fusion-kimi-k2.7-code
fusion-glm-5.2
fusion-sonnet-5-low
fusion-sonnet-5-medium
```

The wizard autofills those aliases in the generated gateway profile. Map those aliases in your gateway, start it, then run `fusion-flow doctor`. Detailed instructions and the upstream mapping table are in [docs/PROXY_SETUP.md](docs/PROXY_SETUP.md).

## Use

From any project:

```bash
cd ~/code/my-project
fusion-flow
```

That launches Claude Code with:

- the Fusion plugin only
- `fusion-workflow:orchestrator` as the main agent
- GPT-5.5 High as the main model alias
- built-in Explore/Plan agents disabled so they cannot silently consume orchestrator quota
- implementation workers isolated in temporary git worktrees

Plain Claude Code remains unchanged:

```bash
claude
```

## Example behavior

Request:

```text
Add project-level notification preferences.
```

A typical run might be:

```text
GPT-5.5 inspects existing organization preferences
        ↓
creates a bounded contract with acceptance tests
        ↓
Qwen3.7 Plus implements in an isolated worktree
        ↓
returns a commit
        ↓
GPT-5.5 inspects and cherry-picks it
        ↓
runs verification in the main checkout
```

For a strongly verified algorithmic task:

```text
DeepSeek Flash ──┐
                 ├── same contract, isolated worktrees
MiMo-V2.5 ───────┘
        ↓
GPT-5.5 selects the better verified commit
```

For a high-risk weakly tested authentication change, the manager should skip the cheap ladder and use Sonnet.

## Routing policy

The detailed policy is in [docs/ROUTING.md](docs/ROUTING.md). The actual technical routing instructions live in `agents/orchestrator.md`.

The active OpenCode roster is intentionally smaller than the full Go catalog. Older and overlapping models are benched until your own results show a useful niche:

- GLM-5.1
- Kimi K2.6
- MiMo-V2.5-Pro
- MiniMax M2.7
- Qwen3.7 Max
- Qwen3.6 Plus
- DeepSeek V4 Pro

This keeps routing data dense enough to learn from.

## Useful commands

```bash
fusion-flow wizard   # configure Fusion and generate gateway alias/profile files
fusion-flow setup    # configure only the local gateway URL/auth
fusion-flow doctor   # check Claude Code, config, gateway, and aliases
fusion-flow models   # print the alias map
fusion-flow config   # show the active launcher config
fusion-flow          # start the workflow
```

Any other arguments are passed to Claude Code:

```bash
fusion-flow --resume
fusion-flow --permission-mode acceptEdits
```

## Update

### macOS / Linux

```bash
git -C ~/.local/share/fusion-workflow pull --ff-only
chmod +x ~/.local/share/fusion-workflow/bin/fusion-flow
```

### Windows

```powershell
git -C "$HOME\.local\share\fusion-workflow" pull --ff-only
Copy-Item "$HOME\.local\share\fusion-workflow\bin\fusion-flow.cmd" "$HOME\.local\bin\fusion-flow.cmd" -Force
```

## Uninstall

### macOS / Linux

```bash
rm ~/.local/bin/fusion-flow
rm -rf ~/.local/share/fusion-workflow
rm -rf ~/.config/fusion-workflow
```

### Windows

```powershell
Remove-Item "$HOME\.local\bin\fusion-flow.cmd" -Force -ErrorAction SilentlyContinue
Remove-Item "$HOME\.local\share\fusion-workflow" -Recurse -Force
Remove-Item "$env:APPDATA\fusion-workflow" -Recurse -Force -ErrorAction SilentlyContinue
```

## Development

```bash
git clone https://github.com/pikalover6/fusion-workflow.git
cd fusion-workflow
python3 bin/fusion-flow.py wizard
python3 bin/fusion-flow.py doctor
python3 bin/fusion-flow.py
```

The plugin also works directly with:

```bash
claude --plugin-dir . --agent fusion-workflow:orchestrator
```

when the gateway environment variables are already configured.
