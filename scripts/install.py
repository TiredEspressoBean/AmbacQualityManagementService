#!/usr/bin/env python3
"""
Ambac Tracker - On-Premise Installation Script

Usage:
    python install.py                      # Interactive install
    python install.py --yes                # Accept all defaults
    python install.py --config config.yml  # Use config file
    python install.py --airgapped          # Airgapped mode
    python install.py --dry-run            # Preview changes
    python install.py --status             # Check installation
    python install.py --uninstall          # Remove installation
    python install.py --support-bundle     # Generate debug info
    python install.py --self-test          # Validate installer

Compile to standalone binary:
    pip install pyinstaller
    pyinstaller --onefile install.py
"""

import hashlib
import json
import os
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Any

# -----------------------------------------------------------------------------
# Dependency Management
# -----------------------------------------------------------------------------

REQUIRED_PACKAGES = ["rich", "python-dotenv", "pyyaml"]


def ensure_dependencies():
    """Install required packages if missing."""
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_").replace("pyyaml", "yaml"))
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"Installing dependencies: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing, "-q"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


ensure_dependencies()

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.syntax import Syntax
import logging


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------


@dataclass
class InstallConfig:
    """Installation configuration."""

    # Paths
    project_dir: Path = field(
        default_factory=lambda: Path(__file__).parent.parent.resolve()
    )

    # Mode flags
    airgapped: bool = False
    dry_run: bool = False
    verbose: bool = False
    non_interactive: bool = False  # --yes flag

    # App settings
    hostname: str = "localhost"
    http_port: int = 80
    https_port: int = 443
    enable_ai: bool = True
    enable_tls: bool = True

    # Database
    db_name: str = "tracker_AMBAC"
    db_user: str = "postgres"
    db_password: str = field(default_factory=lambda: secrets.token_hex(16))

    # Django
    django_secret: str = field(default_factory=lambda: secrets.token_hex(32))

    # Network
    http_proxy: str = ""
    https_proxy: str = ""
    no_proxy: str = "localhost,127.0.0.1"

    # Docker
    docker_network: str = "ambactracker-network"
    compose_profile: str = "local"

    @property
    def env_file(self) -> Path:
        return self.project_dir / ".env"

    @property
    def images_dir(self) -> Path:
        return self.project_dir / "images"

    @property
    def backups_dir(self) -> Path:
        return self.project_dir / "backups"

    @property
    def log_file(self) -> Path:
        return self.project_dir / "install.log"

    @property
    def checksums_file(self) -> Path:
        return self.project_dir / "images" / "checksums.sha256"

    @classmethod
    def from_file(cls, path: Path) -> "InstallConfig":
        """Load configuration from YAML or JSON file."""
        content = path.read_text()

        if path.suffix in (".yml", ".yaml"):
            data = yaml.safe_load(content)
        elif path.suffix == ".json":
            data = json.loads(content)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

        # Convert project_dir to Path if present
        if "project_dir" in data:
            data["project_dir"] = Path(data["project_dir"])

        return cls(**data)

    def to_yaml(self) -> str:
        """Export configuration to YAML."""
        data = asdict(self)
        # Convert Path to string
        data["project_dir"] = str(data["project_dir"])
        return yaml.dump(data, default_flow_style=False, sort_keys=False)


# -----------------------------------------------------------------------------
# Rollback Manager
# -----------------------------------------------------------------------------


class RollbackManager:
    """Manages rollback of installation steps on failure."""

    def __init__(self, console: Console, dry_run: bool = False):
        self.console = console
        self.dry_run = dry_run
        self.actions: list[tuple[str, Callable, tuple, dict]] = []

    def register(self, name: str, rollback_fn: Callable, *args, **kwargs):
        """Register a rollback action."""
        self.actions.append((name, rollback_fn, args, kwargs))

    def execute(self):
        """Execute all rollback actions in reverse order."""
        if not self.actions:
            return

        self.console.print("\n[yellow]Rolling back changes...[/yellow]")

        for name, fn, args, kwargs in reversed(self.actions):
            try:
                self.console.print(f"  Reverting: {name}")
                if not self.dry_run:
                    fn(*args, **kwargs)
            except Exception as e:
                self.console.print(f"  [red]Rollback failed for {name}: {e}[/red]")

        self.console.print("[yellow]Rollback complete.[/yellow]")

    def clear(self):
        """Clear all registered actions (call after successful install)."""
        self.actions.clear()


# -----------------------------------------------------------------------------
# Installer Class
# -----------------------------------------------------------------------------


