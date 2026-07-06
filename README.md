# Fusion Workflow

Fusion Workflow is a multi-model Claude Code workflow where GPT-5.5 High leads the project and routes implementation work to the cheapest model likely to reach a verified result.

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

The core rule is simple:

> Route by expected total cost to a verified result, not by vague task difficulty or first-attempt price.

## Requirements

- Claude Code 2.1.200 or newer
- Python 3.9 or newer
- Git projects for isolated implementation worktrees
- Authorized access to the providers/models you configure

## Install

### macOS / Linux

```bash
mkdir -p ~/.local/share ~/.local/bin
git clone https://github.com/pikalover6/fusion-workflow.git ~/.local/share/fusion-workflow
chmod +x ~/.local/share/fusion-workflow/bin/fusion-flow
ln -sf ~/.local/share/fusion-workflow/bin/fusion-flow ~/.local/bin/fusion-flow
```

Make sure `~/.local/bin` is on your `PATH`, then run:

```bash
fusion-flow wizard
```

### Windows

Open PowerShell:

```powershell
New-Item -ItemType Directory -Force "$HOME\.local\share", "$HOME\.local\bin" | Out-Null
git clone https://github.com/pikalover6/fusion-workflow.git "$HOME\.local\share\fusion-workflow"
Copy-Item "$HOME\.local\share\fusion-workflow\bin\fusion-flow.cmd" "$HOME\.local\bin\fusion-flow.cmd" -Force
```

Add `~\.local\bin` to your user `PATH`, then run:

```powershell
fusion-flow wizard
```

## Setup autopilot

`fusion-flow wizard` now tries to do the whole first-run setup for you.

It:

1. checks whether the configured gateway is already running and advertises all nine Fusion aliases
2. reuses that gateway immediately when it is already compatible
3. reads provider URLs and credentials from environment variables or a previous wizard run
4. queries provider model catalogs when possible and matches conceptual Fusion targets to real provider model IDs
5. generates all nine alias routes as a LiteLLM config
6. installs LiteLLM in an isolated Fusion virtual environment when needed
7. starts the local router automatically, choosing a fallback port when the preferred local port is occupied
8. verifies all nine aliases through the model catalog without sending paid model prompts

The normal experience is one command, not nine manual routing rules.

### Provider discovery

The wizard reuses these variables when present:

| Provider | Base URL | API key |
|---|---|---|
| GPT/OpenAI-compatible | `FUSION_GPT_BASE_URL`, `OPENAI_BASE_URL`, `OPENAI_API_BASE` | `FUSION_GPT_API_KEY`, `OPENAI_API_KEY` |
| OpenCode Go | `FUSION_OPENCODE_GO_BASE_URL` | `FUSION_OPENCODE_GO_API_KEY` |
| Claude/Anthropic-compatible | `FUSION_CLAUDE_BASE_URL` | `FUSION_CLAUDE_API_KEY`, `ANTHROPIC_API_KEY` |

When an interactive run still needs a value, the wizard asks only for the missing setting. Reruns reuse the previous generated profile and private provider secret file.

### Generated managed-router files

On macOS/Linux:

```text
~/.config/fusion-workflow/gateway-profile/
├── fusion-gateway-profile.json
├── litellm-config.yaml
├── provider-secrets.json
├── README.md
├── router.pid        # after start
└── router.log        # after start
```

On Windows, the same directory lives under `%APPDATA%\fusion-workflow`.

Provider credentials are stored in `provider-secrets.json`; generated YAML contains environment-variable references instead of raw provider keys. On POSIX systems the private JSON file is written with mode `0600`.

### Generate without installing or starting

```bash
fusion-flow wizard --non-interactive --skip-install
```

This writes the full router bundle and launcher config but does not install or start LiteLLM.

### Existing or custom gateway

Fusion is still gateway-agnostic. The wizard reuses any already-running gateway that advertises the exact nine aliases. For an externally managed remote gateway, use:

```bash
fusion-flow setup --base-url https://your-gateway.example
fusion-flow doctor
```

See `docs/PROXY_SETUP.md` for the routing contract and manual/external gateway path.

## Model aliases

Fusion sends these stable incoming names to the gateway:

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

The managed router maps them automatically from `config/model-aliases.json`.

## Verify

```bash
fusion-flow doctor
```

`doctor` checks Python, Claude Code, Git, plugin files, the alias contract, saved Fusion config, generated profile directory, gateway reachability, and launcher authentication settings.

## Use

From any Git project:

```bash
cd ~/code/my-project
fusion-flow
```

That launches Claude Code with:

- the Fusion plugin only
- `fusion-workflow:orchestrator` as the main agent
- GPT-5.5 High as the main model alias
- built-in Explore/Plan agents disabled so they cannot silently consume orchestrator quota
- implementation workers isolated in temporary Git worktrees

Plain Claude Code remains unchanged:

```bash
claude
```

Any other arguments are passed through:

```bash
fusion-flow --resume
fusion-flow --permission-mode acceptEdits
```

## Routing policy

The manager inspects the repository, resolves ambiguity, creates explicit implementation contracts, chooses workers from task shape and expected total verification cost, reviews commits before integration, repairs or escalates when needed, and learns aggregate model outcomes over time.

Detailed policy lives in `docs/ROUTING.md`; technical orchestrator instructions live in `agents/orchestrator.md`.

## Useful commands

```bash
fusion-flow wizard   # automatic first-run setup and managed router
fusion-flow setup    # point Fusion at an externally managed gateway
fusion-flow doctor   # check prerequisites and gateway reachability
fusion-flow models   # print the alias map
fusion-flow config   # show sanitized active configuration
fusion-flow          # start the workflow
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
python3 bin/fusion-flow.py wizard --non-interactive --skip-install
python3 -m unittest discover -s tests -v
```

The plugin also works directly with:

```bash
claude --plugin-dir . --agent fusion-workflow:orchestrator
```

when the gateway environment variables are already configured.
