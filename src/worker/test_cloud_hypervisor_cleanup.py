"""Tests for Problem C: CloudHypervisor connection management, close(), and UDS client cleanup."""
import socket
import threading
from pathlib import Path

import pytest
from cloud_hypervisor import CloudHypervisor, VMMUnreachable


def test_cloud_hypervisor_close_and_context_manager(tmp_path):
    sock_path = str(tmp_path / "test.sock")
    ch = CloudHypervisor(sock_path)
    assert not ch._client.is_closed

    ch.close()
    assert ch._client.is_closed

    # Context manager test
    with CloudHypervisor(sock_path) as ch2:
        assert not ch2._client.is_closed
    assert ch2._client.is_closed


def test_cloud_hypervisor_uds_sequential_connections_cleaned_up(tmp_path):
    sock_path = str(tmp_path / "mock_vmm.sock")

    # Start a minimal UDS HTTP server that responds to /api/v1/vm.info
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(16)
    server.settimeout(2.0)

    stop_server = threading.Event()
    accepted_connections = []

    def handle_server():
        while not stop_server.is_set():
            try:
                conn, _ = server.accept()
                accepted_connections.append(conn)
                # Read request
                req = conn.recv(1024)
                if req:
                    resp = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Content-Length: 19\r\n"
                        b"Connection: close\r\n"
                        b"\r\n"
                        b'{"state":"Running"}'
                    )
                    conn.sendall(resp)
                conn.close()
            except socket.timeout:
                continue
            except Exception:
                break

    t = threading.Thread(target=handle_server, daemon=True)
    t.start()

    try:
        # Run 20 sequential calls via context manager
        for i in range(20):
            with CloudHypervisor(sock_path) as ch:
                state = ch.state()
                assert state == "Running"
                assert not ch._client.is_closed
            # Confirmed closed immediately after exiting with block
            assert ch._client.is_closed

        assert len(accepted_connections) == 20
    finally:
        stop_server.set()
        server.close()
        t.join(timeout=1.0)


def test_twenty_plus_sequential_status_calls_against_fake_vmm_never_503(tmp_path):
    sock_path = str(tmp_path / "vmm_seq.sock")

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(32)
    server.settimeout(2.0)

    stop_server = threading.Event()
    success_count = 0

    def fake_vmm_loop():
        nonlocal success_count
        while not stop_server.is_set():
            try:
                conn, _ = server.accept()
                data = conn.recv(1024)
                if data:
                    body = b'{"state":"Running"}'
                    resp = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: application/json\r\n"
                        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                        b"Connection: close\r\n"
                        b"\r\n" + body
                    )
                    conn.sendall(resp)
                    success_count += 1
                conn.close()
            except socket.timeout:
                continue
            except Exception:
                break

    srv_thread = threading.Thread(target=fake_vmm_loop, daemon=True)
    srv_thread.start()

    try:
        # 25 sequential status queries: none should ever fail with 503 or VMMUnreachable
        results = []
        for call_idx in range(25):
            with CloudHypervisor(sock_path) as ch:
                st = ch.state()
                results.append(st)
                assert st == "Running"
                # Ensure client is active during block
                assert not ch._client.is_closed
            # Ensure client socket resources released immediately after block
            assert ch._client.is_closed

        assert len(results) == 25
        assert all(r == "Running" for r in results)
        assert success_count == 25
    finally:
        stop_server.set()
        server.close()
        srv_thread.join(timeout=1.0)
