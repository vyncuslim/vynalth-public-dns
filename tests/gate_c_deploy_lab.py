"""Actual deploy shell guards in private mounts; strict OS/timer shims, not DNS acceptance."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]


def inside(folder,mode):
    lab=Path(folder)
    assert lab.name.startswith('vynalth-transaction-') and (lab/'marker').exists()
    assert os.readlink('/proc/self/ns/mnt')!=(lab/'host-mount').read_text()
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    subprocess.run(['mount','-t','tmpfs','tmpfs','/tmp'],check=True)
    Path('/tmp/vynalth-transaction').mkdir()
    subprocess.run(['mount','--bind',str(lab),'/tmp/vynalth-transaction'],check=True)
    lab=Path('/tmp/vynalth-transaction')
    for name,target in [('etc','/etc'),('varlib','/var/lib'),('run','/run')]:
        subprocess.run(['mount','--bind',str(lab/name),target],check=True)
    import socket
    sock=socket.socket(socket.AF_UNIX); sock.bind('/run/unbound.ctl')
    env={**os.environ,'PATH':str(lab/'bin')+':'+os.environ['PATH'],'VYNALTH_LAB_MODE':mode}
    pending=Path('/var/lib/vynalth-dns/rollback')
    lock=None
    if mode=='locked':
        import fcntl
        lock=open('/var/lib/vynalth-dns/transaction.lock','w')
        fcntl.flock(lock,fcntl.LOCK_EX)
    if mode=='active-timer':
        Path('/run/systemd/transient/vynalth-rollback.timer').write_text('{}')
    if mode=='pending': pending.mkdir()
    repo=lab/'repo'; cfg=hashlib.sha256((repo/'plans/phase-b-unbound.conf').read_bytes()).hexdigest()
    proc=subprocess.run(['bash',str(repo/'scripts/deploy-private.sh'),str(lab/'rendered'),
                         '0'*64 if mode=='hash-mismatch' else cfg,
                         hashlib.sha256((repo/'plans/post-boot-baseline.json').read_bytes()).hexdigest(),
                         '100.85.132.14 1 100.95.65.20 22',str(time.monotonic()+130),
                         Path('/proc/sys/kernel/random/boot_id').read_text().strip()],env=env,capture_output=True,text=True,timeout=20)
    if lock: lock.close()
    assert (proc.returncode==0)==(mode=='success'),proc.stdout+proc.stderr
    active=Path('/etc/unbound/unbound.conf').read_bytes()
    assert active==((repo/'plans/phase-b-unbound.conf').read_bytes() if mode=='success' else b'original\n'),mode
    assert Path('/etc/ssh-sentinel').read_text()=='unchanged\n'
    assert Path('/etc/tailscale-sentinel').read_text()=='unchanged\n'
    assert Path('/var/lib/vynalth-dns/rolled-back-1791611257/retain').exists()
    if mode=='success':
        assert pending.is_dir() and (pending/'snapshot.sha256').exists()
    elif mode in ('bad-timer','listener-failure','interrupt'):
        assert not pending.exists() and list(Path('/var/lib/vynalth-dns').glob('rolled-back-*'))
    elif mode=='restart-failure':
        assert pending.is_dir(),'Failed recovery must retain evidence'
    print(json.dumps({'mode':mode,'pass':True,'scope':'actual deploy/rollback; OS and timer shims; private files'}))


def main():
    if subprocess.check_output(['hostname'],text=True).strip()=='vynalthai-dns':
        raise SystemExit('Known production host forbidden')
    if len(sys.argv)==4 and sys.argv[1]=='--inside':
        inside(sys.argv[2],sys.argv[3]); return
    if sys.argv[1:]!=['--authorized-independent-lab']:
        raise SystemExit('Explicit independent lab authorization required')
    for mode in ('success','locked','active-timer','pending','hash-mismatch','bad-timer','listener-failure','restart-failure','interrupt'):
        with tempfile.TemporaryDirectory(prefix='vynalth-transaction-',dir='/var/tmp') as folder:
            lab=Path(folder); (lab/'marker').touch()
            (lab/'host-mount').write_text(os.readlink('/proc/self/ns/mnt')); (lab/'production-pid').write_text('1234')
            shutil.copytree(ROOT,lab/'repo',ignore=shutil.ignore_patterns('.git','.venv','artifacts','__pycache__'))
            for name in ('etc/unbound/unbound.conf.d','etc/systemd/system/unbound.service.d','varlib/vynalth-dns/rolled-back-1791611257','run/systemd/transient','bin','repo/.venv/bin','rendered'):
                (lab/name).mkdir(parents=True,exist_ok=True)
            (lab/'original.conf').write_text('original\n'); (lab/'etc/unbound/unbound.conf').write_text('original\n')
            (lab/'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\n')
            (lab/'etc/group').write_text('root:x:0:\n')
            for name in ('ssh-sentinel','tailscale-sentinel'): (lab/'etc'/name).write_text('unchanged\n')
            (lab/'varlib/vynalth-dns/rolled-back-1791611257/retain').touch()
            for name in ('remote-control.conf','root-auto-trust-anchor-file.conf'):
                (lab/'etc/unbound/unbound.conf.d'/name).write_text('# fixture\n')
            shutil.copy(lab/'repo/plans/phase-b-unbound.conf',lab/'rendered/unbound.conf')
            active=lab/'repo/plans/phase-b-active.sha256'
            names=['unbound.conf','unbound.conf.d/remote-control.conf','unbound.conf.d/root-auto-trust-anchor-file.conf']
            active.write_text(''.join(hashlib.sha256((lab/'etc/unbound'/n).read_bytes()).hexdigest()+'  /etc/unbound/'+n+'\n' for n in names))
            manifest=lab/'repo/plans/phase-b-service.sha256'
            entries=[x.split('  ',1)[1] for x in manifest.read_text().splitlines()]
            manifest.write_text(''.join(hashlib.sha256((lab/'repo'/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in entries))
            for name in ('systemctl','systemd-run','busctl','ip','dig'):
                extra=''
                if name=='systemctl':
                    extra='if sys.argv[1:]==["restart","unbound"] and os.environ["VYNALTH_LAB_MODE"]=="restart-failure": sys.exit(42)\n'
                if name=='dig':
                    extra='if os.environ["VYNALTH_LAB_MODE"]=="listener-failure": sys.exit(1)\nif os.environ["VYNALTH_LAB_MODE"]=="interrupt": os.kill(os.getppid(),15); sys.exit(1)\n'
                program=lab/'bin'/name
                program.write_text('#!'+sys.executable+'\nimport os,sys\n'+extra+'sys.argv.insert(1,"'+name+'")\nexec(open("/tmp/vynalth-transaction/repo/tests/transaction_command_shim.py").read())\n')
                program.chmod(0o700)
            check=lab/'bin/unbound-checkconf'; check.write_text('#!/bin/sh\nexit 0\n'); check.chmod(0o700)
            wrapper=lab/'repo/.venv/bin/python'
            wrapper.write_text('#!/bin/sh\ncase "$1" in */verify-post-boot.py) exit 0;; esac\nexec '+sys.executable+' "$@"\n'); wrapper.chmod(0o700)
            subprocess.run(['unshare','--mount',sys.executable,str(Path(__file__).resolve()),'--inside',folder,mode],check=True)


if __name__=='__main__': main()
