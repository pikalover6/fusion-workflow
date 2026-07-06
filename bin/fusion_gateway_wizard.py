from __future__ import annotations

from difflib import SequenceMatcher
import getpass
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_GATEWAY_URL = "http://127.0.0.1:8080"
LITELLM_DOCS_URL = "https://docs.litellm.ai/docs/proxy/quick_start"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
PROVIDERS = {
    "gpt": {
        "name": "GPT / OpenAI-compatible provider",
        "base_envs": ("FUSION_GPT_BASE_URL", "OPENAI_BASE_URL", "OPENAI_API_BASE"),
        "key_envs": ("FUSION_GPT_API_KEY", "OPENAI_API_KEY"),
        "secret_env": "FUSION_GPT_API_KEY",
        "default_base": "https://api.openai.com/v1",
    },
    "opencode_go": {
        "name": "OpenCode Go / OpenAI-compatible provider",
        "base_envs": ("FUSION_OPENCODE_GO_BASE_URL",),
        "key_envs": ("FUSION_OPENCODE_GO_API_KEY",),
        "secret_env": "FUSION_OPENCODE_GO_API_KEY",
        "default_base": "",
    },
    "claude": {
        "name": "Claude / Anthropic-compatible provider",
        "base_envs": ("FUSION_CLAUDE_BASE_URL",),
        "key_envs": ("FUSION_CLAUDE_API_KEY", "ANTHROPIC_API_KEY"),
        "secret_env": "FUSION_CLAUDE_API_KEY",
        "default_base": "https://api.anthropic.com",
    },
}


def is_interactive() -> bool:
    return sys.stdin.isatty()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        temporary.chmod(0o600)
    temporary.replace(path)
    if os.name != "nt":
        path.chmod(0o600)


def first_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def provider_key_for(spec: dict[str, Any]) -> str:
    provider = str(spec.get("provider", ""))
    if "OpenCode" in provider:
        return "opencode_go"
    if "Claude" in provider:
        return "claude"
    return "gpt"


