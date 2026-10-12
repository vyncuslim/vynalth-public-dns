import unittest
from unittest.mock import patch
import dns.flags
import dns.message
import dns.rcode
import dns.rrset
from acceptance import check_query, response_shape, case_plan


class NegativeResponseTests(unittest.TestCase):
    def response(self, code='NOERROR', cname=False):
        r=dns.message.make_response(dns.message.make_query('alias.example.','A'))
        r.set_rcode(dns.rcode.from_text(code))
        r.authority.append(dns.rrset.from_text('example.',60,'IN','SOA','ns.example. hostmaster.example. 1 60 60 600 30'))
        if cname:
            r.answer.append(dns.rrset.from_text('alias.example.',60,'IN','CNAME','target.example.'))
        return r

    def test_nodata_preserves_noerror_soa_and_does_not_satisfy_positive_case(self):
        r=self.response()
        with patch('acceptance.dns.query.udp',return_value=r):
            positive=check_query('127.0.0.1','alias.example.',timeout=2)
            negative=check_query('127.0.0.1','alias.example.',timeout=2,expected_nodata=True)
        self.assertFalse(positive['pass'])
        self.assertTrue(negative['pass'])
        self.assertEqual(negative['response']['rcode'],'NOERROR')
        self.assertEqual(negative['response']['shape'],'NODATA')
        self.assertEqual(negative['response']['SOA_negative_ttls'],[30])
        self.assertEqual(len(negative['response']['authority']),1)

    def test_cname_to_nodata_is_not_a_positive_address_result(self):
        with patch('acceptance.dns.query.udp',return_value=self.response(cname=True)):
            self.assertFalse(check_query('127.0.0.1','alias.example.',timeout=2)['pass'])
            self.assertTrue(check_query('127.0.0.1','alias.example.',timeout=2,expected_nodata=True)['pass'])

    def test_nxdomain_with_cname_is_distinct_from_nodata(self):
        r=self.response('NXDOMAIN',cname=True)
        self.assertEqual(response_shape(r,'A'),'NXDOMAIN')
        with patch('acceptance.dns.query.tcp',return_value=r):
            self.assertTrue(check_query('127.0.0.1','alias.example.',tcp=True,expected='NXDOMAIN',timeout=2)['pass'])
            self.assertFalse(check_query('127.0.0.1','alias.example.',tcp=True,expected_nodata=True,timeout=2)['pass'])

    def test_signed_nodata_requires_ad_and_cd_is_not_validation(self):
        r=self.response()
        with patch('acceptance.dns.query.udp',return_value=r):
            self.assertFalse(check_query('127.0.0.1','alias.example.',ad=True,expected_nodata=True,timeout=2)['pass'])
        r.flags|=dns.flags.AD
        with patch('acceptance.dns.query.udp',return_value=r):
            self.assertTrue(check_query('127.0.0.1','alias.example.',ad=True,expected_nodata=True,timeout=2)['pass'])

    def test_empty_noerror_without_soa_is_not_asserted_nodata(self):
        r=self.response(); r.authority.clear()
        self.assertEqual(response_shape(r,'A'),'NOERROR_WITHOUT_MATCHING_RRSET')
        with patch('acceptance.dns.query.udp',return_value=r):
            self.assertFalse(check_query('127.0.0.1','alias.example.',expected_nodata=True,timeout=2)['pass'])

    def test_compact_nxname_denial_is_not_heuristically_rewritten(self):
        r=self.response()
        r.authority.append(dns.rrset.from_text('alias.example.',30,'IN','NSEC',r'\000.alias.example. RRSIG NSEC TYPE128'))
        with patch('acceptance.dns.query.udp',return_value=r):
            row=check_query('127.0.0.1','alias.example.',expected_nodata=True,timeout=2)
        self.assertTrue(row['pass'])
        self.assertEqual(row['response']['shape'],'NODATA')
        self.assertEqual(row['response']['rcode'],'NOERROR')
        self.assertEqual(r.rcode(),dns.rcode.NOERROR)

    def test_builtin_invalid_not_required_to_forge_ad(self):
        case=next(c for c in case_plan('standard') if c[0].endswith('.invalid.'))
        self.assertEqual(case[3:5],('NXDOMAIN',False))
        self.assertTrue(any(c[4] for c in case_plan('dnssec-cold') if c[3]=='NOERROR'))

    def test_negative_mode_cannot_be_misused_with_ptr_or_wrong_rcode(self):
        for kwargs in [{'expected':'NXDOMAIN'},{'expected_ptr':'dns.vynalthai.com.'}]:
            with self.assertRaises(ValueError):
                check_query('127.0.0.1','alias.example.',expected_nodata=True,timeout=2,**kwargs)
