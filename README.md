# JunOS VPN Tunnel Deploy

This is a deploy for a set of JunOS VPN endpoints that implement a site-to-site tunnel.

## Getting started

1. Create/activate a virtualenv for the project:

        mkvirtualenv junos-vpn

2. Install the python requirements (ansible):

        pip install -r requirements.txt

3. Install Ansible requirements (shared roles):

        ansible-galaxy install -r requirements.yml -p shared-roles --force

## Playbooks

* deploy - Deploy to VPN endpoint systems

## Vagrant deploy - VirtualBox

The VirtualBox deploy uses a Vagrant box from Juniper that requires the `vagrant-junos`
and `vagrant-host-shell` plugins.  You will need to install these, for example:
    vagrant plugin install vagrant-junos
    vagrant plugin install vagrant-host-shell

This Vagrant deploy creates a test environment:

            ge-0/0/0 mgmt                                                  ge-0/0/0 mgmt
                 |                                                              |
           / srx1-left \                                                  / srx1-right \
       ge-0/0/1      ge-0/0/2 ------------  r1-middle  ------------  ge-0/0/2        ge-0/0/1
    .10                     .20          .10         .10          .20                       .10
    172.16.10.0/24          172.16.100.0/24          172.16.200.0/24             172.16.20.0/24

In this environment, the srx1-left SRX and srx1-right SRX form a VPN tunnel connecting
their local networks, through the r1-middle host, which acts as a router.  The ge-0/0/2.0 interfaces
are the external VPN endpoints with "public" IPs.

### Bootstrap Configuration

