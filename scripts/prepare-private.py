"""Read-only active policy comparison. Produces review artifacts, never deploys."""
import difflib
import hashlib
import json
from pathlib import Path

from render import ROOT, render

def main():
    out = ROOT / 'artifacts/private'
    out.mkdir(parents=True, exist_ok=True)
    conf, firewall = render(json.loads((ROOT / 'config.private.example.json').read_text()))
    (out / 'unbound.conf').write_bytes(conf.encode('utf-8'))
    (out / 'firewall.nft').write_bytes(firewall.encode('utf-8'))
    active = Path('/etc/unbound/unbound.conf').read_text()
    diff = ''.join(difflib.unified_diff(active.splitlines(True), conf.splitlines(True),
                                       fromfile='/etc/unbound/unbound.conf (active)',
                                       tofile='artifacts/private/unbound.conf (proposed)'))
    (out / 'unbound.diff').write_text(diff)
    print(diff)
    print('APPROVED_CONFIG_SHA256=' + hashlib.sha256(conf.encode()).hexdigest())
    print('Firewall artifact only. No active settings changed.')

if __name__ == '__main__':
    main()
