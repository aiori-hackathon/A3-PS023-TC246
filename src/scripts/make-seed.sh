#!/bin/bash
set -e
D=$HOME/ps023/outer
S=$D/seed
IID="outer-$(date +%s)"   # a fresh instance-id every time the seed is rebuilt
PASS="${PS023_VM_PASSWORD:?set PS023_VM_PASSWORD first}"

cat > $S/user-data <<EOF
#cloud-config
hostname: node-b
users:
  - name: rajyavardhan
    groups: [sudo, kvm]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: false
    plain_text_passwd: "$PASS"
ssh_pwauth: true
chpasswd:
  expire: false
growpart:
  mode: auto
  devices: ["/"]
resize_rootfs: true
EOF

printf 'instance-id: %s\nlocal-hostname: node-b\n' "$IID" > $S/meta-data

cat > $S/network-config <<EOF
version: 2
ethernets:
  nic0:
    match:
      macaddress: "12:34:56:78:90:17"
    set-name: ens3
    addresses: [192.168.100.17/24]
    routes:
      - to: default
        via: 192.168.100.1
    nameservers:
      addresses: [1.1.1.1, 8.8.8.8]
EOF

rm -f $D/seed.img
truncate -s 2M $D/seed.img
mkfs.vfat -n CIDATA $D/seed.img > /dev/null
for f in user-data meta-data network-config; do
  mcopy -i $D/seed.img $S/$f ::/$f
done
echo "seed built, instance-id $IID"
mdir -i $D/seed.img ::