The vagrant-junos plugin (https://github.com/JNPRAutomate/vagrant-junos) provides for
network interface and ssh key provisioning, based off the standard vagrant configuration
items config.vm.network and config.ssh.private_key_path

To bring up the environment:

    vagrant up

JunOS Configuration Setup:

  # Set up bootstrap configuration on nodes, e.g.:
  vagrant ssh srx1-left
  root@vsrx> edit

  # interfaces
  # set interfaces ... inet address is already done by vagrant-junos plugin
  # set interfaces ge-0/0/1 unit 0 family inet address 172.16.10.10/24
  set security zones security-zone trust interfaces ge-0/0/1.0
  # set interfaces ge-0/0/2 unit 0 family inet address 172.16.100.20/24
  set security zones security-zone untrust interfaces ge-0/0/2.0
  # trust zone management traffic
  set security zones security-zone trust host-inbound-traffic system-services ping
  set security zones security-zone trust host-inbound-traffic system-services ssh
  # Policies
  set security policies from-zone untrust to-zone trust policy allow-ping
  set security policies from-zone untrust to-zone trust policy allow-ping match source-address any
  set security policies from-zone untrust to-zone trust policy allow-ping match destination-address any
  set security policies from-zone untrust to-zone trust policy allow-ping match application junos-icmp-ping
  set security policies from-zone untrust to-zone trust policy allow-ping then permit
  insert security policies from-zone untrust to-zone trust policy allow-ping before policy default-deny

  root@vsrx# show |compare
  root@vsrx# commit check
  root@vsrx# commit comment "Add interfaces"
  root@vsrx# quit

Then ssh into the trust interface and test things out:
  ssh -i ~/.vagrant.d/insecure_private_key root@172.16.20.10

Next we will want to run an Ansible playbook to set up the interfaces and such.


## KVM Deploy
This section TBD

The Juniper vSRX KVM install guide:
http://www.juniper.net/techpubs/en_US/vsrx15.1x49/information-products/pathway-pages/security-vsrx-kvm-install-guide-pwp.pdf

Docs on setting up a vSRX 15.1x49 (not Firefly) cluster under KVM are at:
http://www.juniper.net/techpubs/en_US/vsrx15.1x49/topics/task/multi-task/security-vsrx-cluster-stage-provisioning-kvm.html

Notes:
- SRX devices use the fxp0 interface (adapter 1) for out-of-band management,
  needs virtio driver and `ifconfig <bridge-name> promisc`
- Clustered devices will use: em0 (adapter 1) for cluster control link
  ge-{0,7}/0/0 for fabric links, ge-0/0/0==fab0 on node 0 and ge-7/0/0==fab1 on node1


The test deploy creates a test environment:

       / srx1-left \                                                  / srx1-right \
   reth1.0       reth0.0  ------------  r1-middle  ------------  reth0.0         reth1.0
.10    \ srx2-left /    .20          .10         .10          .20     \ srx2-right /    .10
172.16.10.0/24          172.16.100.0/24          172.16.200.0/24             172.16.20.0/24

In this environment, the srx1,2-left cluster and srx1,2-right cluster form a VPN tunnel connecting
their local networks, through the r1-middle host, which acts as a router.  The reth0.0 interfaces
are the external VPN endpoints with "public" IPs.

Would be good to have the option of trying an lo interface for the VPN endpoint as well.
This is useful if for example the two SRX have separate reth interfaces for multiple upstreams.
See https://forums.juniper.net/t5/SRX-Services-Gateway/IPSec-VPN-using-Reth-Interfaces-srx240/td-p/224877

### Bootstrap Configuration

Prep:
- Enable nested virtualization:
  In /etc/modprobe.d/qemu-system-x86.conf:
    options kvm-intel nested=y
- Some more things about APICv

Install with virt-install:
- Download vSRX qcow2 image (will be in artifactory/misc)
- Install with: 4 GB RAM, 2 vCPU, 16 GB disk:
  virt-install --name srx1 --ram 4096 --cpu SandyBridge,+vmx --vcpus=2 --arch=x86_64 --disk path=/mnt/vsrx.qcow2,size=16,device=disk,bus=ide,format=qcow2 --os-type linux --os-variant rhel7 --import
- Connect to console
  virsh console srx1

Create networks:
/etc/libvirt/qemu/networks/default.xml
  NAT, virbr0, stp='on', DHCP server
/etc/libvirt/qemu/networks/testleftnetwork.xml
  NAT, virbr1, stp='on', DHCP server
/etc/libvirt/qemu/networks/testrightnetwork.xml
  NAT, virbr2, stp='on', DHCP server

cp junos-vsrx-vmdisk-15.1X49-D20.2.qcow2 /mnt/vsrx20one.qcow2
virt-install--name vSRX20One --ram4096 --cpu SandyBridge,+vmx,-invtc --vcpus=2 --arch=x86_64 --disk path=/mnt/vsrx20one
.qcow2,size=16,device=disk,bus=ide,format=qcow2 --os-type linux --os-variant rhel7 --import \
  --network=network:default,model=virtio \
  --network=network:TestLeft,model=virtio \
  --network=network:TestRight,model=virtio

One possibility: run an expect script on the console, as in
https://github.com/lamoni/vztp-vsrx/blob/master/scripts/instantiate_new_srx.py
running the expect script at
https://github.com/lamoni/vztp-vsrx/blob/master/console-config.exp
which sets:
- root password
- netconf over ssh
- ge-0/0/0.0 untrust, IP addr
- default route

# Set up bootstrap configuration on nodes, e.g.:
vagrant ssh srx1-left
root@vsrx> edit

# trust zone management traffic
set security zones security-zone trust host-inbound-traffic system-services ping
set security zones security-zone trust host-inbound-traffic system-services ssh
# interfaces
set interfaces ge-0/0/1 unit 0 family inet address 172.16.10.10/24
set security zones security-zone trust interfaces ge-0/0/1.0
set interfaces ge-0/0/2 unit 0 family inet address 172.16.100.20/24
set security zones security-zone trust interfaces ge-0/0/2.0

root@vsrx# show |compare
root@vsrx# commit check
root@vsrx# commit comment "Add interfaces"
root@vsrx# quit
