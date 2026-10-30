import matplotlib.pyplot as plt
import matplotlib.patches as patches

def generate_placement_flowchart():
    fig, ax = plt.subplots(figsize=(10, 8), dpi=300)
    ax.axis('off')
    
    # Styles
    box_blue = dict(boxstyle='round,pad=0.5', facecolor='#E8F0FE', edgecolor='#1A73E8', linewidth=1.5)
    box_green = dict(boxstyle='round,pad=0.5', facecolor='#E6F4EA', edgecolor='#137333', linewidth=1.5)
    box_yellow = dict(boxstyle='round,pad=0.5', facecolor='#FEF7E0', edgecolor='#F9AB00', linewidth=1.5)
    box_red = dict(boxstyle='round,pad=0.5', facecolor='#FCE8E6', edgecolor='#C5221F', linewidth=1.5)
    box_gray = dict(boxstyle='round,pad=0.5', facecolor='#F1F3F4', edgecolor='#5F6368', linewidth=1.5)
    
    arrow = dict(arrowstyle='->', lw=1.5, color='#3C4043')

    # Nodes
    ax.text(0.5, 0.95, "Client: POST /vms\n(vCPUs, Memory MB, Disk GB)", ha='center', va='center', bbox=box_blue, fontsize=10, fontweight='bold')
    ax.text(0.5, 0.82, "1. Poll Nodes & Deduct Reserved Memory\n(Exclude PENDING, RUNNING, UNKNOWN VMs)", ha='center', va='center', bbox=box_gray, fontsize=9.5)
    ax.text(0.5, 0.69, "2. Candidate Selection (Scheduler)\nFilter HEALTHY & eligible; pick max schedulable memory\n(node_id breaks ties stably)", ha='center', va='center', bbox=box_gray, fontsize=9.5)
    
    # Decision: Any eligible node?
    ax.text(0.5, 0.54, "Any eligible node?", ha='center', va='center', bbox=box_yellow, fontsize=10, fontweight='bold')
    
    # Left branch: No
    ax.text(0.15, 0.54, "No eligible node\nRecord decision with\nper-node refusal reasons\nReturn HTTP 409", ha='center', va='center', bbox=box_red, fontsize=9)
    
    # Right/down branch: Yes
    ax.text(0.5, 0.39, "3. Atomic Reservation & Record Decision\nInsert PENDING row in SQLite DB", ha='center', va='center', bbox=box_yellow, fontsize=9.5)
    ax.text(0.5, 0.25, "4. Dispatch to Worker: POST /vms\n(Reflink base image, seed cloud-init, boot VMM)", ha='center', va='center', bbox=box_blue, fontsize=9.5)
    
    # Outcomes of worker call
    ax.text(0.85, 0.25, "Worker 409 Refusal\n(e.g., missing TAP)\nMark node refused,\nrollback PENDING,\nfall through to next node", ha='center', va='center', bbox=box_red, fontsize=8.5)
    ax.text(0.5, 0.08, "5. VM Created Successfully\nMark RUNNING, assign IP, return HTTP 201", ha='center', va='center', bbox=box_green, fontsize=10, fontweight='bold')

    # Arrows
    ax.annotate('', xy=(0.5, 0.87), xytext=(0.5, 0.91), arrowprops=arrow)
    ax.annotate('', xy=(0.5, 0.74), xytext=(0.5, 0.78), arrowprops=arrow)
    ax.annotate('', xy=(0.5, 0.58), xytext=(0.5, 0.64), arrowprops=arrow)
    
    # No branch
    ax.annotate('', xy=(0.26, 0.54), xytext=(0.38, 0.54), arrowprops=arrow)
    ax.text(0.32, 0.56, "No", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#C5221F')
    
    # Yes branch
    ax.annotate('', xy=(0.5, 0.44), xytext=(0.5, 0.50), arrowprops=arrow)
    ax.text(0.52, 0.47, "Yes", ha='left', va='center', fontsize=9, fontweight='bold', color='#137333')
    
    # Dispatch
    ax.annotate('', xy=(0.5, 0.30), xytext=(0.5, 0.34), arrowprops=arrow)
    ax.annotate('', xy=(0.5, 0.13), xytext=(0.5, 0.20), arrowprops=arrow)
    ax.text(0.52, 0.165, "Success", ha='left', va='center', fontsize=8.5, fontweight='bold', color='#137333')
    
    # Fallthrough loop
    ax.annotate('', xy=(0.72, 0.25), xytext=(0.65, 0.25), arrowprops=arrow)
    ax.annotate('', xy=(0.63, 0.69), xytext=(0.85, 0.32),
                arrowprops=dict(arrowstyle='->', lw=1.2, color='#C5221F', connectionstyle="arc3,rad=-0.3"))
    ax.text(0.82, 0.52, "Retry next candidate", ha='center', va='center', fontsize=8.5, color='#C5221F', fontweight='bold')

    plt.tight_layout()
    plt.savefig('/home/rajyavardhan/ps023-submit/docs/figures/placement_flowchart.png', bbox_inches='tight')
    plt.close()
    print("Generated placement_flowchart.png")

def generate_stop_escalation_flowchart():
    fig, ax = plt.subplots(figsize=(10, 7.5), dpi=300)
    ax.axis('off')

    box_blue = dict(boxstyle='round,pad=0.5', facecolor='#E8F0FE', edgecolor='#1A73E8', linewidth=1.5)
    box_green = dict(boxstyle='round,pad=0.5', facecolor='#E6F4EA', edgecolor='#137333', linewidth=1.5)
    box_yellow = dict(boxstyle='round,pad=0.5', facecolor='#FEF7E0', edgecolor='#F9AB00', linewidth=1.5)
    box_red = dict(boxstyle='round,pad=0.5', facecolor='#FCE8E6', edgecolor='#C5221F', linewidth=1.5)
    box_gray = dict(boxstyle='round,pad=0.5', facecolor='#F1F3F4', edgecolor='#5F6368', linewidth=1.5)
    arrow = dict(arrowstyle='->', lw=1.5, color='#3C4043')

    ax.text(0.5, 0.95, "Worker: stop(vm) Request Received", ha='center', va='center', bbox=box_blue, fontsize=10, fontweight='bold')
    ax.text(0.5, 0.83, "Verify PID & Socket Ownership (guards against PID reuse)\nIs VMM process alive?", ha='center', va='center', bbox=box_gray, fontsize=9)
    
    # Already stopped
    ax.text(0.12, 0.83, "Process dead:\nClean socket/pid,\nreap child ->\n'already-stopped'", ha='center', va='center', bbox=box_gray, fontsize=8)
    ax.annotate('', xy=(0.22, 0.83), xytext=(0.33, 0.83), arrowprops=arrow)
    ax.text(0.28, 0.85, "No", ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    # Escalation steps
    ax.text(0.5, 0.69, "Stage 1: ACPI Power Button (Guest OS clean shutdown)\nWait up to 30s for process exit", ha='center', va='center', bbox=box_yellow, fontsize=9)
    ax.text(0.5, 0.53, "Stage 2: API vm.shutdown + vmm.shutdown\nWait up to 5s for VMM exit", ha='center', va='center', bbox=box_yellow, fontsize=9)
    ax.text(0.5, 0.37, "Stage 3: POSIX SIGTERM Signal\nWait up to 5s for termination", ha='center', va='center', bbox=box_yellow, fontsize=9)
    ax.text(0.5, 0.21, "Stage 4: POSIX SIGKILL Signal\nWait up to 5s for forced kill", ha='center', va='center', bbox=box_red, fontsize=9)

    # Success / Clean Reap block
    ax.text(0.88, 0.45, "Process Exited Successfully\n\nCLEANUP & REAP:\n• Delete socket, lock, pid files\n• os.waitpid() reaps child\n• Guarantees NO zombie process!\n• Return HTTP 200 (stopped_via)", ha='center', va='center', bbox=box_green, fontsize=8.5, fontweight='bold')

    # Arrows for escalation
    ax.annotate('', xy=(0.5, 0.88), xytext=(0.5, 0.91), arrowprops=arrow)
    ax.annotate('', xy=(0.5, 0.74), xytext=(0.5, 0.78), arrowprops=arrow)
    ax.text(0.52, 0.76, "Alive", ha='left', va='center', fontsize=8, fontweight='bold')
    
    ax.annotate('', xy=(0.5, 0.58), xytext=(0.5, 0.64), arrowprops=arrow)
    ax.text(0.52, 0.61, "Timeout (30s)", ha='left', va='center', fontsize=8, color='#C5221F')

    ax.annotate('', xy=(0.5, 0.42), xytext=(0.5, 0.48), arrowprops=arrow)
    ax.text(0.52, 0.45, "Timeout (5s)", ha='left', va='center', fontsize=8, color='#C5221F')

    ax.annotate('', xy=(0.5, 0.26), xytext=(0.5, 0.32), arrowprops=arrow)
    ax.text(0.52, 0.29, "Timeout (5s)", ha='left', va='center', fontsize=8, color='#C5221F')

    # Arrows from each stage to Clean Reap
    for y, label in [(0.69, "Exited (graceful)"), (0.53, "Exited (forced-api)"), (0.37, "Exited (sigterm)"), (0.21, "Exited (sigkill)")]:
        ax.annotate('', xy=(0.76, 0.45), xytext=(0.67, y),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color='#137333', connectionstyle="arc3,rad=-0.1"))

    # Final failure
    ax.text(0.5, 0.08, "Failure: Process won't die (Raise error)", ha='center', va='center', bbox=box_red, fontsize=8.5)
    ax.annotate('', xy=(0.5, 0.11), xytext=(0.5, 0.17), arrowprops=arrow)
    ax.text(0.52, 0.14, "Timeout (5s)", ha='left', va='center', fontsize=8, color='#C5221F')

    plt.tight_layout()
    plt.savefig('/home/rajyavardhan/ps023-submit/docs/figures/stop_escalation_flowchart.png', bbox_inches='tight')
    plt.close()
    print("Generated stop_escalation_flowchart.png")

def generate_timeline():
    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=300)
    ax.axis('off')

    # Horizontal timeline axis
    ax.plot([0.5, 10.5], [2.2, 2.2], color='#1A73E8', lw=3, zorder=1)

    milestones = [
        ("Before 21 Oct", "Foundation", "• Ubuntu 24.04 raw base image\n• Reflink cloning & cloud-init seed\n• Prototype controller & worker API", 1.0, 1),
        ("21 Oct", "Node B Bootstrap", "• Nested KVM Ubuntu VM (node B)\n• br-inner & static routing\n• TAP pool tapvm0-7", 2.8, -1),
        ("23-24 Oct", "Hardening & Evidence", "• Cold start verified twice\n• Refusal fallthrough & labels\n• Frozen-VMM stop (70s HTTP 200)\n• Evidence logs recorded", 4.7, 1),
        ("25-27 Oct", "UI & Terminal", "• Mentoring Session 1\n• Web Dashboard (FastAPI)\n• xterm.js browser terminal (SSH)", 6.7, -1),
        ("28-29 Oct", "Testing & Review", "• 87 unit tests passing\n• Integration tests (3 pass, 1 skip)\n• Mentoring Session 2\n• Technical report draft", 8.6, 1),
        ("30 Oct (Today)", "Submission", "• Browser terminal verified\n• Formal Technical Report PDF\n• Video demo recording\n• Final repo push", 10.1, -1),
    ]

    for date_str, title, desc, x, side in milestones:
        # Dot on timeline
        color = '#137333' if "30 Oct" in date_str else '#1A73E8'
        ax.scatter([x], [2.2], s=120, color=color, zorder=3, edgecolor='white', lw=2)

        # Text position
        y_text = 2.9 if side == 1 else 0.8
        y_box = 3.2 if side == 1 else 1.2
        
        # Stems
        ax.plot([x, x], [2.2, 2.5 if side == 1 else 1.9], color='#5F6368', lw=1.2, linestyle=':')

        box_color = '#E6F4EA' if "30 Oct" in date_str else '#F8F9FA'
        border_color = '#137333' if "30 Oct" in date_str else '#BDC1C6'

        ax.text(x, y_box, f"{date_str}\n{title}", ha='center', va='center',
                fontsize=8.5, fontweight='bold', color='#202124',
                bbox=dict(boxstyle='round,pad=0.3', facecolor=box_color, edgecolor=border_color, lw=1))
        
        ax.text(x, y_box + (0.55 if side == 1 else -0.55), desc, ha='center', va='center',
                fontsize=7.2, color='#3C4043',
                bbox=dict(boxstyle='square,pad=0.2', facecolor='white', edgecolor='#E8EAED', lw=0.8))

    ax.set_xlim(0, 11)
    ax.set_ylim(-0.2, 4.5)

    plt.tight_layout()
    plt.savefig('/home/rajyavardhan/ps023-submit/docs/figures/timeline_graphic.png', bbox_inches='tight')
    plt.close()
    print("Generated timeline_graphic.png")

if __name__ == '__main__':
    generate_placement_flowchart()
    generate_stop_escalation_flowchart()
    generate_timeline()
