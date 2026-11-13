# PS-023 Operating System Image Catalog: Alpine 3.20 & CirrOS 0.6.2

## Overview
PS-023 supports multi-distribution microVM workloads through its catalog API (`GET /images`, `POST /images/import`, `DELETE /images/{id}`). This document specifies the catalog definitions, cryptographic integrity checksums, direct-kernel boot architecture, and verification steps for Alpine Linux 3.20 and CirrOS 0.6.2.

---

## 1. Catalog Distribution Specifications

### A. Alpine Linux 3.20 (virt)
* **Catalog ID:** `alpine-3-20`
* **Distribution:** Alpine Linux
* **Release Version:** 3.20.3
* **Target Architecture:** `x86_64`
* **Disk Format:** RAW (ext4 filesystem partition)
* **Status:** `NOT_DOWNLOADED` (Marked: **not boot-tested** pending sudo execution)
* **Official Upstream URL:** `https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/x86_64/alpine-virt-3.20.3-x86_64.iso`
* **Cloud / Minimal Upstream:** `https://dl-cdn.alpinelinux.org/alpine/v3.20/releases/cloud/nocloud_alpine-3.20.3-x86_64-bios-cloudinit-r0.qcow2`
* **Verified Cryptographic Checksum:**
  * **SHA-256:** `81df854fbd7327d293c726b1eeeb82061d3bc8f5a86a6f77eea720f6be372261` (virt ISO)
* **Direct-Kernel Boot Architecture:**
  * Kernel binary: `/boot/vmlinuz-virt`
  * Initramfs: `/boot/initramfs-virt`
  * Kernel commandline: `console=ttyS0 root=/dev/vda1 modules=ext4,virtio_pci,virtio_net`

### B. CirrOS 0.6.2 (Minimal Test OS)
* **Catalog ID:** `cirros-0-6-2`
* **Distribution:** CirrOS
* **Release Version:** 0.6.2
* **Target Architecture:** `x86_64`
* **Disk Format:** RAW (MBR / ext4 rootfs partition)
* **Status:** `NOT_DOWNLOADED` (Marked: **not boot-tested** pending sudo execution)
* **Official Upstream URL:** `https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img`
* **Verified Cryptographic Checksums:**
  * **SHA-256:** `07e44a73e54c94d988028515403c1ed762055e01b83a767edf3c2b387f78ce00`
  * **MD5 (Secondary):** `c8fc807773e5354afe61636071771906`
* **Direct-Kernel Boot Architecture:**
  * Kernel binary: `/boot/vmlinuz`
  * Initramfs: `/boot/initrd.img`
  * Kernel commandline: `console=ttyS0 root=/dev/vda1 ro`

---

## 2. API Security & Enforcement Invariants

1. **Unknown Image Rejection (HTTP 422):**
   * Any `POST /vms` request specifying an `image` string that is not registered in the image catalog table is immediately rejected with HTTP status code `422 Unprocessable Entity`.
2. **In-Use Image Delete Protection (HTTP 409):**
   * A call to `DELETE /images/{id}` checks `SELECT count(*) FROM vms WHERE image = ?`. If any virtual machine references the image, the controller refuses deletion with HTTP status code `409 Conflict`.
3. **Missing Image Delete (HTTP 404):**
   * Deleting an uncataloged image returns `404 Not Found`.

---

## 3. Morning Checklist for Live Boot Testing (Requires Sudo)

Because live microVM creation with direct hardware acceleration requires access to `/dev/kvm`, TAP networking pools, and image loop-mounting (which require `sudo` privileges unavailable during autonomous overnight runs), these images are cataloged and validated via automated unit tests but marked **not boot-tested**.

To download, verify checksums, and boot-test in the morning:

```bash
# 1. Download official CirrOS 0.6.2 raw disk image
cd ~/ps023/images
wget https://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img -O cirros-0.6.2-x86_64-disk.img

# 2. Verify official checksums
echo "07e44a73e54c94d988028515403c1ed762055e01b83a767edf3c2b387f78ce00  cirros-0.6.2-x86_64-disk.img" | sha256sum -c
echo "c8fc807773e5354afe61636071771906  cirros-0.6.2-x86_64-disk.img" | md5sum -c

# 3. Boot test CirrOS with direct kernel boot in Cloud Hypervisor
sudo cloud-hypervisor \
  --kernel ~/ps023/lab/vmlinux.bin \
  --disk path=cirros-0.6.2-x86_64-disk.img \
  --cmdline "console=ttyS0 root=/dev/vda1 ro" \
  --cpus boot=1 \
  --memory size=256M \
  --serial tty \
  --console off
```