def reachable(base_url: str, timeout: float = 0.7) -> bool:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_json(url: str, api_key: str = "", timeout: float = 3) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers.update({"Authorization": f"Bearer {api_key}", "x-api-key": api_key})
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            value = json.load(response)
    except (OSError, HTTPError, URLError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def model_ids(payload: dict[str, Any]) -> list[str]:
    values = payload.get("data")
    if not isinstance(values, list):
        values = payload.get("models")
    if not isinstance(values, list):
        return []
    return [str(item["id"]) for item in values if isinstance(item, dict) and item.get("id")]


def model_catalog(base_url: str, api_key: str = "") -> list[str]:
    base = base_url.rstrip("/")
    endpoints = [base + "/models"] if base.endswith("/v1") else [base + "/v1/models", base + "/models"]
    for endpoint in endpoints:
        models = model_ids(get_json(endpoint, api_key))
        if models:
            return models
    return []


def normalize(value: str) -> str:
    return "".join(character.lower() for character in value if character.isalnum())


def best_model_match(desired: str, candidates: list[str]) -> tuple[str | None, float]:
    desired_normalized = normalize(desired)
    desired_tokens = set(desired.lower().replace("-", " ").replace("_", " ").split())
    best: str | None = None
    score = 0.0
    for candidate in candidates:
        candidate_normalized = normalize(candidate)
        candidate_tokens = set(candidate.lower().replace("-", " ").replace("_", " ").split())
        if desired_normalized == candidate_normalized:
            candidate_score = 1.0
        elif desired_normalized in candidate_normalized or candidate_normalized in desired_normalized:
            candidate_score = 0.92
        else:
            overlap = len(desired_tokens & candidate_tokens) / max(len(desired_tokens), 1)
            ratio = SequenceMatcher(None, desired_normalized, candidate_normalized).ratio()
            candidate_score = (overlap * 0.55) + (ratio * 0.45)
        if candidate_score > score:
            best, score = candidate, candidate_score
    return best, score


def fallback_model(provider_key: str, desired: str) -> str:
    model = desired.strip().lower().replace(" ", "-")
    if provider_key == "claude" and not model.startswith("claude-"):
        model = "claude-" + model
    return model


def gateway_aliases(base_url: str, credential: str = "") -> set[str]:
    return set(model_catalog(base_url, credential))


def choose_gateway_url(preferred: str, required: set[str], credential: str) -> tuple[str, bool]:
    preferred = preferred.rstrip("/")
    if not reachable(preferred):
        return preferred, False
    if required <= gateway_aliases(preferred, credential):
        return preferred, True
    if urlparse(preferred).hostname not in LOCAL_HOSTS:
        return preferred, False
    for port in (4000, 8081, 8765, 8766):
        candidate = f"http://127.0.0.1:{port}"
        if not reachable(candidate):
            return candidate, False
    return preferred, False


def collect_providers(profile_dir: Path, interactive: bool) -> tuple[dict[str, dict[str, Any]], dict[str, str], list[str]]:
    previous = read_json(profile_dir / "fusion-gateway-profile.json").get("providers", {})
    previous = previous if isinstance(previous, dict) else {}
    previous_secrets = read_json(profile_dir / "provider-secrets.json")
    providers: dict[str, dict[str, Any]] = {}
    secrets_by_env: dict[str, str] = {}
    missing: list[str] = []

    for key, definition in PROVIDERS.items():
        old = previous.get(key, {}) if isinstance(previous.get(key), dict) else {}
        base_url = first_env(definition["base_envs"]) or str(old.get("base_url") or definition["default_base"])
        api_key = first_env(definition["key_envs"]) or str(previous_secrets.get(definition["secret_env"]) or "")
        if interactive and key == "opencode_go" and not base_url:
            base_url = input("OpenCode Go base URL (OpenAI-compatible, blank = configure later): ").strip()
        if interactive and not api_key:
            api_key = getpass.getpass(f"{definition['name']} API key (blank = configure later): ").strip()
        base_url = base_url.rstrip("/")
        if not base_url:
            missing.append(f"{definition['name']} base URL")
        if not api_key:
            missing.append(f"{definition['name']} API key")
        providers[key] = {
            "display_name": definition["name"],
            "base_url": base_url,
            "api_key_env": definition["secret_env"],
            "models": model_catalog(base_url, api_key) if base_url and api_key else [],
        }
        secrets_by_env[definition["secret_env"]] = api_key
    return providers, secrets_by_env, missing


def build_profile(aliases: dict[str, Any], providers: dict[str, dict[str, Any]], gateway_url: str) -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    for alias, spec in aliases.items():
        provider_key = provider_key_for(spec)
        desired = str(spec.get("upstream") or alias)
        matched, score = best_model_match(desired, list(providers[provider_key].get("models") or []))
        resolved = matched if matched and score >= 0.60 else fallback_model(provider_key, desired)
        routes.append({
            "incoming_model": alias,
            "provider": provider_key,
            "provider_base_url": providers[provider_key]["base_url"],
            "api_key_env": providers[provider_key]["api_key_env"],
            "upstream_model": desired,
            "resolved_model": resolved,
            "match_score": round(score, 3),
            "mode": spec.get("mode", ""),
            "role": spec.get("role", ""),
        })
    return {
        "schema": "fusion-workflow.gateway-profile.v2",
        "router": "LiteLLM",
        "gateway_url": gateway_url,
        "providers": providers,
        "routes": routes,
    }


def q(value: str) -> str:
    return json.dumps(value)


def render_litellm_config(profile: dict[str, Any]) -> str:
    lines = ["model_list:"]
    for route in profile["routes"]:
        provider = route["provider"]
        prefix = "anthropic" if provider == "claude" else "openai"
        lines.extend([
            f"  - model_name: {q(route['incoming_model'])}",
            "    litellm_params:",
            f"      model: {q(prefix + '/' + route['resolved_model'])}",
            f"      api_key: {q('os.environ/' + route['api_key_env'])}",
        ])
        if route.get("provider_base_url"):
            lines.append(f"      api_base: {q(route['provider_base_url'])}")
        if route.get("mode") and provider == "gpt":
            lines.append(f"      reasoning_effort: {q(str(route['mode']))}")
        if route.get("mode") and provider == "claude":
            lines.extend(["      output_config:", f"        effort: {q(str(route['mode']))}"])
    lines.extend([
        "litellm_settings:",
        "  drop_params: true",
        "general_settings:",
        f"  master_key: {q('os.environ/FUSION_GATEWAY_MASTER_KEY')}",
        "",
    ])
    return "\n".join(lines)


def write_bundle(config_root: Path, profile: dict[str, Any], secrets_by_env: dict[str, str], missing: list[str]) -> Path:
    output_dir = config_root / "gateway-profile"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "fusion-gateway-profile.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    (output_dir / "litellm-config.yaml").write_text(render_litellm_config(profile), encoding="utf-8")
    write_private_json(output_dir / "provider-secrets.json", secrets_by_env)
    lines = [
        "# Fusion managed gateway",
        "",
        "The wizard generated all nine routes automatically and uses this directory as the router runtime bundle.",
        "Provider credentials stay in `provider-secrets.json`; the generated YAML contains environment-variable references only.",
        "",
        f"Gateway: `{profile['gateway_url']}`",
        f"LiteLLM docs: {LITELLM_DOCS_URL}",
    ]
    if missing:
        lines.extend(["", "## Missing provider settings", *[f"- {item}" for item in missing], "", "Rerun `fusion-flow wizard` after setting the corresponding environment variables."])
    (output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_dir


def litellm_executable(config_root: Path) -> Path | None:
    found = shutil.which("litellm")
    if found:
        return Path(found)
    candidate = config_root / "router-venv" / ("Scripts/litellm.exe" if os.name == "nt" else "bin/litellm")
    return candidate if candidate.is_file() else None


def install_litellm(config_root: Path) -> Path:
    venv = config_root / "router-venv"
    print("Installing the managed LiteLLM router in an isolated Fusion environment...")
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable = venv / ("Scripts/litellm.exe" if os.name == "nt" else "bin/litellm")
    subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "litellm[proxy]"], check=True)
    if not executable.is_file():
        raise RuntimeError(f"LiteLLM executable not found at {executable}")
    return executable


