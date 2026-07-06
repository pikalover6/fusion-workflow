from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from typing import Any

CCR_RELEASES_URL = "https://github.com/musistudio/claude-code-router/releases"


def is_interactive() -> bool:
    return sys.stdin.isatty()


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def ask_yes_no(prompt: str, default: bool = True) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_text}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def detected_gateway() -> str | None:
    for executable in ("claude-code-router", "ccr"):
        found = shutil.which(executable)
        if found:
            return found
    return None


def gateway_install_message() -> str:
    found = detected_gateway()
    if found:
        return f"Gateway executable detected: {found}"
    return "Claude Code Router was not detected on PATH. Install/start it from: " + CCR_RELEASES_URL


def provider_key_for(spec: dict[str, Any]) -> str:
    provider = str(spec.get("provider", "custom"))
    if "OpenCode" in provider:
        return "opencode_go"
    if "Claude" in provider:
        return "claude"
    if "Codex" in provider or "OpenAI" in provider or "ChatGPT" in provider:
        return "gpt"
    return "custom"


def build_alias_profile(aliases: dict[str, Any], provider_defaults: dict[str, str]) -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    for alias, spec in aliases.items():
        provider_key = provider_key_for(spec)
        routes.append(
            {
                "incoming_model": alias,
                "provider": provider_key,
                "provider_base_url": provider_defaults.get(f"{provider_key}_base_url", ""),
                "upstream_model": str(spec.get("upstream", alias)),
                "mode": spec.get("mode", ""),
                "role": spec.get("role", ""),
            }
        )

    return {
        "schema": "fusion-workflow.gateway-profile.v1",
        "gateway": {
            "recommended": "Claude Code Router",
            "install_url": CCR_RELEASES_URL,
            "anthropic_compatible_url": provider_defaults.get("gateway_url", "http://127.0.0.1:8080"),
            "notes": [
                "Use incoming_model as the route match key.",
                "Rewrite each request to provider/upstream_model.",
                "Apply mode/effort as a route-specific provider parameter when your gateway supports it.",
            ],
        },
        "providers": {
            "gpt": {
                "display_name": "GPT / Codex / OpenAI-compatible bridge",
                "base_url": provider_defaults.get("gpt_base_url", ""),
                "api_key_env": "FUSION_GPT_API_KEY",
            },
            "opencode_go": {
                "display_name": "OpenCode Go / OpenAI-compatible bridge",
                "base_url": provider_defaults.get("opencode_go_base_url", ""),
                "api_key_env": "FUSION_OPENCODE_GO_API_KEY",
            },
            "claude": {
                "display_name": "Claude / Anthropic-compatible bridge",
                "base_url": provider_defaults.get("claude_base_url", ""),
                "api_key_env": "FUSION_CLAUDE_API_KEY",
            },
        },
        "routes": routes,
    }


def markdown_alias_table(profile: dict[str, Any]) -> str:
    lines = [
        "# Fusion gateway alias rules",
        "",
        "Create one model-routing rule per row in your gateway.",
        "",
        "| Incoming model | Provider | Upstream model | Mode | Role |",
        "|---|---|---|---|---|",
    ]
    for route in profile["routes"]:
        lines.append(
            f"| `{route['incoming_model']}` | `{route['provider']}` | `{route['upstream_model']}` | `{route.get('mode') or ''}` | {route.get('role') or ''} |"
        )
    lines.extend(
        [
            "",
            "## Gateway URL for `fusion-flow setup`",
            "",
            f"`{profile['gateway']['anthropic_compatible_url']}`",
            "",
            "## Notes",
            "",
            "- The incoming Fusion model names are route keys; they do not need to be real upstream model IDs.",
            "- Sonnet Low/Medium and GPT High may need route-specific effort/reasoning parameters.",
            "- Keep credentials in the gateway or environment variables, not in this Markdown file.",
        ]
    )
    return "\n".join(lines) + "\n"


def env_example(profile: dict[str, Any]) -> str:
    lines = [
        "# Optional provider credential environment variables for your gateway.",
        "# Fusion itself only needs the local gateway URL and local gateway credential.",
        "",
    ]
    for provider in profile["providers"].values():
        lines.append(f"{provider['api_key_env']}=")
    return "\n".join(lines) + "\n"


def ccr_quickstart(profile: dict[str, Any]) -> str:
    lines = [
        "# Claude Code Router quickstart for Fusion",
        "",
        "Install/start Claude Code Router:",
        "",
        f"{CCR_RELEASES_URL}",
        "",
        "Then create these model-routing rules exactly:",
        "",
    ]
    for route in profile["routes"]:
        mode = f" with mode `{route['mode']}`" if route.get("mode") else ""
        lines.append(f"- `{route['incoming_model']}` -> provider `{route['provider']}` model `{route['upstream_model']}`{mode}")
    lines.extend(
        [
            "",
            "After the gateway is running, run:",
            "",
            "```bash",
            "fusion-flow doctor",
            "fusion-flow",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def write_profile_files(config_root: Path, aliases: dict[str, Any], provider_defaults: dict[str, str]) -> Path:
    profile = build_alias_profile(aliases, provider_defaults)
    output_dir = config_root / "gateway-profile"
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "fusion-gateway-profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    (output_dir / "fusion-ccr-aliases.md").write_text(markdown_alias_table(profile), encoding="utf-8")
    (output_dir / "CCR_QUICKSTART.md").write_text(ccr_quickstart(profile), encoding="utf-8")
    (output_dir / ".env.example").write_text(env_example(profile), encoding="utf-8")
    return output_dir


def run_gateway_wizard(
    *,
    aliases: dict[str, Any],
    config_root: Path,
    save_fusion_config,
    non_interactive: bool = False,
    skip_install: bool = False,
    gateway_url: str = "http://127.0.0.1:8080",
) -> int:
    print("Fusion gateway wizard")
    print("This generates a Claude Code Router-oriented gateway profile with all Fusion aliases prefilled.")
    print("")

    if not skip_install:
        print(gateway_install_message())

    provider_defaults = {"gateway_url": gateway_url.rstrip("/")}
    if is_interactive() and not non_interactive:
        provider_defaults["gateway_url"] = ask("Local Anthropic-compatible gateway URL", provider_defaults["gateway_url"]).rstrip("/")
        if ask_yes_no("Set provider base URLs now?", False):
            provider_defaults["gpt_base_url"] = ask("GPT/OpenAI-compatible provider base URL", "")
            provider_defaults["opencode_go_base_url"] = ask("OpenCode Go provider base URL", "")
            provider_defaults["claude_base_url"] = ask("Claude/Anthropic provider base URL", "")

    output_dir = write_profile_files(config_root, aliases, provider_defaults)
    save_fusion_config(
        {
            "base_url": provider_defaults["gateway_url"],
            "auth_mode": "api_key",
            "credential": "",
            "gateway_profile_dir": str(output_dir),
        }
    )

    print("")
    print(f"Wrote gateway profile files to: {output_dir}")
    print(f"- {output_dir / 'fusion-gateway-profile.json'}")
    print(f"- {output_dir / 'fusion-ccr-aliases.md'}")
    print(f"- {output_dir / 'CCR_QUICKSTART.md'}")
    print(f"- {output_dir / '.env.example'}")
    print("")
    print("Next steps:")
    print("  1. Install/start Claude Code Router if it is not already running.")
    print("  2. Use fusion-ccr-aliases.md to create the nine model alias routes.")
    print("  3. Start the gateway server.")
    print("  4. Run `fusion-flow doctor`.")
    print("  5. Run `fusion-flow` inside a git project.")
    return 0
