"""Authorized independent local/CI lab only: real180s systemd timers, file mounts.

No host DNS service/config required. Actual rollback.sh; service calls shimmed.
Timer survives killed dummy controller; confirmed snapshot no-ops on expiry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]


def inside(lab):
    assert lab.name.startswith('vynalth-local-gate-c-') and (lab/'marker').is_file()
    assert os.readlink('/proc/self/ns/mnt')!=(lab/'parent-ns').read_text()
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    subprocess.run(['mount','--bind',str(lab/'etc'),'/etc'],check=True)
    subprocess.run(['mount','--bind',str(lab/'varlib'),'/var/lib'],check=True)
    env={**os.environ,'PATH':str(lab/'bin')+':'+os.environ['PATH']}
    subprocess.run(['bash',str(ROOT/'scripts/rollback.sh'),'--service-only'],env=env,check=True)
    (lab/'callback-finished').write_text(str(time.monotonic()))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--authorized-independent-lab',action='store_true')
    p.add_argument('--inside',type=Path)
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    if subprocess.check_output(['hostname'],text=True).strip()=='vynalthai-dns':
        raise SystemExit('Refuse known production hostname; never run this on Oracle')
    if args.inside:
        inside(args.inside); return
    if not args.authorized_independent_lab or args.out is None or os.geteuid()!=0:
        p.error('Explicit authorized independent root lab and output required')
    result={'pass':False,'scope':'independent local systemd timers; private files; service shims',
            'architecture':os.uname().machine,'cases':[]}
    units=[]; folders=[]
    try:
        for mode in ('controller-killed','confirmed-no-op'):
            lab=Path(tempfile.mkdtemp(prefix='vynalth-local-gate-c-'))
            folders.append(lab)
            (lab/'marker').touch(); (lab/'parent-ns').write_text(os.readlink('/proc/self/ns/mnt'))
            for name in ['etc/unbound','etc/systemd/system/unbound.service.d','varlib/vynalth-dns/rollback','varlib/vynalth-dns/rolled-back-1791611257','bin']:
                (lab/name).mkdir(parents=True,exist_ok=True)
            backup=lab/'varlib/vynalth-dns/rollback'
            (backup/'unbound.conf').write_text('original configuration\n')
            (backup/'unbound-private-limits.conf').write_text('original limits\n')
            (backup/'service-only').touch()
            (backup/'snapshot.sha256').write_text(''.join(hashlib.sha256((backup/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in ('unbound.conf','unbound-private-limits.conf')))
            (lab/'etc/unbound/unbound.conf').write_text('candidate configuration\n')
            (lab/'etc/systemd/system/unbound.service.d/private.conf').write_text('candidate limits\n')
            (lab/'etc/systemd/system/unbound.service.d/unrelated.conf').write_text('unrelated\n')
            for name in ('ssh.conf','tailscale.conf'):
                (lab/'etc'/name).write_text('management unchanged\n')
            (lab/'varlib/vynalth-dns/rolled-back-1791611257/retain').write_text('historical backup\n')
            shim=lab/'bin/systemctl'
            shim.write_text('#!/bin/sh\ncase "$*" in "daemon-reload"|"restart unbound") echo "$*" >> /var/lib/vynalth-dns/calls;; *) exit 99;; esac\n')
            shim.chmod(0o700)
            (lab/'bin/nft').write_text('#!/bin/sh\nexit 99\n'); (lab/'bin/nft').chmod(0o700)
            unit='vynalth-local-gate-c-'+uuid.uuid4().hex
            units.append(unit)
            started=time.monotonic()
            subprocess.run(['systemd-run','--unit='+unit,'--on-active=180s','--timer-property=AccuracySec=1s',
                            '/usr/bin/unshare','--mount','/usr/bin/python3',str(Path(__file__).resolve()),'--inside',str(lab)],check=True)
            guard=subprocess.run(['python3',str(ROOT/'scripts/check-rollback-timer.py'),'--unit',unit+'.timer'],capture_output=True,text=True,check=True)
            readiness=json.loads(guard.stdout)
            if mode=='controller-killed':
                controller=subprocess.Popen(['sleep','60'])
                controller.kill(); controller.wait(timeout=5)
                assert controller.returncode==-signal.SIGKILL
            else:
                # Models the atomic commit only; not a production acceptance/confirm PASS.
                backup.rename(lab/'varlib/vynalth-dns/confirmed-lab')
            result['cases'].append({'mode':mode,'started':started,'unit':unit,'timer_readiness':readiness,'lab':str(lab)})
        # Two actual independent180s timers run concurrently; no timer is canceled early.
        for row in result['cases']:
            lab=Path(row['lab'])
            while not (lab/'callback-finished').exists() and time.monotonic()-row['started']<220:
                time.sleep(.5)
            assert (lab/'callback-finished').exists(),row
            elapsed=float((lab/'callback-finished').read_text())-row['started']
            assert 180<=elapsed<220,elapsed
            row['elapsed_seconds']=round(elapsed,6)
            if row['mode']=='controller-killed':
                assert (lab/'etc/unbound/unbound.conf').read_text()=='original configuration\n'
                assert (lab/'etc/systemd/system/unbound.service.d/private.conf').read_text()=='original limits\n'
                assert (lab/'varlib/vynalth-dns/calls').read_text()=='daemon-reload\nrestart unbound\n'
            else:
                assert (lab/'etc/unbound/unbound.conf').read_text()=='candidate configuration\n'
                assert not (lab/'varlib/vynalth-dns/calls').exists()
            for name in ('ssh.conf','tailscale.conf'):
                assert (lab/'etc'/name).read_text()=='management unchanged\n'
            assert (lab/'etc/systemd/system/unbound.service.d/unrelated.conf').read_text()=='unrelated\n'
            assert (lab/'varlib/vynalth-dns/rolled-back-1791611257/retain').read_text()=='historical backup\n'
            assert not (lab/'varlib/vynalth-dns/rollback').exists()
            row['pass']=True
        result['pass']=True
    finally:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        # Local-owned lab resources only, after expiry or failure evidence is saved.
        for unit in units:
            subprocess.run(['systemctl','stop',unit+'.timer',unit+'.service'],capture_output=True)
        for lab in folders:
            shutil.rmtree(lab)
    print(json.dumps(result))


if __name__=='__main__':
    main()
