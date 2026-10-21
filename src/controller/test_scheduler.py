from scheduler import NodeView, place

A = lambda mb, ok=True: NodeView("node-a", ok, mb)
B = lambda mb, ok=True: NodeView("node-b", ok, mb)

# 1. both fit: the one with more memory wins
d = place([A(10240), B(4096)], 2048)
assert d.selected == "node-a", d
# 2. only B fits
d = place([A(1024), B(4096)], 2048)
assert d.selected == "node-b", d
# 3. nobody fits
d = place([A(1024), B(1024)], 4096)
assert d.selected is None, d
# 4. unhealthy node is skipped even with more memory
d = place([A(10240, ok=False), B(4096)], 2048)
assert d.selected == "node-b", d
# 5. exactly enough memory is allowed
d = place([A(2048), B(1024)], 2048)
assert d.selected == "node-a", d
# 6. tie goes to a stable choice
d = place([A(4096), B(4096)], 1024)
assert d.selected == "node-b", d

print("all 6 scheduler tests passed")
print(place([A(10240), B(3072)], 2048))
