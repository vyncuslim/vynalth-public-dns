# Deployment (manual approval boundaries)

## Phase A: development

```sh
python3 -m pip install -r requirements-test.txt -r requirements-discovery.txt
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/render.py config.example.json
# On Ubuntu with tools installed, isolated loopback process:
python3 tests/local_runtime.py
shellcheck scripts/*.sh
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
```

## Discovery: official OCI SDK / CLI

Configure OCI locally using the provider's normal authentication process; never
paste keys into this repo or chat. Read-only inventory plus transient capacity
reports (not capacity reservations):

```sh
python3 scripts/discover.py --profile DEFAULT --out artifacts/discovery.json
# Official CLI equivalent for capacity reports, once CLI is installed:
oci compute compute-capacity-report create --generate-full-command-json-input > artifacts/capacity-input.json
# Edit compartment, AD and both shape requests in the generated schema first:
oci compute compute-capacity-report create --region ap-singapore-1 --from-json file://artifacts/capacity-input.json
```

SDK reports once per AD; never retries instance creation. Verify report status
and requested shape configuration. AVAILABLE is transient, not launch assurance.
Missing credentials/capacity/billing evidence stops Phase B. Review routes,
gateway, subnet, security lists, NSGs and actual VNIC rules; do not overwrite them.
Discover remaining tenancy usage across all compartments separately.

## Plan before approval

```sh
cp terraform/terraform.tfvars.example terraform/local.tfvars
# Fill VERIFIED discovered IDs, exact Ubuntu 24.04 image + architecture, key,
# reviewed NSGs. Leave creation false for initial data-only plan.
terraform -chdir=terraform plan -var-file=local.tfvars -out=../artifacts/dev.tfplan
terraform -chdir=terraform show -no-color ../artifacts/dev.tfplan
```

No VM is created by default. Review the proposed 1 OCPU/6 GB A1 (ARM64) or
E2 Micro (AMD64) with 50 GB boot volume and its net bill; verify shape-image
compatibility from actual OCI image/shape APIs. To obtain a resource-creating
plan, explicit creation/billing flags require recorded human authorization.
Do not mark those flags true merely to bypass a failed gate. Budget flags are
operator attestations, not billing API verification. Plans may expose IDs:
keep them private. State must be protected, backed up and locked for team use.

## Phase B: only after exact saved plan approval

Recheck capacity/prices immediately before execution. A public IP needs separate
verified billing and approval. Never create a NAT, reservation, LB or paid fallback.

```sh
# HUMAN APPROVAL REQUIRED: exact reviewed plan only
terraform -chdir=terraform apply ../artifacts/dev.tfplan
```

Alternative: re-use an already approved VM; confirm OS, architecture, routes,
effective firewall and no unrelated services affected. Transfer repo to that VM
using existing approved SSH credentials. On VM:

```sh
cp config.example.json config.local.json
# Set VM's specific private IPv4 listener and individual approved DNS/SSH hosts.
python3 scripts/render.py config.local.json
sudo unbound-checkconf artifacts/rendered/unbound.conf
sudo nft --check --file artifacts/rendered/firewall.nft
# HUMAN APPROVAL REQUIRED for VM service/firewall changes
sudo bash scripts/install.sh artifacts/rendered
# From a FRESH SSH session and approved client, within three minutes:
python3 tests/acceptance.py --server ORIGIN_IP --authorized-target
sudo bash scripts/confirm.sh
sudo sshd -T | grep -E 'passwordauthentication|kbdinteractiveauthentication|permitrootlogin|allowusers'
sudo python3 scripts/metrics.py
```

If blocked traffic is dropped by host/OCI firewalls, unauthorized-client tests
must expect timeout. Test Unbound REFUSED separately behind the firewall in a
local lab. Do not temporarily open an origin to arbitrary public addresses.
If timed acceptance takes longer than rollback window, arrange console access
and a separately reviewed window; never silently cancel safety rollback.

## Phase C/D

No Spectrum application creation commands or public ACL exist in this release.
Complete contract checks and identity adapter/native compatibility review first.
Then submit exact TCP/UDP app plans, edge addresses, origin sources, costs and
failure drills for approval. Changing live DNS and enabling public recursion
each require human approval. See ARCHITECTURE.md for the hard client-IP blocker.
