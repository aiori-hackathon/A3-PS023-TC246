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
