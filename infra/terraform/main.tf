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
  public_key = fileexists("~/.ssh/id_ed25519.pub") ? file("~/.ssh/id_ed25519.pub") : file("${path.module}/id_ed25519.pub")
}

resource "hcloud_server" "control" {
  count       = var.server_count
  name        = "${var.cluster_name}-control-${count.index}"
  image       = "ubuntu-24.04"
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.default.id]
  user_data   = local.user_data
  labels = {
    cluster = var.cluster_name
    role    = "control-plane"
  }
}

resource "hcloud_firewall" "k3s" {
  name = "${var.cluster_name}-fw"
  rules {
    direction  = "in"
    protocol   = "tcp"
    port       = "22"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rules {
    direction  = "in"
    protocol   = "tcp"
    port       = "80"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rules {
    direction  = "in"
    protocol   = "tcp"
    port       = "443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rules {
    direction  = "in"
    protocol   = "tcp"
    port       = "6443"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
  rules {
    direction  = "in"
    protocol   = "udp"
    port       = "51820"
    source_ips = ["0.0.0.0/0", "::/0"]
  }
}

resource "hcloud_server_network" "control" {
  count     = var.server_count
  server_id = hcloud_server.control[count.index].id
  firewall_id = hcloud_firewall.k3s.id
}
