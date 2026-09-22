# Use your Codex (ChatGPT) subscription in DeepSeek Harness

Run GPT models such as GPT-6 Luna inside [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) (dsh) on your ChatGPT subscription instead of an OpenAI API key.

> **Unofficial workaround.** dsh already ships the `openai-codex` provider but has no sign-in UI for it yet, so this guide writes the OAuth credential by hand. It is not affiliated with DeepSeek or OpenAI. Use it at your own risk and within the terms of your ChatGPT plan. Once the dsh Models page supports OAuth sign-in, use that instead.

Verified on 2026-09-23 with dsh 0.1.7-alpha.1 (pi-ai 0.85.1) on macOS, with GPT-6 Luna at `xhigh` as the default model.

## TL;DR

- dsh bundles pi-ai's `openai-codex` provider, which authenticates with ChatGPT subscription OAuth. The login flow exists in the code, but no UI or CLI starts it: the Models page states that providers signing in with OAuth, such as Codex, are not supported yet.
- Copy the OAuth tokens that Codex CLI already holds into the dsh credential file as a `grant` record, then add an `openai-codex` route to your profile's `cordis.patch.yml`.
- The bundled model catalog (pi-ai 0.85.1) stops at GPT-6 Astra, so declare newer models such as `gpt-6-luna` yourself under `models:`.
- Never set `apiKeyEnv` or `api` on this route. Either one takes the route off the OAuth path.

## How it works

- pi-ai's `openai-codex` provider is OAuth-only. It sends requests with the `openai-codex-responses` protocol to `https://chatgpt.com/backend-api`.
- dsh reads the credential from its credential store, `$DSH_HOME/.credentials.yaml` (default `~/.dsh/.credentials.yaml`), under the record key `llm-pi-ai/openai-codex`. `llm-pi-ai` is the plugin that owns the record and `openai-codex` is the provider id.
- Codex CLI and pi-ai use the same OAuth client, so pi-ai can use, and refresh, tokens that Codex CLI obtained. The ChatGPT account id is read from the access token (a JWT) on every request.
- Once `expires` has passed, pi-ai refreshes the token and writes the new one back into the same record.

## Prerequisites

- dsh installed and started at least once, so `$DSH_HOME` exists.
- Codex CLI signed in with `codex login`, so `~/.codex/auth.json` exists.
- Python 3 for [`dsh-codex-sync.py`](dsh-codex-sync.py). It uses only the standard library.

The paths below use `$DSH_HOME` (default `~/.dsh`) and `<profile>`, your dsh profile name. `ls ~/.dsh/profiles` shows it, for example `web`.

## Setup

### 1. Back up

```sh
DSH_HOME=${DSH_HOME:-$HOME/.dsh}; PROFILE=web   # your profile name
TS=$(date +%Y%m%d-%H%M%S)
cp "$DSH_HOME/.credentials.yaml" "$DSH_HOME/.credentials.yaml.bak.$TS"
cp "$DSH_HOME/profiles/$PROFILE/cordis.patch.yml" "$DSH_HOME/profiles/$PROFILE/cordis.patch.yml.bak.$TS"
```

### 2. Write the credential record

The record looks like this. dsh refuses to load the file unless only its owner can read it (`chmod 600`).

```yaml
version: 1
records:
  llm-pi-ai/openai-codex:
    kind: grant
    payload:
      type: oauth
      access: "<access_token>"
      refresh: "<refresh_token>"
      expires: <epoch_ms>        # access-token expiry in epoch milliseconds
      accountId: "<account_id>"
```

| Payload field | Value in `~/.codex/auth.json` |
|---|---|
| `access` | `tokens.access_token` |
| `refresh` | `tokens.refresh_token` |
| `expires` | the access token's JWT `exp` claim × 1000 |
| `accountId` | `tokens.account_id` |

Instead of copying the values by hand, run the sync script:

```sh
python3 dsh-codex-sync.py
```

It replaces any existing `llm-pi-ai/openai-codex` record, leaves every other record and `refs` untouched, and keeps the file readable by its owner only. It honors `DSH_HOME` and `CODEX_HOME`. dsh reloads the file automatically, so you do not need to stop it.

### 3. Add the route and declare models

