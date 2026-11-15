from scheduler import NodeView, place

A = lambda mb, ok=True: NodeView("node-a", ok, mb)
B = lambda mb, ok=True: NodeView("node-b", ok, mb)


def test_more_memory_wins():
    assert place([A(10240), B(4096)], 2048).selected == "node-a"


def test_only_b_fits():
    assert place([A(1024), B(4096)], 2048).selected == "node-b"


def test_nobody_fits():
    assert place([A(1024), B(1024)], 4096).selected is None


def test_unhealthy_skipped():
    d = place([A(10240, ok=False), B(4096)], 2048)
    assert d.selected == "node-b"
    assert d.candidates[0]["verdict"] == "skipped: unhealthy"


def test_exact_fit_allowed():
    assert place([A(2048), B(1024)], 2048).selected == "node-a"


def test_tie_is_stable():
    assert place([A(4096), B(4096)], 1024).selected == "node-b"


# ---------- Pluggable Policy Tests ----------

def test_default_policy_is_memory_aware():
    # A has 8192, B has 4096 -> A wins under default
    d_default = place([A(8192), B(4096)], 1024)
    d_explicit = place([A(8192), B(4096)], 1024, policy="memory_aware")
    assert d_default.selected == "node-a"
    assert d_default.reason == "highest available memory"
    assert d_default.policy == "memory_aware"
    assert d_default.selected == d_explicit.selected
    assert d_default.reason == d_explicit.reason


def test_first_fit_policy():
    # Node list ordered [A, B]. Both fit 1024. A comes first, so A is selected even if B has more RAM.
    d1 = place([A(2048), B(8192)], 1024, policy="first_fit")
    assert d1.selected == "node-a"
    assert d1.reason == "first fit with sufficient memory"
    assert d1.policy == "first_fit"

    # Node list ordered [B, A]. B comes first, so B is selected.
    d2 = place([B(8192), A(2048)], 1024, policy="first_fit")
    assert d2.selected == "node-b"

    # If first node has insufficient memory, first_fit moves to next
    d3 = place([A(512), B(4096)], 1024, policy="first_fit")
    assert d3.selected == "node-b"


def test_best_fit_policy():
    # A has 2048 (tight fit for 1024), B has 8192.
    # best_fit chooses A (smallest sufficient memory to pack VMs).
    d1 = place([A(2048), B(8192)], 1024, policy="best_fit")
    assert d1.selected == "node-a"
    assert d1.reason == "smallest sufficient memory"
    assert d1.policy == "best_fit"

    # If A has 8192 and B has 2048, best_fit chooses B
    d2 = place([A(8192), B(2048)], 1024, policy="best_fit")
    assert d2.selected == "node-b"

    # Ties in best_fit broken deterministically
    d3 = place([A(2048), B(2048)], 1024, policy="best_fit")
    assert d3.selected == "node-a"  # min tie-breaker picks smaller node_id 'node-a' < 'node-b'


def test_policy_env_override(monkeypatch):
    monkeypatch.setenv("PS023_SCHEDULER_POLICY", "best_fit")
    # Without per-request policy, environment variable selects best_fit
    d = place([A(8192), B(2048)], 1024)
    assert d.selected == "node-b"
    assert d.policy == "best_fit"

    # Per-request override takes precedence over environment variable
    d_override = place([A(8192), B(2048)], 1024, policy="memory_aware")
    assert d_override.selected == "node-a"
    assert d_override.policy == "memory_aware"


def test_all_policies_respect_target_node_pin():
    for pol in ("memory_aware", "first_fit", "best_fit"):
        d = place([A(8192), B(4096)], 1024, target_node="node-b", policy=pol)
        assert d.selected == "node-b"
        assert "pinned to target node node-b" in d.reason


def test_all_policies_respect_unhealthy_and_capacity():
    for pol in ("memory_aware", "first_fit", "best_fit"):
        # Unhealthy skipped
        d_unhealthy = place([A(8192, ok=False), B(4096)], 1024, policy=pol)
        assert d_unhealthy.selected == "node-b"

        # Insufficient memory
        d_nomem = place([A(512), B(512)], 1024, policy=pol)
        assert d_nomem.selected is None
        assert d_nomem.reason == "no healthy node has enough memory"

