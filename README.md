# AskSia MCP plugin

Practice stored exam questions and review vocabulary through your AskSia account.
The MCP service runs in the existing Django backend; this repository contains
client configuration and three shared skills, with no local server or model.

## Skills and tools

- `exam-practice`: one question at a time, server grading, then an explanation.
- `vocab-review`: recall the meaning, reveal the card, then record your feedback.
- `getting-started`: connect AskSia and choose a study activity.

The connected server provides `get_my_exams`, `get_practice_questions`,
`submit_answer`, `get_vocab_cards`, `record_vocab_review`, and `get_vocab_progress`.
Available exams and content come from the server. Stored practice requires a
positive credit balance; these tools do not call AskSia's models or charge model
credits. Empty pools remain empty. Existing account entitlements and usage limits
apply. Practice attempts do not create or advance a learning plan.

## Package status and environments

The source manifests name the production endpoint `https://api.asksia.ai/mcp`.
Production activation remains a separate release decision; a valid package does
not prove that the service is deployed or authorized end to end.

Use `https://api1.asksia.ai/mcp` for preview acceptance. The ZIP builder defaults
to preview and modifies only the packaged configuration, never the source files.
An end-to-end connection also requires the frontend MCP login/consent page.

## Validate and build

Python 3 and Bash are sufficient for the offline package checks and ZIP build:

```bash
python3 scripts/validate-package.py
python3 -m unittest discover -s tests -p 'test_*.py'
bash scripts/build-chatgpt-zip.sh
```

The default output is `dist/asksia-chatgpt-preview.zip`. To prepare a production
artifact after release approval, pass `--env production`. Building a ZIP does
not publish it. The ZIP contains the portable manifests, skills, brand asset,
this README and LICENSE; no credentials, repository history or Claude-specific
configuration are included.

Claude Code 2.1.281 or later validates the current listing metadata and MCP
configuration. Run both manifests through the official CLI:

```bash
claude plugin validate .claude-plugin/plugin.json
claude plugin validate .claude-plugin/marketplace.json
```

Older validators can report current listing metadata as unknown. Use a compatible
validator instead of dropping required metadata or altering the user's global
Claude installation during automated checks.

## Claude Code

The Claude package uses `.claude-plugin/`, `.mcp.json`, and the shared `skills/`.
For preview, make an isolated local copy and change the two MCP configuration
URLs there before installing it:

```bash
python3 - <<'PY'
import json
import shutil
import tempfile
from pathlib import Path

source = Path.cwd()
target = Path(tempfile.mkdtemp(prefix='asksia-preview-')) / 'plugin'
shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git', 'dist', '.env', '.env.*', '__pycache__'))
for name in ('.mcp.json', 'mcp.json'):
    path = target / name
    config = json.loads(path.read_text())
    config['mcpServers']['asksia']['url'] = 'https://api1.asksia.ai/mcp'
    path.write_text(json.dumps(config, indent=2) + '\n')
print(target)
PY
```

Use the printed path with `/plugin marketplace add <path>`, then install
`asksia@asksia`. Alternatively, `claude --plugin-dir <path>` loads that copy for
one session. Use the client's MCP connection UI to complete OAuth in the browser.

After the production endpoint and authorization page are released, repository
installation uses `/plugin marketplace add Asksia-ai/Sia-Mcp` followed by
`/plugin install asksia@asksia`. Access to the repository is required while private.

## ChatGPT

`plugin.json` and `mcp.json` use the Agent Plugins portable format. The MCP server
uses Streamable HTTP. OAuth discovery, browser authorization, and credential
storage are handled by the client. When connection settings ask for authentication,
choose OAuth and prefer CIMD; endpoints and scopes come from the server discovery
documents. There is no client secret, upload API key, or user password in the package.

Follow the account's supported custom MCP/local plugin installation workflow to
connect the preview URL and load the skills. The ZIP is a distributable artifact;
this project does not assume every ChatGPT account has a generic ZIP import UI.
Public directory submission, reviewer accounts, and publishing are outside this
implementation. Follow the current official workflow when those are requested.

The portable MCP file intentionally uses only the standard transport and URL
fields. OpenAI documents an optional per-server authentication extension, but the
Agent Plugins 1.0.0 schema and current Codex loader reject that field. This package
keeps the standard configuration rather than embedding a host-specific auth
override. A schema check is separate from successful client OAuth acceptance.

## Data and privacy

OAuth identifies the AskSia account and grants the requested `progress.read`,
`practice`, and `vocab` permissions. Credentials are entered only on the service's
browser login page. The external AI client receives the selected exam/progress
information, question or vocabulary content, and submitted results. AskSia stores
practice attempts, vocabulary reviews, and tool activity for the connected account.
No database IDs or timestamps are exposed in the tool data; opaque handles connect
questions and cards with later submissions.

The client can also retain conversation content under its own settings and
policies. This plugin does not install hooks, background uploaders, or filesystem
collection scripts. Disconnect the integration using the host client's controls.

- [AskSia privacy policy](https://www.asksia.ai/policies/privacy)
- [Terms of use](https://www.asksia.ai/policies/termofuse)
- [Support](https://www.asksia.ai/contact-us)

The included brand image reuses AskSia's existing application asset. No open-source
license is granted by this package; see LICENSE.

## Implementation references

- [Claude plugin manifests](https://code.claude.com/docs/en/plugins-reference)
- [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [OpenAI portable packages](https://developers.openai.com/plugins/build/plugins)
- [OpenAI authentication](https://developers.openai.com/plugins/build/auth)
- [OpenAI connection testing](https://developers.openai.com/plugins/deploy/connect-chatgpt)
