# Gateway and proxy setup

Fusion keeps the Claude Code plugin provider-agnostic. Claude Code sends stable Fusion model aliases to one Anthropic-compatible gateway; the gateway maps each alias to the configured upstream provider and model.

```text
Claude Code
    |
    | Anthropic Messages API
    v
local or external gateway
    |-- fusion-gpt-5.5-high        -> GPT-5.5 / high reasoning
    |-- fusion-deepseek-v4-flash   -> DeepSeek V4 Flash
    |-- fusion-mimo-v2.5           -> MiMo-V2.5
    |-- fusion-qwen3.7-plus        -> Qwen3.7 Plus
    |-- fusion-minimax-m3          -> MiniMax M3
    |-- fusion-kimi-k2.7-code      -> Kimi K2.7 Code
    |-- fusion-glm-5.2             -> GLM-5.2
    |-- fusion-sonnet-5-low        -> Sonnet 5 / low effort
    `-- fusion-sonnet-5-medium     -> Sonnet 5 / medium effort
```

## Recommended path: the setup autopilot

Run:

```bash
fusion-flow wizard
```

The wizard prefers the least-work path:

1. reuse the currently configured gateway when it is reachable and already advertises every Fusion alias
2. otherwise build a managed LiteLLM router locally
3. load provider settings from environment variables or the previous wizard run
4. query provider model catalogs when credentials allow it
5. automatically match conceptual model names to provider model IDs
6. generate all nine alias routes
7. install LiteLLM in a Fusion-owned virtual environment if it is not already available
8. start the router
9. verify the alias catalog without sending model prompts

No per-alias UI setup is required for the managed path.

## Why LiteLLM is the managed default

Fusion needs a router that can be generated and started reproducibly from files and CLI arguments. The managed wizard therefore emits a LiteLLM config where each Fusion alias is a `model_name` and the upstream target is set in `litellm_params`.

Fusion is not coupled to LiteLLM. Any external gateway remains valid when it:

1. accepts Anthropic Messages requests from Claude Code
2. preserves the requested model name long enough to route on it
3. exposes the exact nine Fusion aliases
4. rewrites each alias to the intended upstream provider/model
5. supports the authentication method you are authorized to use

## Provider discovery

The wizard checks these variables before asking for anything:

| Provider | Base URL variables | Credential variables |
|---|---|---|
| GPT/OpenAI-compatible | `FUSION_GPT_BASE_URL`, `OPENAI_BASE_URL`, `OPENAI_API_BASE` | `FUSION_GPT_API_KEY`, `OPENAI_API_KEY` |
| OpenCode Go | `FUSION_OPENCODE_GO_BASE_URL` | `FUSION_OPENCODE_GO_API_KEY` |
| Claude/Anthropic-compatible | `FUSION_CLAUDE_BASE_URL` | `FUSION_CLAUDE_API_KEY`, `ANTHROPIC_API_KEY` |

GPT defaults to `https://api.openai.com/v1`. Claude defaults to `https://api.anthropic.com`. OpenCode Go has no guessed default base URL because the bridge is deployment-specific.

Interactive runs ask only for still-missing values. Non-interactive runs generate the bundle with blanks that can be filled on a later rerun.

## Model ID matching

`config/model-aliases.json` contains conceptual upstream names such as `Sonnet 5` and `Qwen3.7 Plus`. Provider APIs may expose dated or namespaced IDs instead.

When a provider model catalog is available, the wizard scores candidate IDs using normalized names, token overlap, and sequence similarity. A confident match is written to `resolved_model`; otherwise the wizard falls back to a normalized conceptual ID.

The machine-readable output is:

```text
~/.config/fusion-workflow/gateway-profile/fusion-gateway-profile.json
```

or `%APPDATA%\fusion-workflow\gateway-profile\fusion-gateway-profile.json` on Windows.

## Generated managed-router bundle

```text
gateway-profile/
├── fusion-gateway-profile.json
├── litellm-config.yaml
├── provider-secrets.json
├── README.md
├── router.pid
└── router.log
```

`provider-secrets.json` contains provider credentials. `litellm-config.yaml` contains references such as `os.environ/FUSION_GPT_API_KEY`, not raw provider keys. On POSIX systems the secret file is written with mode `0600`.

The local gateway master key is stored in Fusion's private launcher config and injected into the router process through `FUSION_GATEWAY_MASTER_KEY`.

## Port conflicts

The preferred gateway URL remains:

```text
http://127.0.0.1:8080
```

When that local port is occupied by a service that does not advertise every Fusion alias, the wizard automatically tries free fallback ports in this order:

```text
4000, 8081, 8765, 8766
```

The selected URL is saved to Fusion's launcher config.

## Effort mapping

The managed config adds route-specific effort controls:

- `fusion-gpt-5.5-high` uses `reasoning_effort: high`
- `fusion-sonnet-5-low` uses `output_config.effort: low`
- `fusion-sonnet-5-medium` uses `output_config.effort: medium`

Gateways other than LiteLLM may express these settings differently. The behavior is the contract, not one config syntax.

## Generate only

For CI, inspection, or a machine where you do not want the wizard to install/start a process:

```bash
fusion-flow wizard --non-interactive --skip-install
```

This still writes the full alias profile, LiteLLM config, private secret file, and Fusion launcher config.

## External gateway path

To use a remote or independently managed gateway:

```bash
fusion-flow setup --base-url https://your-gateway.example
fusion-flow doctor
```

The wizard also automatically reuses an existing gateway when its model catalog already contains all nine required aliases.

The exact alias contract is:

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

## Verification

After setup:

```bash
fusion-flow doctor
```

The wizard itself verifies alias availability through the gateway's model catalog. It intentionally does not send nine test prompts, so verification does not spend model quota.

## Troubleshooting

### The managed router installation fails

The generated bundle is preserved. Read the terminal error, fix the local Python/pip problem, then rerun `fusion-flow wizard`.

### The router exits immediately

Inspect:

```text
gateway-profile/router.log
```

The most common cause is a missing or invalid provider setting.

### A conceptual model name does not match the provider ID

Set the provider base URL and credential so the wizard can read the provider model catalog, then rerun it. The previous profile and credentials are reused.

### The main model works but workers fail

Compare `fusion-flow models` with the gateway model catalog. Every incoming alias must be present exactly.

### Plain `claude` also goes through the proxy

That comes from global Claude Code or shell configuration. `fusion-flow` injects gateway variables only into its child process.

## Security note

A local gateway can see prompts, source code, tool messages, and provider credentials. Use software you trust, bind local services conservatively, protect local API keys, and configure only provider access you are authorized to use.
