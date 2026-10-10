"""Optional low-volume public diagnostics from LOCAL host, never Oracle/CI default.

External observations are time-bound, not deterministic regression assertions.
1.1.1.1 is a comparison/discovery target only, never an Unbound forwarder.
At most24 one-shot requests,2s each, no retries,75s overall cap.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype
from acceptance import response_shape


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--authorized-local-external-probes',action='store_true',required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    started=time.monotonic(); rows=[]
    def query(server,name,kind='A',authoritative=False,tcp=False,cd=False):
        if len(rows)>=24 or time.monotonic()-started>73:
            raise TimeoutError('External diagnostic global/query cap')
        q=dns.message.make_query(name,kind,want_dnssec=True,payload=1232)
        if authoritative: q.flags &= ~dns.flags.RD
        if cd: q.flags |= dns.flags.CD
        row={'scope':'EXTERNAL LOCAL HOST, not Oracle','server':server,'name':name,'type':kind,
             'RD':bool(q.flags & dns.flags.RD),'CD_query':cd,'transport':'TCP' if tcp else 'UDP',
             'started_utc':datetime.now(timezone.utc).isoformat(),'attempts':1,'error':None,'response':None}
        t=time.monotonic()
        try:
            r=(dns.query.tcp if tcp else dns.query.udp)(q,server,timeout=2)
            row['response']={'rcode':dns.rcode.to_text(r.rcode()),'shape':response_shape(r,kind),
                             'AD':bool(r.flags & dns.flags.AD),'AA':bool(r.flags & dns.flags.AA),
                             'CD':bool(r.flags & dns.flags.CD),'TC':bool(r.flags & dns.flags.TC),
                             'answers':[x.to_text() for x in r.answer],'authority':[x.to_text() for x in r.authority]}
            return r
        except Exception as e:
            row['error']={'type':type(e).__name__,'message':str(e)}
            return None
        finally:
            row['elapsed_seconds']=round(time.monotonic()-t,6); rows.append(row)
    for zone in ('example.com.','cloudflare.com.','github.com.'):
        name='test-nx-20261010.'+zone
        query('1.1.1.1',name)
        ns=query('1.1.1.1',zone,'NS')
        hosts=[item.target.to_text() for rr in ns.answer if rr.rdtype==dns.rdatatype.NS for item in rr] if ns else []
        # github uses multiple providers: explicitly sample one NS1 and one AWS,
        # rather than assume the first two NS records cover both implementations.
        if zone=='github.com.':
            hosts=[next((h for h in hosts if suffix in h),'') for suffix in ('nsone.net.','awsdns-')]
            hosts=[h for h in hosts if h]
        else:
            hosts=hosts[:2]
        for host in hosts:
            ip=query('1.1.1.1',host)
            addresses=[item.address for rr in ip.answer if rr.rdtype==dns.rdatatype.A for item in rr] if ip else []
            if addresses:
                query(addresses[0],name,authoritative=True)
    for tcp in (False,True):
        query('1.1.1.1','cloudflare.com.',tcp=tcp)
        query('1.1.1.1','dnssec-failed.org.',tcp=tcp)
        query('1.1.1.1','dnssec-failed.org.',tcp=tcp,cd=True)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps({'scope':'EXTERNAL LOCAL HOST; no Oracle access','elapsed_seconds':round(time.monotonic()-started,6),'queries':rows},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'query_count':len(rows),'replies':sum(x['response'] is not None for x in rows),'output':str(args.out)}))


if __name__=='__main__':
    main()
