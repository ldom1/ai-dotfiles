"""install-act.sh creates ~/.local/bin when it is missing (network tools stubbed)."""
import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "install-act.sh"


def stub(bin_dir, name, body):
    p = bin_dir / name
    p.write_text(f"#!/usr/bin/env bash\n{body}\n")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


def test_installs_into_a_missing_local_bin(tmp_path):
    bin_dir, home = tmp_path / "stubs", tmp_path / "home"
    bin_dir.mkdir()
    home.mkdir()
    # curl -fsSL -o <file> <url>: write the checksum list or a dummy archive.
    stub(bin_dir, "curl", 'out=$3; case "$4" in *checksums.txt) echo "x  act_Linux_x86_64.tar.gz" > "$out";; *) : > "$out";; esac')
    stub(bin_dir, "sha256sum", "cat > /dev/null")
    # tar -xzf <archive> -C <dir> act: write a fake act binary.
    stub(bin_dir, "tar", 'printf "#!/usr/bin/env bash\\necho act version 0.2.89\\n" > "$4/act"; chmod +x "$4/act"')
    r = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True,
                       env={**os.environ, "HOME": str(home), "PATH": f"{bin_dir}:{os.environ['PATH']}"})
    assert r.returncode == 0, r.stderr
    assert (home / ".local" / "bin" / "act").is_file() and "0.2.89" in r.stdout
