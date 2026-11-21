"""Translate Copilot CLI events into Constellation's existing scope controls.

The native client runs agents and owns permissions. This adapter neither launches
agents nor runs tests. It never reads transcripts or stores hook input. Unknown
tools retain native permission handling; known writes with unknown shapes fail
closed. Shell execution remains outside the structured-write guarantee.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Mapping, TextIO

from . import hooks
from .state import Store

EVENTS = frozenset({'sessionStart', 'subagentStart', 'preToolUse', 'agentStop', 'subagentStop'})
WRITE_TOOLS = frozenset({'create', 'edit', 'apply_patch', 'str_replace_editor'})
SHELL_TOOLS = frozenset({'bash', 'powershell'})


def _deny(reason: str) -> dict[str, str]:
    return {'permissionDecision': 'deny', 'permissionDecisionReason': 'Constellation: ' + reason}


def _identity(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Keep the native parent session separate from an explicitly supplied child."""
    session = payload.get('sessionId')
    child = payload.get('agentId')
    if not isinstance(session, str) or not session.strip():
        raise ValueError('A native sessionId is required')
    if 'agentId' in payload and (not isinstance(child, str) or not child.strip()):
        raise ValueError('A supplied agentId must be a nonempty native identifier')
    if not child and any(payload.get(field) for field in ('agentType', 'parentAgentId')):
        raise ValueError('A subagent event must carry its own agentId')
    return {'session_id': session, 'agent_id': child or session, 'cwd': payload.get('cwd')}


def _arguments(value: Any) -> Mapping[str, Any]:
    """Decode native object arguments or their JSON string representation."""
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError('Expected structured tool arguments')
    return value


def _target(arguments: Mapping[str, Any]) -> str:
    """Accept known target aliases only when they agree on the exact path."""
    paths = [arguments[key] for key in ('path', 'file_path', 'filePath') if key in arguments]
    if (not paths or not all(isinstance(path, str) and path for path in paths)
            or any(path != paths[0] for path in paths)):
        raise ValueError('Missing or conflicting structured edit target')
    return paths[0]