class Installer:
    """Ambac Tracker installer."""

    VERSION = "1.0.0"
    MIN_DOCKER_VERSION = "20.0.0"
    MIN_DISK_GB = 10
    MIN_MEMORY_GB = 4

    def __init__(self, config: InstallConfig):
        self.config = config
        self.console = Console()
        self.steps_completed: list[str] = []
        self.rollback = RollbackManager(self.console, config.dry_run)
        self.setup_logging()

    def setup_logging(self):
        """Configure file and console logging."""
        self.logger = logging.getLogger("installer")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()

        # File handler - always verbose
        fh = logging.FileHandler(self.config.log_file, mode="w", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        self.logger.addHandler(fh)

        self.log(f"Installer v{self.VERSION} started")
        self.log(f"Platform: {platform.system()} {platform.release()} {platform.machine()}")
        self.log(f"Python: {sys.version}")
        self.log(f"Working directory: {self.config.project_dir}")
        self.log(f"Config: airgapped={self.config.airgapped}, dry_run={self.config.dry_run}")

    def log(self, message: str, level: str = "info"):
        """Log message to file."""
        getattr(self.logger, level)(message)

    def run_command(
        self,
        cmd: list[str],
        capture: bool = False,
        check: bool = True,
        timeout: int = 300,
        env: Optional[dict] = None,
    ) -> Optional[str]:
        """Run a shell command."""
        cmd_str = " ".join(cmd)
        self.log(f"Running: {cmd_str}")

        if self.config.dry_run:
            self.console.print(f"  [dim]Would run: {cmd_str}[/dim]")
            return "" if capture else None

        # Merge environment with proxy settings
        full_env = os.environ.copy()
        if self.config.http_proxy:
            full_env["HTTP_PROXY"] = self.config.http_proxy
            full_env["http_proxy"] = self.config.http_proxy
        if self.config.https_proxy:
            full_env["HTTPS_PROXY"] = self.config.https_proxy
            full_env["https_proxy"] = self.config.https_proxy
        if self.config.no_proxy:
            full_env["NO_PROXY"] = self.config.no_proxy
            full_env["no_proxy"] = self.config.no_proxy
        if env:
            full_env.update(env)

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                check=check,
                cwd=self.config.project_dir,
                timeout=timeout,
                env=full_env,
            )
            if capture and result.stdout:
                self.log(f"Output: {result.stdout[:1000]}")
            return result.stdout if capture else None
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out after {timeout}s: {cmd_str}", "error")
            raise
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed (exit {e.returncode}): {e.stderr}", "error")
            if check:
                raise
            return None
        except FileNotFoundError:
            self.log(f"Command not found: {cmd[0]}", "error")
            return None

    def prompt(self, message: str, default: str = "") -> str:
        """Prompt for input, or return default in non-interactive mode."""
        if self.config.non_interactive:
            self.log(f"Non-interactive: using default '{default}' for '{message}'")
            return default
        return Prompt.ask(message, default=default)

    def confirm(self, message: str, default: bool = True) -> bool:
        """Confirm action, or return default in non-interactive mode."""
        if self.config.non_interactive:
            self.log(f"Non-interactive: using default {default} for '{message}'")
            return default
        return Confirm.ask(message, default=default)

    def print_header(self):
        """Print installation header."""
        mode = []
        if self.config.airgapped:
            mode.append("airgapped")
        if self.config.dry_run:
            mode.append("dry-run")
        if self.config.non_interactive:
            mode.append("non-interactive")

        mode_str = f" ({', '.join(mode)})" if mode else ""

        self.console.print(
            Panel.fit(
                f"[bold]Ambac Tracker[/bold] v{self.VERSION}\n"
                f"On-Premise Installation{mode_str}",
                border_style="blue",
            )
        )

    # -------------------------------------------------------------------------
    # Prerequisite Checks
    # -------------------------------------------------------------------------

    def check_existing_installation(self) -> Optional[dict]:
        """Check if there's an existing installation."""
        if not self.config.env_file.exists():
            return None

        result = self.run_command(
            ["docker", "compose", "ps", "--format", "json"],
            capture=True,
            check=False,
        )

        containers = []
        if result:
            try:
                for line in result.strip().split("\n"):
                    if line:
                        containers.append(json.loads(line))
            except json.JSONDecodeError:
                pass

        return {"containers": containers, "env_exists": True}

    def check_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(("127.0.0.1", port))
                return result != 0
        except Exception:
            return True

    def check_docker(self) -> tuple[bool, str, str]:
        """Check Docker installation and version."""
        output = self.run_command(["docker", "--version"], capture=True, check=False)
        if not output:
            return False, "", "Docker is not installed. Install from https://docs.docker.com/get-docker/"

        try:
            version = output.split()[2].rstrip(",")
        except IndexError:
            version = "unknown"

        if self.run_command(["docker", "info"], capture=True, check=False) is None:
            return False, version, "Docker is installed but not running. Please start Docker Desktop or the Docker service."

        return True, version, "OK"

    def check_docker_compose(self) -> tuple[bool, str, str]:
        """Check Docker Compose installation."""
        output = self.run_command(
            ["docker", "compose", "version"], capture=True, check=False
        )
        if not output:
            return False, "", "Docker Compose is not installed. It should be included with Docker Desktop."

        version = output.strip().split()[-1]
        return True, version, "OK"

    def check_disk_space(self) -> tuple[bool, int, str]:
        """Check available disk space."""
        try:
            total, used, free = shutil.disk_usage(self.config.project_dir)
            free_gb = free // (1024**3)

            if free_gb >= self.MIN_DISK_GB:
                return True, free_gb, "OK"
            else:
                return (
                    False,
                    free_gb,
                    f"Need {self.MIN_DISK_GB}GB free, only {free_gb}GB available. Free up disk space and try again.",
                )
        except Exception as e:
            return True, 0, f"Could not check: {e}"

    def check_memory(self) -> tuple[bool, int, str]:
        """Check available system memory (cross-platform)."""
        try:
            system = platform.system()

            if system == "Windows":
                import ctypes

                kernel32 = ctypes.windll.kernel32

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                total_gb = stat.ullTotalPhys // (1024**3)

            elif system == "Darwin":  # macOS
                output = subprocess.check_output(
                    ["sysctl", "-n", "hw.memsize"], text=True
                )
                total_gb = int(output.strip()) // (1024**3)

            else:  # Linux
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            total_kb = int(line.split()[1])
                            total_gb = total_kb // (1024**2)
                            break
                    else:
                        raise ValueError("MemTotal not found")

            if total_gb >= self.MIN_MEMORY_GB:
                return True, total_gb, "OK"
            else:
                return (
                    False,
                    total_gb,
                    f"Need {self.MIN_MEMORY_GB}GB RAM, only {total_gb}GB available.",
                )
        except Exception as e:
            self.log(f"Memory check failed: {e}", "warning")
            return True, 0, f"Could not check: {e}"

    def run_prerequisites(self) -> bool:
        """Run all prerequisite checks."""
        self.console.print("\n[bold]Checking prerequisites...[/bold]")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Status", width=3)
        table.add_column("Check", width=20)
        table.add_column("Details")

        all_passed = True
        warnings = []

        # Docker
        ok, version, msg = self.check_docker()
        if ok:
            table.add_row("[green]✓[/green]", "Docker", f"v{version}")
        else:
            table.add_row("[red]✗[/red]", "Docker", f"[red]{msg}[/red]")
            all_passed = False

        # Docker Compose
        ok, version, msg = self.check_docker_compose()
        if ok:
            table.add_row("[green]✓[/green]", "Docker Compose", f"v{version}")
        else:
            table.add_row("[red]✗[/red]", "Docker Compose", f"[red]{msg}[/red]")
            all_passed = False

        # Disk space
        ok, value, msg = self.check_disk_space()
        if ok:
            table.add_row("[green]✓[/green]", "Disk Space", f"{value} GB free")
        else:
            table.add_row("[red]✗[/red]", "Disk Space", f"[red]{msg}[/red]")
            all_passed = False

        # Memory
        ok, value, msg = self.check_memory()
        if ok:
            table.add_row("[green]✓[/green]", "Memory", f"{value} GB")
        else:
            table.add_row("[yellow]![/yellow]", "Memory", f"[yellow]{msg}[/yellow]")
            warnings.append(msg)

        # Port availability
        ports_in_use = []
        for port in [self.config.http_port, self.config.https_port]:
            if not self.check_port_available(port):
                ports_in_use.append(port)

        if ports_in_use:
            table.add_row(
                "[yellow]![/yellow]",
                "Ports",
                f"[yellow]In use: {ports_in_use}. Stop other services or change ports.[/yellow]",
            )
            warnings.append(f"Ports {ports_in_use} are in use")
        else:
            table.add_row(
                "[green]✓[/green]",
                "Ports",
                f"{self.config.http_port}, {self.config.https_port} available",
            )

        # Proxy detection
        http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        if http_proxy:
            self.config.http_proxy = http_proxy
            self.config.https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy", http_proxy)
            table.add_row("[blue]i[/blue]", "Proxy", f"Detected: {http_proxy[:50]}...")

        self.console.print(table)

        if warnings:
            self.console.print()
            for w in warnings:
                self.console.print(f"  [yellow]⚠[/yellow]  {w}")

        if not all_passed:
            self.console.print(
                "\n[red]Please fix the errors above and try again.[/red]"
            )

        return all_passed

    # -------------------------------------------------------------------------
    # Checksum Verification (Airgapped)
    # -------------------------------------------------------------------------

    def verify_checksums(self) -> bool:
        """Verify image checksums for airgapped installation."""
        if not self.config.checksums_file.exists():
            self.log("No checksums file found, skipping verification", "warning")
            return True

        self.console.print("\n[bold]Verifying image integrity...[/bold]")

        checksums = {}
        for line in self.config.checksums_file.read_text().strip().split("\n"):
            if line and not line.startswith("#"):
                parts = line.split()
                if len(parts) >= 2:
                    checksums[parts[1]] = parts[0]

        all_valid = True
        for filename, expected_hash in checksums.items():
            filepath = self.config.images_dir / filename
            if not filepath.exists():
                self.console.print(f"  [red]✗[/red] {filename} - missing")
                all_valid = False
                continue

            # Calculate SHA256
            sha256 = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            actual_hash = sha256.hexdigest()

            if actual_hash == expected_hash:
                self.console.print(f"  [green]✓[/green] {filename}")
            else:
                self.console.print(f"  [red]✗[/red] {filename} - checksum mismatch")
                self.log(f"Checksum mismatch: {filename} expected {expected_hash}, got {actual_hash}", "error")
                all_valid = False

        if not all_valid:
            self.console.print(
                "\n[red]Image verification failed. Files may be corrupted.[/red]"
            )
            self.console.print("Re-download the release package and try again.")

        return all_valid

    # -------------------------------------------------------------------------
    # Installation Steps
    # -------------------------------------------------------------------------

    def step(self, name: str, func: Callable, *args, **kwargs) -> bool:
        """Run an installation step with logging and error handling."""
        self.log(f"=== Starting step: {name} ===")
        try:
            result = func(*args, **kwargs)
            if result:
                self.steps_completed.append(name)
                self.log(f"=== Completed step: {name} ===")
            else:
                self.log(f"=== Step returned False: {name} ===", "warning")
            return result
        except Exception as e:
            self.log(f"=== Failed step {name}: {e} ===", "error")
            self.log(traceback.format_exc(), "error")
            self.console.print(f"[red]Error in {name}:[/red] {e}")
            return False

    def setup_network(self) -> bool:
        """Create Docker network."""
        self.console.print("\n[bold]Setting up Docker network...[/bold]")

        result = self.run_command(
            ["docker", "network", "inspect", self.config.docker_network],
            capture=True,
            check=False,
        )

        if result:
            self.console.print("  [green]✓[/green] Network already exists")
        else:
            self.run_command(
                ["docker", "network", "create", self.config.docker_network]
            )
            self.console.print("  [green]✓[/green] Network created")

            # Register rollback
            self.rollback.register(
                "Remove network",
                lambda: self.run_command(
                    ["docker", "network", "rm", self.config.docker_network],
                    check=False,
                ),
            )

        return True

    def load_images(self) -> bool:
        """Load Docker images from tar files (airgapped mode)."""
        if not self.config.images_dir.exists():
            return True

        tar_files = list(self.config.images_dir.glob("*.tar"))
        if not tar_files:
            return True

        # Verify checksums first
        if not self.verify_checksums():
            return False

        self.console.print("\n[bold]Loading Docker images...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Loading images...", total=len(tar_files))

            for tar_file in tar_files:
                progress.update(task, description=f"Loading {tar_file.name}...")
                self.run_command(["docker", "load", "-i", str(tar_file)])
                progress.advance(task)

        self.console.print("  [green]✓[/green] All images loaded")
        return True

    def configure_environment(self) -> bool:
        """Configure the .env file."""
        self.console.print("\n[bold]Configuring environment...[/bold]")

        # Check existing
        if self.config.env_file.exists():
            if not self.confirm("  [yellow].env exists.[/yellow] Reconfigure?", default=False):
                self.console.print("  [green]✓[/green] Using existing configuration")
                return True

            # Backup existing
            backup_path = self.config.env_file.with_suffix(".env.backup")
            if not self.config.dry_run:
                shutil.copy(self.config.env_file, backup_path)
            self.log(f"Backed up existing .env to {backup_path}")

        # Interactive configuration (or defaults in non-interactive mode)
        self.console.print("\n  [bold]Application Settings[/bold]")

        self.config.hostname = self.prompt("  Hostname/domain", default=self.config.hostname)
        self.config.enable_tls = self.confirm("  Enable HTTPS?", default=self.config.enable_tls)
        self.config.enable_ai = self.confirm("  Enable AI features?", default=self.config.enable_ai)

        # Proxy configuration
        if self.config.http_proxy or not self.config.non_interactive:
            if self.confirm("  Configure proxy settings?", default=bool(self.config.http_proxy)):
                self.config.http_proxy = self.prompt("  HTTP Proxy", default=self.config.http_proxy)
                self.config.https_proxy = self.prompt("  HTTPS Proxy", default=self.config.https_proxy or self.config.http_proxy)

        # Generate .env content
        env_content = self._generate_env_content()

        if self.config.dry_run:
            self.console.print("  [dim]Would write .env file[/dim]")
        else:
            self.config.env_file.write_text(env_content)
            self.rollback.register(
                "Remove .env",
                lambda: self.config.env_file.unlink() if self.config.env_file.exists() else None,
            )

        self.console.print("  [green]✓[/green] Configuration saved")

        # Show summary
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Setting")
        table.add_column("Value")
        table.add_row("Hostname", self.config.hostname)
        table.add_row("HTTPS", "Enabled" if self.config.enable_tls else "Disabled")
        table.add_row("AI Features", "Enabled" if self.config.enable_ai else "Disabled")
        table.add_row("Database", self.config.db_name)
        if self.config.http_proxy:
            table.add_row("Proxy", self.config.http_proxy[:40] + "...")
        self.console.print(table)

        return True

    def _generate_env_content(self) -> str:
        """Generate .env file content."""
        proxy_section = ""
        if self.config.http_proxy:
            proxy_section = f"""
# =============================================================================
# PROXY (for corporate networks)
# =============================================================================
HTTP_PROXY={self.config.http_proxy}
HTTPS_PROXY={self.config.https_proxy}
NO_PROXY={self.config.no_proxy}
"""

        return f"""# Ambac Tracker Configuration
# Generated: {datetime.now().isoformat()}
# Installer: v{self.VERSION}

# =============================================================================
# DATABASE
# =============================================================================
POSTGRES_PASSWORD={self.config.db_password}
POSTGRES_DB={self.config.db_name}
POSTGRES_USER={self.config.db_user}
POSTGRES_HOST=postgres

# =============================================================================
# DJANGO
# =============================================================================
DJANGO_SECRET_KEY={self.config.django_secret}
DJANGO_DEBUG=false
ALLOWED_HOSTS={self.config.hostname},localhost,127.0.0.1

# =============================================================================
# DEPLOYMENT
# =============================================================================
DEPLOYMENT_MODE=dedicated

# =============================================================================
# AI FEATURES
# =============================================================================
AI_EMBED_ENABLED={'true' if self.config.enable_ai else 'false'}
OLLAMA_URL=http://ollama:11434
OLLAMA_EMBED_MODEL=nomic-embed-text

# =============================================================================
# SECURITY
# =============================================================================
CORS_ALLOWED_ORIGINS=https://{self.config.hostname},http://{self.config.hostname}
CSRF_TRUSTED_ORIGINS=https://{self.config.hostname},http://{self.config.hostname}
CORS_ALLOW_CREDENTIALS=true
{proxy_section}
# =============================================================================
# EMAIL (Optional - configure for notifications)
# =============================================================================
# EMAIL_HOST=smtp.example.com
# EMAIL_PORT=587
# EMAIL_HOST_USER=
# EMAIL_HOST_PASSWORD=
# EMAIL_USE_TLS=true
# DEFAULT_FROM_EMAIL=noreply@{self.config.hostname}

# =============================================================================
# INTEGRATIONS (Optional)
# =============================================================================
# HUBSPOT_API_KEY=
# SENTRY_DSN=
"""

    def create_directories(self) -> bool:
        """Create required directories."""
        self.console.print("\n[bold]Creating directories...[/bold]")

        dirs = [
            self.config.backups_dir,
            self.config.project_dir / "PartsTracker" / "media",
            self.config.project_dir / "certs",
        ]

        for d in dirs:
            if not self.config.dry_run:
                d.mkdir(parents=True, exist_ok=True)
            self.log(f"Created directory: {d}")

        self.console.print("  [green]✓[/green] Directories ready")
        return True

    def pull_images(self) -> bool:
        """Pull and build Docker images."""
        if self.config.airgapped:
            self.console.print("\n[dim]Skipping pull (airgapped mode)[/dim]")
            return True

        self.console.print("\n[bold]Pulling and building images...[/bold]")
        self.console.print("  [dim]This may take several minutes...[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Pulling base images...", total=None)
            self.run_command(
                ["docker", "compose", "pull", "postgres", "redis"], check=False
            )

            progress.update(task, description="Building application images...")
            self.run_command(["docker", "compose", "build"])

        self.console.print("  [green]✓[/green] Images ready")
        return True

    def start_services(self) -> bool:
        """Start Docker services."""
        self.console.print("\n[bold]Starting services...[/bold]")

        profile = "local" if self.config.enable_tls else "production"
        self.run_command(["docker", "compose", "--profile", profile, "up", "-d"])

        # Register rollback
        self.rollback.register(
            "Stop services",
            lambda: self.run_command(["docker", "compose", "down"], check=False),
        )

        self.console.print("  [green]✓[/green] Services started")
        return True

    def wait_for_healthy(self, timeout: int = 180) -> bool:
        """Wait for services to be healthy."""
        self.console.print("\n[bold]Waiting for services to be ready...[/bold]")

        if self.config.dry_run:
            self.console.print("  [dim]Would wait for health check[/dim]")
            return True

        services = [
            ("postgres", "pg_isready -U postgres", "Database"),
            ("backend", "curl -sf http://localhost:8000/health/", "Backend API"),
        ]

        start_time = time.time()

        for service_name, health_cmd, display_name in services:
            service_start = time.time()

            while time.time() - start_time < timeout:
                result = self.run_command(
                    [
                        "docker",
                        "compose",
                        "exec",
                        "-T",
                        service_name,
                        "sh",
                        "-c",
                        health_cmd,
                    ],
                    capture=True,
                    check=False,
                )

                if result is not None:
                    elapsed = int(time.time() - service_start)
                    self.console.print(
                        f"  [green]✓[/green] {display_name} ready ({elapsed}s)"
                    )
                    break

                time.sleep(3)
            else:
                self.console.print(
                    f"  [red]✗[/red] {display_name} failed to start within {timeout}s"
                )
                self.console.print(
                    f"      Check logs: docker compose logs {service_name}"
                )
                return False

        return True

    def verify_installation(self) -> bool:
        """Run post-installation verification."""
        self.console.print("\n[bold]Verifying installation...[/bold]")

        if self.config.dry_run:
            self.console.print("  [dim]Would verify installation[/dim]")
            return True

        checks = []

        # Check containers running
        result = self.run_command(
            ["docker", "compose", "ps", "--format", "{{.Name}}: {{.Status}}"],
            capture=True,
            check=False,
        )
        if result:
            running = result.count("Up")
            checks.append(("Containers", running >= 3, f"{running} running"))

        # Check backend responds
        result = self.run_command(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "curl",
                "-sf",
                "http://localhost:8000/health/",
            ],
            capture=True,
            check=False,
        )
        checks.append(("API Health", result is not None, "OK" if result else "Failed"))

        # Check database connection
        result = self.run_command(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "python",
                "manage.py",
                "check",
                "--database",
                "default",
            ],
            capture=True,
            check=False,
        )
        checks.append(
            ("Database", result is not None and "error" not in result.lower(), "Connected" if result else "Failed")
        )

        # Display results
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Status", width=3)
        table.add_column("Check")
        table.add_column("Details")

        all_passed = True
        for name, passed, details in checks:
            if passed:
                table.add_row("[green]✓[/green]", name, details)
            else:
                table.add_row("[red]✗[/red]", name, f"[red]{details}[/red]")
                all_passed = False

        self.console.print(table)

        return all_passed

    def print_summary(self):
        """Print installation summary."""
        protocol = "https" if self.config.enable_tls else "http"
        url = f"{protocol}://{self.config.hostname}"

        summary = f"""
[bold green]Installation Complete![/bold green]

[bold]Access the application:[/bold]
  {url}

[bold]Quick start:[/bold]
  1. Open {url} in your browser
  2. Log in with admin credentials from: docker compose logs backend | grep -i password
  3. Configure your organization settings

[bold]Useful commands:[/bold]
  docker compose logs -f        View logs
  docker compose ps             Check status
  docker compose restart        Restart services
  python scripts/backup.py      Backup database
  python scripts/install.py --status    Check health

[bold]Log file:[/bold]
  {self.config.log_file}

[bold]Need help?[/bold]
  python scripts/install.py --support-bundle
"""
        self.console.print(Panel(summary, title="Ambac Tracker", border_style="green"))

    # -------------------------------------------------------------------------
    # Uninstall
    # -------------------------------------------------------------------------

    def uninstall(self) -> bool:
        """Remove installation."""
        self.console.print(
            Panel.fit("[bold red]Uninstall Ambac Tracker[/bold red]", border_style="red")
        )

        self.console.print("\n[yellow]This will:[/yellow]")
        self.console.print("  • Stop and remove all containers")
        self.console.print("  • Remove Docker network")
        self.console.print("  • [bold]NOT[/bold] delete your data by default")

        if not self.confirm("\nProceed with uninstall?", default=False):
            self.console.print("Cancelled.")
            return False

        self.console.print("\n[bold]Stopping services...[/bold]")
        self.run_command(["docker", "compose", "down"], check=False)
        self.console.print("  [green]✓[/green] Services stopped")

        self.console.print("\n[bold]Removing network...[/bold]")
        self.run_command(
            ["docker", "network", "rm", self.config.docker_network], check=False
        )
        self.console.print("  [green]✓[/green] Network removed")

        if self.confirm("\nDelete configuration (.env)?", default=False):
            if self.config.env_file.exists():
                self.config.env_file.unlink()
                self.console.print("  [green]✓[/green] Removed .env")

        if self.confirm("Delete database volume? [bold red]ALL DATA WILL BE LOST[/bold red]", default=False):
            self.run_command(
                ["docker", "volume", "rm", "ambactracker_postgres_data"], check=False
            )
            self.console.print("  [green]✓[/green] Removed database volume")

        self.console.print("\n[green]Uninstall complete.[/green]")
        return True

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def show_status(self):
        """Show current installation status."""
        self.console.print(
            Panel.fit("[bold]Ambac Tracker Status[/bold]", border_style="blue")
        )

        existing = self.check_existing_installation()

        if not existing:
            self.console.print("\n[yellow]Not installed[/yellow]")
            self.console.print("Run: python install.py")
            return

        self.console.print("\n[bold]Configuration:[/bold]")
        self.console.print(
            f"  .env file: {'[green]✓ exists[/green]' if existing['env_exists'] else '[red]✗ missing[/red]'}"
        )

        # Show container status
        self.console.print("\n[bold]Services:[/bold]")
        result = self.run_command(
            [
                "docker",
                "compose",
                "ps",
                "--format",
                "table {{.Name}}\t{{.Status}}\t{{.Ports}}",
            ],
            capture=True,
            check=False,
        )
        if result:
            self.console.print(result)
        else:
            self.console.print("  [dim]No containers found[/dim]")

        # Health check
        self.console.print("\n[bold]Health:[/bold]")
        result = self.run_command(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "backend",
                "curl",
                "-sf",
                "http://localhost:8000/health/",
            ],
            capture=True,
            check=False,
        )
        if result:
            self.console.print("  Backend: [green]healthy[/green]")
        else:
            self.console.print("  Backend: [red]not responding[/red]")

        # Disk usage
        self.console.print("\n[bold]Disk Usage:[/bold]")
        result = self.run_command(
            ["docker", "system", "df", "--format", "table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}"],
            capture=True,
            check=False,
        )
        if result:
            self.console.print(result)

    # -------------------------------------------------------------------------
    # Support Bundle
    # -------------------------------------------------------------------------

    def generate_support_bundle(self) -> bool:
        """Generate a support bundle for debugging."""
        self.console.print(
            Panel.fit("[bold]Generating Support Bundle[/bold]", border_style="blue")
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_dir = self.config.project_dir / f"support_bundle_{timestamp}"
        bundle_dir.mkdir(exist_ok=True)

        self.console.print(f"\nCollecting information to: {bundle_dir}")

        # System info
        self.console.print("  Collecting system info...")
        system_info = {
            "timestamp": datetime.now().isoformat(),
            "installer_version": self.VERSION,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python": sys.version,
            },
            "docker": {},
            "disk": {},
            "memory": {},
        }

        # Docker info
        result = self.run_command(["docker", "version", "--format", "json"], capture=True, check=False)
        if result:
            try:
                system_info["docker"]["version"] = json.loads(result)
            except json.JSONDecodeError:
                system_info["docker"]["version"] = result

        # Disk space
        try:
            total, used, free = shutil.disk_usage(self.config.project_dir)
            system_info["disk"] = {
                "total_gb": total // (1024**3),
                "used_gb": used // (1024**3),
                "free_gb": free // (1024**3),
            }
        except Exception as e:
            system_info["disk"]["error"] = str(e)

        (bundle_dir / "system_info.json").write_text(
            json.dumps(system_info, indent=2, default=str)
        )

        # Docker logs
        self.console.print("  Collecting Docker logs...")
        services = ["backend", "postgres", "redis", "celery-worker"]
        for service in services:
            result = self.run_command(
                ["docker", "compose", "logs", "--tail", "500", service],
                capture=True,
                check=False,
            )
            if result:
                (bundle_dir / f"logs_{service}.txt").write_text(result)

        # Container status
        self.console.print("  Collecting container status...")
        result = self.run_command(
            ["docker", "compose", "ps", "-a"], capture=True, check=False
        )
        if result:
            (bundle_dir / "container_status.txt").write_text(result)

        # Copy install log
        if self.config.log_file.exists():
            shutil.copy(self.config.log_file, bundle_dir / "install.log")

        # Copy .env (redacted)
        if self.config.env_file.exists():
            env_content = self.config.env_file.read_text()
            # Redact sensitive values
            redacted = []
            for line in env_content.split("\n"):
                if "=" in line and not line.strip().startswith("#"):
                    key, _, value = line.partition("=")
                    if any(s in key.upper() for s in ["PASSWORD", "SECRET", "KEY", "TOKEN"]):
                        redacted.append(f"{key}=<REDACTED>")
                    else:
                        redacted.append(line)
                else:
                    redacted.append(line)
            (bundle_dir / "env_redacted.txt").write_text("\n".join(redacted))

        # Create archive
        self.console.print("  Creating archive...")
        archive_path = self.config.project_dir / f"support_bundle_{timestamp}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(bundle_dir, arcname=f"support_bundle_{timestamp}")

        # Cleanup temp directory
        shutil.rmtree(bundle_dir)

        self.console.print(f"\n[green]✓[/green] Support bundle created: {archive_path}")
        self.console.print("\nSend this file to support for assistance.")
        self.console.print("[dim]Note: Sensitive values (passwords, keys) have been redacted.[/dim]")

        return True

    # -------------------------------------------------------------------------
    # Self Test
    # -------------------------------------------------------------------------

    def self_test(self) -> bool:
        """Run installer self-tests."""
        self.console.print(
            Panel.fit("[bold]Installer Self-Test[/bold]", border_style="blue")
        )

        tests = []

        # Test 1: Dependencies
        self.console.print("\n[bold]Testing dependencies...[/bold]")
        try:
            import rich
            import yaml
            import dotenv
            tests.append(("Python dependencies", True, "All imported"))
        except ImportError as e:
            tests.append(("Python dependencies", False, str(e)))

        # Test 2: Docker available
        self.console.print("[bold]Testing Docker...[/bold]")
        ok, version, msg = self.check_docker()
        tests.append(("Docker", ok, version if ok else msg))

        # Test 3: Docker Compose available
        ok, version, msg = self.check_docker_compose()
        tests.append(("Docker Compose", ok, version if ok else msg))

        # Test 4: Project structure
        self.console.print("[bold]Testing project structure...[/bold]")
        required_files = [
            "docker-compose.yml",
            "PartsTracker/Dockerfile",
            "PartsTracker/manage.py",
        ]
        missing = [f for f in required_files if not (self.config.project_dir / f).exists()]
        tests.append(
            ("Project files", len(missing) == 0, f"Missing: {missing}" if missing else "All present")
        )

        # Test 5: Write permissions
        self.console.print("[bold]Testing permissions...[/bold]")
        try:
            test_file = self.config.project_dir / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            tests.append(("Write permissions", True, "OK"))
        except Exception as e:
            tests.append(("Write permissions", False, str(e)))

        # Display results
        self.console.print("\n[bold]Results:[/bold]")
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Status", width=3)
        table.add_column("Test")
        table.add_column("Details")

        all_passed = True
        for name, passed, details in tests:
            if passed:
                table.add_row("[green]✓[/green]", name, details)
            else:
                table.add_row("[red]✗[/red]", name, f"[red]{details}[/red]")
                all_passed = False

        self.console.print(table)

        if all_passed:
            self.console.print("\n[green]All tests passed![/green]")
        else:
            self.console.print("\n[red]Some tests failed.[/red]")

        return all_passed

    # -------------------------------------------------------------------------
    # Main
    # -------------------------------------------------------------------------

    def run(self) -> bool:
        """Run the installation."""
        self.print_header()

        # Check for existing installation
        existing = self.check_existing_installation()
        if existing and existing.get("containers"):
            self.console.print("\n[yellow]Existing installation detected.[/yellow]")
            if not self.confirm("Continue and reconfigure?", default=False):
                self.console.print(
                    "Use --status to check or --uninstall to remove."
                )
                return False

        # Run installation steps
        steps = [
            ("Prerequisites", self.run_prerequisites),
            ("Network", self.setup_network),
            ("Load Images", self.load_images),
            ("Configuration", self.configure_environment),
            ("Directories", self.create_directories),
            ("Pull Images", self.pull_images),
            ("Start Services", self.start_services),
            ("Health Check", self.wait_for_healthy),
            ("Verification", self.verify_installation),
        ]

        for name, func in steps:
            if not self.step(name, func):
                self.console.print(f"\n[red]Installation failed at: {name}[/red]")
                self.console.print(f"Log file: {self.config.log_file}")

                if self.confirm("\nRollback changes?", default=True):
                    self.rollback.execute()

                return False

        # Clear rollback actions on success
        self.rollback.clear()

        self.print_summary()
        return True


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Ambac Tracker On-Premise Installation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install.py                      Interactive installation
  python install.py --yes                Accept all defaults
  python install.py --config prod.yml    Use config file
  python install.py --dry-run            Preview without changes
  python install.py --status             Check current status
  python install.py --uninstall          Remove installation
  python install.py --support-bundle     Generate debug info
        """,
    )
    parser.add_argument(
        "--config", "-c", type=Path, help="Configuration file (YAML or JSON)"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Non-interactive mode, accept defaults"
    )
    parser.add_argument(
        "--airgapped", action="store_true", help="Airgapped mode (load images from tar)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen without changes"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--uninstall", action="store_true", help="Remove installation"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show installation status"
    )
    parser.add_argument(
        "--support-bundle", action="store_true", help="Generate support bundle"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run installer self-tests"
    )
    parser.add_argument(
        "--export-config", type=Path, help="Export current config to file"
    )

    args = parser.parse_args()

    # Load config from file or create default
    if args.config:
        if not args.config.exists():
            print(f"Error: Config file not found: {args.config}")
            sys.exit(1)
        config = InstallConfig.from_file(args.config)
    else:
        config = InstallConfig()

    # Apply CLI overrides
    config.airgapped = args.airgapped or config.airgapped
    config.dry_run = args.dry_run
    config.verbose = args.verbose
    config.non_interactive = args.yes

    # Auto-detect airgapped mode
    if config.images_dir.exists() and list(config.images_dir.glob("*.tar")):
        config.airgapped = True

    # Export config and exit
    if args.export_config:
        args.export_config.write_text(config.to_yaml())
        print(f"Configuration exported to: {args.export_config}")
        sys.exit(0)

    installer = Installer(config)

    try:
        if args.self_test:
            success = installer.self_test()
        elif args.support_bundle:
            success = installer.generate_support_bundle()
        elif args.status:
            installer.show_status()
            success = True
        elif args.uninstall:
            success = installer.uninstall()
        else:
            success = installer.run()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        installer.console.print("\n[yellow]Cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        installer.console.print(f"\n[red]Unexpected error:[/red] {e}")
        installer.log(traceback.format_exc(), "error")
        installer.console.print(f"Check log file: {config.log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()
