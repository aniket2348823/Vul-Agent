"""
Alpha V6 Test Suite — Command Planning Tests.

Tests command planner without running any tools:
- Correct argv construction
- No shell strings in output
- Proper output path generation
- Timeout and parser_hint propagation
- Phase assignments
"""
import pytest
from pathlib import Path
from backend.tools.recon.commands import ReconCommand, ReconCommandPlanner
from backend.agents.alpha_recon.models import ReconScope, ScanMode


@pytest.fixture
def planner():
    return ReconCommandPlanner(tool_root="D:\\projects")


@pytest.fixture
def scope():
    return ReconScope(
        base_domain="example.com",
        allowed_hosts=["api.example.com"],
        scan_mode=ScanMode.STANDARD,
        max_rps=50,
        max_depth=3,
        explicit_authorization=True,
    )


@pytest.fixture
def raw_dir(tmp_path):
    return tmp_path / "raw"


class TestPassiveCommands:
    """Passive phase command planning."""

    def test_subfinder_command(self, planner, scope, raw_dir):
        cmds = planner.passive_commands(scope, raw_dir)
        subfinder_cmds = [c for c in cmds if c.tool_name == "subfinder"]
        assert len(subfinder_cmds) >= 1
        cmd = subfinder_cmds[0]
        assert cmd.phase == "passive_intelligence"
        assert "subfinder" in cmd.argv[0]
        assert "-d" in cmd.argv
        assert "example.com" in cmd.argv
        assert "-json" in cmd.argv or "-jsonl" in cmd.argv or "-oJ" in cmd.argv or "-o" in cmd.argv

    def test_no_shell_strings(self, planner, scope, raw_dir):
        cmds = planner.passive_commands(scope, raw_dir)
        for cmd in cmds:
            full = " ".join(str(a) for a in cmd.argv)
            assert "|" not in full, f"Shell pipe in {cmd.tool_name}: {cmd.argv}"
            assert "&&" not in full, f"Shell AND in {cmd.tool_name}: {cmd.argv}"
            assert "$(" not in full, f"Command substitution in {cmd.tool_name}: {cmd.argv}"

    def test_output_paths_are_absolute_or_relative(self, planner, scope, raw_dir):
        cmds = planner.passive_commands(scope, raw_dir)
        for cmd in cmds:
            assert isinstance(cmd.output_path, Path)

    def test_all_have_timeout(self, planner, scope, raw_dir):
        cmds = planner.passive_commands(scope, raw_dir)
        for cmd in cmds:
            assert cmd.timeout_seconds > 0

    def test_all_have_parser_hint(self, planner, scope, raw_dir):
        cmds = planner.passive_commands(scope, raw_dir)
        for cmd in cmds:
            assert cmd.parser_hint in {
                "jsonl", "json", "json-file", "lines", "urls", "xml", "csv", "custom",
            }


class TestDNSCommands:
    """DNS phase command planning."""

    def test_dnsx_command(self, planner, scope, raw_dir):
        hosts_file = raw_dir / "subdomains.txt"
        hosts_file.parent.mkdir(parents=True, exist_ok=True)
        hosts_file.write_text("api.example.com\nstaging.example.com\n")

        cmds = planner.dns_commands(scope, raw_dir, hosts_file)
        dnsx_cmds = [c for c in cmds if c.tool_name == "dnsx"]
        assert len(dnsx_cmds) >= 1
        cmd = dnsx_cmds[0]
        assert cmd.phase == "dns_infrastructure"
        assert "dnsx" in cmd.argv[0]


class TestHTTPCommands:
    """HTTP phase command planning."""

    def test_httpx_command(self, planner, scope, raw_dir):
        hosts_file = raw_dir / "live_hosts.txt"
        hosts_file.parent.mkdir(parents=True, exist_ok=True)
        hosts_file.write_text("api.example.com\n")

        cmds = planner.http_commands(scope, raw_dir, hosts_file)
        httpx_cmds = [c for c in cmds if c.tool_name == "httpx"]
        assert len(httpx_cmds) >= 1
        cmd = httpx_cmds[0]
        assert cmd.phase == "http_browser_intelligence"
        assert "httpx" in cmd.argv[0]


class TestDiscoveryCommands:
    """Discovery phase command planning."""

    def test_feroxbuster_command(self, planner, scope, raw_dir):
        raw_dir.mkdir(parents=True, exist_ok=True)
        urls = ["https://example.com"]
        cmds = planner.discovery_commands(scope, raw_dir, urls)
        ferox_cmds = [c for c in cmds if c.tool_name == "feroxbuster"]
        # feroxbuster may or may not be planned depending on mode
        for cmd in ferox_cmds:
            assert cmd.phase == "directory_route_discovery"
            assert "feroxbuster" in cmd.argv[0]


class TestReconCommandModel:
    """ReconCommand model validation."""

    def test_frozen_dataclass(self):
        cmd = ReconCommand(
            tool_name="test",
            phase="test_phase",
            argv=("echo", "hello"),
            output_path=Path("/tmp/out.txt"),
        )
        with pytest.raises(AttributeError):
            cmd.tool_name = "changed"

    def test_argv_is_tuple(self):
        cmd = ReconCommand(
            tool_name="test",
            phase="test_phase",
            argv=("subfinder", "-d", "example.com"),
            output_path=Path("/tmp/out.txt"),
        )
        assert isinstance(cmd.argv, tuple)
