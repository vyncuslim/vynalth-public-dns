# Discovery status — 2026-10-10, Asia/Kuala_Lumpur

Confirmed:
- Existing GitHub repository was empty; reused rather than creating a new repo.
- Windows shell initially had no OCI CLI/SDK or Terraform and no ~/.oci/config.
- Authenticated Chrome OCI creation form names root compartment Vynalth_AI,
  Singapore, existing vynalth-dns-vcn/dns-public-subnet, Ubuntu 24.04,
  A1 1 OCPU/6 GB. The form displays `Too many requests for the user`.
  This is not proof of available capacity or a created instance.
- Cloudflare vynalthai.com shows Enterprise and a UDP/53 creation form with
  IPv4+IPv6 selection. No Spectrum applications are listed behind that form.
  The load-balancer origin selection is disabled as not configured.

Not verified:
OCI resource OCIDs, actual VCN/subnet CIDRs/routes/security/IGW state,
current instances, free allowances, quota usage, prices, capacity reports,
Spectrum contract/add-on billing/static IP entitlement and actual client-IP path.

No create/apply/purchase/DNS/firewall changes were performed in either dashboard.
Do not submit the existing OCI form repeatedly. Run official SDK discovery once
credentials are configured; browser UI evidence does not replace API inventory.