def pre_tool(payload: Mapping[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Apply existing scope rules without approving native permissions.

    Args:
        payload: A camelCase Copilot preToolUse event.
        store: Optional shared ledger; the normal private store is used otherwise.

    Returns:
        A native denial, or an empty object preserving the client's permission
        flow. Argument aliases are compatibility handling, not a complete tool
        schema: GitHub documents toolArgs as an unknown value.
    """
    tool = payload.get('toolName')
    if not isinstance(tool, str) or not tool:
        return _deny('Missing native toolName')
    if tool not in WRITE_TOOLS | SHELL_TOOLS:
        return {}
    try:
        value = payload.get('toolArgs')
        if tool == 'apply_patch':
            # The common parser validates every target, including both sides of
            # a move. Never fall back to extracting a single filename from text.
            arguments = value if isinstance(value, str) and value.lstrip().startswith('*** Begin Patch') else _arguments(value)
            normalized = {**_identity(payload), 'tool_name': 'apply_patch', 'tool_input': arguments}
        elif tool in SHELL_TOOLS:
            arguments = _arguments(value)
            command = arguments.get('command')
            if not isinstance(command, str):
                raise ValueError('Shell tool lacks a command string')
            normalized = {'tool_name': 'bash', 'tool_input': {'command': command}}
        else:
            arguments = _arguments(value)
            # A view operation must remain read-only. Unknown editor operations
            # are treated as writes and still require the exact assigned path.
            if tool == 'str_replace_editor' and arguments.get('command') == 'view':
                return {}
            normalized = {**_identity(payload), 'tool_name': 'write' if tool == 'create' else 'edit',
                          'tool_input': {'file_path': _target(arguments)}}
        result = hooks.pre_tool(normalized, store)
        decision = result.get('hookSpecificOutput', {})
        if decision.get('permissionDecision') == 'deny':
            return {'permissionDecision': 'deny',
                    'permissionDecisionReason': decision['permissionDecisionReason']}
        return {}
    except (ValueError, TypeError, KeyError):
        return _deny('Cannot interpret this known write or shell operation; inspect its native schema and declared scope.')


def _pending(payload: Mapping[str, Any], store: Store | None) -> list[dict[str, Any]]:
    """Select only tasks associated with the supplied native session and actor."""
    native = _identity(payload)
    session, actor = native['session_id'], native['agent_id']
    return [task for task in hooks._active(store)
            if hooks._participates(task, session, hooks._actor(task, session, actor))]


def _task_names(tasks: list[dict[str, Any]]) -> str:
    return ', '.join(task['id'] for task in tasks[:8])


def start_context(payload: Mapping[str, Any], *, subagent: bool = False,
                  store: Store | None = None) -> dict[str, str]:
    """Provide a short workflow reminder without inspecting a user's prompt."""
    source = Path(__file__).resolve().parents[1]
    context = (f'Constellation source: {source}. Read its README and the applicable project profile. '
               'Use native agents for independent work; assign exact paths and register returned native IDs '
               'before editing. Inherit the session model and effort. Make the smallest complete change. '
               'Follow the shared engineering rules for readable code and focused testing. '
               'Use independent read-only review and state the limits of static evidence. '
               'Do not read or archive transcripts for this workflow.')
    if subagent:
        # subagentStart names the role but does not guarantee the child's native
        # ID. Only the coordinator can register the returned execution identity.
        return {'additionalContext': context + ' Wait for the coordinator to register your identity and ownership. '
                'Return files, findings, evidence and limits; the coordinator integrates and records review.'}
    tasks = _pending(payload, store)
    if tasks:
        context += ' Resume associated local tasks: ' + _task_names(tasks) + '.'
    return {'additionalContext': context}


def agent_stop(payload: Mapping[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Reuse the shared one-continuation reminder without certifying completion."""
    normalized = {**_identity(payload), 'stop_hook_active': payload.get('stop_hook_active') is True}
    result = hooks.stop(normalized, store)
    if result.get('decision') == 'block':
        return {'decision': 'block', 'reason': result['reason']}
    return {}


def subagent_stop(payload: Mapping[str, Any], store: Store | None = None) -> dict[str, str]:
    """Attach an honest handoff status; a child never waits for its parent's review.

    The original response is preserved verbatim and never written to disk. A
    pending task is normal when an author finishes: review and integration belong
    to the coordinator, so blocking the child here would create a dependency loop.
    """
    if not isinstance(payload.get('agentId'), str) or not payload['agentId']:
        return {}
    tasks = _pending(payload, store)
    response = payload.get('response')
    if not tasks or not isinstance(response, str):
        return {}
    status = ('Constellation handoff: ' + _task_names(tasks) + ' remains open. '
              'This response is not approval. The coordinator must integrate the candidate, '
              'record permitted checks and obtain independent review before completion.')
    return {'modifiedResponse': status + '\n\n' + response}


def main(event: str, stdin: TextIO | None = None) -> int:
    """Handle one documented camelCase event and emit a single JSON object.

    Malformed pre-tool input denies execution. Lifecycle errors are reported on
    stderr without blocking a recovery conversation or exposing payload data.
    """
    if event not in EVENTS:
        raise ValueError('Unsupported Copilot hook event')
    try:
        payload = json.load(stdin or sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError('Hook input must be an object')
        if event == 'preToolUse':
            result = pre_tool(payload)
        elif event in {'sessionStart', 'subagentStart'}:
            result = start_context(payload, subagent=event == 'subagentStart')
        elif event == 'agentStop':
            result = agent_stop(payload)
        else:
            result = subagent_stop(payload)
    except (ValueError, OSError, KeyError, TypeError):
        if event == 'preToolUse':
            result = _deny('Malformed hook input or unavailable scope evidence')
        else:
            result = {}
            print('Constellation could not inspect this lifecycle event; no completion is certified.', file=sys.stderr)
    print(json.dumps(result))
    return 0
