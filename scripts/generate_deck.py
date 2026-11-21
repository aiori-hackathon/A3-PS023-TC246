#!/usr/bin/env python3
"""
PS-023: Presentation Deck Generator (12-Slide Hackathon Edition)
Builds an audited 16:9 PowerPoint deck into docs/deck/ps023_draft.pptx using python-pptx.
Renders diagrams with matplotlib and converts slides to PDF and PNGs.
Every number is audited directly against evidence/ and source code.
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
PPTX_DRAFT_PATH = os.path.join(OUTPUT_DIR, "ps023_draft.pptx")
PPTX_FINAL_PATH = os.path.join(OUTPUT_DIR, "ps023_final.pptx")
PDF_FINAL_PATH = os.path.join(OUTPUT_DIR, "ps023_final.pdf")
PDF_DRAFT_PATH = os.path.join(OUTPUT_DIR, "ps023_draft.pdf")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(SLIDES_DIR, exist_ok=True)

# ------------------------------------------------------------------------------
# 1. Matplotlib Diagram Renderers
# ------------------------------------------------------------------------------

def render_arch_diagram():
    fig, ax = plt.subplots(figsize=(10, 5.0), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.0)
    ax.axis("off")

    # Host boundary
    host_rect = patches.FancyBboxPatch((0.2, 0.2), 9.6, 4.6, boxstyle="round,pad=0.15", ec="#202522", fc="#F8F9FA", lw=2)
    ax.add_patch(host_rect)
    ax.text(0.5, 4.5, "Physical Host: AMD Ryzen 7 7445HS (12 vCPUs, 15 GB RAM, Fedora Linux)", fontsize=11, fontweight="bold", color="#202522")

    # Controller box
    ctrl_box = patches.FancyBboxPatch((0.5, 2.5), 4.2, 1.8, boxstyle="round,pad=0.1", ec="#168A62", fc="#E8F5E9", lw=1.5)
    ax.add_patch(ctrl_box)
    ax.text(2.6, 4.0, "PS-023 Controller (:8000)", fontsize=10, fontweight="bold", ha="center", color="#168A62")
    ax.text(2.6, 3.55, "FastAPI / Uvicorn (WAL SQLite DB)", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 3.15, "Heartbeat Lease Monitor (5s tick) + Reconciler", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 2.75, "Pluggable Scheduler (memory_aware, best_fit)", fontsize=8.5, ha="center", color="#333333")

    # Node A box (Direct KVM)
    node_a = patches.FancyBboxPatch((0.5, 0.4), 4.2, 1.8, boxstyle="round,pad=0.1", ec="#2980B9", fc="#EBF5FB", lw=1.5)
    ax.add_patch(node_a)
    ax.text(2.6, 1.9, "Compute Node A (Direct KVM Host)", fontsize=10, fontweight="bold", ha="center", color="#2980B9")
    ax.text(2.6, 1.5, "Worker A (:8001) | Subnet 192.168.100.0/24", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 1.1, "Direct Kernel Boot (Cloud Hypervisor /api/v1)", fontsize=8.5, ha="center", color="#333333")
    ax.text(2.6, 0.7, "Cgroups v2 Limits (/sys/fs/cgroup/ps023-vmm-*)", fontsize=8.5, ha="center", color="#333333")

    # Node B Fallback box (Nested KVM)
    node_b = patches.FancyBboxPatch((5.3, 0.4), 4.3, 3.9, boxstyle="round,pad=0.1", ec="#8E44AD", fc="#F4ECF7", lw=1.5)
    ax.add_patch(node_b)
    ax.text(7.45, 4.0, "Compute Node B (Nested KVM Fallback)", fontsize=10, fontweight="bold", ha="center", color="#8E44AD")
    ax.text(7.45, 3.55, "Outer VM: 192.168.100.17 (4 vCPUs, 4 GB RAM)", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 3.1, "Worker B (:8002) via DelegateSubgroup=service", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 2.65, "Bridge Route: 10.77.0.0/24 via 192.168.100.17", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 2.05, "Nested Cloud Hypervisor MicroVMs", fontsize=9, fontweight="bold", ha="center", color="#2C3E50")
    ax.text(7.45, 1.6, "TAP Network: tapvm0..7 (10.77.0.10+)", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 1.15, "Tombstone Fencing on Return (2.0s - 9.3s)", fontsize=8.5, ha="center", color="#333333")
    ax.text(7.45, 0.7, "Independent /sys/fs/cgroup hierarchy", fontsize=8.5, ha="center", color="#333333")

    # Arrows
    ax.annotate("", xy=(2.6, 2.2), xytext=(2.6, 2.5), arrowprops=dict(arrowstyle="->", color="#168A62", lw=2))
    ax.annotate("", xy=(5.3, 2.8), xytext=(4.7, 2.8), arrowprops=dict(arrowstyle="->", color="#168A62", lw=2))

    path = os.path.join(IMAGES_DIR, "arch_diagram.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

def render_placement_flow():
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    # Flowchart boxes
    b1 = patches.FancyBboxPatch((0.3, 3.4), 2.2, 0.9, boxstyle="round,pad=0.1", ec="#2980B9", fc="#EBF5FB", lw=1.5)
    ax.add_patch(b1)
    ax.text(1.4, 3.85, "POST /vms\n(RAM, vCPU, target_node)", fontsize=8.5, fontweight="bold", ha="center", va="center")

    b2 = patches.FancyBboxPatch((3.2, 3.4), 2.0, 0.9, boxstyle="round,pad=0.1", ec="#D4AC0D", fc="#FEF9E7", lw=1.5)
    ax.add_patch(b2)
    ax.text(4.2, 3.85, "Target Node\nPinned?", fontsize=8.5, fontweight="bold", ha="center", va="center")

    b_pin_yes = patches.FancyBboxPatch((6.0, 3.4), 3.6, 0.9, boxstyle="round,pad=0.1", ec="#27AE60", fc="#EAFAF1", lw=1.5)
    ax.add_patch(b_pin_yes)
    ax.text(7.8, 3.85, "Validate Pinned Node:\n• Unknown -> 422 Unprocessable\n• Insufficient RAM -> 409 Conflict", fontsize=8, ha="center", va="center")

    b_auto = patches.FancyBboxPatch((3.2, 1.6), 2.0, 1.1, boxstyle="round,pad=0.1", ec="#8E44AD", fc="#F4ECF7", lw=1.5)
    ax.add_patch(b_auto)
    ax.text(4.2, 2.15, "Auto-Schedule:\nEvaluate Heuristics\n(memory_aware, best_fit)", fontsize=8, ha="center", va="center")

    b_fit = patches.FancyBboxPatch((6.0, 1.6), 3.6, 1.1, boxstyle="round,pad=0.1", ec="#168A62", fc="#E8F5E9", lw=1.5)
    ax.add_patch(b_fit)
    ax.text(7.8, 2.15, "Candidate Selection:\n• Fits: Dispatch to Worker API (201)\n• Exceeds all: 409 with candidate reasons\n• Refusal: Fall-through to next node", fontsize=8, ha="center", va="center")

    # Arrows
    ax.annotate("", xy=(3.2, 3.85), xytext=(2.5, 3.85), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))
    ax.annotate("Yes", xy=(6.0, 3.85), xytext=(5.2, 3.85), arrowprops=dict(arrowstyle="->", color="#27AE60", lw=1.5), fontsize=8.5, color="#27AE60", fontweight="bold")
    ax.annotate("No (Auto)", xy=(4.2, 2.7), xytext=(4.2, 3.4), arrowprops=dict(arrowstyle="->", color="#8E44AD", lw=1.5), fontsize=8.5, color="#8E44AD", fontweight="bold")
    ax.annotate("", xy=(6.0, 2.15), xytext=(5.2, 2.15), arrowprops=dict(arrowstyle="->", color="#333", lw=1.5))

    path = os.path.join(IMAGES_DIR, "placement_flow.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

def render_stop_escalation_diagram():
    fig, ax = plt.subplots(figsize=(10, 3.8), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.8)
    ax.axis("off")

    t1 = patches.FancyBboxPatch((0.3, 1.0), 2.8, 2.2, boxstyle="round,pad=0.12", ec="#27AE60", fc="#EAFAF1", lw=1.5)
    ax.add_patch(t1)
    ax.text(1.7, 2.8, "Tier 1: ACPI Power Button", fontsize=9.5, fontweight="bold", ha="center", color="#27AE60")
    ax.text(1.7, 2.1, "ch.power_button()\nSignals in-guest ACPI daemon\nGraceful shutdown wait\n(30s stop / 10s delete)", fontsize=8, ha="center")
    ax.text(1.7, 1.3, "Exit clean -> Return 'graceful'", fontsize=8, fontweight="bold", ha="center", color="#27AE60")

    t2 = patches.FancyBboxPatch((3.6, 1.0), 2.8, 2.2, boxstyle="round,pad=0.12", ec="#D4AC0D", fc="#FEF9E7", lw=1.5)
    ax.add_patch(t2)
    ax.text(5.0, 2.8, "Tier 2: Cloud Hypervisor API", fontsize=9.5, fontweight="bold", ha="center", color="#B7950B")
    ax.text(5.0, 2.1, "ch.shutdown() +\nch.vmm_shutdown()\nDirect VMM socket API\nWait up to 5s for exit", fontsize=8, ha="center")
    ax.text(5.0, 1.3, "Exit clean -> Return 'forced-api'", fontsize=8, fontweight="bold", ha="center", color="#B7950B")

    t3 = patches.FancyBboxPatch((6.9, 1.0), 2.8, 2.2, boxstyle="round,pad=0.12", ec="#C0392B", fc="#FDEDEC", lw=1.5)
    ax.add_patch(t3)
    ax.text(8.3, 2.8, "Tier 3: Hard Kill Escalation", fontsize=9.5, fontweight="bold", ha="center", color="#C0392B")
    ax.text(8.3, 2.1, "SIGTERM -> wait 2.0s\nSIGKILL if process lingers\nPurge cgroup slice\nClean socket / meta files", fontsize=8, ha="center")
    ax.text(8.3, 1.3, "Purged -> Return 'killed-hard'", fontsize=8, fontweight="bold", ha="center", color="#C0392B")

    ax.annotate("Timeout", xy=(3.6, 2.1), xytext=(3.1, 2.1), arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.5), fontsize=8, color="#C0392B", fontweight="bold")
    ax.annotate("Timeout", xy=(6.9, 2.1), xytext=(6.4, 2.1), arrowprops=dict(arrowstyle="->", color="#C0392B", lw=1.5), fontsize=8, color="#C0392B", fontweight="bold")

    path = os.path.join(IMAGES_DIR, "stop_escalation.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path

# ------------------------------------------------------------------------------
# 2. PowerPoint Deck Builder (12 Slides)
# ------------------------------------------------------------------------------

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Theme Colors
    c_dark = RGBColor(0x20, 0x25, 0x22)
    c_green = RGBColor(0x16, 0x8A, 0x62)
    c_blue = RGBColor(0x29, 0x80, 0xB9)
    c_gray = RGBColor(0x55, 0x55, 0x55)
    c_red = RGBColor(0xC0, 0x39, 0x2B)
    c_bg_card = RGBColor(0xF8, 0xF9, 0xFA)

    def add_header(slide, title_text, category="PS-023 HACKATHON DEFENSE"):
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.3))
        tf = cat_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category.upper()
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = c_green

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.65), Inches(11.7), Inches(0.6))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(21)
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

    # ==========================================================================
    # Slide 1: Title Slide
    # ==========================================================================
    s1 = prs.slides.add_slide(blank_layout)
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
    p.text = "Automated HA Failover (Live: Total Recovery 14.19s, Detection 13.18s, Cold Evacuation 1.01s; figures from different observation points and do not sum; Fallback repeats 14.33s–16.39s),\nCgroups v2 Defensive Isolation (128MB Overhead, 256 PIDs) & Pluggable Policy Scheduling"
    p.font.size = Pt(15.5)
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
    p3.text = "Primary Target: Local Direct KVM Node A + Nested KVM Node B (Local Fallback Stack)"
    p3.font.size = Pt(11)
    p3.font.color.rgb = c_blue

    # ==========================================================================
    # Slide 2: Problem & Engineering Goals
    # ==========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Problem Statement & Project Engineering Goals")
    tb = s2.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf = tb.text_frame
    tf.word_wrap = True

    pts_s2 = [
        ("The Challenge: Virtualization Bloat & Cascading Faults",
         "Traditional hypervisors (QEMU/KVM) emulate legacy hardware (BIOS, PCI bridges), driving multi-minute boot cycles and >500MB memory overheads. In multi-tenant edge nodes, unconstrained rogue VMs trigger host kernel OOM panics, while dropped nodes risk split-brain dual-primary corruption on recovery."),
        ("Goal 1: Direct Kernel Boot & Lightweight Paravirtualization",
         "Leverage Rust-based Cloud Hypervisor with modern virtio devices and direct uncompressed kernel boot (vmlinux.bin), eliminating BIOS overhead and booting to userspace in seconds (direct kernel init: 327–474 ms)."),
        ("Goal 2: Deterministic HA Failover Leading with Total Recovery",
         "Implement autonomous heartbeat lease monitoring (5s ticks) and cold evacuation on surviving nodes: achieving 14.19s live total recovery (detection: 13.18s; cold evacuation: 1.01s; note: the three figures come from different observation points and do not sum) and 14.33s–16.39s across fallback repeats."),
        ("Goal 3: Defense-in-Depth Cgroups v2 Isolation",
         "Enforce strict single-hierarchy cgroup v2 slices per microVM (memory.max = RAM + 128MB overhead, cpu.max = 1.25x CFS quota, pids.max = 256), ensuring in-guest OOM kills never impact the physical host."),
        ("Goal 4: Pluggable Scheduling & Zero-Orphan Reconciler",
         "Provide heuristic placement (memory_aware, best_fit) and an idempotent control plane in SQLite WAL mode that survives abrupt controller restarts without killing active guests.")
    ]
    for title, desc in pts_s2:
        p_t = tf.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13)
        p_t.font.color.rgb = c_dark
        p_d = tf.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s2, "docs/architecture.md, worker/cgroup_manager.py:L21-L25")

    # ==========================================================================
    # Slide 3: Architecture
    # ==========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "System Architecture: Heterogeneous Two-Node Cluster")
    arch_img = render_arch_diagram()
    s3.shapes.add_picture(arch_img, Inches(1.5), Inches(1.35), width=Inches(10.3))
    add_footnote(s3, "docs/architecture.md, scripts/bring-up.sh, docs/nested_node_b_setup.md")

    # ==========================================================================
    # Slide 4: Placement & Scheduling
    # ==========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Pluggable Scheduling & Placement Logic")
    place_img = render_placement_flow()
    s4.shapes.add_picture(place_img, Inches(1.2), Inches(1.5), width=Inches(10.9))
    add_footnote(s4, "evidence/placement_cases_20261115.txt:L11-L62, controller/scheduler.py")

    # ==========================================================================
    # Slide 5: Progressive Stop Escalation
    # ==========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Worker 3-Tier Progressive Stop Escalation Mechanism")
    stop_img = render_stop_escalation_diagram()
    s5.shapes.add_picture(stop_img, Inches(1.2), Inches(1.4), width=Inches(10.9))

    tb_s5 = s5.shapes.add_textbox(Inches(0.8), Inches(4.7), Inches(11.7), Inches(2.0))
    tf_s5 = tb_s5.text_frame
    tf_s5.word_wrap = True
    pts_s5 = [
        ("Deterministic Shutdown Flow", "worker/vm_manager.py:L289-L323 implements progressive escalation: Tier 1 ACPI power button (wait up to 30s for stop, 10s for delete) -> Tier 2 Cloud Hypervisor VMM shutdown API (wait up to 5s) -> Tier 3 host SIGTERM/SIGKILL hard force kill."),
        ("Clean Resource Cleanup", "Every tier guarantees that lingering cgroup v2 directory entries, TAP network interfaces, and Unix domain sockets are unlinked before returning control to the caller.")
    ]
    for title, desc in pts_s5:
        p_t = tf_s5.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(12.5)
        p_t.font.color.rgb = c_dark
        p_d = tf_s5.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s5, "worker/vm_manager.py:L289-L323 (def stop), worker/vm_manager.py:L342-L345 (def delete)")

    # ==========================================================================
    # Slide 6: Failure Handling & Automated Evacuation
    # ==========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Failure Handling: Total Recovery First & Dual-Layer Fencing")
    tb_s6 = s6.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf_s6 = tb_s6.text_frame
    tf_s6.word_wrap = True

    pts_s6 = [
        ("Leading with Total Recovery (Live: 14.19 s; Repeats: 14.33 s – 16.39 s)",
         "Total failover recovery from failure injection to healthy running state on surviving node: verified live failover achieved 14.19s total recovery (13.18s detection, 1.01s evacuation; note: the three figures come from different observation points and do not sum). Fallback 6-run repeats span 14.33s – 16.39s; historical Azure runs span 15.35s – 21.05s."),
        ("Failure Detection Latency (13.18 s – 15.70 s)",
         "Controller polls worker heartbeats every 5s; node is marked UNHEALTHY after missing 3 consecutive heartbeats (13.18s in live test; 13.83s–15.70s across fallback repeats; 14.84s–20.35s in Azure historical over SSH tunnel)."),
        ("Cold Evacuation Latency (0.00 s – 1.01 s)",
         "Once detected, the controller cold-evacuates the HA VM to surviving node in 0.00s–1.01s (1.01s in live test; 0.00s–0.70s in fallback repeats). In run 5, cold evacuation was 0.00s because detection and placement occurred synchronously in the same controller tick (<0.005s)."),
        ("Dual-Layer Tombstone Split-Brain Fencing (2.0 s – 9.33 s)",
         "When a failed node recovers, the controller queries stale tombstones and purges duplicate VMs on the returning worker via delete_vm() (2.0s–9.33s). Historical Run 6 took 9.33s (the split between 5s reconcile wait and worker ACPI shutdown was not instrumented). In today's run, timestamped reconcile logged immediate fencing at 23:24:12 IST.")
    ]
    for title, desc in pts_s6:
        p_t = tf_s6.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13)
        p_t.font.color.rgb = c_dark
        p_d = tf_s6.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s6, "evidence/failover_timestamped_20261115.txt:L10-L17, evidence/chaos_fallback_repeats_20261115.txt:L187-L195")

    # ==========================================================================
    # Slide 7: Results Table
    # ==========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Audited Quantitative Benchmark Results")

    rows = 8
    cols = 4
    t_shape = s7.shapes.add_table(rows, cols, Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.1))
    tbl = t_shape.table
    tbl.columns[0].width = Inches(2.7)
    tbl.columns[1].width = Inches(2.2)
    tbl.columns[2].width = Inches(3.8)
    tbl.columns[3].width = Inches(3.0)

    hdrs = ["Benchmark / Metric", "Baseline Standard", "PS-023 Platform (Measured)", "Exact Evidence Citation"]
    for j, h in enumerate(hdrs):
        cell = tbl.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_green
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(10.5)
            p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    tbl_data = [
        ("VMM Memory Overhead", "256 MB – 1024 MB", "128 MB fixed overhead (overhead is 128 MB; 256 is pids.max)", "worker/cgroup_manager.py:L23, stress:L10"),
        ("Direct Kernel Boot Time", "2.5 s – 8.0 s", "327 ms – 474 ms (Direct KVM kernel init)", "boot_node_a_bimodality_20261114.txt:L33-L46"),
        ("API Create -> Running", "5.0 s – 15.0 s", "0.751 s – 0.997 s (Direct KVM API latency)", "boot_node_a_contention_20261114.txt:L20"),
        ("Node A Full Boot (SSH)", "15.0 s – 60.0 s", "6.846 s – 11.257 s (contention set, n=20, med 8.460 s)\n7.058 s – 16.398 s (diagnostic set, n=15, med 8.372 s)", "contention_20261114.txt:L45-L48\nbimodality_20261114.txt:L49-L55"),
        ("Total Failover Recovery", "45 s – 180 s", "14.19 s (live: 13.18s det, 1.01s evac; do not sum)\n14.33 s – 16.39 s (fallback repeats, n=6)\n15.35 s – 21.05 s (recorded 13-14 Nov, ssh-tunnel)", "failover_timestamped_20261115.txt:L10-L12\nchaos_fallback_repeats_20261115.txt:L190\nchaos_azure_repeats_20261114.txt:L402"),
        ("Cold Evacuation Latency", "10 s – 45 s", "1.01 s (live run) | 0.00 s – 0.70 s (fallback)", "failover_timestamped_20261115.txt:L11"),
        ("Controller Restart Sync", "Manual reboot", "2.06 s (zero orphans, 2/2 VMs preserved)", "controller_restart_20261115.txt:L20-L32"),
    ]
    for i, row in enumerate(tbl_data):
        for j, val in enumerate(row):
            cell = tbl.cell(i + 1, j)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(9.5)
                if j == 2:
                    p.font.bold = True
                    p.font.color.rgb = c_green

    add_footnote(s7, "Comprehensive Evidence Index: docs/EVIDENCE_INDEX.md")

    # ==========================================================================
    # Slide 8: Cgroups v2 Isolation
    # ==========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Cgroups v2 Resource Guarantees & Host Containment")
    tb_s8 = s8.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf_s8 = tb_s8.text_frame
    tf_s8.word_wrap = True

    pts_s8 = [
        ("Strict Resource Configuration (worker/cgroup_manager.py:L21-L25)",
         "Every microVM slice (/sys/fs/cgroup/ps023-vmm-<vm_id>) is enforced with hard bounds: memory.max = guest RAM + 128 MB fixed overhead (DEFAULT_MEMORY_OVERHEAD_MB = 128), pids.max = 256 (DEFAULT_PIDS_MIN = 256), and cpu.max = 1.25x CFS quota (DEFAULT_CPU_HEADROOM = 1.25)."),
        ("In-Guest OOM Containment (cgroups_memory_stress_20261114.txt:L10-L71)",
         "Progressive memory allocation stress inside a 512MB guest triggered the internal guest Linux kernel OOM killer (killing python3 PID 2081) before reaching the host cgroup limit (640MB)."),
        ("Zero Host-Level OOM Disruption (oom_kill = 0)",
         "Host memory events recorded exactly oom_kill = 0. The host Cloud Hypervisor VMM process (PID 19235) remained alive, healthy, and isolated, protecting neighboring VMs from cascading failure."),
        ("systemd DelegateSubgroup=service Compliance",
         "Worker services run with systemd delegation, ensuring daemon upgrades and service restarts never dismantle active microVM cgroup leaves.")
    ]
    for title, desc in pts_s8:
        p_t = tf_s8.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13)
        p_t.font.color.rgb = c_dark
        p_d = tf_s8.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s8, "worker/cgroup_manager.py:L21-L25, evidence/cgroups_memory_stress_20261114.txt:L10-L71")

    # ==========================================================================
    # Slide 9: Live Demo Flow & Rehearsal
    # ==========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Live Demonstration Flow & Rehearsal Verification")
    tb_s9 = s9.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf_s9 = tb_s9.text_frame
    tf_s9.word_wrap = True

    pts_s9 = [
        ("Verified 8-Step Demonstration Flow (docs/demo-script.md)",
         "1. Cluster Overview & Schedulable RAM -> 2. Direct KVM Boot on Node A -> 3. In-Browser Interactive Terminal -> 4. Nested Boot on Node B -> 5. Pluggable Placement & Capacity Refusal (409) -> 6. Chaos Failure Injection on Node B -> 7. Auto-Evacuation to Node A -> 8. Clean Tombstone Fencing on Return."),
        ("Automated Rehearsal Suite (scripts/demo_rehearsal.py)",
         "The full 8-step flow was verified across 3 automated rehearsal runs via the REST API in 86.49 s – 91.76 s with 0 errors (Run 1: 86.49s; Run 2: 91.76s; Run 3: 91.53s)."),
        ("Live Pre-Flight Sanity Automation (scripts/demo_preflight.sh)",
         "Automated preflight checks host available memory (accounting for 4096 MB nested Node B), verifies zero stale VMMs, zero leftover cgroups, and validates token loading prior to demonstration."),
        ("Demo Day Fallback Ladder (docs/demo_day_checklist.md)",
         "Tier 1: Primary live fallback stack -> Tier 2: Recorded Azure benchmark reference (recorded 13–14 Nov, ssh-tunnel / mobile hotspot WireGuard) -> Tier 3: Automated rehearsal audit telemetry.")
    ]
    for title, desc in pts_s9:
        p_t = tf_s9.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13)
        p_t.font.color.rgb = c_dark
        p_d = tf_s9.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s9, "evidence/demo_rehearsal_run1_20261115.txt:L60-L76, docs/demo_day_checklist.md")

    # ==========================================================================
    # Slide 10: Architectural Limitations
    # ==========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Architectural Limitations & Engineering Scope", "TRANSPARENCY & BOUNDARIES")
    tb_s10 = s10.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf_s10 = tb_s10.text_frame
    tf_s10.word_wrap = True

    pts_s10 = [
        ("Deterministic Cold Evacuation vs Live Migration",
         "Failover is cold rescheduling with a clean direct kernel boot on the surviving node. In-flight guest RAM pages and open TCP sessions are not preserved (unshared local storage architecture)."),
        ("Plain HTTP Control Plane & Static Tokens",
         "Internal controller-worker communication uses plain HTTP authenticated via static bearer tokens without mTLS; transport encryption across clouds is delegated to WireGuard or SSH tunnels."),
        ("Local Fallback Shared Hardware Contention",
         "In primary demo mode, Node B runs as a nested Cloud Hypervisor VM on the same physical host (AMD Ryzen 7 7445HS), sharing host memory bus and disk I/O."),
        ("Single Controller Instance (SPOF)",
         "The controller runs as a single process backed by SQLite WAL mode. While it recovers in 2.06s with 0 orphans, control plane high availability (e.g. Raft consensus) is out of hackathon scope."),
        ("WireGuard Network Scope",
         "WireGuard was verified over a mobile hotspot (avg ping 154.5–189.8 ms; recorded 13–14 Nov); it is blocked on local hostel Wi-Fi due to UDP 51820 firewall filtering.")
    ]
    for title, desc in pts_s10:
        p_t = tf_s10.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(12.5)
        p_t.font.color.rgb = c_red
        p_d = tf_s10.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = c_gray
    add_footnote(s10, "docs/limitations.md (Sections 1 through 6), evidence/wireguard_hotspot_20261114.txt:L75-L80")

    # ==========================================================================
    # Slide 11: Conclusion
    # ==========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Conclusion: Deliverables & Architectural Verdict")
    tb_s11 = s11.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf_s11 = tb_s11.text_frame
    tf_s11.word_wrap = True

    pts_s11 = [
        ("Deterministic High Availability Leading with Total Recovery",
         "Autonomous detection and cold evacuation reliably recovers stateful HA workloads: 14.19 s live total recovery (13.18 s detection, 1.01 s cold evacuation; note: figures from different observation points and do not sum) and 14.33 s – 16.39 s fallback repeats (0.00 s – 1.01 s cold evacuation), with zero-leak tombstone split-brain fencing on worker return."),
        ("Guaranteed Defensive Host Containment",
         "Cgroups v2 resource slices (128 MB overhead, 256 PIDs, 1.25x CPU quota) successfully isolate guest workloads, keeping physical host memory and hypervisor processes fully protected during guest memory exhaustion (oom_kill = 0)."),
        ("Resilient Zero-Orphan Control Plane",
         "Controller recovers from abrupt process failure in 2.06 s, discovering and reconciling all active virtual machines without dropping connections or generating orphaned processes."),
        ("Fully Audited & Empirically Verified Platform",
         "182 Python unit tests passed (0 failures), 12 frontend UI tests passed, and all performance metrics verified with traceable evidence log files.")
    ]
    for title, desc in pts_s11:
        p_t = tf_s11.add_paragraph()
        p_t.text = f"• {title}: "
        p_t.font.bold = True
        p_t.font.size = Pt(13)
        p_t.font.color.rgb = c_green
        p_d = tf_s11.add_paragraph()
        p_d.text = f"  {desc}\n"
        p_d.font.size = Pt(11.5)
        p_d.font.color.rgb = c_dark
    add_footnote(s11, "docs/EVIDENCE_INDEX.md, docs/demo_day_checklist.md")

    # ==========================================================================
    # Slide 12: Jury Defense Q&A
    # ==========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Jury Defense Guide: Key Architectural Questions", "JURY DEFENSE")
    tb_s12 = s12.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(5.3))
    tf_s12 = tb_s12.text_frame
    tf_s12.word_wrap = True

    qa_pts = [
        ("Q1: How fast is boot really, and what causes the 7s to 16s variance?",
         "Kernel initialization is invariantly fast (327–474 ms). Full SSH readiness on direct KVM spans 6.846 s – 11.257 s across the 20-run contention set (median 8.460 s). An earlier 15-run diagnostic set reached 7.058 s – 16.398 s (median 8.372 s). In-guest delay during pollinate.service was observed in 1 of 5 instrumented runs; cause not established; the host-contention test did not show an effect.",
         "boot_node_a_contention_20261114.txt:L45-L48, boot_node_a_bimodality_20261114.txt:L16-L27"),
        ("Q2: What prevents split-brain execution when a failed node returns?",
         "Total recovery takes 14.19s in live testing (13.18s detection, 1.01s cold evacuation; note: the three figures come from different observation points and do not sum) and 14.33s – 16.39s across fallback repeats. When the failed node returns, the controller matches tombstones in SQLite against the worker's active VM list and executes delete_vm() to fence stale duplicates (fenced in 2.0s–9.33s). Historical Run 6 took 9.33s (wait/shutdown split not instrumented); live test logged immediate fencing at 23:24:12 IST.",
         "failover_timestamped_20261115.txt:L10-L17, chaos_fallback_repeats_20261115.txt:L187-L195"),
        ("Q3: How do you guarantee a rogue VM will not take down the host?",
         "Each VM runs in a dedicated cgroup v2 slice with hard memory.max (guest RAM + 128 MB overhead; overhead is 128 MB, 256 is pids.max; DEFAULT_MEMORY_OVERHEAD_MB = 128 in cgroup_manager.py:L23), cpu.max (1.25x quota), and pids.max (256). In stress tests, the in-guest kernel OOM killer terminates rogue processes internally before the 640MB host limit is reached (oom_kill = 0).",
         "worker/cgroup_manager.py:L21-L25, evidence/cgroups_memory_stress_20261114.txt:L10-L71"),
        ("Q4: If the controller process crashes, do running VMs terminate?",
         "No. Worker daemons and Cloud Hypervisor processes operate independently. On restart (2.06 s), the reconciler polls worker /vms endpoints and recovers state with 0 orphans and 0 duplicates.",
         "evidence/controller_restart_20261115.txt:L20-L32")
    ]
    for q, a, src in qa_pts:
        p_q = tf_s12.add_paragraph()
        p_q.text = f"{q}"
        p_q.font.bold = True
        p_q.font.size = Pt(11)
        p_q.font.color.rgb = c_dark
        p_a = tf_s12.add_paragraph()
        p_a.text = f"Answer: {a} [{src}]"
        p_a.font.size = Pt(9.5)
        p_a.font.color.rgb = c_gray

    prs.save(PPTX_DRAFT_PATH)
    prs.save(PPTX_FINAL_PATH)
    print(f"Presentation saved to:\n  {PPTX_DRAFT_PATH}\n  {PPTX_FINAL_PATH}")
    return len(prs.slides)

def export_pdf_and_png():
    print("Exporting PPTX to PDF via LibreOffice...")
    cmd_pdf = ["soffice", "--headless", "--convert-to", "pdf", PPTX_FINAL_PATH, "--outdir", OUTPUT_DIR]
    res_pdf = subprocess.run(cmd_pdf, capture_output=True, text=True)
    if res_pdf.returncode != 0:
        print(f"Error converting to PDF: {res_pdf.stderr}")
        return False
    print(f"PDF exported to: {PDF_FINAL_PATH}")

    # Copy to ps023_draft.pdf as well for backward compatibility
    import shutil
    shutil.copyfile(PDF_FINAL_PATH, PDF_DRAFT_PATH)

    print("Rendering slides to PNG via pdftoppm...")
    for f in os.listdir(SLIDES_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(SLIDES_DIR, f))
    cmd_png = ["pdftoppm", "-png", "-r", "150", PDF_FINAL_PATH, os.path.join(SLIDES_DIR, "slide")]
    res_png = subprocess.run(cmd_png, capture_output=True, text=True)
    if res_png.returncode != 0:
        print(f"Error rendering PNGs: {res_png.stderr}")
        return False

    pngs = sorted([f for f in os.listdir(SLIDES_DIR) if f.startswith("slide") and f.endswith(".png")])
    print(f"Rendered {len(pngs)} slide PNGs in {SLIDES_DIR}:")
    for p in pngs:
        print(f"  - {p}")
    return True

if __name__ == "__main__":
    count = build_presentation()
    print(f"Total Slides Generated: {count}")
    assert count <= 12, f"Slide count {count} exceeds 12 slides maximum!"
    success = export_pdf_and_png()
    if not success:
        sys.exit(1)
