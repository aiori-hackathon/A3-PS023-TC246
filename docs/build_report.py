import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_elements(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_elements(self, total_pages):
        # Suppress headers/footers on cover page
        if self._pageNumber == 1:
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#5F6368"))

        # Running Header
        self.drawString(54, 755, "A3-PS023-TC246: Minimal Two-Node Cloud Hypervisor VM Controller")
        self.drawRightString(612 - 54, 755, "AIORI Hackathon 3 | Team TC246")
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.6)
        self.line(54, 748, 612 - 54, 748)

        # Running Footer
        self.setFont("Helvetica", 8)
        self.drawString(54, 38, "Confidential - Final Submission Document (30 Oct 2026)")
        page_text = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(612 - 54, 38, page_text)
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.6)
        self.line(54, 48, 612 - 54, 48)

        self.restoreState()

def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#1A73E8")
    dark_neutral = colors.HexColor("#202124")
    muted_text = colors.HexColor("#5F6368")

    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1A202C"),
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#1A202C"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14.5,
        textColor=primary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.2,
        leading=13,
        textColor=dark_neutral,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=dark_neutral,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3.5
    )

    callout_style = ParagraphStyle(
        'Callout_Text',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#3C4043")
    )

    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10.5,
        textColor=muted_text,
        alignment=1,
        spaceAfter=6,
        spaceBefore=3
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.2,
        leading=10.5,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=dark_neutral
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10.5,
        textColor=dark_neutral
    )

    story = []

    # =========================================================================
    # PAGE 1: 1. COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 35))
    story.append(Paragraph("AIORI Hackathon 3 — Technical Report", ParagraphStyle('CoverPill', fontName='Helvetica-Bold', fontSize=10, textColor=primary_color, spaceAfter=12)))
    story.append(Paragraph("Minimal Two-Node Cloud Hypervisor<br/>VM Controller", title_style))
    story.append(Paragraph("Problem Statement: A3-PS023 &nbsp;|&nbsp; Category: Cloud Computing", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceBefore=4, spaceAfter=20))

    meta_table_data = [
        [Paragraph("<b>Team Name:</b>", body_style), Paragraph("The Mavericks (TC246)", body_style)],
        [Paragraph("<b>Problem Statement:</b>", body_style), Paragraph("PS-023: Minimal Two-Node Cloud Hypervisor VM Controller", body_style)],
        [Paragraph("<b>Team Members:</b>", body_style), Paragraph("rajya vardhan .M<br/>Shivani S R", body_style)],
        [Paragraph("<b>Host Machine:</b>", body_style), Paragraph("ASUS TUF A15 (AMD Ryzen 7 7445HS 12-thread, 16 GB RAM, Fedora Linux)", body_style)],
        [Paragraph("<b>Hypervisor Engine:</b>", body_style), Paragraph("Cloud Hypervisor v54.0.0 (/dev/kvm hardware virtualization)", body_style)],
        [Paragraph("<b>Submission Date:</b>", body_style), Paragraph("Friday, 30 October 2026 (IST)", body_style)],
        [Paragraph("<b>Git Repository:</b>", body_style), Paragraph("aiori-hackathon/A3-PS023-TC246 (branch: main)", body_style)],
    ]
    meta_table = Table(meta_table_data, colWidths=[130, 374])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#F1F3F4")),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 30))

    disclosure_content = [
        [Paragraph("<b>Mandatory Architecture Disclosure & Integrity Statement:</b>", ParagraphStyle('DiscH', fontName='Helvetica-Bold', fontSize=8.8, textColor=colors.HexColor("#B06000")))],
        [Paragraph("This implementation was developed and evaluated on a single physical host laptop. <b>Node A</b> runs as a native host worker; <b>Node B</b> operates as a nested KVM virtual machine (4 vCPUs, 4 GB RAM) running its own Cloud Hypervisor daemon and worker agent. Inter-node communication uses authenticated HTTP bearer tokens on private Linux bridge subnets. Resource specifications are strictly validated and passed directly to Cloud Hypervisor boot configurations without Linux cgroup v2 enforcement. All reported results (87 automated unit tests passed; integration 3 passed, 1 skipped; cold starts verified twice) represent exact physical measurements directly reproducible from repository artifacts.", callout_style)]
    ]
    disclosure_box = Table(disclosure_content, colWidths=[504])
    disclosure_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FEF7E0")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#F9AB00")),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(disclosure_box)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: 2. TABLE OF CONTENTS & 3. PROBLEM DESCRIPTION
    # =========================================================================
    story.append(Paragraph("2. Table of Contents", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=8))

    toc_data = [
        [Paragraph("<b>Section</b>", table_header_style), Paragraph("<b>Title</b>", table_header_style), Paragraph("<b>Page</b>", table_header_style)],
        [Paragraph("1", table_cell_bold), Paragraph("Cover Page", table_cell_style), Paragraph("1", table_cell_bold)],
        [Paragraph("2", table_cell_bold), Paragraph("Table of Contents", table_cell_style), Paragraph("2", table_cell_bold)],
        [Paragraph("3", table_cell_bold), Paragraph("Problem Description", table_cell_style), Paragraph("2", table_cell_bold)],
        [Paragraph("4", table_cell_bold), Paragraph("Solution Proposed", table_cell_style), Paragraph("3", table_cell_bold)],
        [Paragraph("5", table_cell_bold), Paragraph("Optimization Proposed by the Team", table_cell_style), Paragraph("4", table_cell_bold)],
        [Paragraph("6", table_cell_bold), Paragraph("Solution Architecture and Design", table_cell_style), Paragraph("6", table_cell_bold)],
        [Paragraph("7", table_cell_bold), Paragraph("Timeline of Delivery", table_cell_style), Paragraph("8", table_cell_bold)],
        [Paragraph("8", table_cell_bold), Paragraph("References", table_cell_style), Paragraph("9", table_cell_bold)],
        [Paragraph("9", table_cell_bold), Paragraph("Conclusion", table_cell_style), Paragraph("9", table_cell_bold)],
    ]
    toc_table = Table(toc_data, colWidths=[45, 414, 45])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Problem Description", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Modern cloud environments demand lean, predictable hardware virtualization without the massive overhead, sluggish startup times, and complex dependency graphs associated with traditional multi-node hypervisors. Cloud Hypervisor provides high-performance, security-focused hardware virtualization on Linux KVM. However, orchestrating multiple nodes introduces severe coordination and stability challenges that must be resolved by a dedicated control plane:",
        body_style
    ))

    key_issues = [
        "<b>Multi-Host Coordination & Single Management Endpoint:</b> Managing the complete lifecycle of virtual machines (create, start, stop, list, delete) across multiple physical or virtual compute nodes requires a centralized, unified REST interface that reliably synchronizes with node-level execution agents.",
        "<b>Resource Overcommitment & Concurrent Provisioning Hazards:</b> When multiple creation requests arrive in rapid succession, simple placement heuristics that poll instantaneous host memory cause double-booking on the same node, leading to host memory exhaustion, kernel out-of-memory (OOM) kills, or failed VM launches.",
        "<b>Cluster Inconsistency & Network Partitions:</b> Transient network failures, agent crashes, or host reboots can leave central database records out of sync with physical hypervisor processes, generating ghost records, untracked orphan VMs, or dual-allocation errors.",
        "<b>Hypervisor Process Leaks & Zombie Processes:</b> Hung guest kernels, frozen API sockets, or unhandled worker terminations can abandon active VMM processes or create zombie processes, permanently holding host RAM, CPU threads, and TAP network interfaces.",
        "<b>Authenticated Component Boundaries:</b> Exposing REST control across nodes requires strict authentication, constant-time token verification, and granular request validation to prevent unauthorized operations or path injection attacks."
    ]
    for issue in key_issues:
        story.append(Paragraph(f"• {issue}", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: 4. SOLUTION PROPOSED
    # =========================================================================
    story.append(Paragraph("4. Solution Proposed", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "To satisfy problem statement PS-023, team TC246 designed and implemented an asynchronous, lightweight two-node VM controller architecture composed of a centralized controller, distributed worker agents, SQLite relational state persistence, and an interactive browser dashboard.",
        body_style
    ))

    story.append(Paragraph("4.1 System Components & Architecture", h2_style))
    story.append(Paragraph("• <b>Central Controller (FastAPI, SQLite, Port 8000):</b> Serves the authenticated REST API. Houses the memory-aware placement scheduler, background node poller (5-second cadence), automated state reconciliation engine, and the WebSocket terminal relay.", bullet_style))
    story.append(Paragraph("• <b>Worker Agents (FastAPI, Ports 8001 & 8002):</b> Autonomous daemons deployed on each KVM node. Each worker manages its host TAP interface pool, maintains isolated per-VM storage folders (reflinked disk images and cloud-init seeds), issues Unix domain socket commands to Cloud Hypervisor, and supervises VMM processes with guaranteed stop escalation.", bullet_style))
    story.append(Paragraph("• <b>Storage Management:</b> Each VM receives an independent raw disk image created via copy-on-write reflink cloning (<code>cp --reflink=auto</code>) from a single prepared Ubuntu 24.04 base image, providing instant provisioning without disk space duplication. Unique cloud-init seeds configure hostname, user credentials, and network interfaces.", bullet_style))
    story.append(Paragraph("• <b>Web Dashboard & Browser Terminal:</b> A single-page application at <code>/dashboard/</code> providing real-time visibility into node health metrics, VM statuses, and recorded placement decisions. A web terminal powered by xterm.js connects over an authenticated WebSocket relay to guest SSH without installing external agents.", bullet_style))

    story.append(Paragraph("4.2 System Disclosures & Operational Boundaries", h2_style))
    story.append(Paragraph(
        "In strict adherence to academic honesty and engineering integrity, the team explicitly documents the precise boundaries of our testing environment:",
        body_style
    ))

    disclosures = [
        "<b>Single Physical Host Laptop:</b> Testing was conducted on one physical ASUS TUF A15 laptop. <b>Node A</b> is a native host worker; <b>Node B</b> is a nested KVM virtual machine (4 vCPU, 4 GB RAM) configured with nested virtualization (<code>nested=on</code>) running worker B and an inner Cloud Hypervisor daemon. While behaving architecturally as two autonomous KVM nodes, they share one physical CPU and memory bus.",
        "<b>Authentication & Protocol Boundary:</b> Controller-to-worker and client-to-controller communication utilizes plain HTTP with constant-time Bearer token verification. Transport Layer Security (TLS/mTLS) is omitted and recommended for production deployment over untrusted networks.",
        "<b>Resource Enforcement:</b> Requested vCPU counts (1–8), memory sizes (128–8192 MB), and disk capacities (1–50 GB) are strictly validated and passed to Cloud Hypervisor API configurations. Kernel cgroups v2 resource capping is not implemented.",
        "<b>Transient Node Unhealthiness on Frozen VMM:</b> In manual fault injection tests, a frozen VMM (simulated via SIGSTOP) caused the parent node to report UNHEALTHY for ~70 seconds. The inferred cause is worker status inspection calls blocking on the stalled process past the controller's 5 s timeout. The system safely recovered without process or memory leaks.",
        "<b>Single VM Image & Shell Permissions:</b> Provisioning utilizes a single prepared Ubuntu 24.04 LTS cloud image with automatic placement. Anyone possessing the controller API Bearer token can initiate an interactive terminal shell on any running guest VM."
    ]
    for d in disclosures:
        story.append(Paragraph(f"• {d}", bullet_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: 5. OPTIMIZATION PROPOSED BY THE TEAM
    # =========================================================================
    story.append(Paragraph("5. Optimization Proposed by the Team", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "To elevate the system beyond basic hypervisor wrappers, team TC246 implemented five core architectural optimizations addressing race conditions, process leaks, boot performance, and fault recovery:",
        body_style
    ))

    opt_items = [
        "<b>1. Atomic Memory Reservation for PENDING, RUNNING, and UNKNOWN VMs:</b> Rather than relying solely on raw host memory telemetry, the controller computes schedulable memory by actively subtracting memory committed to VMs in <code>PENDING</code>, <code>RUNNING</code>, and <code>UNKNOWN</code> states. This prevents concurrent provisioning requests from double-booking memory.",
        "<b>2. Worker Refusal Fallthrough with Granular Reason Tracking:</b> If a selected node refuses a creation request (e.g., HTTP 409 due to missing TAP devices or slot exhaustion), the controller atomically rolls back the reservation, logs the refusal reason, keeps the node marked healthy, and immediately attempts placement on the next eligible candidate.",
        "<b>3. Multi-Stage Stop Escalation with Child Process Reaping:</b> VM stop requests follow a strict 4-stage escalation sequence (ACPI power button 30 s → API vm/vmm.shutdown 5 s → SIGTERM 5 s → SIGKILL 5 s). Once terminated, the worker invokes <code>os.waitpid()</code> to reap the child, eliminating zombie hypervisor processes.",
        "<b>4. Copy-on-Write (CoW) Reflink Disk Provisioning:</b> Utilizing Btrfs/XFS reflink capabilities (<code>cp --reflink=auto</code>), new VM disk images are instantiated instantaneously with zero initial block duplication, reducing VM creation latency to sub-second durations.",
        "<b>5. Cloud-Init Interface Predictability (<code>set-name: ens3</code>):</b> Configured deterministic interface naming in cloud-init network-config, eliminating network discovery stalls during VM initialization (noted in team logs as resolving an observed ~2 minute boot delay)."
    ]
    for opt in opt_items:
        story.append(Paragraph(opt, bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("5.1 Before vs. After Optimization Comparison", h2_style))
    story.append(Paragraph(
        "The following table compares baseline hypervisor management approaches against the optimized PS-023 controller. Measured values reflect actual testbed telemetry; qualitative rows represent algorithmic enhancements.",
        body_style
    ))

    ba_headers = [
        Paragraph("<b>Architectural Aspect</b>", table_header_style),
        Paragraph("<b>Standard / Baseline Approach</b>", table_header_style),
        Paragraph("<b>TC246 Optimized Solution</b>", table_header_style),
        Paragraph("<b>Verification / Evidence</b>", table_header_style)
    ]
    ba_rows = [
        [
            Paragraph("<b>Memory Allocation & Scheduling</b>", table_cell_bold),
            Paragraph("Basic host selection based on instantaneous free RAM; vulnerable to race conditions.", table_cell_style),
            Paragraph("Memory-aware scheduler with atomic subtraction for PENDING, RUNNING, and UNKNOWN VMs.", table_cell_style),
            Paragraph("Automated unit tests (test_scheduler.py); 87 passed.", table_cell_style)
        ],
        [
            Paragraph("<b>Provisioning Refusal Handling</b>", table_cell_bold),
            Paragraph("Provisioning fails completely if primary host refuses; node marked down blindly.", table_cell_style),
            Paragraph("Refusal fallthrough: controller logs per-node reason, retains healthy flag, tries next node.", table_cell_style),
            Paragraph("evidence-decisions.json (Node B refused tapvm0; Node A served request).", table_cell_style)
        ],
        [
            Paragraph("<b>Hypervisor Stop & Cleanup</b>", table_cell_bold),
            Paragraph("Single SIGKILL or ACPI call; unhandled hangs produce zombie VMM processes.", table_cell_style),
            Paragraph("4-tier escalation (ACPI → API → SIGTERM → SIGKILL) followed by explicit child reaping.", table_cell_style),
            Paragraph("evidence-stuck-stop.txt: 70 s return, 0 zombie processes left.", table_cell_style)
        ],
        [
            Paragraph("<b>Node Health & Failure Recovery</b>", table_cell_bold),
            Paragraph("Stale database entries persist indefinitely on worker disconnect or host crash.", table_cell_style),
            Paragraph("5 s polling; UNHEALTHY after 15 s; automatic resync and orphan cleanup (120 s).", table_cell_style),
            Paragraph("Cold start verified twice (bring-up3.txt, bring-up4.txt).", table_cell_style)
        ],
        [
            Paragraph("<b>Storage & Boot Latency</b>", table_cell_bold),
            Paragraph("Full disk copying; non-deterministic interface enumeration causing boot stalls.", table_cell_style),
            Paragraph("CoW reflink cloning; cloud-init set-name: ens3 eliminates device discovery delays.", table_cell_style),
            Paragraph("Team bench observations; verified sub-second disk cloning.", table_cell_style)
        ],
    ]
    ba_table_data = [ba_headers] + ba_rows
    ba_table = Table(ba_table_data, colWidths=[90, 135, 145, 134])
    ba_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(ba_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: 5.2 OPTIMIZATION PROCESS FLOWCHARTS
    # =========================================================================
    story.append(Paragraph("5.2 Optimization Process Flowcharts", h2_style))
    story.append(Paragraph("The diagrams below illustrate the algorithmic workflows for VM placement with refusal fallthrough and the non-leaking stop escalation sequence.", body_style))
    story.append(Spacer(1, 4))

    flowchart_img_path = "/home/rajyavardhan/ps023-submit/docs/figures/placement_flowchart.png"
    if os.path.exists(flowchart_img_path):
        story.append(Image(flowchart_img_path, width=470, height=270))
        story.append(Paragraph("Figure 5.1: VM Placement Scheduling Algorithm with Atomic Reservation and Refusal Fallthrough", caption_style))

    story.append(Spacer(1, 8))

    stop_flowchart_path = "/home/rajyavardhan/ps023-submit/docs/figures/stop_escalation_flowchart.png"
    if os.path.exists(stop_flowchart_path):
        story.append(Image(stop_flowchart_path, width=470, height=270))
        story.append(Paragraph("Figure 5.2: Multi-Stage Stop Escalation Protocol with Explicit Process Reaping", caption_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: 6. SOLUTION ARCHITECTURE AND DESIGN
    # =========================================================================
    story.append(Paragraph("6. Solution Architecture and Design", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "The PS-023 architecture decouples global cluster coordination from node-level hypervisor management. The central controller handles client authentication, placement decisions, state reconciliation, and terminal bridging, while independent workers manage the physical KVM hypervisor lifecycles.",
        body_style
    ))

    arch_uml_path = "/home/rajyavardhan/ps023-submit/docs/figures/presentation_arch_uml.png"
    if os.path.exists(arch_uml_path):
        story.append(Image(arch_uml_path, width=490, height=176))
        story.append(Paragraph("Figure 6.1: System Architecture UML Diagram (Controller, Workers, and KVM Hosts)", caption_style))

    story.append(Spacer(1, 4))

    dfd_path = "/home/rajyavardhan/ps023-submit/docs/figures/presentation_dfd.png"
    if os.path.exists(dfd_path):
        story.append(Image(dfd_path, width=480, height=245))
        story.append(Paragraph("Figure 6.2: Data Flow Diagram (DFD) — Client Request Routing, Scheduling, and VMM Execution", caption_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: 6.1 SUBSYSTEM DESIGN & VERIFICATION
    # =========================================================================
    story.append(Paragraph("6.1 Subsystem Design Specifications", h2_style))
    story.append(Paragraph("• <b>Controller API & Auth:</b> Built on FastAPI. All endpoints except <code>/health</code> enforce HTTP Bearer tokens with constant-time comparison (<code>secrets.compare_digest</code>). Per-worker tokens isolate node daemons.", bullet_style))
    story.append(Paragraph("• <b>Network Topography:</b> Linux bridge <code>br-ps023</code> (192.168.100.1/24) on the host connects Node A TAP devices (<code>tapvm0-3</code>, IPs .10–.13) and Node B TAP (<code>tapvm7</code>, IP .17). Inside Node B, inner bridge <code>br-inner</code> (10.77.0.1/24) routes traffic to nested guest TAPs via host static route <code>10.77.0.0/24 via 192.168.100.17</code>.", bullet_style))
    story.append(Paragraph("• <b>Process Isolation & Clean Reaping:</b> Workers execute Cloud Hypervisor via <code>subprocess.Popen</code> with <code>start_new_session=True</code>. Running VMs survive worker agent reboots. PID files are verified against socket arguments to protect against PID recycling.", bullet_style))
    story.append(Paragraph("• <b>Automated Reconciliation Engine:</b> Every 5 seconds after health polling, the controller audits cluster state: VMs on UNHEALTHY nodes transition to <code>UNKNOWN</code>, returning nodes trigger state resynchronization, unrecorded worker VMs older than 120 s are deleted, and stale <code>PENDING</code> rows (120 s) become <code>FAILED</code>.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("6.2 Verification Results & Empirical Evidence", h2_style))
    story.append(Paragraph(
        "The implementation was thoroughly evaluated through unit tests, live integration tests, and manual failure injection tests with raw artifacts preserved in <code>evidence/</code>:",
        body_style
    ))

    verif_headers = [
        Paragraph("<b>Test Suite / Scenario</b>", table_header_style),
        Paragraph("<b>Scope & Methodology</b>", table_header_style),
        Paragraph("<b>Observed Outcome & Metrics</b>", table_header_style)
    ]
    verif_rows = [
        [
            Paragraph("<b>Automated Logic Suite</b><br/>(pytest unit tests)", table_cell_bold),
            Paragraph("In-process mock workers; covers scheduler, state machine, reconcile, auth, validation, and terminal relay.", table_cell_style),
            Paragraph("<b>87 passed</b> in 7.86 s (0 failures). Verifies all controller logic without KVM requirements.", table_cell_style)
        ],
        [
            Paragraph("<b>Live Integration Suite</b><br/>(test_live_cluster.py)", table_cell_bold),
            Paragraph("End-to-end VM lifecycle across live nodes via controller API; checks memory allocation and VMM counts.", table_cell_style),
            Paragraph("<b>3 passed, 1 skipped</b> (skipped test tests 8 GB VM exceeding single-node capacity by design).", table_cell_style)
        ],
        [
            Paragraph("<b>Cold Start Recovery</b><br/>(bring-up.sh)", table_cell_bold),
            Paragraph("Cold start executed following complete laptop reboot; recreates network, nested node B, and agents.", table_cell_style),
            Paragraph("<b>Verified twice</b> (bring-up3.txt, bring-up4.txt). Both nodes report HEALTHY upon completion.", table_cell_style)
        ],
        [
            Paragraph("<b>Frozen VMM Fault</b><br/>(SIGSTOP injection)", table_cell_bold),
            Paragraph("Injected SIGSTOP into active Cloud Hypervisor process; invoked stop API through controller.", table_cell_style),
            Paragraph("HTTP 200 returned in <b>70 s</b> via SIGKILL escalation. 0 zombie processes; VM cleaned up (204).", table_cell_style)
        ],
        [
            Paragraph("<b>Worker Refusal Fallthrough</b><br/>(TAP exhaustion simulation)", table_cell_bold),
            Paragraph("Removed Node B TAP devices; worker A stopped; issued VM creation request.", table_cell_style),
            Paragraph("Controller returned HTTP 409 detailing <code>node-b: tapvm0 missing</code>; recorded in decisions table.", table_cell_style)
        ],
    ]
    verif_table = Table([verif_headers] + verif_rows, colWidths=[120, 204, 180])
    verif_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(verif_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: 7. TIMELINE OF DELIVERY
    # =========================================================================
    story.append(Paragraph("7. Timeline of Delivery", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Project delivery progressed through systematic prototyping, nested environment stabilization, automated test development, and thorough failure testing leading to final submission.",
        body_style
    ))

    timeline_img_path = "/home/rajyavardhan/ps023-submit/docs/figures/timeline_graphic.png"
    if os.path.exists(timeline_img_path):
        story.append(Image(timeline_img_path, width=490, height=195))
        story.append(Paragraph("Figure 7.1: Project Milestone and Delivery Timeline", caption_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("7.1 Delivery Milestone Matrix", h2_style))

    timeline_table_data = [
        [Paragraph("<b>Date / Phase</b>", table_header_style), Paragraph("<b>Milestone Description</b>", table_header_style), Paragraph("<b>Status & Outcome</b>", table_header_style)],
        [
            Paragraph("Completed before 21 Oct", table_cell_bold),
            Paragraph("Core Architecture Prototyping: Ubuntu 24.04 base image creation, Cloud Hypervisor API integration, initial controller & worker drafts.", table_cell_style),
            Paragraph("Verified: Basic VM boot and socket communication established.", table_cell_style)
        ],
        [
            Paragraph("21 Oct 2026", table_cell_bold),
            Paragraph("Nested Node B Deployment: Built inner-net configuration, TAP device provisioning, and static route relay through 192.168.100.17.", table_cell_style),
            Paragraph("Verified: Two autonomous KVM nodes active on single laptop.", table_cell_style)
        ],
        [
            Paragraph("23–24 Oct 2026", table_cell_bold),
            Paragraph("Reliability & Failure Hardening: Refusal fallthrough logic implemented, frozen VMM stop test (70 s, 0 leaks), cold start verified twice.", table_cell_style),
            Paragraph("Verified: bring-up3.txt, bring-up4.txt, evidence-stuck-stop.txt recorded.", table_cell_style)
        ],
        [
            Paragraph("25–27 Oct 2026", table_cell_bold),
            Paragraph("Management UI & Terminal Relay: Implemented web dashboard and xterm.js WebSocket terminal relay; updated architecture docs.", table_cell_style),
            Paragraph("Verified: Interactive browser terminal to guest SSH functional.", table_cell_style)
        ],
        [
            Paragraph("28–29 Oct 2026", table_cell_bold),
            Paragraph("Testing & Verification Suite: Expanded automated suite to 87 unit tests; executed live integration tests (3 passed, 1 skipped).", table_cell_style),
            Paragraph("Verified: Clean pytest runs; project context handoff completed.", table_cell_style)
        ],
        [
            Paragraph("30 Oct 2026 (Today)", table_cell_bold),
            Paragraph("Final Submission: End-to-end browser terminal verification, formal technical report compilation, video demonstration, and repo finalization.", table_cell_style),
            Paragraph("Delivered: Complete repository and documentation package.", table_cell_style)
        ],
        [
            Paragraph("31 Oct – 4 Nov 2026", table_cell_bold),
            Paragraph("Evaluator Access Window: Cluster kept continuously online for evaluators; laptop power management configured.", table_cell_style),
            Paragraph("Scheduled: Evaluator cluster access and scoring.", table_cell_style)
        ],
    ]
    t_table = Table(timeline_table_data, colWidths=[105, 235, 164])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(t_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: 8. REFERENCES & 9. CONCLUSION
    # =========================================================================
    story.append(Paragraph("8. References", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    refs = [
        "[1] R. N. Calheiros, R. Ranjan, A. Beloglazov, C. A. F. De Rose, and R. Buyya, “CloudSim: A Toolkit for Modeling and Simulation of Cloud Computing Environments and Evaluation of Resource Provisioning Algorithms,” <i>Software: Practice and Experience</i>, vol. 41, no. 1, pp. 23–50, 2011. doi: 10.1002/spe.995.",
        "[2] A. Beloglazov, J. Abawajy, and R. Buyya, “Energy-aware Resource Allocation Heuristics for Efficient Management of Data Centers for Cloud Computing,” <i>Future Generation Computer Systems</i>, vol. 28, no. 5, pp. 755–768, 2012. doi: 10.1016/j.future.2011.04.017.",
        "[3] Cloud Hypervisor Project, “Cloud Hypervisor API Documentation,” 2024. [Online]. Available: https://github.com/cloud-hypervisor/cloud-hypervisor/blob/main/docs/api.md.",
        "[4] Linux Kernel Documentation, “Control Group v2,” 2024. [Online]. Available: https://docs.kernel.org/admin-guide/cgroup-v2.html.",
        "[5] IETF, “RFC 9110: HTTP Semantics,” 2022. [Online]. Available: https://www.rfc-editor.org/rfc/rfc9110.html.",
        "[6] Linux Kernel Documentation, “The Definitive KVM (Kernel-based Virtual Machine) API Documentation,” 2024. [Online]. Available: https://docs.kernel.org/virt/kvm/api.html.",
        "[7] IETF, “RFC 6750: The OAuth 2.0 Authorization Framework: Bearer Token Usage,” 2012. [Online]. Available: https://www.rfc-editor.org/rfc/rfc6750.html."
    ]
    for r in refs:
        story.append(Paragraph(r, bullet_style))

    story.append(Spacer(1, 10))

    story.append(Paragraph("9. Conclusion", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("9.1 Summary of Accomplishments", h2_style))
    story.append(Paragraph(
        "Team TC246 has successfully designed, built, and verified a robust, minimal two-node Cloud Hypervisor VM Controller for PS-023. Key deliverables include:",
        body_style
    ))
    story.append(Paragraph("• A resilient centralized controller with memory-aware scheduling and atomic reservation preventing race conditions.", bullet_style))
    story.append(Paragraph("• Autonomous worker agents executing Cloud Hypervisor commands with a 4-tier stop escalation protocol that guarantees zero leaked VMM or zombie processes.", bullet_style))
    story.append(Paragraph("• Complete lifecycle management (create, start, stop, delete, list) coupled with automatic state reconciliation and orphan garbage collection.", bullet_style))
    story.append(Paragraph("• An integrated web management dashboard and in-browser terminal relay providing real-time operator control.", bullet_style))
    story.append(Paragraph("• Comprehensive quality verification comprising 87 automated unit tests, 4 integration tests, and documented failure injection evidence.", bullet_style))

    story.append(Paragraph("9.2 Engineering Significance", h2_style))
    story.append(Paragraph(
        "The project demonstrates that high-performance, predictable virtualization orchestration can be achieved with minimal architectural footprint. By replacing heavyweight cloud daemons with lean asynchronous Python microservices and direct hypervisor Unix sockets, the solution achieves sub-second provisioning and robust fault tolerance without superfluous layers of abstraction.",
        body_style
    ))

    story.append(Paragraph("9.3 Next Steps & Future Enhancements", h2_style))
    story.append(Paragraph("1. <b>mTLS Transport Encryption:</b> Implementing mutual TLS across controller and worker endpoints for untrusted networks.", bullet_style))
    story.append(Paragraph("2. <b>Linux cgroup v2 Throttling:</b> Enforcing fine-grained CPU bandwidth and memory cgroup limits directly on VMM process trees.", bullet_style))
    story.append(Paragraph("3. <b>Multi-OS Image Catalog:</b> Extending provisioning to support multiple base operating system images with customizable cloud-init templates.", bullet_style))
    story.append(Paragraph("4. <b>Physical Multi-Host Deployment:</b> Migrating Node B from a nested VM to an independent bare-metal server across a physical Ethernet switch.", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report PDF built successfully: {filename}")

if __name__ == '__main__':
    output_pdf = "/home/rajyavardhan/ps023-submit/docs/PS023-TC246-report.pdf"
    build_pdf(output_pdf)
