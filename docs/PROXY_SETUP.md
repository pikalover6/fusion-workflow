# Proxy setup

Fusion keeps the Claude Code plugin provider-agnostic. Claude Code only sees stable model aliases; your local gateway decides which provider and upstream model each alias reaches.

```text
Claude Code
    |
    | Anthropic Messages API
    v
local gateway
    |-- fusion-gpt-5.5-high       -> GPT-5.5 High
    |-- fusion-deepseek-v4-flash  -> OpenCode Go / DeepSeek V4 Flash
    |-- fusion-mimo-v2.5          -> OpenCode Go / MiMo-V2.5
    |-- fusion-qwen3.7-plus       -> OpenCode Go / Qwen3.7 Plus
    |-- fusion-minimax-m3         -> OpenCode Go / MiniMax M3
    |-- fusion-kimi-k2.7-code     -> OpenCode Go / Kimi K2.7 Code
    |-- fusion-glm-5.2            -> OpenCode Go / GLM-5.2
    |-- fusion-sonnet-5-low       -> Claude / Sonnet 5 Low
    `-- fusion-sonnet-5-medium    -> Claude / Sonnet 5 Medium
```

## Recommended first experiment: Claude Code Router

[Claude Code Router](https://github.com/musistudio/claude-code-router) is a good fit because it exposes one local gateway, supports multiple providers, request rewrites, model-based routing, and Claude Code launch profiles.

Fusion does not depend on CCR specifically. Any gateway is fine if it:

1. accepts Anthropic Messages requests from Claude Code
2. preserves the requested `model` name long enough to route on it
3. can translate each route to the upstream provider protocol
4. supports the authentication method you are authorized to use for that provider

## Easiest setup path

Run:

```bash
fusion-flow wizard
```

The wizard:

- checks whether a CCR executable is already available
- prints the official CCR release page if CCR is not installed yet
- configures Fusion's local gateway URL, defaulting to `http://127.0.0.1:8080`
- optionally records provider base URLs
- generates a complete gateway profile bundle

Generated files:

```text
~/.config/fusion-workflow/gateway-profile/fusion-gateway-profile.json
~/.config/fusion-workflow/gateway-profile/fusion-ccr-aliases.md
~/.config/fusion-workflow/gateway-profile/CCR_QUICKSTART.md
~/.config/fusion-workflow/gateway-profile/.env.example
```

On Windows, these live under `%APPDATA%\fusion-workflow\gateway-profile`.

Use `fusion-ccr-aliases.md` while creating routing rules in CCR. `fusion-gateway-profile.json` is the stable machine-readable profile for future import tooling.

## 1. Install and start the gateway

Install your gateway and start its local server. CCR listens on `http://127.0.0.1:8080` by default unless you change the port.

Do not point normal Claude Code at the gateway globally unless you want that. Fusion sets gateway environment variables only for the `fusion-flow` process, so plain `claude` stays plain.

## 2. Add upstream providers

Configure three upstream routes in the gateway:

### GPT route

Target GPT-5.5 at High reasoning effort.

The authentication bridge is gateway-specific. For the aesthetic subscription-based experiment, use a route that can legally and reliably expose your existing Codex/ChatGPT-authenticated GPT-5.5 access to the gateway. An API-backed OpenAI-compatible route also works.

Fusion itself does not copy, scrape, or translate subscription credentials.

### OpenCode Go route

Configure a provider that can reach the OpenCode Go catalog and expose these models:

- DeepSeek V4 Flash
- MiMo-V2.5
- Qwen3.7 Plus
- MiniMax M3
- Kimi K2.7 Code
- GLM-5.2

The exact upstream model IDs depend on the bridge. Use the names/IDs your provider actually reports.

### Claude route

Configure Sonnet 5 with two selectable effort modes:

- Low
- Medium

The gateway may represent effort as separate model IDs, request rewrites, provider parameters, or route metadata. Fusion only requires that its two incoming aliases resolve to the intended behavior.

