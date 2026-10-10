"""Local/CI only: negative semantics and finite reply-age A/B, no live host."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype
from negative_authority import NegativeAuthority
from local_runtime import Authority
from acceptance import check_query

ROOT = Path(__file__).resolve().parents[1]


def config(folder):
    text = (ROOT/'plans/phase-b-unbound.conf').read_text()
    text = text.replace('username: "unbound"', 'username: ""').replace('directory: "/etc/unbound"', f'directory: "{folder}"')
    text = text.replace('    interface: 100.95.65.20\n', '').replace('port: 53', 'port: 15359')
    text = text.replace('/run/unbound.ctl', f'{folder}/control.sock')
    text = text.replace('/usr/share/dns/root.hints', str(Path(os.environ.get('DNS_ROOT_DATA', '/usr/share/dns'))/'root.hints'))
    text = '\n'.join(line for line in text.splitlines() if 'auto-trust-anchor-file:' not in line)+'\n'
    return text+f'\nserver:\n    pidfile: "{folder}/unbound.pid"\n    use-syslog: no\n    do-not-query-localhost: no\n    local-zone: "test." nodefault\n'


def start(path, log, enforcing):
    subprocess.run(['unbound-checkconf', str(path)], check=True, stdout=subprocess.DEVNULL)
    proc = subprocess.Popen(['unbound','-d','-c',str(path)],stdout=log,stderr=log)
    try:
        for _ in range(100):
            if proc.poll() is not None:
                raise RuntimeError('Fixture startup failed: '+str(path))
            if (path.parent/'control.sock').exists():
                break
            time.sleep(.05)
        else:
            raise TimeoutError('Fixture not ready')
        label=Path(f'/proc/{proc.pid}/attr/current').read_text().strip().rstrip('\0')
        if enforcing and label!='unbound (enforce)':
            raise RuntimeError('Enforcing AppArmor required, unavailable: '+label)
        return proc,label
    except BaseException:
        proc.terminate()
        proc.wait(timeout=5)
        raise


def stop(proc):
    if proc.poll() is None:
        proc.terminate()
    proc.wait(timeout=5)


def negatives(args, parent):
    authority=NegativeAuthority()
    result={'pass':False,'queries':[], 'negative_cache':[]}
    try:
        with tempfile.TemporaryDirectory(prefix='vynalth-negatives-',dir=parent) as folder:
            base=Path(folder)
            (base/'fixture.key').write_text(''.join(records[dns.name.from_text(zone)][dns.rdatatype.DNSKEY].to_text()+'\n'
                for zone,(signed,records) in authority.zones.items() if signed))
            conf=config(folder)+f'    trust-anchor-file: "{base}/fixture.key"\n    domain-insecure: "unsigned-negative.test."\n'
            for zone in authority.zones:
                conf+=f'stub-zone:\n    name: "{zone}"\n    stub-addr: 127.0.0.1@15358\n    stub-first: no\n'
            path=base/'unbound.conf'; path.write_text(conf)
            with (base/'log').open('w') as log:
                proc,label=start(path,log,args.require_apparmor)
                result['apparmor']=label
                try:
                    for zone,(signed,_) in authority.zones.items():
                        if zone=='bad-negative.test.':
                            continue  # Keep tampered-proof trust domain cold, outside cached valid proofs.
                        absent_code='NOERROR' if zone.startswith('compact') else 'NXDOMAIN'
                        cases=[('missing','A',absent_code,False), ('only-v6','A','NOERROR',False),
                               ('target','AAAA','NOERROR',False), ('ent','A','NOERROR',False),
                               ('only-v6','TYPE65280','NOERROR',False), ('x.wild','A','NOERROR',True),
                               ('x.wild','AAAA','NOERROR',False), ('x.alias','A','NOERROR',True),
                               ('to-missing','A',absent_code,False)]
                        for tcp in (False,True):
                            for label_name,kind,expected,positive in cases:
                                # Preserve candidate20qps ACL; keep the fixture below it.
                                time.sleep(.1)
                                q=dns.message.make_query(label_name+'.'+zone,kind,want_dnssec=True,payload=4096)
                                t=time.monotonic()
                                r=(dns.query.tcp if tcp else dns.query.udp)(q,'127.0.0.1',port=15359,timeout=3)
                                row={'name':q.question[0].name.to_text(),'type':kind,'transport':'TCP' if tcp else 'UDP',
                                     'rcode':dns.rcode.to_text(r.rcode()),'AD':bool(r.flags & dns.flags.AD),
                                     'CD':bool(r.flags & dns.flags.CD),'AA':bool(r.flags & dns.flags.AA),
                                     'elapsed_seconds':round(time.monotonic()-t,6),'answer':[x.to_text() for x in r.answer],
                                     'authority':[x.to_text() for x in r.authority]}
                                result['queries'].append(row)
                                assert row['rcode']==expected,row
                                assert row['AD']==signed,row
                                assert not row['CD'] and not row['AA'],row
                                matching=[x for x in r.answer if x.rdtype==q.question[0].rdtype]
                                assert bool(matching)==positive,row
                                if not positive:
                                    soa=[x for x in r.authority if x.rdtype==dns.rdatatype.SOA]
                                    assert len(soa)==1 and soa[0].name.to_text()==zone,row
                                    assert 0 < soa[0].ttl <= 30,row
                                    if signed:
                                        assert any(x.rdtype==dns.rdatatype.NSEC for x in r.authority),row
                                        assert any(x.rdtype==dns.rdatatype.RRSIG for x in r.authority),row
                                if label_name=='x.alias':
                                    assert any(x.rdtype==dns.rdatatype.CNAME for x in r.answer),row
                        control=['unbound-control','-c',str(path),'stats_noreset']
                        def cache_counts():
                            data=dict(x.split('=',1) for x in subprocess.check_output(control,text=True).splitlines() if '=' in x)
                            return {k:float(v) for k,v in data.items() if k=='total.num.cachehits' or 'aggressive' in k}
                        for name,expected in [('missing',absent_code),('only-v6','NOERROR')]:
                            time.sleep(.1)
                            before=cache_counts(); count=dict(authority.count)
                            q=dns.message.make_query(name+'.'+zone,'A',want_dnssec=True,payload=4096)
                            r=dns.query.udp(q,'127.0.0.1',port=15359,timeout=2)
                            after=cache_counts()
                            delta={k:after[k]-before.get(k,0) for k in after}
                            assert sum(delta.values())>=1 and authority.count==count, (zone,name,delta,count,authority.count)
                            assert dns.rcode.to_text(r.rcode())==expected
                            result['negative_cache'].append({'name':name+'.'+zone,'cache_counter_deltas':delta,'no_new_authority_query':True})
                    result['bogus_negative_proof']=[]
                    for tcp in (False,True):
                        time.sleep(.1)
                        row=check_query('127.0.0.1','bad-proof.bad-negative.test.',port=15359,tcp=tcp,expected='SERVFAIL',timeout=3,scenario='tampered-signed-negative-SOA')
                        result['bogus_negative_proof'].append(row)
                        assert row['pass'],row
                    q=dns.message.make_query('test-nx-20261010.invalid.','A',want_dnssec=True)
                    r=dns.query.udp(q,'127.0.0.1',port=15359,timeout=2)
                    result['local_invalid']={'rcode':dns.rcode.to_text(r.rcode()),'AD':bool(r.flags & dns.flags.AD),'AA':bool(r.flags & dns.flags.AA),'authority':[x.to_text() for x in r.authority]}
                    assert r.rcode()==dns.rcode.NXDOMAIN
                    result['authority_transport_counts']=authority.count
                    assert authority.count['TCP']>0,'No authoritative TCP fallback observed'
                    result['pass']=True
                finally:
                    stop(proc)
    finally:
        authority.close()
    return result


def delayed(args,parent):
    rows=[]
    for window in (1900,15000):
        for tcp in (False,True):
            for bogus in (False,True):
                authority=Authority(delay_seconds=6)
                try:
                    with tempfile.TemporaryDirectory(prefix='vynalth-delay-',dir=parent) as folder:
                        base=Path(folder); (base/'fixture.key').write_text(authority.keys.to_text()+'\n')
                        conf=config(folder).replace('discard-timeout: 15000',f'discard-timeout: {window}')
                        conf+=f'    trust-anchor-file: "{base}/fixture.key"\nstub-zone:\n    name: "signed-fixture.test."\n    stub-addr: 127.0.0.1@15354\n    stub-first: no\n'
                        path=base/'unbound.conf'; path.write_text(conf)
                        with (base/'log').open('w') as log:
                            proc,label=start(path,log,args.require_apparmor)
                            try:
                                name=('bogus' if bogus else 'valid')+'.signed-fixture.test.'
                                code='SERVFAIL' if bogus else 'NOERROR'
                                cold=check_query('127.0.0.1',name,port=15359,tcp=tcp,expected=code,ad=not bogus,timeout=8,scenario='fresh-process-six-second-authority-delay')
                                row={'discard_timeout_ms':window,'apparmor':label,'cold':cold,'warm':None,'CD':None,'authority_request_count':authority.count}
                                if window==15000:
                                    assert cold['pass'],cold
                                    row['warm']=check_query('127.0.0.1',name,port=15359,tcp=tcp,expected=code,ad=not bogus,timeout=2,scenario='warm-after-cold-pass')
                                    assert row['warm']['pass'],row
                                    if bogus:
                                        row['CD']=check_query('127.0.0.1',name,port=15359,tcp=tcp,cd=True,expected='NOERROR',timeout=2,scenario='checking-disabled-diagnostic')
                                        assert row['CD']['pass'],row
                                else:
                                    assert not cold['pass'] and cold['response'] is None,cold
                                    # Planned independent diagnostic, never a retry counted as validation.
                                    if bogus:
                                        row['CD']=check_query('127.0.0.1',name,port=15359,tcp=tcp,cd=True,expected='NOERROR',timeout=2,scenario='post-failure-CD-diagnostic')
                                        assert row['CD']['pass'],row
                                rows.append(row)
                            finally:
                                stop(proc)
                finally:
                    authority.close()
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--inside',action='store_true'); p.add_argument('--require-apparmor',action='store_true')
    p.add_argument('--out',type=Path,required=True); p.add_argument('--skip-delay',action='store_true')
    args=p.parse_args()
    if not args.inside:
        argv=[sys.executable,str(Path(__file__).resolve()),'--inside','--out',str(args.out.resolve())]
        if args.require_apparmor: argv+=['--require-apparmor']
        if args.skip_delay: argv+=['--skip-delay']
        raise SystemExit(subprocess.run(['unshare','--net',*argv]).returncode)
    subprocess.run(['ip','link','set','lo','up'],check=True)
    assert not subprocess.check_output(['ip','route','show','default'],text=True).strip()
    parent='/var/lib/unbound' if Path('/etc/apparmor.d/usr.sbin.unbound').exists() else None
    diff=(ROOT/'plans/phase-b-unbound.diff').read_text().splitlines()
    original='\n'.join(x[1:] for x in diff if x.startswith('-') and not x.startswith('---'))+'\n'
    assert hashlib.sha256(original.encode()).hexdigest()=='8808b474175ff8eeebecbf407f9091fd73f65c4a43a6ee212e8ae2d9f80778f8'
    result={'pass':False,'scope':'local/CI namespace without default route; never Oracle',
            'unbound_version':subprocess.check_output(['unbound','-V'],text=True,stderr=subprocess.STDOUT).splitlines()[0],
            'baseline_main_bytes_verified':True,'baseline_effective_runtime':'NOT RECONSTRUCTED: include files/package/live environment not identical',
            'candidate_sha256':hashlib.sha256((ROOT/'plans/phase-b-unbound.conf').read_bytes()).hexdigest()}
    try:
        result['negatives']=negatives(args,parent)
        if not args.skip_delay:
            result['delayed']=delayed(args,parent)
        result['pass']=True
    finally:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':
    main()
