# -*- mode: ruby -*-
# vi: set ft=ruby :
#
# Vagrant only creates the virtual machines. It runs no provisioner: every
# step after `vagrant up` is an ansible-playbook run against inventory.ini,
# exactly as it would be against real servers.
#
#   vagrant up                       # VirtualBox
#   vagrant up --provider=libvirt    # KVM/libvirt (needs the vagrant-libvirt plugin)
#
# With libvirt, export VAGRANT_DEFAULT_PROVIDER=libvirt so that a plain
# `vagrant up` (for example after `vagrant destroy -f`) uses libvirt too.

NODES = [
  { name: "master", ip: "192.168.56.10", cpus: 2, memory: 2048 },
  { name: "node1",  ip: "192.168.56.11", cpus: 2, memory: 4096 },
]

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-22.04"

  # A real server has no /vagrant share, and the playbooks must not need one.
  config.vm.synced_folder ".", "/vagrant", disabled: true

  NODES.each do |n|
    config.vm.define n[:name] do |node|
      node.vm.hostname = n[:name]
      node.vm.network "private_network", ip: n[:ip]

      node.vm.provider :virtualbox do |vb|
        vb.name = "k8s-#{n[:name]}"
        vb.cpus = n[:cpus]
        vb.memory = n[:memory]
        vb.linked_clone = true
      end

      node.vm.provider :libvirt do |lv, override|
        # The bento box is built for VirtualBox; this one is built for libvirt.
        # Another Ubuntu 22.04 libvirt box can be used with K8S_LIBVIRT_BOX=...
        override.vm.box = ENV.fetch("K8S_LIBVIRT_BOX", "generic/ubuntu2204")
        lv.default_prefix = "k8s-"
        lv.cpus = n[:cpus]
        lv.memory = n[:memory]
        # The VMs' first interface sits on vagrant-libvirt's management network
        # (192.168.121.0/24). Unlike VirtualBox NAT, where every VM is
        # 10.0.2.15, the VMs can reach each other there, which hides the two
        # networking traps. playbooks/network-experiment.yml can cut that path
        # with -e isolate_mgmt=true.
      end
    end
  end
end