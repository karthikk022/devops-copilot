output "cluster_name" {
  value = var.cluster_name
}

output "control_plane_ips" {
  value = hcloud_server.control[*].ipv4_address
}

output "ssh_command" {
  value = "ssh root@${hcloud_server.control[0].ipv4_address}"
}

output "kubeconfig_command" {
  value = "ssh root@${hcloud_server.control[0].ipv4_address} 'cat /etc/rancher/k3s/k3s.yaml' | sed 's/127.0.0.1/${hcloud_server.control[0].ipv4_address}/g' > ${var.kubeconfig_path}"
}

output "next_steps" {
  value = [
    "1. Save kubeconfig: ${self.kubeconfig_command.value}",
    "2. Set KUBECONFIG env var: $env:KUBECONFIG=\"$(Resolve-Path ${var.kubeconfig_path})\"",
    "3. Verify: kubectl get nodes",
    "4. Deploy: kubectl apply -f infra/k8s/manifests/",
  ]
}
