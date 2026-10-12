"""Local authoritative fixture: complete NSEC chain, UDP/TCP, never outbound DNS."""
import copy
import socket
import threading
import time
import dns.dnssec
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rdatatype
import dns.rrset
from cryptography.hazmat.primitives.asymmetric import ec


class NegativeAuthority:
    def __init__(self, port=15358):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.dnskey = dns.dnssec.make_dnskey(self.key.public_key(), 'ECDSAP256SHA256', flags=257)
        self.zones = {}
        for zone, signed in [('signed-negative.test.', True), ('unsigned-negative.test.', False), ('compact-negative.test.', True), ('bad-negative.test.', True)]:
            records = {}
            def add(label, kind, text):
                name = zone if label == '@' else label + '.' + zone
                rr = dns.rrset.from_text(name, 60, 'IN', kind, text)
                records.setdefault(rr.name, {})[rr.rdtype] = rr
            add('@', 'SOA', f'ns.{zone} hostmaster.{zone} 1 60 60 600 30')
            add('@', 'NS', f'ns.{zone}')
            add('ns', 'A', '203.0.113.53')
            add('only-v6', 'AAAA', '2001:db8::9')
            add('target', 'A', '203.0.113.9')
            add('child.ent', 'A', '203.0.113.10')
            add('*.wild', 'A', '203.0.113.11')
            add('*.alias', 'CNAME', f'target.{zone}')
            add('to-missing', 'CNAME', f'missing.{zone}')
            # Actual tree existence includes empty nonterminals.
            for name in list(records):
                parent = name.parent()
                while parent.is_subdomain(dns.name.from_text(zone)):
                    records.setdefault(parent, {})
                    if parent == dns.name.from_text(zone):
                        break
                    parent = parent.parent()
            if signed:
                records[dns.name.from_text(zone)][dns.rdatatype.DNSKEY] = dns.rrset.from_rdata(zone, 60, self.dnskey)
                ordered = sorted(records)
                for i, name in enumerate(ordered):
                    types = [dns.rdatatype.to_text(k) for k in records[name]] + ['NSEC', 'RRSIG']
                    records[name][dns.rdatatype.NSEC] = dns.rrset.from_text(name, 60, 'IN', 'NSEC',
                        ordered[(i+1) % len(ordered)].to_text()+' '+' '.join(types))
            self.zones[zone] = (signed, records)
        self.count = {'UDP': 0, 'TCP': 0}
        self.stop = threading.Event()
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind(('127.0.0.1', port))
        self.udp.settimeout(.1)
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp.bind(('127.0.0.1', port))
        self.tcp.listen(8)
        self.tcp.settimeout(.1)
        self.threads = [threading.Thread(target=self.serve_udp, daemon=True), threading.Thread(target=self.serve_tcp, daemon=True)]
        for thread in self.threads:
            thread.start()

    def signed_rr(self, rr, zone, owner=None):
        sig = dns.dnssec.sign(rr, self.key, zone, self.dnskey,
                              inception=int(time.time())-3600, expiration=int(time.time())+86400)
        answer = copy.deepcopy(rr)
        if owner is not None:
            answer.name = owner
        return [answer, dns.rrset.from_rdata(answer.name, rr.ttl, sig)]

    def response(self, query):
        reply = dns.message.make_response(query)
        reply.flags |= dns.flags.AA
        reply.flags &= ~dns.flags.RA
        name, kind = query.question[0].name, query.question[0].rdtype
        zone = next(z for z in self.zones if name.is_subdomain(dns.name.from_text(z)))
        signed, records = self.zones[zone]
        owner = name
        if owner not in records:
            closest = owner.parent()
            while closest not in records:
                closest = closest.parent()
            wildcard = dns.name.from_text('*', origin=closest)
            if wildcard in records:
                owner = wildcard
            else:
                reply.set_rcode(dns.rcode.NXDOMAIN)
        rr = records.get(owner, {}).get(kind) or records.get(owner, {}).get(dns.rdatatype.CNAME)
        if zone=='compact-negative.test.' and reply.rcode()==dns.rcode.NXDOMAIN:
            # RFC9824 compact denial is NOERROR, never a heuristic rewrite by the resolver.
            reply.set_rcode(dns.rcode.NOERROR)
            soa=records[dns.name.from_text(zone)][dns.rdatatype.SOA]
            proof=dns.rrset.from_text(name,30,'IN','NSEC',r'\000.'+name.to_text()+' RRSIG NSEC TYPE128')
            reply.authority.extend(self.signed_rr(soa,zone)+self.signed_rr(proof,zone))
            return reply
        if rr is not None:
            reply.answer.extend(self.signed_rr(rr, zone, name) if signed else [dns.rrset.from_text(name, rr.ttl, 'IN', rr.rdtype, *[r.to_text() for r in rr])])
        else:
            soa = records[dns.name.from_text(zone)][dns.rdatatype.SOA]
            reply.authority.extend(self.signed_rr(soa, zone) if signed else [soa])
        # Complete proofs simplify the fixture; tests don't emulate provider internals.
        if signed and (rr is None or owner != name):
            for data in records.values():
                reply.authority.extend(self.signed_rr(data[dns.rdatatype.NSEC], zone))
        if name.to_text().startswith('bad-proof.') and signed:
            # Tamper SOA data after signing, retaining its now-invalid RRSIG.
            for i, data in enumerate(reply.authority):
                if data.rdtype==dns.rdatatype.SOA:
                    reply.authority[i]=dns.rrset.from_text(zone,60,'IN','SOA',f'ns.{zone} hostmaster.{zone} 2 60 60 600 30')
        return reply

    def serve_udp(self):
        while not self.stop.is_set():
            try:
                wire, peer = self.udp.recvfrom(8192)
                self.count['UDP'] += 1
                q = dns.message.from_wire(wire)
                r = self.response(q)
                full = r.to_wire(max_size=65535)
                if len(full) > (q.payload if q.edns >= 0 else 512):
                    r.answer.clear()
                    r.authority.clear()
                    r.flags |= dns.flags.TC
                    full = r.to_wire()
                self.udp.sendto(full, peer)
            except socket.timeout:
                continue
            except OSError:
                return

    @staticmethod
    def receive(sock, length):
        data = b''
        while len(data) < length:
            chunk = sock.recv(length-len(data))
            if not chunk:
                raise EOFError('Fixture TCP closed')
            data += chunk
        return data

    def serve_tcp(self):
        while not self.stop.is_set():
            try:
                conn, _ = self.tcp.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with conn:
                conn.settimeout(2)
                self.count['TCP'] += 1
                size = int.from_bytes(self.receive(conn, 2), 'big')
                wire = self.response(dns.message.from_wire(self.receive(conn, size))).to_wire(max_size=65535)
                conn.sendall(len(wire).to_bytes(2, 'big')+wire)

    def close(self):
        self.stop.set()
        self.udp.close()
        self.tcp.close()
        for thread in self.threads:
            thread.join(timeout=2)