def start_gateway(executable: Path, output_dir: Path, gateway_url: str, provider_secrets: dict[str, str], master_key: str) -> tuple[bool, str]:
    parsed = urlparse(gateway_url)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS:
        return False, "managed router requires a local http:// URL"
    if reachable(gateway_url):
        return True, "gateway is already running"
    log_file = output_dir / "router.log"
    env = os.environ.copy()
    env.update(provider_secrets)
    env["FUSION_GATEWAY_MASTER_KEY"] = master_key
    command = [str(executable), "--config", str(output_dir / "litellm-config.yaml"), "--host", "127.0.0.1", "--port", str(parsed.port or 80)]
    with log_file.open("a", encoding="utf-8") as log:
        kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT, "env": env}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            kwargs["start_new_session"] = True
        process = subprocess.Popen(command, **kwargs)
    (output_dir / "router.pid").write_text(str(process.pid) + "\n", encoding="utf-8")
    for _ in range(30):
        if reachable(gateway_url):
            return True, f"started managed router (pid {process.pid})"
        if process.poll() is not None:
            return False, f"router exited with code {process.returncode}; see {log_file}"
        time.sleep(0.5)
    return False, f"router did not become reachable; see {log_file}"


def run_gateway_wizard(
    *,
    aliases: dict[str, Any],
    config_root: Path,
    save_fusion_config,
    non_interactive: bool = False,
    skip_install: bool = False,
    gateway_url: str = DEFAULT_GATEWAY_URL,
) -> int:
    print("Fusion setup autopilot")
    print("Reuse a working gateway, or generate, install, start, and verify a managed one automatically.\n")
    interactive = is_interactive() and not non_interactive
    required = set(aliases)
    existing = read_json(config_root / "config.json")
    credential = str(existing.get("credential") or "")
    preferred = gateway_url.rstrip("/")
    if preferred == DEFAULT_GATEWAY_URL:
        preferred = str(existing.get("base_url") or preferred).rstrip("/")

    chosen, reused = choose_gateway_url(preferred, required, credential)
    if reused:
        save_fusion_config({**existing, "base_url": chosen, "router": str(existing.get("router") or "external")})
        print(f"Ready. Reusing {chosen}; all {len(required)} Fusion aliases are present.")
        return 0
    if urlparse(chosen).hostname not in LOCAL_HOSTS or urlparse(chosen).scheme != "http":
        print(f"Remote gateway is not already ready: {chosen}", file=sys.stderr)
        print("Use `fusion-flow setup` for an externally managed gateway.", file=sys.stderr)
        return 1

    providers, provider_secrets, missing = collect_providers(config_root / "gateway-profile", interactive)
    profile = build_profile(aliases, providers, chosen)
    output_dir = write_bundle(config_root, profile, provider_secrets, missing)
    master_key = credential if existing.get("router") == "litellm" and credential else "sk-fusion-" + secrets.token_urlsafe(24)
    executable = litellm_executable(config_root)
    install_error = ""
    if executable is None and not skip_install:
        try:
            executable = install_litellm(config_root)
        except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
            install_error = str(exc)

    save_fusion_config({
        "base_url": chosen,
        "auth_mode": "api_key",
        "credential": master_key,
        "gateway_profile_dir": str(output_dir),
        "router": "litellm",
        "router_executable": str(executable) if executable else "",
        "router_pid_file": str(output_dir / "router.pid"),
        "router_log_file": str(output_dir / "router.log"),
    })
    print(f"Generated all {len(required)} routes in {output_dir / 'litellm-config.yaml'}")
    matched = sum(float(route.get("match_score") or 0) >= 0.60 for route in profile["routes"])
    if matched:
        print(f"Auto-matched {matched} upstream model ID(s) from provider catalogs.")
    if install_error:
        print(f"Managed router installation failed: {install_error}", file=sys.stderr)
        return 1
    if skip_install:
        print("Generated the complete managed-router bundle; install/start was skipped by request.")
        return 0
    if executable is None:
        print("LiteLLM is not available.", file=sys.stderr)
        return 1

    started, detail = start_gateway(executable, output_dir, chosen, provider_secrets, master_key)
    print(detail)
    if not started:
        return 1
    missing_aliases = sorted(required - gateway_aliases(chosen, master_key))
    if missing_aliases:
        print("Gateway started but did not advertise every Fusion alias:", file=sys.stderr)
        for alias in missing_aliases:
            print(f"  - {alias}", file=sys.stderr)
        return 1
    if missing:
        print(f"Gateway and aliases are ready; {len(missing)} provider setting(s) are still blank. Rerun the wizard after setting them.")
        return 0
    print("\nFusion is ready. All aliases were verified without sending paid model prompts.")
    print("Run `fusion-flow` inside a git project.")
    return 0
