# -*- mode: ruby -*-
# vi: set ft=ruby :

# Juniper Firefly Image
FIREFLY_VERSION = "juniper/ffp-12.1X47-D15.4"

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  if Vagrant.has_plugin?('vagrant-hostmanager')
    config.hostmanager.enabled = true
    config.hostmanager.manage_host = true
    config.hostmanager.include_offline = true
    # config.hostmanager.ignore_private_ip = true
  else
    raise "** Install vagrant-hostmanager plugin `vagrant plugin install vagrant-hostmanager`.**\n"
  end

  # The VirtualBox deploy uses a Vagrant box from Juniper that requires the vagrant-junos
  # and vagrant-host-shell plugins.  You will need to install these, for example:
  #   vagrant plugin install vagrant-junos
  #   vagrant plugin install vagrant-host-shell
  if not Vagrant.has_plugin?('vagrant-junos')
    raise "** Install vagrant-junos plugin `vagrant plugin install vagrant-junos`.**\n"
  end
  if not Vagrant.has_plugin?('vagrant-host-shell')
    raise "** Install vagrant-host-shell plugin `vagrant plugin install vagrant-host-shell`.**\n"
  end

  config.ssh.insert_key = false  # Do not add a unique custom-generated key

  # We add private_network interfaces to these, which just create the host-only networks.
  # The junos plugin is needed to configure them.
  # Also note that the host gets the .1 addresses in these private nets.
  config.vm.define 'srx1-left' do |left|
    left.vm.box = FIREFLY_VERSION
    left.vm.hostname = "srx1-left.vagrant"
    left.vm.network "private_network", ip: "172.16.10.10" #,  virtualbox__intnet: "left-inside"
    left.vm.network "private_network", ip: "172.16.100.20", virtualbox__intnet: "left-outside"
    left.hostmanager.manage_guest = false  # No /etc/hosts for vagrant-hostmanager on these
    left.vm.provision "file", source: "provision/srx-provision.cfg", destination: "/cf/root/provision.cfg"
    left.vm.provision :host_shell do |host_shell|
      host_shell.inline = 'vagrant ssh srx1-left -c "/usr/sbin/cli -f /cf/root/provision.cfg"'
    end
  end

  config.vm.define 'middle' do |middle|
    middle.vm.box = FIREFLY_VERSION + "-packetmode"
    middle.vm.hostname = "r1-middle.vagrant"
    middle.vm.network "private_network", ip: "172.16.100.10", virtualbox__intnet: "left-outside"  #  eth1
    middle.vm.network "private_network", ip: "172.16.200.10", virtualbox__intnet: "right-outside" #  eth2
    middle.vm.provision "file", source: "provision/middle-provision.cfg", destination: "/cf/root/provision.cfg"
    middle.vm.provision :host_shell do |host_shell|
      host_shell.inline = 'vagrant ssh middle -c "/usr/sbin/cli -f /cf/root/provision.cfg"'
    end
    middle.hostmanager.manage_guest = false  # No /etc/hosts for vagrant-hostmanager on these
  end

  config.vm.define 'srx1-right' do |right|
    right.vm.box = FIREFLY_VERSION
    right.vm.hostname = "srx1-right.vagrant"
    right.vm.network "private_network", ip: "172.16.20.10" #,  virtualbox__intnet: "right-inside"
    right.vm.network "private_network", ip: "172.16.200.20", virtualbox__intnet: "right-outside"
    right.vm.provision "file", source: "provision/srx-provision.cfg", destination: "/cf/root/provision.cfg"
    right.vm.provision :host_shell do |host_shell|
      host_shell.inline = 'vagrant ssh srx1-right -c "/usr/sbin/cli -f /cf/root/provision.cfg"'
    end
    right.hostmanager.manage_guest = false  # No /etc/hosts for vagrant-hostmanager on these
  end
end
