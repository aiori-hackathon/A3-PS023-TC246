#!/usr/bin/env python3
"""
PS-023: Presentation Deck Generator
Builds a professional 16:9 PowerPoint deck from docs/ppt_outline.md into docs/deck/ps023_draft.pptx
using python-pptx and renders diagrams with matplotlib.
Converts deck to PDF/PNG via LibreOffice and pdftoppm.
"""

import os
import sys
import subprocess
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

OUTPUT_DIR = "/home/rajyavardhan/ps023/docs/deck"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
SLIDES_DIR = os.path.join(OUTPUT_DIR, "slides")
PPTX_PATH = os.path.join(OUTPUT_DIR, "ps023_draft.pptx")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(SLIDES_DIR, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Matplotlib Diagram Renderers
# ------------------------------------------------------------------------------

def render_arch_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.2)
    ax.axis("off")

    # Host boundary
    host_rect = patches.FancyBboxPatch((0.2, 0.2), 9.6, 4.8, boxstyle="round,pad=0.15", ec="#202522", fc="#F8F9FA", lw=2)
    ax.add_patch(host_rect)
    ax.text(0.5, 4.7, "Physical Host: Intel Core i7-12700H (12 vCPUs, 15 GB RAM, Fedora Linux)", fontsize=11, fontweight="bold", color="#202522")

    # Controller box
    ctrl_box = patches.FancyBboxPatch((0.5, 2.7), 4.2, 1.7, boxstyle="round,pad=0.1", ec="#168A62", fc="#E8F5E9", lw=1.5)
    ax.add_patch(ctrl_box)
    ax.text(2.6, 4.1, "PS-023 Controller (:8000)", fontsize=10, fontweight="bold", ha="center", color="#168A62")
    ax.text(2.6, 3.65, "FastAPI / Uvicorn (WAL SQLite DB)", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 3.25, "Heartbeat Lease Monitor (5s) + Auto Reconciler", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 2.9, "Pluggable Scheduler (memory_aware, best_fit)", fontsize=8.5, ha="center", color="#333333")

    # Node A box (Direct KVM)
    node_a = patches.FancyBboxPatch((0.5, 0.5), 4.2, 1.9, boxstyle="round,pad=0.1", ec="#2980B9", fc="#EBF5FB", lw=1.5)
    ax.add_patch(node_a)
    ax.text(2.6, 2.15, "Compute Node A (Direct KVM Host)", fontsize=10, fontweight="bold", ha="center", color="#2980B9")
    ax.text(2.6, 1.75, "Worker A (:8001) | Subnet 192.168.100.0/24", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 1.35, "Direct Kernel Boot (Cloud Hypervisor /api/v1)", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 0.95, "Cgroups v2 Limits (/sys/fs/cgroup/ps023-vmm-*)", fontsize=8.5, ha="center", color="#333333")

    # Node B Fallback box (Nested KVM)
    node_b = patches.FancyBboxPatch((5.3, 0.5), 4.3, 3.9, boxstyle="round,pad=0.1", ec="#8E44AD", fc="#F4ECF7", lw=1.5)
    ax.add_patch(node_b)
    ax.text(7.45, 4.1, "Compute Node B (Nested KVM Fallback)", fontsize=10, fontweight="bold", ha="center", color="#8E44AD")
    ax.text(7.45, 3.7, "Outer VM: 192.168.100.17 (4 vCPUs, 4 GB RAM)", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 3.25, "Worker B (:8002) via systemd DelegateSubgroup=service", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 2.8, "Bridge Route: 10.77.0.0/24 via 192.168.100.17", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 2.2, "Nested Cloud Hypervisor MicroVMs", fontsize=9, fontweight="bold", ha="center", color="#2C3E50")
    ax.text(7.45, 1.75, "TAP Network: tapvm0..7 (10.77.0.10+)", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 1.35, "Clean Fencing on Worker Return (2.0s - 9.3s)", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 0.95, "Independent /sys/fs/cgroup hierarchy", fontsize=8.5, ha="center", color="#333333")

    # Arrows
    ax.annotate("", xy=(2.6, 2.4), xytext=(2.6, 2.7), arrowprops=dict(arrowstyle="->", color="#168A62", lw=2))
    ax.annotate("", xy=(5.3, 3.0), xytext=(4.7, 3.0), arrowprops=dict(arrowstyle="->", color="#168A62", lw=2))

    path = os.path.join(IMAGES_DIR, "arch_diagram.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

def render_placement_flow():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.8)
    ax.axis("off")

    # Flowchart boxes
    b1 = patches.FancyBboxPatch((0.3, 3.6), 2.2, 0.9, boxstyle="round,pad=0.1", ec="#2980B9", fc="#EBF5FB", lw=1.5)
    ax.add_patch(b1)
    ax.text(1.4, 4.05, "POST /vms\n(RAM, vCPU, target_node)", fontsize=8.5, fontweight="bold", ha="center", va="center")

    b2 = patches.FancyBboxPatch((3.2, 3.6), 2.0, 0.9, boxstyle="round,pad=0.1", ec="#D4AC0D", fc="#FEF9E7", lw=1.5)
    ax.add_patch(b2)
    ax.text(4.2, 4.05, "Target Node\nPinned?", fontsize=8.5, fontweight="bold", ha="center", va="center")

    b_pin_yes = patches.FancyBboxPatch((6.0, 3.6), 3.6, 0.9, boxstyle="round,pad=0.1", ec="#27AE60", fc="#EAFAF1", lw=1.5)
    ax.add_patch(b_pin_yes)
    ax.text(7.8, 4.05, "Validate Pinned Node:\n• Unknown -> 422 Unprocessable\n• Insufficient RAM -> 409 Conflict", fontsize=8, ha="center", va="center")

    b_auto = patches.FancyBboxPatch((3.2, 1.8), 2.0, 1.1, boxstyle="round,pad=0.1", ec="#8E44AD", fc="#F4ECF7", lw=1.5)
    ax.add_patch(b_auto)
    ax.text(4.2, 2.35, "Auto-Schedule:\nEvaluate Heuristics\n(memory_aware, best_fit)", fontsize=8, ha="center", va="center")

    b_fit = patches.FancyBboxPatch((6.0, 1.8), 3.6, 1.1, boxstyle="round,pad=0.1", ec="#168A62", fc="#E8F5E9", lw=1.5)
    ax.add_patch(b_fit)
    ax.text(7.8, 2.35, "Candidate Selection:\n• Fits: Dispatch to Worker API (201)\n• Exceeds all: 409 with candidate reasons\n• Refusal: Fall-through to next node", fontsize=8, ha="center", va="center")

    # Arrows
    ax.annotate("", xy=(3.2, 4.05), xytext=(2.5, 4.05), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))
    ax.annotate("Yes", xy=(6.0, 4.05), xytext=(5.2, 4.05), arrowprops=dict(arrowstyle="->", color="#27AE60", lw=1.5), fontsize=8.5, color="#27AE60", fontweight="bold")
    ax.annotate("No (Auto)", xy=(4.2, 2.9), xytext=(4.2, 3.6), arrowprops=dict(arrowstyle="->", color="#8E44AD", lw=1.5), fontsize=8.5, color="#8E44AD", fontweight="bold")
    ax.annotate("", xy=(6.0, 2.35), xytext=(5.2, 2.35), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))

    path = os.path.join(IMAGES_DIR, "placement_flow.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

def render_failover_seq():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.8)
    ax.axis("off")

    # Sequence stages
    s1 = patches.FancyBboxPatch((0.3, 2.7), 2.8, 1.7, boxstyle="round,pad=0.1", ec="#C0392B", fc="#FDEDEC", lw=1.5)
    ax.add_patch(s1)
    ax.text(1.7, 4.1, "1. Node B Failure Injection", fontsize=9.5, fontweight="bold", ha="center", color="#C0392B")
    ax.text(1.7, 3.5, "Worker process killed / crash\nMisses 3 heartbeats (5s lease)\nDetection: 13.83s – 15.70s", fontsize=8.5, ha="center")
    ax.text(1.7, 2.9, "Node B -> UNHEALTHY", fontsize=8.5, fontweight="bold", ha="center", color="#C0392B")

    s2 = patches.FancyBboxPatch((3.6, 2.7), 2.8, 1.7, boxstyle="round,pad=0.1", ec="#27AE60", fc="#EAFAF1", lw=1.5)
    ax.add_patch(s2)
    ax.text(5.0, 4.1, "2. Cold Auto-Evacuation", fontsize=9.5, fontweight="bold", ha="center", color="#27AE60")
    ax.text(5.0, 3.5, "Auto-evacuate ha=true VMs\nCold-spawned on Node A\nEvac Latency: 0.00s – 0.70s", fontsize=8.5, ha="center")
    ax.text(5.0, 2.9, "Total Recovery: 14.33s – 16.39s", fontsize=8.5, fontweight="bold", ha="center", color="#27AE60")

    s3 = patches.FancyBboxPatch((6.9, 2.7), 2.8, 1.7, boxstyle="round,pad=0.1", ec="#2980B9", fc="#EBF5FB", lw=1.5)
    ax.add_patch(s3)
    ax.text(8.3, 4.1, "3. Split-Brain Fencing", fontsize=9.5, fontweight="bold", ha="center", color="#2980B9")
    ax.text(8.3, 3.5, "Node B returns to HEALTHY\nController detects stale ghost\nWorker executes delete_vm()", fontsize=8.5, ha="center")
    ax.text(8.3, 2.9, "Fenced in 2.0s – 9.33s", fontsize=8.5, fontweight="bold", ha="center", color="#2980B9")

    # Stop escalation breakdown below
    s4 = patches.FancyBboxPatch((0.3, 0.4), 9.4, 1.8, boxstyle="round,pad=0.1", ec="#34495E", fc="#F8F9F9", lw=1.5)
    ax.add_patch(s4)
    ax.text(5.0, 1.85, "Worker 4-Tier Stop Escalation Mechanism (delete_vm / stop_vm)", fontsize=9.5, fontweight="bold", ha="center", color="#34495E")
    ax.text(1.8, 1.25, "Tier 1: ACPI Power Button\nGraceful OS shutdown (<30s)", fontsize=8, ha="center")
    ax.text(4.8, 1.25, "Tier 2: Cloud Hypervisor\nShutdown API (vmm_shutdown)", fontsize=8, ha="center")
    ax.text(8.0, 1.25, "Tier 3 & 4: SIGTERM / SIGKILL\nHost force cleanup + cgroup purge", fontsize=8, ha="center")

    # Arrows
    ax.annotate("", xy=(3.6, 3.55), xytext=(3.1, 3.55), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))
    ax.annotate("", xy=(6.9, 3.55), xytext=(6.4, 3.55), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))

    path = os.path.join(IMAGES_DIR, "failover_seq.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

def render_dfd_diagram():
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    stages = [
        ("Web Browser / Client\n(React SPA / REST)", 0.2, "#EBF5FB", "#2980B9"),
        ("FastAPI Gateway\n(:8000 Bearer Auth)", 2.2, "#E8F5E9", "#27AE60"),
        ("VM Service & Scheduler\n(SQLite WAL DB)", 4.2, "#FEF9E7", "#D4AC0D"),
        ("Remote Worker Daemon\n(:8001 / :8002 Agent)", 6.2, "#F4ECF7", "#8E44AD"),
        ("Cloud Hypervisor\n(/api/v1 Unix Socket)", 8.2, "#FDEDEC", "#C0392B"),
    ]

    for name, x, fc, ec in stages:
        box = patches.FancyBboxPatch((x, 1.8), 1.6, 1.4, boxstyle="round,pad=0.1", ec=ec, fc=fc, lw=1.5)
        ax.add_patch(box)
        ax.text(x + 0.8, 2.5, name, fontsize=8, fontweight="bold", ha="center", va="center")

    # Arrows
    for i in range(len(stages) - 1):
        x1 = stages[i][1] + 1.6
        x2 = stages[i+1][1]
        ax.annotate("", xy=(x2, 2.5), xytext=(x1, 2.5), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))

    # Cgroups callout at bottom
    cg_box = patches.FancyBboxPatch((5.8, 0.4), 4.0, 0.9, boxstyle="round,pad=0.1", ec="#168A62", fc="#E8F8F5", lw=1.2)
    ax.add_patch(cg_box)
    ax.text(7.8, 0.85, "Cgroups v2 Limits (/sys/fs/cgroup/ps023-vmm-*)\nmemory.max (RAM+128MB) | cpu.max (1.25x quota)", fontsize=8, ha="center", va="center")
    ax.annotate("", xy=(7.0, 1.8), xytext=(7.0, 1.3), arrowprops=dict(arrowstyle="->", color="#168A62", lw=1.2))

    path = os.path.join(IMAGES_DIR, "dfd_diagram.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

# ------------------------------------------------------------------------------
# 2. PowerPoint Deck Builder
# ------------------------------------------------------------------------------

def build_presentation():
    prs = Presentation()
    # 16:9 widescreen
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Colors
    c_dark = RGBColor(0x20, 0x25, 0x22)
    c_green = RGBColor(0x16, 0x8A, 0x62)
    c_blue = RGBColor(0x29, 0x80, 0xB9)
    c_gray = RGBColor(0x55, 0x55, 0x55)
    c_red = RGBColor(0xC0, 0x39, 0x2B)
    c_bg_card = RGBColor(0xF8, 0xF9, 0xFA)

    def add_header(slide, title_text, category="PS-023 HACKATHON PRESENTATION"):
        # Category
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.3))
        tf = cat_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category.upper()
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = c_green

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.7), Inches(0.6))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = c_dark

    def add_footnote(slide, footnote_text):
        fn_box = slide.shapes.add_textbox(Inches(0.8), Inches(6.9), Inches(11.7), Inches(0.35))
        tf = fn_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"Source Evidence: {footnote_text}"
        p.font.size = Pt(9)
        p.font.italic = True
        p.font.color.rgb = c_gray

    # --- Slide 1: Title Slide ---
    s1 = prs.slides.add_slide(blank_layout)
    # Background accent card
    card = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9))
    card.fill.solid()
    card.fill.fore_color.rgb = c_bg_card
    card.line.color.rgb = c_green
    card.line.width = Pt(2)

    tb = s1.shapes.add_textbox(Inches(1.2), Inches(1.3), Inches(10.9), Inches(1.2))
    p = tb.text_frame.paragraphs[0]
    p.text = "Minimal Two-Node Cloud Hypervisor VM Controller"
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = c_dark

    tb_sub = s1.shapes.add_textbox(Inches(1.2), Inches(2.6), Inches(10.9), Inches(1.2))
    p = tb_sub.text_frame.paragraphs[0]
    p.text = "Automated HA Failover (14.3s–16.4s Total Recovery, 0.4s–0.7s Cold Evacuation),\nCgroups v2 Isolation & Pluggable Policy Scheduling across Heterogeneous Infrastructure"
    p.font.size = Pt(17)
    p.font.color.rgb = c_green

    tb_meta = s1.shapes.add_textbox(Inches(1.2), Inches(4.5), Inches(10.9), Inches(1.5))
    tf = tb_meta.text_frame
    p1 = tf.paragraphs[0]
    p1.text = "Team: The Mavericks | Institution: PES University"
    p1.font.size = Pt(14)
    p1.font.bold = True
    p1.font.color.rgb = c_dark

    p2 = tf.add_paragraph()
    p2.text = "Presenter: Rajyavardhan | Track: AIORI Hackathon 3 | Date: November 15, 2026"
    p2.font.size = Pt(12)
    p2.font.color.rgb = c_gray

    p3 = tf.add_paragraph()
    p3.text = "Primary Target: Local Direct KVM Node A + Nested KVM Node B (Local Fallback)"
    p3.font.size = Pt(11)
    p3.font.color.rgb = c_blue

    # --- Slide 2: Problem Description ---
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Problem Description: Virtualization Bloat & Failover Gaps")
    tb = s2.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s2 = [
        ("Traditional Hypervisor Bloat", "Legacy QEMU/KVM hypervisors emulate decades of legacy hardware (BIOS, PCI bridges, IDE controllers), resulting in multi-minute cold boot times and heavyweight 500MB+ per-guest memory footprints."),
        ("Noisy Neighbor Contention", "In multi-tenant edge nodes, uncontrolled rogue VM processes can exhaust host RAM and starve CPU CFS quotas, triggering cascading host kernel OOM panics."),
        ("Catastrophic Failures & Split-Brain Risks", "Edge orchestrators often require minutes to detect dropped nodes. When an offline node suddenly recovers, dual-primary split-brain execution risks severe data corruption."),
        ("Rigid Scheduling", "Monolithic cloud schedulers cannot dynamically pivot between density packing (best_fit) and latency-sensitive distribution (memory_aware) across asymmetric hardware.")
    ]
    for title, desc in points_s2:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(14)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = c_gray

    # --- Slide 3: Background & Solution Goals ---
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Background & Engineering Objectives")
    tb = s3.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s3 = [
        ("Lightweight Rust Virtualization", "Adopt Cloud Hypervisor focusing exclusively on virtio modern paravirtual devices and direct uncompressed kernel boot (vmlinux.bin) with minimal memory overhead."),
        ("Deterministic High Availability", "Replace manual failure intervention with automated heartbeat monitoring (5s leases) and sub-second cold evacuation on surviving nodes (0.00s–0.70s cold evacuation, 14.3s–16.4s total recovery)."),
        ("Defensive Isolation via Cgroups v2", "Enforce strict single-hierarchy cgroup v2 slices per microVM (memory.max = RAM + 128MB overhead, cpu.max = 1.25x quota, pids.max = 256)."),
        ("Stateful Zero-Orphan Reconciler", "Design a decoupled controller reconciliation loop in SQLite WAL mode that tolerates abrupt controller service restarts without killing or duplicating active guests.")
    ]
    for title, desc in points_s3:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(14)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = c_gray

    # --- Slide 4: Prior Art & Standards ---
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Literature & RFC Review: Foundations of PS-023")
    tb = s4.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s4 = [
        ("Linux Cgroups v2 Unified Hierarchy (Kernel Docs)", "Eliminates multi-hierarchy synchronization deadlocks present in cgroups v1. Provides single-tree controller delegation (DelegateSubgroup=service) for non-disruptive daemon restarts."),
        ("Rust-vmm / Cloud Hypervisor Project", "High-performance, memory-safe Virtual Machine Monitor written in Rust. Replaces legacy PCI buses with virtio-mmio / modern virtio-pci devices, reducing hypervisor initialization to sub-500ms."),
        ("RFC 793 / TCP & WireGuard Overlay (Donenfeld, 2017)", "Kernel-space ChaCha20-Poly1305 encrypted tunneling for secure multi-node communication across untrusted public clouds."),
        ("Distributed Quorum & Fencing Mechanisms", "Asynchronous tombstone tracking and active process fencing ensuring recovered nodes purge duplicate primary execution units.")
    ]
    for title, desc in points_s4:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(14)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = c_gray

    # --- Slide 5: Solution Architecture Diagram ---
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "System Architecture: Heterogeneous Two-Node Cluster")
    arch_img = render_arch_diagram()
    s5.shapes.add_picture(arch_img, Inches(1.2), Inches(1.4), width=Inches(10.9))
    add_footnote(s5, "docs/architecture.md, scripts/bring-up.sh, docs/nested_node_b_setup.md")

    # --- Slide 6: MicroVM Placement Flow ---
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Pluggable Scheduling & Placement Logic")
    place_img = render_placement_flow()
    s6.shapes.add_picture(place_img, Inches(1.2), Inches(1.5), width=Inches(10.9))
    add_footnote(s6, "evidence/placement_cases_20261115.txt:L11-L62, controller/scheduler.py")

    # --- Slide 7: Failover & Stop Escalation Sequence ---
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "High Availability Failover & Stop Escalation Sequence")
    failover_img = render_failover_seq()
    s7.shapes.add_picture(failover_img, Inches(1.2), Inches(1.5), width=Inches(10.9))
    add_footnote(s7, "evidence/chaos_fallback_repeats_20261115.txt:L189-L194, worker/vm_service.py")

    # --- Slide 8: Data Flow Diagram (DFD) ---
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Data Flow Architecture: Control Plane to Rust VMM")
    dfd_img = render_dfd_diagram()
    s8.shapes.add_picture(dfd_img, Inches(1.2), Inches(1.6), width=Inches(10.9))
    add_footnote(s8, "docs/architecture.md (Section 3), controller/main.py, worker/main.py")

    # --- Slide 9: Optimization & Measured Performance Table ---
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Empirical Performance Comparison: Baseline vs PS-023")

    # Add Table
    rows = 7
    cols = 4
    left = Inches(0.8)
    top = Inches(1.5)
    width = Inches(11.7)
    height = Inches(4.8)
    table_shape = s9.shapes.add_table(rows, cols, left, top, width, height)
    table = table_shape.table
    table.columns[0].width = Inches(2.6)
    table.columns[1].width = Inches(2.6)
    table.columns[2].width = Inches(3.7)
    table.columns[3].width = Inches(2.8)

    headers = ["Capability / Metric", "Traditional Orchestrator", "PS-023 Platform (Measured)", "Evidence Footnote"]
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_green
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    data = [
        ("VMM Memory Overhead", "256 MB – 1024 MB", "128 MB fixed overhead (cgroups enforced)", "cgroups_memory_stress_20261114.txt:L10-L12"),
        ("Kernel Boot Duration", "2.5 s – 8.0 s", "327 ms – 474 ms (Node A direct KVM)", "boot_node_a_bimodality_20261114.txt:L33-L46, L59"),
        ("API Create -> Running", "5.0 s – 15.0 s", "0.772 s – 0.997 s (Min: 0.751 s in 20-run set)", "boot_node_a_bimodality_20261114.txt:L13-L27"),
        ("Node A Full Boot (SSH)", "15.0 s – 60.0 s", "6.846 s – 11.257 s (median 8.460 s, 20-run set)", "boot_node_a_contention_20261114.txt:L45-L48"),
        ("Total Failover Recovery", "45 s – 180 s", "14.33 s – 16.39 s (fallback, 6 runs)\n15.35 s – 21.05 s (Azure historical, 6 runs)", "chaos_fallback_repeats_20261115.txt:L189-L194\nchaos_azure_repeats_20261114.txt:L402-L407"),
        ("Cold Evacuation Latency", "10 s – 45 s", "0.00 s – 0.70 s (sub-second cold placement)", "chaos_fallback_repeats_20261115.txt:L189-L194"),
    ]

    for i, row_data in enumerate(data):
        for j, val in enumerate(row_data):
            cell = table.cell(i + 1, j)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10)
                if j == 2:
                    p.font.bold = True
                    p.font.color.rgb = c_green

    add_footnote(s9, "Comprehensive Evidence Index: docs/EVIDENCE_INDEX.md")

    # --- Slide 10: Boot Performance Breakdown ---
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Boot Latency Breakdown: Kernel Init vs In-Guest Userspace")
    tb = s10.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s10 = [
        ("Invariant Kernel Initialization (327 ms – 474 ms)", "Cloud Hypervisor direct uncompressed kernel boot (vmlinux.bin) is remarkably consistent across all measured runs, taking less than half a second to complete."),
        ("Direct KVM Guest SSH Readiness (6.846 s – 11.257 s)", "Across the 20-run contention benchmark set (boot_node_a_contention_20261114.txt:L45-L48), median boot from API creation to accepting SSH connections is 8.460 s (Min: 6.846 s, Max: 11.257 s)."),
        ("Nested KVM Guest SSH Readiness (11.775 s – 19.027 s)", "On nested Node B (boot_test_fallback_20261114.txt:L46-L50), full boot to SSH ready spans 11.775 s – 19.027 s with a median of 13.130 s (due to nested virtualization overhead)."),
        ("Diagnostic Variance & Telemetry (7.058 s – 16.398 s)", "In an earlier 15-run diagnostic set (boot_node_a_bimodality_20261114.txt:L49-L55), outlier runs took up to 16.398 s (median 8.372 s). In-guest delay during pollinate.service (up to 6.5s) attempting to fetch entropy from entropy.ubuntu.com over bridge NAT was observed in 1 of 5 instrumented runs; cause not established; the host-contention test did not show an effect.")
    ]
    for title, desc in points_s10:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13.5)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11.5)
        p_d.font.color.rgb = c_gray
    add_footnote(s10, "evidence/boot_node_a_contention_20261114.txt, evidence/boot_node_a_bimodality_20261114.txt")

    # --- Slide 11: Failover Chaos Benchmark Details ---
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "High-Availability Failover & Split-Brain Fencing Results")

    # Add Table for Failover
    rows = 8
    cols = 5
    table_shape = s11.shapes.add_table(rows, cols, Inches(0.8), Inches(1.5), Inches(11.7), Inches(4.8))
    table = table_shape.table
    table.columns[0].width = Inches(1.6)
    table.columns[1].width = Inches(2.6)
    table.columns[2].width = Inches(2.5)
    table.columns[3].width = Inches(2.5)
    table.columns[4].width = Inches(2.5)

    headers_f = ["Environment", "Failure Mode", "Detection Delay", "Cold Evacuation", "Total Recovery"]
    for j, h in enumerate(headers_f):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_blue
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(11)
            p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    data_f = [
        ("Fallback Run 1", "worker crash", "14.61 s", "0.51 s", "15.12 s (Clean fencing)"),
        ("Fallback Run 2", "worker crash", "14.79 s", "0.51 s", "15.30 s (Clean fencing)"),
        ("Fallback Run 3", "worker crash", "14.20 s", "0.51 s", "14.71 s (Clean fencing)"),
        ("Fallback Run 4", "worker-preserve-vms", "13.83 s", "0.51 s", "14.33 s (Fenced in 2.0s)"),
        ("Fallback Run 5", "worker-preserve-vms", "14.74 s", "0.00 s (sync tick)", "14.74 s (Fenced in 6.75s)"),
        ("Fallback Run 6", "worker-preserve-vms", "15.70 s", "0.70 s", "16.39 s (Fenced in 9.33s*)"),
        ("Azure Historical", "SSH tunnel (6 runs)", "15.32 s – 19.99 s", "0.35 s – 0.36 s", "15.35 s – 21.05 s (All RUNNING)"),
    ]
    for i, row_data in enumerate(data_f):
        for j, val in enumerate(row_data):
            cell = table.cell(i + 1, j)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(10)
                if j == 4:
                    p.font.bold = True
                    p.font.color.rgb = c_green

    add_footnote(s11, "evidence/chaos_fallback_repeats_20261115.txt:L189-L194; *Run 6 split between wait and shutdown was not instrumented")

    # --- Slide 12: Controller Reliability & Placement Cases ---
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Controller Reliability & Placement Edge Cases")
    tb = s12.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s12 = [
        ("Zero-Orphan Controller Restart (2.06 s)", "When the controller service process is abruptly killed and restarted (taking 2.06 s), the reconciliation loop polls both worker daemons and synchronizes state: 2/2 pre-restart VMs preserved in RUNNING status with 0 duplicates and 0 orphans."),
        ("Insufficient Capacity Refusal (HTTP 409)", "When VM resource requests exceed available cluster schedulable memory (e.g. 4096 MB request against 2045 MB and 2549 MB nodes), the controller returns HTTP 409 with structured per-node candidate rejection reasons."),
        ("Unknown Target Node Pinning (HTTP 422)", "Invalid target node identifiers (e.g. nonexistent-node-xyz) are rejected immediately with HTTP 422 Unprocessable Entity."),
        ("Dynamic Capacity Fall-Through", "Unpinned requests that exceed Node A's schedulable RAM (e.g. 2301 MB requested when Node A has 2045 MB) automatically bypass Node A and fall through to Node B (2549 MB available), returning 201 Created.")
    ]
    for title, desc in points_s12:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13.5)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11.5)
        p_d.font.color.rgb = c_gray
    add_footnote(s12, "evidence/controller_restart_20261115.txt:L20-L32, evidence/placement_cases_20261115.txt:L11-L62")

    # --- Slide 13: Cgroups v2 Host Defense ---
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Cgroups v2 Resource Guarantees & Host Containment")
    tb = s13.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s13 = [
        ("Defense-in-Depth Cgroup Limits", "Every microVM is bound to a dedicated cgroup v2 slice (/sys/fs/cgroup/ps023-vmm-<vm_id>) with hard limits: memory.max = VM_RAM + 128MB overhead, cpu.max = vCPU CFS quota with 1.25x burst headroom, pids.max = 256."),
        ("In-Guest OOM Containment Verification", "In live stress tests (cgroups_memory_stress_20261114.txt:L10-L71), progressive memory allocation inside the guest triggered the IN-GUEST Linux kernel's internal OOM killer (sshd invoked oom-killer -> killed python3 pid 2081)."),
        ("Zero Host-Level OOM Kills (oom_kill = 0)", "Because guest memory exhausted itself internally before host limits were exceeded, the host cgroup ceiling (640MB) was not breached (oom_kill = 0). The Cloud Hypervisor VMM process (PID 19235) remained alive, healthy, and isolated."),
        ("systemd DelegateSubgroup=service Compliant", "Worker services run with DelegateSubgroup=service, ensuring worker daemon restarts do not disrupt active microVM cgroup leaves.")
    ]
    for title, desc in points_s13:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13.5)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11.5)
        p_d.font.color.rgb = c_gray
    add_footnote(s13, "evidence/cgroups_memory_stress_20261114.txt:L10-L71, worker/cgroup_manager.py")

    # --- Slide 14: Known Limitations Slide ---
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Architectural Limitations & Engineering Scope", "TRANSPARENCY & BOUNDARIES")
    tb = s14.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s14 = [
        ("Plain HTTP & Static Bearer Tokens", "Controller-worker communication uses plain HTTP authenticated via static bearer tokens. There is no application-layer mTLS; transport security in cloud mode is delegated to WireGuard or SSH tunnels."),
        ("Single Boot-Tested OS (Ubuntu 24.04 LTS)", "Only the Ubuntu 24.04 LTS cloud image (noble-server-cloudimg-amd64.raw) has been boot-tested. Debian 12, Alpine 3.20, and CirrOS catalog entries have verified checksums but are marked 'not boot-tested'."),
        ("Local Fallback Shared Hardware", "In the primary demonstration mode, Node B is a nested Cloud Hypervisor VM on the same physical host (Intel Core i7-12700H) sharing CPU, RAM, and disk bandwidth."),
        ("Cold Evacuation vs Live Migration", "HA failover is deterministic cold failover (stateful metadata reschedule + fresh boot from clean disk). In-flight RAM and active TCP sockets are not preserved."),
        ("Uninstrumented Block I/O (io.max)", "CPU quota and memory.max boundaries are verified; block device I/O throttling (io.max) is not currently implemented in the worker agent."),
        ("WireGuard Scope", "Verified on a dedicated mobile hotspot only (rtt avg 154.5–189.8 ms); blocked by local hostel Wi-Fi UDP 51820 filtering; bandwidth was not measured.")
    ]
    for title, desc in points_s14:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13)
        p_t.font.color.rgb = c_red
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s14, "docs/limitations.md (Sections 1 through 6)")

    # --- Slide 15: Milestones & Implementation Timeline ---
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "Project Milestones & Implementation Progression")
    tb = s15.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s15 = [
        ("Phase 1: Hypervisor Core & Network Plumbing (Late Oct 2026)", "Cloud Hypervisor REST API integration, direct kernel boot pipeline, TAP device bridging, cloud-init automated provisioning, and SQLite WAL database schema."),
        ("Phase 2: Pluggable Scheduling & Cgroups v2 Hardening (Early Nov 2026)", "Implementation of memory_aware, best_fit, and first_fit algorithms; cgroups v2 memory.max (RAM+128MB), cpu.max, and systemd DelegateSubgroup=service isolation."),
        ("Phase 3: High Availability, Failover & Split-Brain Fencing (12–14 Nov 2026)", "Heartbeat lease monitor, auto-evacuation engine, tombstone tracking, and Azure hybrid cloud integration over WireGuard and SSH-tunnel."),
        ("Phase 4: Fallback Hardening, Rehearsal Automation & Audit (15 Nov 2026)", "6-run fallback chaos repeat suite, 3 automated end-to-end rehearsal passes (86s–91s duration), pre-flight sanity automation, and full evidence audit.")
    ]
    for title, desc in points_s15:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13.5)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11.5)
        p_d.font.color.rgb = c_gray
    add_footnote(s15, "docs/ppt_outline.md (Slide 9)")

    # --- Slide 16: Summary & Conclusion ---
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "Conclusion: Deliverables & Architectural Verdict")
    tb = s16.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.0))
    tf = tb.text_frame
    tf.word_wrap = True

    points_s16 = [
        ("Sub-Second Cold Evacuation on Surviving Node", "Surviving node schedules and cold-boots an evacuated guest in 0.00 s – 0.70 s (total failover recovery 14.33 s – 16.39 s on fallback; 15.35 s – 21.05 s on Azure historical)."),
        ("Defensive Isolation without Cascading Failure", "Cgroups v2 boundaries protect physical host stability: in-guest OOM kills rogue processes without breaching host ceilings or affecting neighboring guests."),
        ("Zero-Orphan Control Plane Reliability", "Controller restarts take 2.06 s with 100% preservation of in-flight virtual machines and 0 orphaned hypervisor processes."),
        ("Empirically Verified & Rehearsed", "182 automated unit tests passed (0 failures), 12 frontend UI tests passed, and 3 consecutive automated API rehearsals completed without error.")
    ]
    for title, desc in points_s16:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(14)
        p_t.font.color.rgb = c_green
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(12)
        p_d.font.color.rgb = c_dark
    add_footnote(s16, "docs/EVIDENCE_INDEX.md, docs/demo_day_checklist.md")

    # --- Slide 17: Appendix - Jury Defense Q&A (Part 1) ---
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "Appendix: Jury Defense Cheat Sheet (Part 1)", "APPENDIX")
    tb = s17.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.2))
    tf = tb.text_frame
    tf.word_wrap = True

    qa_p1 = [
        ("Q1: How fast is cold boot really, and why does it vary from 7s to 16s?",
         "Cloud Hypervisor kernel initialization is invariantly fast at 327–474 ms. Guest boot to SSH ready on direct KVM spans 6.846 s – 11.257 s across the 20-run contention set (median 8.460 s). An earlier 15-run diagnostic set reached up to 16.398 s (median 8.372 s). Regarding causes: in-guest delay during pollinate.service was observed in 1 of 5 instrumented runs; cause not established; the host-contention test did not show an effect.",
         "boot_node_a_contention_20261114.txt:L45-L48, boot_node_a_bimodality_20261114.txt:L10-L65"),
        ("Q2: What happens if a failed node comes back online while its VM was evacuated elsewhere?",
         "Total failover recovery takes 14.33 s – 16.39 s (fallback; detection is 13.83s–15.70s; cold evacuation is 0.00s–0.70s). In run 5, cold evacuation recorded 0.00s because failure detection and evacuation placement occurred synchronously in the same controller tick (<0.005s). When Node B returns, stale VMMs are fenced in 2.0s to 9.33s (in run 6, fencing took 9.33s; the split between wait and shutdown was not instrumented).",
         "chaos_fallback_repeats_20261115.txt:L187-L194")
    ]
    for q, a, src in qa_p1:
        p_q = tf.add_paragraph()
        p_q.text = f"{q}"
        p_q.font.bold = True
        p_q.font.size = Pt(13)
        p_q.font.color.rgb = c_dark
        p_a = tf.add_paragraph()
        p_a.text = f"Answer: {a}"
        p_a.font.size = Pt(11)
        p_a.font.color.rgb = c_gray
        p_s = tf.add_paragraph()
        p_s.text = f"Source: {src}\n"
        p_s.font.size = Pt(9.5)
        p_s.font.italic = True
        p_s.font.color.rgb = c_blue

    # --- Slide 18: Appendix - Jury Defense Q&A (Part 2) ---
    s18 = prs.slides.add_slide(blank_layout)
    add_header(s18, "Appendix: Jury Defense Cheat Sheet (Part 2)", "APPENDIX")
    tb = s18.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.2))
    tf = tb.text_frame
    tf.word_wrap = True

    qa_p2 = [
        ("Q3: If the controller crashes, do running MicroVMs get killed?",
         "No. Worker daemons and Cloud Hypervisor processes operate independently of the controller. When the controller restarts (taking 2.06 s), the reconciliation loop discovers existing running VMs via /vms on each worker, re-syncs state with 0 orphans and 0 duplicates.",
         "controller_restart_20261115.txt:L20-L32"),
        ("Q4: How do you prevent a runaway VM from taking down the host?",
         "Each MicroVM is placed in a cgroup v2 slice with hard memory.max (VM_RAM + 128MB), cpu.max (vCPU CFS quota with 1.25x headroom), and pids.max (256). Stress tests confirm the in-guest kernel OOM-killer terminates the over-allocating process inside the guest before the host cgroup limit (640MB) is breached. The VMM process remains alive and unharmed, and host memory is strictly protected.",
         "cgroups_memory_stress_20261114.txt:L10-L12, L40-L71"),
        ("Q5: Why is local fallback used instead of Azure for today's presentation?",
         "Azure hybrid mode was benchmarked on 13–14 Nov over WireGuard and SSH tunnel. However, local venue hostel Wi-Fi enforces strict UDP firewall filters that block WireGuard (UDP 51820). The local fallback architecture provides identical KVM isolation and subnet routing reliably without external network dependencies.",
         "wireguard_hotspot_20261114.txt:L9-L15, L75-L80, chaos_azure_repeats_20261114.txt:L398-L410")
    ]
    for q, a, src in qa_p2:
        p_q = tf.add_paragraph()
        p_q.text = f"{q}"
        p_q.font.bold = True
        p_q.font.size = Pt(12.5)
        p_q.font.color.rgb = c_dark
        p_a = tf.add_paragraph()
        p_a.text = f"Answer: {a}"
        p_a.font.size = Pt(10.5)
        p_a.font.color.rgb = c_gray
        p_s = tf.add_paragraph()
        p_s.text = f"Source: {src}\n"
        p_s.font.size = Pt(9)
        p_s.font.italic = True
        p_s.font.color.rgb = c_blue

    prs.save(PPTX_PATH)
    print(f"Presentation saved to: {PPTX_PATH}")
    return len(prs.slides)

if __name__ == "__main__":
    count = build_presentation()
    print(f"Total Slides Generated: {count}")
