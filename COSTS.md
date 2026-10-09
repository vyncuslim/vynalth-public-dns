# Costs and billing gate

Initial monthly target: **RM0** (`monthly_budget_myr=0`). Target is a policy,
not a provider spending cap. OCI budgets/alerts do not stop spend. No verified
all-in quote exists for this tenancy; all cloud creation remains blocked.

Always Free eligibility depends on home region, account terms and aggregate
tenancy usage. PAYG does not make arbitrary shapes/IPs/backups free. Published
allowances can change: do not hard-code remembered A1 quotas. Validate console
free-eligible labels, subscription-specific allowances, existing consumption,
boot/block volumes, performance units, public IP pricing, outbound traffic,
monitoring/log ingestion, backups and taxes at approval time.

| Item | Hourly estimate | Monthly estimate | Status |
|---|---|---|---|
| Local repository/CI development | no OCI resources | RM0 OCI | No infrastructure created |
| A1 1 OCPU / 6 GB or E2 Micro | unverified | unverified | blocked |
| 50 GB boot volume + public IPv4 | unverified | unverified | blocked |
| Spectrum TCP/UDP traffic + static edge IPs | contract quote needed | contract quote needed | blocked |
| Secondary origin/LB/health checks/backups | quote needed | quote needed | not provisioned |

Before paid approval provide timestamped SKU prices, quantity, free allowance
remaining, USD/MYR conversion source and rate, 730-hour monthly estimate,
traffic scenario, storage, taxes and contractual commitments. Formula:
`monthly_MYR = (730 * net_hourly_USD + net_monthly_storage_USD + traffic_USD + addon_USD) * FX + tax`.
Do not present unknown costs as zero. If all eligible components are verified
within free allowances, expected hourly/monthly charge can be RM0, but approval
must still review the exact resource plan. Never silently switch shapes.

In OCI Cost Analysis review daily usage by compartment and service, including
boot volumes from failed launches. Inventory all compartments, not only root.
Record current limits/usage and subscription documents alongside the plan.
Configure actual/forecast alerts before deployment; if OCI does not accept a
zero budget threshold, use the smallest supported threshold as an alert ONLY
and keep the deployment policy target at RM0. Include email destinations and
notification costs in the approved plan. Reconcile invoices daily initially.

Spectrum contract verification must explicitly cover UDP/53, TCP/53, IPv4/IPv6,
static Anycast IP entitlement, traffic charging, DDoS policy, LB, monitors and
failover. UI availability or Enterprise badge proves none of these charges.

Official sources:
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://www.oracle.com/cloud/price-list/
- https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm
- https://developers.cloudflare.com/spectrum/reference/settings-by-plan/
