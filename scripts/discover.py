"""Official OCI SDK inventory and capacity reports; no instance creation."""
import argparse
import json
from pathlib import Path
import oci

def all_items(fn, **kwargs):
    return oci.pagination.list_call_get_all_results(fn, **kwargs).data

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--profile', default='DEFAULT')
    p.add_argument('--out', type=Path, default=Path('artifacts/discovery.json'))
    a = p.parse_args()
    config = oci.config.from_file(profile_name=a.profile)
    config['region'] = 'ap-singapore-1'
    tenancy = config['tenancy']
    identity = oci.identity.IdentityClient(config)
    network = oci.core.VirtualNetworkClient(config)
    compute = oci.core.ComputeClient(config)
    regions = all_items(identity.list_region_subscriptions, tenancy_id=tenancy)
    if not any(r.region_name == config['region'] and r.is_home_region for r in regions):
        raise RuntimeError('Singapore home-region requirement not verified')
    vcns = all_items(network.list_vcns, compartment_id=tenancy)
    matches = [x for x in vcns if x.display_name == 'vynalth-dns-vcn' and x.lifecycle_state == 'AVAILABLE']
    if len(matches) != 1 or matches[0].cidr_block != '10.0.0.0/16':
        raise RuntimeError('VCN identity/CIDR ambiguous or mismatched')
    vcn = matches[0]
    subnets = all_items(network.list_subnets, compartment_id=tenancy, vcn_id=vcn.id)
    matches = [x for x in subnets if x.display_name == 'dns-public-subnet' and x.lifecycle_state == 'AVAILABLE']
    if len(matches) != 1 or matches[0].cidr_block != '10.0.0.0/24':
        raise RuntimeError('subnet identity/CIDR ambiguous or mismatched')
    subnet = matches[0]
    ads = all_items(identity.list_availability_domains, compartment_id=tenancy)
    reports = []
    # Exactly one report per AD, covering both candidate shapes. Never retries launch.
    for ad in ads:
        details = oci.core.models.CreateComputeCapacityReportDetails(
            compartment_id=tenancy, availability_domain=ad.name,
            shape_availabilities=[
                oci.core.models.CreateCapacityReportShapeAvailabilityDetails(
                    instance_shape='VM.Standard.A1.Flex',
                    instance_shape_config=oci.core.models.CapacityReportInstanceShapeConfig(ocpus=1, memory_in_gbs=6)),
                oci.core.models.CreateCapacityReportShapeAvailabilityDetails(instance_shape='VM.Standard.E2.1.Micro')])
        reports.append(compute.create_compute_capacity_report(details, retry_strategy=oci.retry.NoneRetryStrategy()).data)
    result = {
        'region': config['region'], 'billing_verified': False,
        'vcn': vcn, 'subnet': subnet,
        'route_table': network.get_route_table(subnet.route_table_id).data,
        'security_lists': [network.get_security_list(x).data for x in subnet.security_list_ids],
        'gateways': all_items(network.list_internet_gateways, compartment_id=tenancy, vcn_id=vcn.id),
        'nsgs': all_items(network.list_network_security_groups, compartment_id=tenancy, vcn_id=vcn.id),
        'instances': all_items(compute.list_instances, compartment_id=tenancy),
        'images': all_items(compute.list_images, compartment_id=tenancy, operating_system='Canonical Ubuntu'),
        'capacity_reports': reports,
        'note': 'Capacity is transient, not a reservation or billing entitlement. Review attached VNIC NSGs separately.'}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(oci.util.to_dict(result), indent=2))

if __name__ == '__main__':
    main()
