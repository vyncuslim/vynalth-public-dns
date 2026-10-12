# Existing network is data-only. No VCN/subnet/routes/security-list mutation.
data "oci_core_subnet" "existing" {
  subnet_id = var.subnet_id
}
resource "oci_core_instance" "dns" {
  count               = var.create_instance ? 1 : 0
  compartment_id      = var.compartment_id
  availability_domain = var.availability_domain
  display_name        = "vynalth-dns-dev"
  shape               = var.shape
  dynamic "shape_config" {
    for_each = var.shape == "VM.Standard.A1.Flex" ? [1] : []
    content {
      ocpus         = var.ocpus
      memory_in_gbs = var.memory_gb
    }
  }
  create_vnic_details {
    subnet_id        = data.oci_core_subnet.existing.id
    assign_public_ip = var.assign_public_ip
    nsg_ids          = var.reviewed_nsg_ids
  }
  source_details {
    source_type             = "image"
    source_id               = var.image_id
    boot_volume_size_in_gbs = 50
  }
  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = base64encode(file("${path.module}/../cloud-init/bootstrap.yaml"))
  }
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.human_creation_approval && var.billing_eligibility_verified && var.approved_estimated_monthly_myr >= 0 && var.approved_estimated_monthly_myr <= var.monthly_budget_myr
      error_message = "Creation blocked: explicit approval and verified all-in estimate within budget required."
    }
    precondition {
      condition     = !var.assign_public_ip || var.public_ip_billing_verified
      error_message = "Public IP billing must be independently verified."
    }
    precondition {
      condition     = data.oci_core_subnet.existing.cidr_block == "10.0.0.0/24" && data.oci_core_subnet.existing.display_name == "dns-public-subnet" && length(var.reviewed_nsg_ids) > 0
      error_message = "Verify subnet identity and reviewed effective ingress rules first. NSGs cannot override permissive security lists."
    }
  }
}
output "instance_id" {
  value = try(oci_core_instance.dns[0].id, null)
}
