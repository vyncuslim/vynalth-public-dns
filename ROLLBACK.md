# Rollback and backup

Installation records previous Unbound config and dedicated firewall table,
systemd policy and persistence files. An independent systemd timer restores
them in 180 seconds unless a new SSH session confirms the policy. Existing
unrelated firewall tables are preserved. Installation failures trigger rollback.
Package upgrades and cloud-init SSH changes are outside this config rollback;
maintain OCI console recovery access and image/package rollback plans.

```sh
# Immediate rollback of an unconfirmed install:
sudo bash scripts/rollback.sh
# Recover a confirmed retained snapshot (review directory before copying):
sudo cp -a /var/lib/vynalth-dns/confirmed-TIMESTAMP /var/lib/vynalth-dns/rollback
sudo bash scripts/rollback.sh
sudo unbound-checkconf
sudo systemctl status unbound --no-pager
dig @127.0.0.1 example.com +time=2 +tries=1
```

Do not Terraform destroy: instance has prevent_destroy. Cloud deletion requires
explicit destructive approval. Network and live DNS are never automatically reverted.
Any later Spectrum/record rollback must use the exact separately approved plan.

Back up configuration, managed root.key, package versions and approved inventory:

```sh
sudo tar -czf /var/lib/vynalth-dns/backup-$(date +%Y%m%d).tgz \
  /etc/unbound /var/lib/unbound/root.key /etc/vynalth-dns.nft \
  /etc/systemd/system/unbound.service.d /etc/ssh/sshd_config.d
dpkg-query -W unbound dns-root-data nftables
```

Store offline encrypted with access controls; do not commit archives or private
keys. Cloud backup services require pricing approval. Restore to an isolated VM,
check trust-anchor permissions/time/config, then perform full acceptance before
reattachment. Cache is disposable and need not be backed up. Retention defaults
to seven daily snapshots, managed manually until an approved prune policy exists.
