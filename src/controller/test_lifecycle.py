import pytest

import database as db
import vm_service as vs
from conftest import DOWN, REMOTE


def test_full_lifecycle(env):
    vm = vs.create_vm("w1", 1, 512, 4, path=env)
    assert vm["status"] == "RUNNING"
    assert vs.stop_vm(vm["id"], env)["status"] == "STOPPED"
    assert vs.start_vm(vm["id"], env)["status"] == "RUNNING"
    assert len(vs.list_vms(env)) == 1
    vs.delete_vm(vm["id"], env)
    assert vs.list_vms(env) == []
    assert REMOTE["node-a"] == {}


def test_delete_when_worker_lost_the_vm(env):
    vm = vs.create_vm("w1", 1, 512, 4, path=env)
    REMOTE["node-a"].clear()
    vs.delete_vm(vm["id"], env)  # worker says 404: still fine
    assert vs.list_vms(env) == []


def test_unknown_vm(env):
    with pytest.raises(vs.NotFound):
        vs.get_vm("vm-nope", env)


def test_stop_on_unreachable_node_keeps_the_row(env):
    vm = vs.create_vm("w1", 1, 512, 4, path=env)
    DOWN.add("node-a")
    with pytest.raises(vs.NodeUnavailable):
        vs.stop_vm(vm["id"], env)
    assert db.get_vm(vm["id"], env) is not None