## 3. Add the exact Fusion aliases

The wizard autofills these rows in `fusion-ccr-aliases.md`.

| Incoming alias | Provider | Conceptual upstream target |
|---|---|---|
| `fusion-gpt-5.5-high` | Codex / OpenAI bridge | GPT-5.5, High |
| `fusion-deepseek-v4-flash` | OpenCode Go | DeepSeek V4 Flash |
| `fusion-mimo-v2.5` | OpenCode Go | MiMo-V2.5 |
| `fusion-qwen3.7-plus` | OpenCode Go | Qwen3.7 Plus |
| `fusion-minimax-m3` | OpenCode Go | MiniMax M3 |
| `fusion-kimi-k2.7-code` | OpenCode Go | Kimi K2.7 Code |
| `fusion-glm-5.2` | OpenCode Go | GLM-5.2 |
| `fusion-sonnet-5-low` | Claude | Sonnet 5, Low |
| `fusion-sonnet-5-medium` | Claude | Sonnet 5, Medium |

The source alias contract is `config/model-aliases.json`.

### CCR routing shape

In CCR, the conceptual setup is:

1. add each upstream provider
2. verify provider connectivity
3. add a model rule or request rewrite matching the exact incoming Fusion alias
4. send it to the intended provider/model
5. add effort/request rewriting where needed for GPT High and Sonnet Low/Medium

The exact UI labels can change between CCR releases, so treat the generated alias files as the source of truth rather than screenshots.

## 4. Configure the Fusion launcher

Prefer:

```bash
fusion-flow wizard
```

For the old manual path, use:

```bash
fusion-flow setup
```

Typical local CCR values:

```text
Gateway URL: http://127.0.0.1:8080
Authentication mode: api_key
```

If your local gateway accepts no credential, choose `none`.

The credential is stored only in the local Fusion config file:

- macOS/Linux: `~/.config/fusion-workflow/config.json`
- Windows: `%APPDATA%\fusion-workflow\config.json`

On POSIX systems Fusion writes the file with mode `0600`.

Environment overrides are available for temporary experiments:

```text
FUSION_BASE_URL
FUSION_AUTH_MODE
FUSION_API_KEY
FUSION_AUTH_TOKEN
```

## 5. Run the checks

```bash
fusion-flow models
fusion-flow doctor
```

`doctor` checks:

- Python
- Claude Code
- Git
- plugin files
- gateway wizard file
- alias contract
- Fusion config
- generated gateway profile directory, when present
- TCP reachability of the gateway

It intentionally does not send nine probe prompts. Automatic alias probing would consume real quota.

## 6. Launch inside a git repository

```bash
cd ~/code/my-project
fusion-flow
```

Implementation agents use isolated git worktrees and return commits to the GPT-5.5 orchestrator for inspection and integration.

## Troubleshooting

### The main model starts but workers fail

The GPT alias is wired correctly but one or more worker aliases are not. Run `fusion-flow models`, compare every exact spelling with the gateway rules, and inspect gateway request logs.

### The gateway receives the alias but forwards the same alias upstream

Add a request rewrite. The incoming Fusion alias is a routing key, not necessarily a real upstream model ID.

### Sonnet Low and Medium behave identically

Your gateway is probably routing both aliases to the same model without translating the effort setting. Add route-specific request parameters or separate upstream targets.

### Plain `claude` also goes through the proxy

That came from global Claude Code or shell configuration, not Fusion. `fusion-flow` injects gateway variables only into its child process.

### A consumer-subscription bridge is unreliable

That is the experimental part of the aesthetic architecture. Keep the Fusion alias contract and swap only the provider route. The plugin does not need to change.

## Security note

A local gateway can see prompts, source code, tool messages, and provider credentials. Use software you trust, bind local services conservatively, protect local API keys, and only configure provider access you are authorized to use.
