#!/usr/bin/env python3
"""Write a Codex OAuth credential into the dsh grant record llm-pi-ai/openai-codex.

Usage:
  dsh-codex-sync.py              copy the tokens Codex CLI holds ($CODEX_HOME/auth.json)
  dsh-codex-sync.py AUTH_JSON    copy the credential `pi-ai login openai-codex` wrote

Replaces an existing llm-pi-ai/openai-codex record, keeps every other record and
ref, and leaves $DSH_HOME/.credentials.yaml readable by its owner only. dsh
reloads the file on its own.
"""
import base64
import json
import os
import re
import sys

DSH_HOME = os.environ.get('DSH_HOME') or os.path.expanduser('~/.dsh')
CODEX_HOME = os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex')
CRED = os.path.join(DSH_HOME, '.credentials.yaml')

if len(sys.argv) > 1:
    c = json.load(open(sys.argv[1]))['openai-codex']
    access, refresh, expires, account = c['access'], c['refresh'], c['expires'], c['accountId']
else:
    t = json.load(open(os.path.join(CODEX_HOME, 'auth.json')))['tokens']
    access, refresh, account = t['access_token'], t['refresh_token'], t['account_id']
    # pi-ai refreshes once `expires` has passed, so use the access token's own expiry.
    p = access.split('.')[1]
    expires = json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))['exp'] * 1000

src = open(CRED).read() if os.path.exists(CRED) else 'version: 1\n'
src = re.sub(r'\n  llm-pi-ai/openai-codex:\n(?:    .*\n)*', '\n', src)
if 'records:\n' not in src:
    src = src.rstrip('\n') + '\nrecords:\n'
block = ('  llm-pi-ai/openai-codex:\n'
         '    kind: grant\n'
         '    payload:\n'
         '      type: oauth\n'
         f'      access: "{access}"\n'
         f'      refresh: "{refresh}"\n'
         f'      expires: {expires}\n'
         f'      accountId: "{account}"\n')
fd = os.open(CRED, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write(src.replace('records:\n', 'records:\n' + block, 1))
os.chmod(CRED, 0o600)
print(f'wrote llm-pi-ai/openai-codex to {CRED}; access token expires at {expires} (epoch ms)')
