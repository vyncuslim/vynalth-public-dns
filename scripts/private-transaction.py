"""One authorized future trial. Never run during development-only work.

Global monotonic T0 precedes ALL commands, network and verification. No retries.
The conservative server deadline includes clock-probe roundtrip and a1s margin;
it cannot restart a fresh140s window after remote preflight. SSH key is filename
only. Unit tests inject a fake executor, never access Oracle.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/home/ubuntu/vynalth-public-dns'
HOST = 'ubuntu@100.95.65.20'


def mapped_deadline(server_monotonic, received_client_monotonic, origin):
    # Probe emission occurred before receipt. Use the earliest server deadline
    # consistent with that fact, not an optimistic clock offset/zero-latency guess.
    remaining = 140 - (received_client_monotonic - origin)
    if remaining <= 20 or not 0 < server_monotonic < float('inf'):
        raise ValueError('Clock probe invalid or global budget insufficient')
    return server_monotonic + remaining - 1


def execute(args, run=subprocess.run, clock=time.monotonic):
    origin = clock()  # BEFORE Git, SSH clock probe, verification or deployment.
    result = {'pass': False, 'global_limit_seconds': 140, 'commands': [], 'error': None,
              'deployment_command_started': False, 'confirmation_command_started': False}
    ssh = ['ssh', '-i', args.ssh_key, '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=4', '-o', 'ServerAliveInterval=3',
           '-o', 'ServerAliveCountMax=1', HOST]

    def command(argv, cap):
        remaining = 140 - (clock() - origin)
        if remaining <= 0:
            raise TimeoutError('Global140s deadline exhausted; no command started')
        proc = run(argv, text=True, capture_output=True, timeout=min(cap, remaining), check=True, cwd=ROOT)
        result['commands'].append({'program': argv[0], 'elapsed_global_seconds': clock() - origin})
        if clock() - origin >= 140:
            raise TimeoutError('Command completed beyond global deadline')
        return proc.stdout.strip()

    try:
        if command(['git', 'rev-parse', 'HEAD'], 5) != args.commit or command(['git', 'status', '--porcelain'], 5):
            raise ValueError('Local review drift')
        ref = command(['git', 'ls-remote', 'origin', 'refs/heads/codex/phase-a-dns'], 10).split()
        if not ref or ref[0] != args.commit:
            raise ValueError('Remote review drift')
        probe = json.loads(command(ssh + [f'cd {REMOTE} && sudo -n .venv/bin/python scripts/clock-probe.py'], 8))
        deadline = mapped_deadline(probe['monotonic'], clock(), origin)
        if not re.fullmatch(r'[a-f0-9-]{36}', probe['boot_id']):
            raise ValueError('Invalid clock-probe boot identity')
        result['server_global_deadline_monotonic'] = deadline
        preflight = (f'cd {REMOTE} && test "$(git rev-parse HEAD)" = {args.commit} && test -z "$(git status --porcelain)"'
                     ' && .venv/bin/python scripts/prepare-private.py && sha256sum --check plans/phase-b-service.sha256'
                     ' && sudo -n .venv/bin/python scripts/post-maintenance-readiness.py --baseline plans/post-boot-baseline.json'
                     ' --ssh-connection "$SSH_CONNECTION" --out artifacts/transaction-preflight.json')
        command(ssh + [preflight], 75)
        if clock() - origin >= 120:
            raise TimeoutError('Insufficient global deployment/confirmation reserve')
        result['deployment_command_started'] = True
        deploy = (f'cd {REMOTE} && sudo -n bash scripts/deploy-private.sh artifacts/private {args.config_sha256}'
                  f' {args.baseline_sha256} "$SSH_CONNECTION" {deadline:.9f} {probe["boot_id"]}')
        command(ssh + [deploy], 50)
        remaining = min(100, 120 - (clock() - origin))
        if remaining <= 0:
            raise TimeoutError('No acceptance budget remains')
        receipt_path = ROOT / 'artifacts/private-acceptance.json'
        command([sys.executable, str(ROOT / 'scripts/private-acceptance.py'), '--ssh-key', args.ssh_key,
                 '--config-sha256', args.config_sha256, '--authorized-target', '--deadline-seconds', str(remaining),
                 '--out', str(receipt_path)], remaining)
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('pass') is not True:
            raise ValueError('No complete PASS receipt')
        command(ssh[:-1] + [HOST, 'true'], 4)  # Fresh approved private recovery connection.
        command(['scp', '-i', args.ssh_key, '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
                 '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=4', str(receipt_path),
                 HOST + ':' + REMOTE + '/artifacts/private-acceptance.json'], 8)
        if clock() - origin >= 120:
            raise TimeoutError('Confirmation reserve exhausted')
        result['confirmation_command_started'] = True
        command(ssh + [f'cd {REMOTE} && sudo -n timeout --kill-after=45s 15s bash scripts/confirm.sh artifacts/private-acceptance.json "$SSH_CONNECTION"'], 19)
        result['pass'] = True
    except Exception as exc:
        result['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        if result['deployment_command_started']:
            # Recovery is NOT confirmation and is allowed after the acceptance
            # deadline. One attempt only; independent180s protection stays armed.
            try:
                run(ssh + ['sudo -n bash /var/lib/vynalth-dns/rollback.sh --service-only'],
                    text=True, capture_output=True, timeout=45, check=True, cwd=ROOT)
                result['recovery_command_returned_success'] = True
            except Exception as recovery:
                result['recovery_error'] = type(recovery).__name__
            if result['confirmation_command_started']:
                result['confirmation_outcome'] = 'UNKNOWN until approved snapshot/state inspection; never retry'
    result['elapsed_global_seconds'] = clock() - origin
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute-authorized-private-trial', action='store_true', required=True)
    for field in ('commit', 'config-sha256', 'baseline-sha256', 'ssh-key'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[a-f0-9]{40}', args.commit) or any(not re.fullmatch('[a-f0-9]{64}', value) for value in (args.config_sha256, args.baseline_sha256)):
        parser.error('Exact reviewed commit/config/baseline hashes required')
    result = execute(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))
    raise SystemExit(0 if result['pass'] else 1)
