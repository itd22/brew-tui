import subprocess


class BrewCLIRunner:
    """Runs the real `brew` executable, if one is on PATH."""

    def list_packages(self) -> list[str] | None:
        try:
            result = subprocess.run(
                ["brew", "list", "--formula"],
                capture_output=True, text=True, timeout=30,
            )
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())

    def install(self, name: str, on_line=None) -> str | None:
        """Runs `brew install <name>` for real, streaming each output line to on_line."""
        try:
            proc = subprocess.Popen(
                ["brew", "install", name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
        except (FileNotFoundError, OSError):
            return None
        lines: list[str] = []
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n")
            lines.append(line)
            if on_line is not None:
                on_line(line)
        proc.wait()
        return "\n".join(lines)

    def uninstall(self, name: str, on_line=None) -> str | None:
        """Runs `brew uninstall <name>` for real, streaming each output line to on_line."""
        try:
            proc = subprocess.Popen(
                ["brew", "uninstall", name],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
        except (FileNotFoundError, OSError):
            return None
        lines: list[str] = []
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\n")
            lines.append(line)
            if on_line is not None:
                on_line(line)
        proc.wait()
        return "\n".join(lines)
