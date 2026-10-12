"""Read-only independent ARM lab capability gate, never production authorization."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess


def evaluate(row):
    failures=[]
    for ok,message in [(row['hostname']!='vynalthai-dns','Known production hostname forbidden'),
                       (row['architecture']=='aarch64','Actual ARM64 required; x86/emulation not equivalent'),
                       (row['ubuntu24'],'Ubuntu24.04 required'),(row['systemd'],'Real systemd manager required'),
                       (row['apparmor_enabled'],'AppArmor enforcement unavailable'),
                       (row['unbound_available'],'Actual Unbound package required')]:
        if not ok: failures.append(message)
    return {'pass':not failures,'failures':failures,'capabilities':row,
            'authorization':'Independent lab prerequisite only; never approves Oracle or deployment'}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--authorized-independent-lab',action='store_true',required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    release=Path('/etc/os-release').read_text()
    row={'hostname':platform.node(),'architecture':platform.machine(),
         'ubuntu24':'ID=ubuntu' in release and 'VERSION_ID="24.04"' in release,
         'systemd':Path('/proc/1/comm').read_text().strip()=='systemd',
         'apparmor_enabled':Path('/sys/module/apparmor/parameters/enabled').exists() and
             Path('/sys/module/apparmor/parameters/enabled').read_text().strip()=='Y',
         'unbound_available':shutil.which('unbound') is not None}
    result=evaluate(row)
    if row['hostname']=='vynalthai-dns':
        raise SystemExit('Refuse production host; no output file written')
    if row['unbound_available']:
        result['unbound_version']=subprocess.check_output(['unbound','-V'],text=True,stderr=subprocess.STDOUT).splitlines()[0]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    raise SystemExit(0 if result['pass'] else 1)


if __name__=='__main__':
    main()