In `$DSH_HOME/profiles/<profile>/cordis.patch.yml`, add `openai-codex` under `providers` in the `llm-pi-ai` entry. If the entry already exists, which it does once you have saved any provider on the Models page, add to it rather than writing a second one: an override replaces the whole entry config, so keep the providers that are already there.

```yaml
- id: llm-pi-ai
  name: "@deepseek-ai/dsh-llm-pi-ai"
  config:
    providers:
      openai-codex:
        displayName: ChatGPT (Codex)
        reasoning: xhigh          # effort used while a session has picked none
        models:
          - id: gpt-6-luna
            name: GPT-6 Luna
            contextWindow: 272000
            maxTokens: 128000
            input: [text, image]
            reasoningEfforts:     # key = level shown in the picker, value = value sent on the wire
              low: low
              medium: medium
              high: high
              xhigh: xhigh
              max: max
          # list gpt-6-astra, gpt-6-sol, gpt-5.6-* and gpt-5.5 the same way
```

- `models:` replaces the bundled catalog instead of extending it. Only the models you list appear in the picker.
- Leave out `api` and `baseURL`. Listed models inherit `openai-codex-responses` and `https://chatgpt.com/backend-api` from the catalog route.
- A model that the bundled catalog does not know gets no Effort menu unless you declare `reasoningEfforts`.

### 4. Make it the default (optional)

Selecting a model in the picker also saves it as the default for new sessions. To set the default in the file instead:

```yaml
- id: agent-default-model
  name: "@deepseek-ai/dsh-agent-default-model"
  config:
    provider: openai-codex
    model: gpt-6-luna
    reasoningEffort: xhigh
```

To let subagents use it too, add an entry to `allowedModels` and keep your existing ones:

```yaml
- id: subagent-model-selection-settings
  name: "@deepseek-ai/dsh-tool-subagent/model-selection-settings"
  config:
    enabled: true
    allowedModels:
      - provider: openai-codex
        model: gpt-6-luna
      # ...your existing entries
```

### 5. Check

According to the dsh documentation, changes to `cordis.patch.yml` and `.credentials.yaml` take effect on the next request. If "ChatGPT (Codex)" does not appear in the model picker, restart dsh. Pick GPT-6 Luna and send a message. A reply means you are done.

## Models (reference)

`~/.codex/models_cache.json` lists the models that the Codex backend currently serves. Codex CLI fetches it, and it is newer than the catalog bundled with dsh. The table shows its `visibility: list` entries as of 2026-09-22. Yours may differ by plan and date.

| id | Name | Efforts |
|---|---|---|
| `gpt-6-luna` | GPT-6 Luna | low / medium / high / xhigh / max |
| `gpt-6-astra` | GPT-6 Astra | low / medium / high / xhigh / max |
| `gpt-6-sol` | GPT-6 Sol | low / medium / high / xhigh / max |
| `gpt-5.6-luna` | GPT-5.6 Luna | low / medium / high / xhigh / max |
| `gpt-5.6-terra` | GPT-5.6 Terra | low / medium / high / xhigh / max |
| `gpt-5.6-sol` | GPT-5.6 Sol | low / medium / high / xhigh / max |
| `gpt-5.5` | GPT-5.5 | low / medium / high / xhigh |

`contextWindow` follows the backend's `context_window` (272,000) and `maxTokens` follows the bundled catalog (128,000). All of them take text and image input.

To see what your own account serves:

```sh
python3 -c "
import json, os
home = os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex')
d = json.load(open(os.path.join(home, 'models_cache.json')))
print('fetched_at', d['fetched_at'])
for m in d['models']:
    if m.get('visibility') == 'list':
        print(m['slug'], m['context_window'], [e['effort'] for e in m['supported_reasoning_levels']])
"
```

## Caveats

