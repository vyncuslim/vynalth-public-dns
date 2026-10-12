variable "region" {
  type    = string
  default = "ap-singapore-1"
  validation {
    condition     = var.region == "ap-singapore-1"
    error_message = "Initial deployment is restricted to the verified home region."
  }
}
variable "compartment_id" { type = string }
variable "subnet_id" { type = string }
variable "availability_domain" { type = string }
variable "image_id" { type = string }
variable "ssh_public_key" {
  type = string
  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) ", var.ssh_public_key))
    error_message = "Supply a public SSH key, never a private key."
  }
}
variable "shape" {
  type    = string
  default = "VM.Standard.A1.Flex"
  validation {
    condition     = contains(["VM.Standard.A1.Flex", "VM.Standard.E2.1.Micro"], var.shape)
    error_message = "No automatic paid shape fallback."
  }
}
variable "ocpus" {
  type    = number
  default = 1
}
variable "memory_gb" {
  type    = number
  default = 6
}
variable "monthly_budget_myr" {
  type    = number
  default = 0
}
variable "billing_eligibility_verified" {
  type    = bool
  default = false
}
variable "approved_estimated_monthly_myr" {
  type    = number
  default = -1
}
variable "human_creation_approval" {
  type    = bool
  default = false
}
variable "create_instance" {
  type    = bool
  default = false
}
variable "assign_public_ip" {
  type    = bool
  default = false
}
variable "public_ip_billing_verified" {
  type    = bool
  default = false
}
variable "reviewed_nsg_ids" {
  type    = list(string)
  default = []
}
