locals {
  user_data = <<-EOT
    #!/bin/bash
    set -euo pipefail
    apt-get update -y
    apt-get install -y curl
    curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="${var.k3s_version}" sh -s - server \
      --disable=traefik \
      --write-kubeconfig-mode=644 \
      --node-name="${var.cluster_name}-control"
    sleep 5
    until kubectl get nodes >/dev/null 2>&1; do sleep 2; done
    kubectl get nodes
  EOT
}

resource "hcloud_ssh_key" "default" {
  name       = "${var.cluster_name}-key"
  public_key = file(var.ssh_public_key_file)
}

resource "hcloud_server" "control" {
  count        = var.server_count
  name         = "${var.cluster_name}-control-${count.index}"
  image        = "ubuntu-24.04"
  server_type  = var.server_type
  location     = var.location
  ssh_keys     = [hcloud_ssh_key.default.id]
  firewall_ids = [hcloud_firewall.k3s.id]
  user_data    = local.user_data
  labels = {
    cluster = var.cluster_name
    role    = "control-plane"
  }
}

resource "hcloud_firewall" "k3s" {
  name = "${var.cluster_name}-fw"
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "tcp"
    port       = "6443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rule {
    direction  = "in"
    protocol   = "udp"
    port       = "51820"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}
