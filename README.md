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
  TODO: describe this more here

## Vagrant deploy - VirtualBox

The VirtualBox deploy uses a Vagrant box from Juniper that requires the `vagrant-junos`
and `vagrant-host-shell` plugins.  You will need to install these, for example:
    vagrant plugin install vagrant-junos
    vagrant plugin install vagrant-host-shell

This Vagrant deploy creates a test environment:

            ge-0/0/0 Vagrant mgmt                                           ge-0/0/0 Vagrant mgmt
                 |                                                              |
           / srx1-left \                                                  / srx1-right \
       ge-0/0/1      ge-0/0/2 ------------  r1-middle  ------------  ge-0/0/2        ge-0/0/1
    .10                     .20          .10         .10          .20                       .10
    172.16.10.0/24          172.16.100.0/24          172.16.200.0/24             172.16.20.0/24

In this environment, the srx1-left SRX and srx1-right SRX form a VPN tunnel connecting
their local networks, through the r1-middle host, which acts as a router.  The ge-0/0/2.0 interfaces
are the external VPN endpoints with "public" IPs.

### SRX Vagrant VM Bootstrap Configuration

The vagrant-junos plugin (https://github.com/JNPRAutomate/vagrant-junos) provides for
network interface and ssh key provisioning, based off the standard vagrant configuration
items config.vm.network and config.ssh.private_key_path

To bring up the environment:

    vagrant up

Vagrant expects you to manage the devices through their ge-0/0/0 interfaces with its
port forwarding etc.  For simplicity we are going to Ansible manage through the "internal"
ge-0/0/1 interfaces via their static IPs on host-only networks.

Log in to the SRX devices and set some bootstrap configuration to allow management via Ansible:

    vagrant ssh srx1-left
    root@srx1-left% cli
    root@vsrx> edit
    root@srx1-left.vagrant# set system services netconf ssh
    root@srx1-left.vagrant# set security zones security-zone trust interfaces ge-0/0/1.0
    root@srx1-left.vagrant# set security zones security-zone trust host-inbound-traffic system-services ping
    root@srx1-left.vagrant# set security zones security-zone trust host-inbound-traffic system-services ssh
    root@srx1-left.vagrant# set security zones security-zone trust host-inbound-traffic system-services netconf
    root@srx1-left.vagrant# commit comment "Enable netconf management" and-quit

NETCONF needs the key to be active, so be sure to:

    ssh-add ~/.vagrant.d/insecure_private_key

Note that these interface IP addresses are already set by the vagrant-junos plugin:

    # set interfaces ge-0/0/1 unit 0 family inet address 172.16.10.10/24
    # set interfaces ge-0/0/2 unit 0 family inet address 172.16.100.20/24

Optionally, some untrust zone interface and handy policy settings would be:

    set security zones security-zone untrust interfaces ge-0/0/2.0
    set security policies from-zone untrust to-zone trust policy allow-ping
    set security policies from-zone untrust to-zone trust policy allow-ping match source-address any
    set security policies from-zone untrust to-zone trust policy allow-ping match destination-address any
    set security policies from-zone untrust to-zone trust policy allow-ping match application junos-icmp-ping
    set security policies from-zone untrust to-zone trust policy allow-ping then permit
    insert security policies from-zone untrust to-zone trust policy allow-ping before policy default-deny

Then you can ssh into the trust interface and test things out:

    ssh -i ~/.vagrant.d/insecure_private_key vagrant@172.16.10.10  # srx1-left
    ssh -i ~/.vagrant.d/insecure_private_key vagrant@172.16.20.10  # srx1-right

Next we will want to run the Ansible deploy playbook to set up other interfaces, policies and such.


## KVM Deploy
This section (and onwards) is still a work in progress, with _way_ too many notes.  It should probably be broken up into multiple files.

The Juniper vSRX KVM install guide:
http://www.juniper.net/techpubs/en_US/vsrx15.1x49/information-products/pathway-pages/security-vsrx-kvm-install-guide-pwp.pdf

Branch SRX Active/Passive Cluster Implementation guide:
https://kb.juniper.net/library/CUSTOMERSERVICE/technotes/8010055-EN.PDF
Really good but does not address issues specific to vSRX.

Docs on setting up a vSRX 15.1x49 (not Firefly) cluster under KVM are at:
http://www.juniper.net/techpubs/en_US/vsrx15.1x49/topics/task/multi-task/security-vsrx-cluster-stage-provisioning-kvm.html

Notes on interfaces:
- All SRX devices use the fxp0 interface (adapter 1) for out-of-band management,
  this needs the virtio driver and `ifconfig <bridge-name> promisc`
- Standalone devices will use:
  - ge-0/0/0-n (adapters 2 on) for revenue interfaces
- Clustered devices will use:
  - em0 (adapter 2) for cluster control link
  - ge-{0,7}/0/0 (adapter 3) for fabric links: ge-0/0/0==fab0 on node 0 and ge-7/0/0==fab1 on node1
  - ge-0/0/1-n (adapters 4 on) for revenue interfaces
  - Optionally, you can use a second fabric link with another pair of ge interfaces

Cluster networking looks like this:

        mgmt                           mgmt
         |                              |
    fxp0 |   em0   Control link  em0    | fxp0
       vSRX  -----------------------  vSRX
      Node 0 ----------------------- Node 1
             fab0  Fabric Link  fab1

The single-host test deploy creates a test environment:

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

### KVM Hypervisor Preparation

- Enable nested virtualization:
  - Check:
        cat /sys/module/kvm_intel/parameters/nested
        Y
  - Set:
    In `/etc/modprobe.d/qemu-system-x86.conf`:
        options kvm-intel nested=y
- Disable APICv if supported:
  - Check:
        cat /sys/module/kvm_intel/parameters/enable_apicv
        N
  - Set:
    In `/etc/modprobe.d/qemu-system-x86.conf`:
        options kvm-intel enable_apicv=n

### KVM Hypervisor Networks (single-host libvirt networks)

Create libvirt networks (host-only, for single-host testing only):

Name          Properties                                        Usage Notes
default       virbr0, host-only 192.168.122.1/24  NAT and DHCP  libvirt default, does NAT and DHCP, use for fxp0 mgmt
srx_ctrl      virbr1, host-only 192.168.125.1/24                SRX cluster control link
srx_fab       virbr2, host-only 192.168.126.1/24                SRX cluster fabric link, needs MTU 9000
srx_left_in   virbr3, 172.16.10.1/24              route         srx-left inside net
srx_left_out  virbr4, 172.16.100.1/24             route         srx-left outside net
...

config files are e.g. `/etc/libvirt/qemu/networks/<net-name>.xml`:
  <network>
    <name>srx_left_in</name>
    <bridge name="virbr1" />
    <forward mode="route"/>
    <ip address="172.16.10.1" netmask="255.255.255.0">
    </ip>
  </network>
Saved a copy in /var/lib/libvirt/images/network-definitions/

virsh net-list --all
virsh net-destroy <net-name>
virsh net-undefine <net-name>
virsh net-define /path/to/<net-name>.xml
virsh net-start <net-name>

### KVM Hypervisor Networks (2-host cluster with bridges)

Create host bridges:

Switch vlans:
Vlan         ID    Name            Ports
-----------  ----  --------------  -------------------
mgmt         1     DEFAULT_VLAN    untagged 1-4,7-48
in-left      101   in-left         tagged 5-6
sync-left    102   sync-left       tagged 5-6
data-left    103   data-left       tagged 5-6
out-left     104   out-left        tagged 5-6
out-right    105   out-right       tagged 5-6
in-right     106   in-right        tagged 5-6

In /etc/network/interfaces:
    # Bridges for router test networks
    auto em2.101
    iface em2.101 inet manual
    auto br_in_left
      iface br_in_left inet manual
      bridge_ports em2.101
    auto em2.102
    iface em2.102 inet manual
    auto br_sync_left
      iface br_sync_left inet manual
      bridge_ports em2.102
    auto em2.103
    iface em2.103 inet manual
    auto br_data_left
      iface br_data_left inet manual
      bridge_ports em2.103
    auto em2.104
    iface em2.104 inet manual
    auto br_out_left
      iface br_out_left inet manual
      bridge_ports em2.104
    auto em2.105
    iface em2.105 inet manual
    auto br_out_right
      iface br_out_right inet manual
      bridge_ports em2.105
    auto em2.106
    iface em2.106 inet manual
    auto br_in_right
      iface br_in_right inet manual
      bridge_ports em2.106


### SRX KVM VM Bootstrap Configuration

Create VMs with virt-install:

    QEMU_IMAGE_PATH="/var/lib/libvirt/images"
    SRX_NAME="srx1-left"
    SRX_IMAGE="${QEMU_IMAGE_PATH}/${SRX_NAME}.img"
    SRX_SRC_IMAGE="${QEMU_IMAGE_PATH}/media-vsrx-vmdisk-15.1X49-D60.7.qcow2"

- Download vSRX qcow2 image (will be in artifactory/misc)

- Copy the image:

      cp $SRX_SRC_IMAGE $SRX_IMAGE

- Install VM with: 4 GB RAM, 2 vCPU, 16 GB disk:

    virt-install --name $SRX_NAME --ram 4096 --cpu SandyBridge,+vmx --vcpus=2 --arch=x86_64 \
    --disk path=${SRX_IMAGE},size=16,device=disk,bus=ide,format=qcow2 \
    --os-type linux --os-variant rhel7 --import \

    # single-host libvirt network settings:
    --network=network:default,model=virtio \
    --network=network:srx_ctrl,model=virtio \
    --network=network:srx_fab,model=virtio \
    --network=network:srx_left_in,model=virtio \
    --network=network:srx_left_out,model=virtio

    # two-host cluster bridged network settings:
    # br0           # fxp0 mgmt (DHCP)
    # br_data_left  # em0 data
    # br_sync_left  # fabN sync
    # br_in_left    # ge-0/0/1 internal
    # br_out_left   # ge-0/0/2 external
    --network bridge=br0,model=virtio \
    --network bridge=br_data_left,model=virtio \
    --network bridge=br_sync_left,model=virtio \
    --network bridge=br_in_left,model=virtio \
    --network bridge=br_out_left,model=virtio
    # stand-alone with bridged network settings (srx1-right):
    # br0           # fxp0 mgmt (DHCP)
    # br_in_right   # ge-0/0/1 internal
    # br_out_left   # ge-0/0/2 external (instead of br_out_right with no intermediate host)
    --network bridge=br0,model=virtio \
    --network bridge=br_in_right,model=virtio \
    --network bridge=br_out_left,model=virtio

JunOS Configuration Setup:

Connect to VM console and set initial configuration:

    virsh console $SRX_NAME

    root@vsrx> edit
    # configure here
    root@vsrx# commit comment "Initial configuration"
    root@vsrx# quit

Also good to do before committing configuration:

    root@vsrx# show |compare
    root@vsrx# commit check

Basic Configuration, root password:

    set system root-authentication encrypted-password "$5$LfdyRnV4$kZdd6xVMBVbRnf6kz0mHfP7Pc46ppQJBGgMpYmFBdbD"
    # passwd is Wavemarket

Non-clustered test system settings:

    # single-host kvm:
    # 10.38.31.39  srx1-right fxp0    host3.itlab.hq.wavemarket.com
    set system host-name srx1-right
    set interfaces fxp0 unit 0 family inet address 10.38.31.39/27
    set routing-options static route 0/0 next-hop 10.38.31.33
    commit comment "Initial configuration"

Clustered test system settings:

    # Enable cluster mode and reboot
    root@srx1-left> set chassis cluster cluster-id 1 node 0 reboot
    root@srx2-left> set chassis cluster cluster-id 1 node 1 reboot
    # Note that interfaces are renamed and hostname is the same on both now
    # From now on, you only need to make configuration changes on one cluster member
    # NOTE: I could not get setting fxp0 interfaces to dhcp-client to work at all in a cluster

    # Node-dependent settings
    set groups node0 system host-name <name-node0>
    set groups node0 interfaces fxp0 unit 0 family inet address <ip address/mask>
    set groups node1 system host-name <name-node1>
    set groups node1 interfaces fxp0 unit 0 family inet address <ip address/mask>
    set apply-groups "${node}"
    set routing-options static route 0/0 next-hop <gateway IP>
    # FAB links
    set interfaces fab0 fabric-options member-interfaces ge-0/0/0
    set interfaces fab1 fabric-options member-interfaces ge-7/0/0
    # Check cluster status and control traffic with:
    #   show chassis cluster status
    #   show chassis cluster statistics

    # single-host libvirt
    # srx1-left fxp0.0: 192.168.122.101
    # srx2-left fxp0.0: 192.168.122.102
    set groups node0 system host-name srx1-left
    set groups node0 interfaces fxp0 unit 0 family inet address 192.168.122.101/24
    set groups node1 system host-name srx2-left
    set groups node1 interfaces fxp0 unit 0 family inet address 192.168.122.102/24
    set apply-groups "${node}"

    # two-host cluster:
    # 10.38.31.37  srx1-left  fxp0    host1.itlab.hq.wavemarket.com
    # 10.38.31.38  srx2-left  fxp0    host2.itlab.hq.wavemarket.com
    set groups node0 system host-name srx1-left
    set groups node0 interfaces fxp0 unit 0 family inet address 10.38.31.37/27
    set groups node1 system host-name srx2-left
    set groups node1 interfaces fxp0 unit 0 family inet address 10.38.31.38/27
    set apply-groups "${node}"
    set routing-options static route 0/0 next-hop 10.38.31.33


## SRX Ansible Management

Junos Ansible Module Docs:
http://junos-ansible-modules.readthedocs.org/
or,
http://junos-ansible-modules.readthedocs.io/en/1.4.0/

Github of the modules:
https://github.com/Juniper/ansible-junos-stdlib

The modules are installed in ~/.virtualenvs/junos-vpn/lib/python2.7/site-packages/ansible/modules/core/network/junos/

Good examples of ways to do it:

http://www.juniper.net/techpubs/en_US/junos-ansible1.0/information-products/pathway-pages/product/1.0/index.html
Pretty primitive, mainly loading and saving snippets to local files...

https://pynet.twb-tech.com/blog/juniper/juniper-ansible.html
Config snippet file:
    $ cat test_config.conf
    routing-options {
        static {
            route 1.1.1.0/24 next-hop 10.220.88.1;
        }
    }
Then in the playbook:
    - name: Add a static route
      junos_install_config:
        host={{ inventory_hostname }}    # variable is from inventory file
        file=test_config.conf
        overwrite=false                # Add to existing configuration
        user={{ junos_config_user }}

This is a pretty cool way to assemble configs from parts then push them to Juniper gear:
https://github.com/dgjnpr/ansible-template-for-junos

### Setting Up SRX For Ansible Management

Setting up Ansible for Junos OS Managed Nodes
http://www.juniper.net/techpubs/en_US/junos-ansible1.0/topics/task/installation/junos-ansible-client-configuring.html

Enable NETCONF management via ssh, and set ssh key:

    set system services netconf ssh
    set system root-authentication ssh-rsa "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCoeELibgrP7LBpFKChyotKddgZ2MwairR3Q0Ixul8NBHxpwrNi038RN13NHnUMK3AfTKeX+Ch4FcD3G9bQykUfzZNJ7JZHtbTvQ27adn6+HDOd14uckK7fCI2cpQ8/Bt6+H4U4K7ThWLMC9UsM+Mro4+PWBKM4n014Fi5k5KrfkW88rBhHM9uLLAX2e9/zcOafddSU9Zl5R68DLCgFIxzIdd2rL8sjye4s50avLHeX77az8hNQwdVSxd58TS+iXU3/PsFYkWSvL52WBQv+HXNRWieufO9vOdL5sBCE9kSHcz+LedyDDdJphqv+ZatWK1xOSiCTK8qeduqND+TXB84Es01NYGYad48h7tti0SU4HDcyw9gbkNKi2ktURZmL2rGPBfkdKFsNuh3PQntkgRx14NwvW8VHsf18vVM9tSmHOPahIUi4rQ1HPpAbDquoriva/rC9qVlgxJepzsGPOWXKGXSctUOQLVlCWaln9mKTFwo0wBIwrCcSeGTZL74MHhl1PsU0zQqAX800PUPDs/DXq3kQs/Pbf/sLQWV3c4dc3A8B1qWA2BWHKx3XdlXbO9SxOHiSxr2tnyNWpyR8xJ5ufaJXDSXV0/pbKaFyoW9zgqO50QX8tV7ETN48t1ANkz14yc27Homddn8I8JyPfN/B77zQwqVQOf9fKqMNTwXPCQ== peter.pletcher@peterpletcher-lt"

test this with e.g.:

    ssh root@host1.itlab.hq.wavemarket.com

Install required Python library (handled in requirements.txt):

    pip install junos-eznc



## SRX Configuration Methods

To use rollback:

    root@srx1-right> show system commit                  
    0   2016-12-07 00:25:10 UTC by root via netconf
        Pushing config ... please wait
    1   2016-12-06 22:29:09 UTC by root via cli
        Set up NETCONF over SSH
    2   2016-12-06 20:15:23 UTC by root via cli
        Initial configuration
    3   2016-12-06 20:07:45 UTC by root via other

    root@srx1-right> edit
    Entering configuration mode

    [edit]
    root@srx1-right# rollback 1
    load complete

    [edit]
    root@srx1-right# commit and-quit
    commit complete
    Exiting configuration mode

Verifying your changes:

    root@vsrx# show |compare
    root@vsrx# commit check
    root@vsrx# commit comment "Add interfaces"
    root@vsrx# quit


### SRX Redundant Ethernet Configuration

Example Configuration:

    # Redundancy Groups (0 for Routing Engine, 1 for reth interfaces)
    set chassis cluster redundancy-group 0 node 0 priority 100
    set chassis cluster redundancy-group 0 node 1 priority 1
    set chassis cluster redundancy-group 1 node 0 priority 100
    set chassis cluster redundancy-group 1 node 1 priority 1
    # preempt setting on would mean RG fails back to priority node when an interface recovers

    # reth interfaces
    set chassis cluster reth-count 2
    set interfaces ge-0/0/1 gigether-options redundant-parent reth0
    set interfaces ge-7/0/1 gigether-options redundant-parent reth0
    set interfaces reth0 redundant-ether-options redundancy-group 1
    set interfaces reth0.0 family inet address 172.16.10.10/24
    set security zones security-zone trust interfaces reth0.0
    set interfaces ge-0/0/2 gigether-options redundant-parent reth1
    set interfaces ge-7/0/2 gigether-options redundant-parent reth1
    set interfaces reth1 redundant-ether-options redundancy-group 1
    set interfaces reth1.0 family inet address 172.16.100.10/24
    set security zones security-zone untrust interfaces reth1.0

    # reth interface monitoring (not used yet)
    # TODO is interface-monitor needed or useful in virt?
    # Note: The link status of VirtIO interfaces is always reported as UP, so a vSRX chassis cluster
    #       cannot receive link up and link down messages from VirtIO interfaces.
    # TODO should probably use IP monitoring here
    # Failed physical interfaces have their weight subtracted from the RG threshold of 255,
    # and failover happens when this reaches 0
    set chassis cluster redundancy-group 1 interface-monitor ge-0/0/1 weight 255
    set chassis cluster redundancy-group 1 interface-monitor ge-0/0/2 weight 255
    set chassis cluster redundancy-group 1 interface-monitor ge-7/0/1 weight 255
    set chassis cluster redundancy-group 1 interface-monitor ge-7/0/2 weight 255
    # What about this?:
    set chassis cluster control-link-recovery

### SRX Interfaces and zones

    # standalone test system
    set interfaces ge-0/0/0 unit 0 family inet address 172.16.10.10/24
    set interfaces ge-0/0/1 unit 0 family inet address 172.16.100.10/24
    set security zones security-zone trust interfaces ge-0/0/0.0 host-inbound-traffic system-services all
    set security zones security-zone untrust interfaces ge-0/0/1.0




### Some Debugging Notes

single-host libvirt networking issues:
Cannot ping from host to the fxp0 interface on srx1-left
- Created srx1-left, as only cluster member.  No ping of its fxp0
- virt-install of srx2-left starts, then ping srx1-left fxp0 works!
- Added srx2-left to cluster
  - ping srx1-left host still works, but no ping of srx2-left fxp0!
  - srx1-left and srx2-left can ping each other...
According to http://www.juniper.net/techpubs/en_US/vsrx15.1x49/topics/reference/general/security-vsrx-factory-default-setting.html
The management interface, fxp0, requires the following:
- KVM uses the virtIO vNIC and requires promiscuous mode on the bridge. Use the ifconfig bridge-name promisc command on the host OS to enable promiscuous mode on the Linux bridge.
No help though.


Check chassis cluster:
  show chassis cluster status
  show chassis cluster statistics
  show chassis cluster interfaces
  show chassis cluster control-plane statistics
  show chassis cluster data-plane statistics
  show chassis cluster status redundancy-group 1

To check network interfaces:
  # virsh domiflist 7
  Interface  Type       Source     Model       MAC
  -------------------------------------------------------
  vnet4      network    default    virtio      52:54:00:60:5c:c1
  vnet5      network    srx_left_in virtio      52:54:00:e3:79:3c
  vnet6      network    srx_left_out virtio      52:54:00:04:ed:47


## Misc Notes

### Automatic VM Provisioning

One possibility: run an expect script on the console, as in
https://github.com/lamoni/vztp-vsrx/blob/master/scripts/instantiate_new_srx.py
running the expect script at
https://github.com/lamoni/vztp-vsrx/blob/master/console-config.exp
which sets:
- root password
- netconf over ssh
- ge-0/0/0.0 untrust, IP addr
- default route

### Using Artifactory

https://confluence.locationlabs.com/display/TOOLS/Artifactory

Downloading in playbook, e.g. in `ansible/roles/ldap-account-manager/tasks/setup.yml`:
- name: Download LDAP Account Manager
  get_url:
    url=http://artifactory.locationlabs.com/misc/org/ldap-account-manager/ldap-account-manager/{{ lam_version }}/ldap-account-manager-{{ lam_version }}.tar.bz2
    dest=/var/tmp/lam
    sha256sum="{{ lam_tar_sha256sum }}"

### Default vSRX Configuration

root# run show configuration |display set|no-more
set version 15.1X49-D60.7
set system autoinstallation delete-upon-commit
set system autoinstallation traceoptions level verbose
set system autoinstallation traceoptions flag all
set system services ssh
set system services web-management http interface fxp0.0
set system syslog user * any emergency
set system syslog file messages any any
set system syslog file messages authorization info
set system syslog file interactive-commands interactive-commands any
set system license autoupdate url https://ae1.juniper.net/junos/key_retrieval
set security screen ids-option untrust-screen icmp ping-death
set security screen ids-option untrust-screen ip source-route-option
set security screen ids-option untrust-screen ip tear-drop
set security screen ids-option untrust-screen tcp syn-flood alarm-threshold 1024
set security screen ids-option untrust-screen tcp syn-flood attack-threshold 200
set security screen ids-option untrust-screen tcp syn-flood source-threshold 1024
set security screen ids-option untrust-screen tcp syn-flood destination-threshold 2048
set security screen ids-option untrust-screen tcp syn-flood queue-size 2000
set security screen ids-option untrust-screen tcp syn-flood timeout 20
set security screen ids-option untrust-screen tcp land
set security policies from-zone trust to-zone trust policy default-permit match source-address any
set security policies from-zone trust to-zone trust policy default-permit match destination-address any
set security policies from-zone trust to-zone trust policy default-permit match application any
set security policies from-zone trust to-zone trust policy default-permit then permit
set security policies from-zone trust to-zone untrust policy default-permit match source-address any
set security policies from-zone trust to-zone untrust policy default-permit match destination-address any
set security policies from-zone trust to-zone untrust policy default-permit match application any
set security policies from-zone trust to-zone untrust policy default-permit then permit
set security zones security-zone trust tcp-rst
set security zones security-zone untrust screen untrust-screen
set interfaces fxp0 unit 0

### Boot Messages

What's up with the "Linux" ?

    Booting `Juniper Linux`

  Loading Linux ...
  Consoles: serial port  
  BIOS drive C: is disk0
  BIOS drive D: is disk1
  BIOS drive E: is disk2
  BIOS drive F: is disk3
  BIOS drive G: is disk4
  BIOS 639kB/999416kB available memory

  FreeBSD/i386 bootstrap loader, Revision 1.2
  (builder@svl-junos-p003, Tue Sep 13 19:55:58  2016)
  Loading /boot/defaults/loader.conf
  /kernel text=0xa68fb0 data=0x63c3c+0x11fc38 syms=[0x4+0xb5970+0x4+0x10a99e]
  ...

Some interesting boot devices and messages:

em0: <VirtIO Networking Adapter> on virtio_pci0
em1: <VirtIO Networking Adapter> on virtio_pci1
em2: <VirtIO Networking Adapter> on virtio_pci2
em3: <Intel(R) PRO/1000 Network Connection Version - 3.2.18> port 0xc140-0xc17f mem 0xfebc0000-0xfebdffff irq 11 at device 16.0 on pci0
fxp0: bus=0, device=16, func=0, Ethernet address 52:54:00:60:5c:c1
Trying to mount root from ufs:/dev/vtbd0s1a
Formatting data disk /dev/vtbd1
/dev/vtbd1s1e: 307.2MB (629080 sectors) block size 16384, fragment size 2048
/dev/vtbd1s1f: 2764.5MB (5661764 sectors) block size 16384, fragment size 2048
Loading configuration ...
mgd: error: Cannot open configuration file: /config/juniper.conf
mgd: warning: activating factory configuration
Generating RSA2 key /etc/ssh/ssh_host_rsa_key
Generating public/private rsa key pair.
Your identification has been saved in /etc/ssh/ssh_host_rsa_key.
Your public key has been saved in /etc/ssh/ssh_host_rsa_key.pub.

Amnesiac (ttyd0)

login:

### Cluster Notes

Before "set chassis cluster"

root@srx1-left> show interfaces terse                           
Interface               Admin Link Proto    Local                 Remote
ge-0/0/0                up    up
gr-0/0/0                up    up
ip-0/0/0                up    up
lsq-0/0/0               up    up
lt-0/0/0                up    up
mt-0/0/0                up    up
sp-0/0/0                up    up
sp-0/0/0.0              up    up   inet    
                                   inet6   
sp-0/0/0.16383          up    up   inet    
ge-0/0/1                up    up
ge-0/0/2                up    up
ge-0/0/3                up    up
dsc                     up    up
em0                     up    up
em0.0                   up    up   inet     128.0.0.1/2     
em1                     up    up
em1.32768               up    up   inet     192.168.1.2/24  
em2                     up    up
fxp0                    up    up
fxp0.0                  up    up   inet     192.168.122.118/24
gre                     up    up
ipip                    up    up        
irb                     up    up
lo0                     up    up
lo0.16384               up    up   inet     127.0.0.1           --> 0/0
lo0.16385               up    up   inet     10.0.0.1            --> 0/0
                                            10.0.0.16           --> 0/0
                                            128.0.0.1           --> 0/0
                                            128.0.0.4           --> 0/0
                                            128.0.1.16          --> 0/0
lo0.32768               up    up  
lsi                     up    up
mtun                    up    up
pimd                    up    up
pime                    up    up
pp0                     up    up
ppd0                    up    up
ppe0                    up    up
st0                     up    up
tap                     up    up
vlan                    up    down
vtep                    up    up

After "set chassis cluster"

{primary:node0}
root@srx1-left> show interfaces terse
Interface               Admin Link Proto    Local                 Remote
ge-0/0/0                up    up
gr-0/0/0                up    up
ip-0/0/0                up    up
ge-0/0/1                up    up
ge-0/0/2                up    up
dsc                     up    up
em0                     up    up
em0.0                   up    up   inet     129.16.0.1/2    
                                            143.16.0.1/2    
                                   tnp      0x1100001       
em1                     up    up
em1.32768               up    up   inet     192.168.1.2/24  
em2                     up    up
fab0                    up    down
fab0.0                  up    down inet     30.17.0.200/24  
fxp0                    up    up
fxp0.0                  up    up   inet     192.168.122.118/24
gre                     up    up
ipip                    up    up
irb                     up    up
lo0                     up    up
lo0.16384               up    up   inet     127.0.0.1           --> 0/0
lo0.16385               up    up   inet     10.0.0.1            --> 0/0
                                            10.0.0.16           --> 0/0
                                            128.0.0.1           --> 0/0
                                            128.0.0.4           --> 0/0
                                            128.0.1.16          --> 0/0
lsi                     up    up
mtun                    up    up
pimd                    up    up
pime                    up    up
pp0                     up    up
ppd0                    up    up
ppe0                    up    up
st0                     up    up
tap                     up    up
vtep                    up    up
