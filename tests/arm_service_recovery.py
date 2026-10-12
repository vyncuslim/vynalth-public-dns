"""Hosted ARM CI only: actual unique Unbound service/cgroup and service-only restore.

No default unbound.service changes; no VPN/network/public DNS. Private namespaces.
AppArmor enforcement is mandatory. Local-data recovery is not production recovery.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]


def fixture_config(conf,lab):
    conf=conf.replace('username: "unbound"','username: ""').replace('directory: "/etc/unbound"',f'directory: "{lab}"')
    conf=conf.replace('/run/unbound.ctl',str(lab/'control.sock'))
    conf='\n'.join(x for x in conf.splitlines() if 'auto-trust-anchor-file:' not in x)+'\n'
    return conf+f'\nserver:\n    pidfile: "{lab}/unbound.pid"\n    use-syslog: no\n    local-zone: "fixture.test." static\n    local-data: "a.fixture.test. 60 IN A 203.0.113.8"\n'


def run(*argv):
    return subprocess.check_output(argv,text=True,timeout=45).strip()


def restore(lab):
    assert lab.name.startswith('vynalth-arm-ci-') and (lab/'marker').exists()
    assert os.readlink('/proc/self/ns/mnt')!=(lab/'parent-ns').read_text()
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    # /var/lib overlay would hide the lab; retain an alias outside it.
    temp=Path(tempfile.mkdtemp(prefix='vynalth-arm-restore-',dir='/tmp'))
    try:
        subprocess.run(['mount','--bind',str(lab),str(temp)],check=True)
        subprocess.run(['mount','--bind',str(temp/'etc'),'/etc/unbound'],check=True)
        subprocess.run(['mount','--bind',str(temp/'shadow-system'),'/etc/systemd/system'],check=True)
        subprocess.run(['mount','--bind',str(temp/'units'),'/etc/systemd/system/unbound.service.d'],check=True)
        subprocess.run(['mount','--bind',str(temp/'varlib'),'/var/lib'],check=True)
        subprocess.run(['bash',str(ROOT/'scripts/rollback.sh'),'--service-only'],env={**os.environ,'PATH':str(temp/'bin')+':'+os.environ['PATH']},check=True)
    finally:
        subprocess.run(['umount',str(temp)],check=True)
        temp.rmdir()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--inside',type=Path); p.add_argument('--out',type=Path)
    args=p.parse_args()
    if os.uname().nodename=='vynalthai-dns': raise SystemExit('Production forbidden')
    if args.inside: restore(args.inside); return
    if os.environ.get('GITHUB_ACTIONS')!='true' or os.environ.get('RUNNER_ARCH')!='ARM64' or os.uname().machine!='aarch64':
        raise SystemExit('Only authorized native ARM hosted CI; no local/Oracle fallback')
    if os.geteuid()!=0 or args.out is None: p.error('Root and output required')
    enabled=Path('/sys/module/apparmor/parameters/enabled')
    if not enabled.exists() or enabled.read_text().strip()!='Y': raise SystemExit('Enforcement unavailable')
    result={'pass':False,'scope':'hosted ARM unique actual service; local fixture; NOT production recovery'}
    lab=Path(tempfile.mkdtemp(prefix='vynalth-arm-ci-',dir='/var/lib/unbound'))
    unit='vynalth-arm-ci-'+uuid.uuid4().hex+'.service'
    unitfile=Path('/run/systemd/system')/unit
    dropin=Path('/run/systemd/system')/(unit+'.d')
    try:
        (lab/'marker').touch(); (lab/'parent-ns').write_text(os.readlink('/proc/self/ns/mnt'))
        for name in ('etc','units','varlib/vynalth-dns/rollback','bin','shadow-system/unbound.service.d'):
            (lab/name).mkdir(parents=True,exist_ok=True)
        conf=fixture_config((ROOT/'plans/phase-b-unbound.conf').read_text(),lab)
        original=conf
        config=lab/'etc/unbound.conf'; config.write_text(conf)
        (lab/'units/private.conf').write_text('[Service]\nMemoryMax=256M\nTasksMax=32\nLimitNOFILE=512\n')
        entry=lab/'entry.sh'
        entry.write_text('#!/bin/bash\nset -euo pipefail\nip link set lo up\ntest -z "$(ip route show default)"\nfor ip in 100.95.65.20 100.85.132.14 100.75.232.110; do ip addr add "$ip/32" dev lo; done\nexec /usr/sbin/unbound -d -c '+str(config)+'\n')
        unitfile.write_text('[Service]\nType=simple\nExecStart=/usr/bin/unshare --net /bin/bash '+str(entry)+'\n')
        dropin.symlink_to(lab/'units',target_is_directory=True)
        subprocess.run(['unbound-checkconf',str(config)],check=True)
        run('systemctl','daemon-reload'); run('systemctl','start',unit)
        def inspect(expected_ip,expected_limits):
            pid=int(run('systemctl','show',unit,'-p','MainPID','--value'))
            for _ in range(100):
                if Path(f'/proc/{pid}/comm').read_text().strip()=='unbound' and (lab/'control.sock').exists(): break
                time.sleep(.05)
            else: raise RuntimeError('Actual service not ready')
            label=Path(f'/proc/{pid}/attr/current').read_text().strip().rstrip('\0')
            assert label=='unbound (enforce)',label
            props=dict(x.split('=',1) for x in run('systemctl','show',unit,'-p','MemoryMax','-p','TasksMax','-p','LimitNOFILE').splitlines())
            assert tuple(int(props[k]) for k in ('MemoryMax','TasksMax','LimitNOFILE'))==expected_limits,props
            cgroup=next(x.split(':',2)[2] for x in Path(f'/proc/{pid}/cgroup').read_text().splitlines() if x.startswith('0::'))
            memory=Path('/sys/fs/cgroup'+cgroup+'/memory.max').read_text().strip()
            tasks=Path('/sys/fs/cgroup'+cgroup+'/pids.max').read_text().strip()
            assert int(memory)==expected_limits[0] and int(tasks)==expected_limits[1]
            limits=Path(f'/proc/{pid}/limits').read_text()
            line=next(x for x in limits.splitlines() if x.startswith('Max open files'))
            assert int(line.split()[3])==expected_limits[2],line
            for client in ('100.85.132.14','100.75.232.110'):
                for transport in ('+notcp','+tcp'):
                    reply=run('nsenter','-t',str(pid),'-n','dig','-b',client,'@100.95.65.20','a.fixture.test.','A',transport,'+short','+tries=1','+time=2')
                    assert reply==expected_ip,reply
            return {'pid':pid,'profile':label,'unit_limits':props,'cgroup_memory_max':memory,'cgroup_pids_max':tasks,'open_files':line}
        result['original']=inspect('203.0.113.8',(268435456,32,512))
        backup=lab/'varlib/vynalth-dns/rollback'
        (backup/'unbound.conf').write_text(original)
        shutil.copy(lab/'units/private.conf',backup/'unbound-private-limits.conf')
        (backup/'snapshot.sha256').write_text(''.join(hashlib.sha256((backup/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ('unbound.conf','unbound-private-limits.conf')))
        config.write_text(conf.replace('203.0.113.8','203.0.113.9'))
        (lab/'units/private.conf').write_text('[Service]\nMemoryMax=384M\nTasksMax=64\nLimitNOFILE=1024\n')
        run('systemctl','daemon-reload'); run('systemctl','restart',unit)
        result['candidate']=inspect('203.0.113.9',(402653184,64,1024))
        shim=lab/'bin/systemctl'
        shim.write_text('#!/bin/sh\ncase "$*" in "daemon-reload") exec /usr/bin/systemctl daemon-reload;; "restart unbound") exec /usr/bin/systemctl restart '+unit+';; *) exit 99;; esac\n'); shim.chmod(0o700)
        (lab/'bin/nft').write_text('#!/bin/sh\nexit 99\n'); (lab/'bin/nft').chmod(0o700)
        subprocess.run(['unshare','--mount',sys.executable,str(Path(__file__).resolve()),'--inside',str(lab)],check=True)
        assert config.read_text()==original
        result['restored']=inspect('203.0.113.8',(268435456,32,512))
        assert len({result[x]['pid'] for x in ('original','candidate','restored')})==3
        result['pass']=True
    finally:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        with open(str(args.out)+'.journal.txt','w') as journal:
            subprocess.run(['journalctl','--no-pager','-u',unit,'-n','50'],stdout=journal)
        stopped=subprocess.run(['systemctl','stop',unit],capture_output=True)
        active=subprocess.run(['systemctl','is-active','--quiet',unit]).returncode==0
        if stopped.returncode or active:
            result.update(cleanup_error='Unique lab unit not stopped; owned files retained',retained_lab=str(lab))
            result['pass']=False
            args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            raise RuntimeError('Lab cleanup failed; no PASS claimed')
        dropin.unlink(missing_ok=True); unitfile.unlink(missing_ok=True)
        subprocess.run(['systemctl','daemon-reload'],capture_output=True)
        shutil.rmtree(lab)


if __name__=='__main__': main()
