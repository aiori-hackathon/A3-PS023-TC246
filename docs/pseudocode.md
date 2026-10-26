# Pseudocode: VM placement with refusal handling

This is the core of `create_vm` in `src/controller/vm_service.py`.

```
create_vm(name, vcpus, memory_mb, disk_gb):
    poll all nodes
    skipped = {}                      # node -> why it failed during this request
    loop:
        lock placement
            for each node:
                healthy = node is HEALTHY and node not in skipped
                free    = schedulable memory
                          - memory reserved by PENDING / RUNNING / UNKNOWN VMs
            choice = healthy node with the most free memory that can fit
                     memory_mb   (node_id breaks ties)
            if no choice:
                store the decision with every candidate
                error 409: "no node accepted the VM: <node: reason>, ..."
            store a PENDING row and the decision
        unlock

        try worker(choice).create_vm(...)
            success:
                mark the row RUNNING, store the IP, return the VM
            worker unreachable:
                delete the row, mark the node UNHEALTHY, skip it, retry
            worker refuses (HTTP 409):
                delete the row, skip the node, retry
            any other worker error:
                delete the row, return 502
```

# Pseudocode: stopping a VM without leaking a process

This is `stop` in `src/worker/vm_manager.py`.

```
stop(vm):
    if the VMM process is not alive:
        remove socket and pid files, reap the child; return "already-stopped"

    ask the VM to power off (power button)          # guest shuts down cleanly
    if the VMM exits within 30 s:  cleanup; return "graceful"

    send vm.shutdown and vmm.shutdown through the API
    if the VMM exits within 5 s:   cleanup; return "forced-api"

    send SIGTERM
    if the VMM exits within 5 s:   cleanup; return "sigterm"

    send SIGKILL
    if the VMM exits within 5 s:   cleanup; return "sigkill"
    otherwise: raise "VMM process will not die"

cleanup(vm):
    delete the socket, lock and pid files
    wait on the child process so no zombie remains
```

The process is trusted only if its pid file points to a live process whose
command line contains this VM's own socket path (guards against pid reuse).
