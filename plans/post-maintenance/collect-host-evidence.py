"""Read-only evidence; run with sudo in the VM repository."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

def read(*args):
    proc = subprocess.run(args, text=True, capture_output=True, timeout=15)
    return {'exit_code': proc.returncode, 'stdout': proc.stdout.strip(), 'stderr': proc.stderr.strip()}

result = {'recorded_utc': datetime.now(timezone.utc).isoformat(),
    'kernel_running': read('uname', '-r'),
    'installed_kernels': read('dpkg-query', '-W', 'linux-image-*oracle'),
    'boot_links': read('readlink', '-f', '/boot/vmlinuz', '/boot/initrd.img'),
    'kernel_files': [p.name for p in Path('/boot').glob('*oracle')],
    'grub_entries': [line for line in Path('/boot/grub/grub.cfg').read_text().splitlines() if line.startswith('menuentry ') or 'menuentry ' in line and 'oracle' in line],
    'grub_default': [line for line in Path('/etc/default/grub').read_text().splitlines() if line.startswith('GRUB_DEFAULT=')],
    'scheduled_shutdown_exists': Path('/run/systemd/shutdown/scheduled').exists(),
    'apt_policy': read('apt-config', 'dump'),
    'ssh_socket': read('systemctl', 'show', 'ssh.socket', '-p', 'ActiveState', '-p', 'Listen', '-p', 'UnitFileState'),
    'old_timer_journal': read('journalctl', '--no-pager', '-u', 'vynalth-rollback.timer', '-u', 'vynalth-rollback.service', '--since', '2026-10-10 05:47:00', '-o', 'short-iso'),
    'retained_backup': read('test', '-d', '/var/lib/vynalth-dns/rolled-back-1791611257')}
result['apt_policy']['stdout'] = '\n'.join(line for line in result['apt_policy']['stdout'].splitlines() if line.startswith('APT::Periodic') or line.startswith('Unattended-Upgrade::Automatic-Reboot'))
Path('artifacts/post-maintenance-host.json').write_text(json.dumps(result, indent=2))
print(json.dumps({'recorded_utc': result['recorded_utc'], 'kernel': result['kernel_running']['stdout']}))
