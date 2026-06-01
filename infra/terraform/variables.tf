variable "hcloud_token" {
  description = "Hetzner Cloud API token"
  type        = string
  sensitive   = true
}

variable "cluster_name" {
  description = "Name of the k3s cluster"
  type        = string
  default     = "devops-copilot"
}

variable "kubeconfig_path" {
  description = "Local path to write the kubeconfig"
  type        = string
  default     = "./kubeconfig.yaml"
}

variable "server_count" {
  description = "Number of control-plane + worker nodes (k3s in single-server mode)"
  type        = number
  default     = 1
}

variable "server_type" {
  description = "Hetzner server type"
  type        = string
  default     = "cx22"
}

variable "location" {
  description = "Hetzner location"
  type        = string
  default     = "fsn1"
}

variable "k3s_version" {
  description = "k3s version tag"
  type        = string
  default     = "v1.30.4+k3s1"
}

variable "ssh_public_key_file" {
  description = "Path to a public SSH key to install on the cluster nodes"
  type        = string
  default     = "./fixtures/ssh_key.pub"
}
