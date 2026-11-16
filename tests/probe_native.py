"""Probe a fresh native Codex process without saving prompts or transcripts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import select
import subprocess
import time
import tomllib
from typing import Any


class NativeClient:
    """A short-lived stdio client that issues only read-only metadata requests."""

    def __init__(self, executable: str):
        self.process = subprocess.Popen([executable, 'app-server', '--stdio'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.buffer = b''
        self.sequence = 0
        self.call('initialize', {'clientInfo': {'name': 'constellation_native_probe', 'version': '1'}, 'capabilities': {'experimentalApi': True}})
        self.process.stdin.write(b'{"method":"initialized"}\n')
        self.process.stdin.flush()

    def call(self, method: str, params: dict[str, Any]) -> Any:
        """Return one matching response, ignoring notifications, within 45 seconds."""
        self.sequence += 1
        request_id = self.sequence
        self.process.stdin.write((json.dumps({'id': request_id, 'method': method, 'params': params}) + '\n').encode())
        self.process.stdin.flush()
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            while b'\n' in self.buffer:
                line, self.buffer = self.buffer.split(b'\n', 1)
                response = json.loads(line)
                if response.get('id') == request_id:
                    if 'error' in response:
                        raise RuntimeError(f'Native {method} failed: {response["error"].get("code")}')
                    return response['result']
            if select.select([self.process.stdout], [], [], 1)[0]:
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('Native app-server closed unexpectedly')
                self.buffer += chunk
        raise TimeoutError(f'Native {method} timed out')

    def close(self) -> None:
        """End only the isolated process created by this probe."""
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


def probe(source: Path, cwds: list[Path], executable: str, require_trust: bool) -> dict[str, Any]:
    """Inspect discovery and rendered role context, retaining only bounded metadata."""
    source = source.resolve()
    roles = [tomllib.loads(path.read_text())['name'] for path in sorted((source / 'agents').glob('*.toml'))]
    client = NativeClient(executable)
    try:
        skills = client.call('skills/list', {'cwds': [str(p) for p in cwds], 'forceReload': True})
        hooks = client.call('hooks/list', {'cwds': [str(p) for p in cwds]})
    finally:
        client.close()
    report: dict[str, Any] = {'fresh_process': True, 'version': subprocess.check_output([executable, '--version'], text=True).strip(), 'contexts': [], 'ok': True}
    for cwd in cwds:
        context_skills = next(item for item in skills['data'] if item['cwd'] == str(cwd))
        context_hooks = next(item for item in hooks['data'] if item['cwd'] == str(cwd))
        selected_skills = [row for row in context_skills['skills'] if Path(row['path']).resolve().is_relative_to(source)]
        selected_hooks = [row for row in context_hooks['hooks'] if str(source / 'constellation.py') in row.get('command', '')]
        # Rendering prompt input is native configuration evidence, not a model
        # response. Keep raw output only in process memory; never publish it.
        prompt = subprocess.run([executable, 'debug', 'prompt-input', 'Inspect installed capabilities only.'], cwd=cwd, capture_output=True, text=True, timeout=60)
        present = {role: role in prompt.stdout for role in roles}
        context = {'cwd': str(cwd), 'roles_present': present, 'skills': [{'name': row['name'], 'path': str(Path(row['path']).resolve()), 'enabled': row['enabled']} for row in selected_skills], 'hooks': [{'event': row['eventName'], 'enabled': row['enabled'], 'trust': row['trustStatus'], 'hash': row['currentHash']} for row in selected_hooks], 'errors': context_skills['errors'] + context_hooks['errors'], 'prompt_render_exit': prompt.returncode}
        context['ok'] = prompt.returncode == 0 and len(roles) == 8 and all(present.values()) and bool(selected_skills) and len(selected_hooks) == 2 and not context['errors'] and all(row['enabled'] for row in selected_hooks)
        if require_trust:
            context['ok'] = context['ok'] and all(row['trustStatus'] == 'trusted' for row in selected_hooks)
        report['contexts'].append(context)
        report['ok'] = report['ok'] and context['ok']
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--cwd', action='append', type=Path, required=True)
    parser.add_argument('--codex', default='codex')
    parser.add_argument('--require-trust', action='store_true')
    options = parser.parse_args()
    result = probe(options.source, options.cwd, options.codex, options.require_trust)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
