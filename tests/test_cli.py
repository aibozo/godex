import subprocess, sys, json
def test_cli_help():
    out = subprocess.check_output([sys.executable, "-m", "cli", "--help"])
    assert b"Cokeydex" in out