- **Do not set `apiKeyEnv`.** dsh would resolve that reference as an API key and send it ahead of the OAuth token. A reference that resolves to nothing fails with `MISSING_CREDENTIAL`.
- **Do not set `api`.** The config schema rejects `openai-codex-responses`, and any other protocol, such as `openai-responses`, stops dsh from reusing the catalog provider, so requests no longer go through the Codex-specific implementation.
- **No `ultra` effort.** The backend offers `ultra` on Sol, Astra and Terra, but pi-ai's levels stop at `off / minimal / low / medium / high / xhigh / max`.
- **Fast mode (`service_tier: priority`) has no effect.** pi-ai can send a `serviceTier`, but the dsh `llm-pi-ai` adapter does not pass one in its [`streamSimple` call](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/packages/llm/llm-pi-ai/src/adapter.ts#L380-L388).
- **Shared tokens get invalidated.** When the access token expires, whichever of dsh and Codex CLI refreshes first receives a new refresh token, and the other one's copy can stop working. Copying tokens from Codex CLI puts you in exactly this situation. The next section avoids it.

## Optional: a separate sign-in for dsh (untested)

Signing in with pi-ai's own CLI creates an OAuth session separate from Codex CLI's, so the two never compete for a refresh token. The CLI writes `auth.json` to the current directory as `{"openai-codex": {type, access, refresh, expires, accountId}}`, which is the same shape as the grant payload, and `dsh-codex-sync.py` accepts that file. The CLI starts and its `list` command shows `openai-codex`, but the sign-in itself has not been tested yet.

```sh
D=$(mktemp -d) && cd "$D"
npx @earendil-works/pi-ai@0.85.1 login openai-codex   # 1 = browser, 2 = device code
python3 /path/to/dsh-codex-sync.py "$D/auth.json"
cd - && rm -rf "$D"
```

In a dsh source checkout you can run `packages/llm/llm-pi-ai/node_modules/.bin/pi-ai` instead of `npx`. After this, dsh and Codex CLI each refresh their own tokens.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Provider is not configured: openai-codex` (`PI_AI_ERROR`) | dsh cannot read the grant record. Check the key `llm-pi-ai/openai-codex`, the indentation, and `chmod 600`. |
| `OpenAI Codex token refresh failed (…)` | The refresh token is no longer valid. Run `codex login` and rerun the sync script, or redo the separate sign-in. |
| `MISSING_CREDENTIAL` | The route has an `apiKeyEnv`. Remove it. |
| `UNKNOWN_MODEL` | The default model's id is not listed under `models:`. |
| A model is missing from the picker | Only models listed under `models:` appear. Check the YAML indentation and restart dsh. |
| No Effort menu | The model has no `reasoningEfforts`. |

## Revert

1. Delete the `llm-pi-ai/openai-codex` record from `$DSH_HOME/.credentials.yaml`. dsh reloads the file automatically.
2. Remove the `openai-codex` route from `cordis.patch.yml` and restore `agent-default-model` and `allowedModels`, or restore the file from its `*.bak.<timestamp>` backup.

## Alternative: Codex as a subagent

[`@deepseek-ai/dsh-subagent-codex`](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/packages/subagent/subagent-codex/README.md) runs genuine Codex sessions as child processes and uses Codex CLI's own sign-in. Your conversation model stays the same, and only delegated tasks run on Codex. This path is officially supported.

## References

Links point at the dsh `dsh-v0.1.7-alpha.1` tag.

- [Configure models](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/docs/user/guide/providers.md): the Models page does not support OAuth providers yet; `reasoningEfforts` and `reasoning`
- [`dsh-llm-pi-ai` README](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/packages/llm/llm-pi-ai/README.md): route configuration, `models` versus `modelOverrides`
- [`dsh-credentials-local` README](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/packages/credentials/credentials-local/README.md): the `.credentials.yaml` format and permissions
- [`provider.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/packages/llm/llm-pi-ai/src/provider.ts): `routeAuth`, what `apiKeyEnv` adds to an OAuth-only route
- [`catalog.ts`](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/packages/llm/llm-pi-ai/src/catalog.ts): `resolveRouteModels`, how listed models inherit `api` and `baseUrl`
- [Credential records and authorization flows](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.7-alpha.1/.agents/notes/implemented/architecture/2026-08-13-credential-records-and-authorization-flows.md): the design note behind the credential store and the unused login flow
- [`@earendil-works/pi-ai`](https://www.npmjs.com/package/@earendil-works/pi-ai): the Codex OAuth implementation is `dist/auth/oauth/openai-codex.js`
