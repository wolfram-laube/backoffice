"""
Runner Capability Ontology

OWL-based semantic model for GitLab CI runner capabilities.
Enables reasoning about runner suitability for specific jobs.

Classes:
    RunnerOntology: Main ontology manager for runner capabilities

Example:
    >>> onto = RunnerOntology()
    >>> onto.add_runner("nordic", capabilities=["docker", "shell", "gcp"])
    >>> runners = onto.get_runners_with_capability("docker")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from enum import Enum, auto
import json


class CapabilityType(Enum):
    """Runner capability categories."""
    EXECUTOR = auto()      # docker, shell, kubernetes
    PLATFORM = auto()      # linux, macos, windows
    CLOUD = auto()         # gcp, aws, azure
    HARDWARE = auto()      # gpu, arm64, x86_64
    NETWORK = auto()       # region-eu, region-us, vpn
    CUSTOM = auto()        # user-defined tags


@dataclass
class RunnerCapability:
    """A single capability with metadata."""
    name: str
    cap_type: CapabilityType
    description: str = ""
    constraints: Dict[str, any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        return self.name == other.name


@dataclass
class Runner:
    """A GitLab CI runner with its capabilities."""
    name: str
    runner_id: Optional[int] = None
    capabilities: Set[RunnerCapability] = field(default_factory=set)
    tags: List[str] = field(default_factory=list)
    online: bool = True
    cost_per_minute: float = 0.0
    mab_tag: str = ""  # Tag used by MAB service for this runner

    def has_capability(self, cap_name: str) -> bool:
        return any(c.name == cap_name for c in self.capabilities)

    def has_all_capabilities(self, cap_names: List[str]) -> bool:
        return all(self.has_capability(c) for c in cap_names)

    def has_any_capability(self, cap_names: List[str]) -> bool:
        return any(self.has_capability(c) for c in cap_names)


class RunnerOntology:
    """
    OWL-inspired ontology for runner capabilities.

    Provides semantic reasoning about runner suitability based on
    declared capabilities and job requirements.
    """

    STANDARD_CAPABILITIES = {
        "docker": CapabilityType.EXECUTOR,
        "shell": CapabilityType.EXECUTOR,
        "kubernetes": CapabilityType.EXECUTOR,
        "docker-machine": CapabilityType.EXECUTOR,
        "linux": CapabilityType.PLATFORM,
        "macos": CapabilityType.PLATFORM,
        "windows": CapabilityType.PLATFORM,
        "gcp": CapabilityType.CLOUD,
        "aws": CapabilityType.CLOUD,
        "azure": CapabilityType.CLOUD,
        "gpu": CapabilityType.HARDWARE,
        "arm64": CapabilityType.HARDWARE,
        "x86_64": CapabilityType.HARDWARE,
        "nordic": CapabilityType.NETWORK,
        "eu-west": CapabilityType.NETWORK,
        "us-east": CapabilityType.NETWORK,
    }

    CAPABILITY_IMPLICATIONS = {
        "docker": ["linux"],
        "gcp": ["cloud"],
        "aws": ["cloud"],
        "azure": ["cloud"],
        "nordic": ["eu-west", "gcp"],
    }

    def __init__(self):
        self.runners: Dict[str, Runner] = {}
        self.capabilities: Dict[str, RunnerCapability] = {}
        self._mab_tag_map: Dict[str, str] = {}  # mab_tag → runner_name
        self._init_standard_capabilities()

    def _init_standard_capabilities(self):
        for name, cap_type in self.STANDARD_CAPABILITIES.items():
            self.capabilities[name] = RunnerCapability(name=name, cap_type=cap_type)

    def add_capability(self, name: str, cap_type: CapabilityType,
                       description: str = "", **constraints) -> RunnerCapability:
        cap = RunnerCapability(name=name, cap_type=cap_type,
                               description=description, constraints=constraints)
        self.capabilities[name] = cap
        return cap

    def add_runner(self, name: str, runner_id: int = None,
                   capabilities: List[str] = None,
                   tags: List[str] = None,
                   cost_per_minute: float = 0.0,
                   online: bool = True,
                   mab_tag: str = "") -> Runner:
        """Register a runner with its capabilities and MAB tag mapping."""
        caps = set()
        for cap_name in (capabilities or []):
            if cap_name in self.capabilities:
                caps.add(self.capabilities[cap_name])
                for implied in self.CAPABILITY_IMPLICATIONS.get(cap_name, []):
                    if implied in self.capabilities:
                        caps.add(self.capabilities[implied])
            else:
                new_cap = self.add_capability(cap_name, CapabilityType.CUSTOM)
                caps.add(new_cap)

        runner = Runner(
            name=name, runner_id=runner_id, capabilities=caps,
            tags=tags or [], cost_per_minute=cost_per_minute,
            online=online, mab_tag=mab_tag or name
        )
        self.runners[name] = runner
        self._mab_tag_map[runner.mab_tag] = name
        return runner

    def runner_name_for_mab_tag(self, mab_tag: str) -> Optional[str]:
        """Resolve MAB service tag → ontology runner name."""
        return self._mab_tag_map.get(mab_tag)

    def mab_tag_for_runner(self, runner_name: str) -> Optional[str]:
        """Get MAB service tag for a runner."""
        runner = self.runners.get(runner_name)
        return runner.mab_tag if runner else None

    def get_runners_with_capability(self, cap_name: str) -> List[Runner]:
        return [r for r in self.runners.values() if r.has_capability(cap_name)]

    def get_runners_with_all_capabilities(self, cap_names: List[str]) -> List[Runner]:
        return [r for r in self.runners.values() if r.has_all_capabilities(cap_names)]

    def get_feasible_runners(self, required: List[str],
                             excluded: List[str] = None) -> List[Runner]:
        excluded = excluded or []
        feasible = []
        for runner in self.runners.values():
            if not runner.online:
                continue
            if not runner.has_all_capabilities(required):
                continue
            if any(runner.has_capability(e) for e in excluded):
                continue
            feasible.append(runner)
        return feasible

    def to_dict(self) -> dict:
        return {
            "runners": {
                name: {
                    "runner_id": r.runner_id,
                    "capabilities": sorted(c.name for c in r.capabilities),
                    "tags": r.tags,
                    "online": r.online,
                    "cost_per_minute": r.cost_per_minute,
                    "mab_tag": r.mab_tag
                }
                for name, r in self.runners.items()
            },
            "capabilities": sorted(self.capabilities.keys())
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "RunnerOntology":
        onto = cls()
        for name, rdata in data.get("runners", {}).items():
            onto.add_runner(
                name=name,
                runner_id=rdata.get("runner_id"),
                capabilities=rdata.get("capabilities", []),
                tags=rdata.get("tags", []),
                cost_per_minute=rdata.get("cost_per_minute", 0.0),
                mab_tag=rdata.get("mab_tag", "")
            )
        return onto


# ============================================================
# Production Ontology
# ============================================================

def create_blauweiss_ontology() -> RunnerOntology:
    """
    Create the ontology with the complete blauweiss_llc runner fleet.

    Runner Fleet (2026-02, aligned with INF-002):

        Machine     Executor   Ontology Name              ID          MAB Tag        GitLab Tags
        ──────────  ─────────  ─────────────────────────   ──────────  ─────────────  ───────────────────────────────────
        GCP Nordic  Docker     gitlab-runner-nordic        51608579    nordic         docker-any, shell-any, nordic, gcp
        Mac         Docker     Mac Docker Runner           51336735    mac-docker     docker-any, mac-docker, mac-any
        Mac2        Docker     Mac2 Docker Runner          51337424    mac2-docker    docker-any, mac2-docker, mac-any
        Linux Yoga  Docker     Linux Yoga Docker Runner    51337426    linux-docker   docker-any, linux-docker, linux-any
        Mac         Shell      Mac Shell Runner            51336483    mac-shell      shell-any, mac-group-shell, mac-any
        Mac2        Shell      Mac2 Shell Runner           51337423    mac2-shell     shell-any, mac2-shell, mac-any
        Linux Yoga  Shell      Linux Yoga Shell Runner     51337425    linux-shell    shell-any, linux-shell, linux-any
        Mac         K8s        Mac K8s Runner              51336736    mac-k8s        k8s-any, mac-k8s, mac-any
        Mac2        K8s        Mac2 K8s Runner             51337457    mac2-k8s       k8s-any, mac2-k8s, mac-any
        Linux Yoga  K8s        Linux Yoga K8s Runner       51337498    linux-k8s      k8s-any, linux-k8s, linux-any
        GCP Nordic  K8s        Nordic K8s Runner           51408312    nordic-k8s     k8s-any, gcp-k8s, nordic

    Tag Hierarchy:
        any-runner ⊃ {docker-any, shell-any, k8s-any}
        docker-any ⊃ {nordic, mac-docker, mac2-docker, linux-docker}
        shell-any  ⊃ {nordic, mac-group-shell, mac2-shell, linux-shell}
        k8s-any    ⊃ {mac-k8s, mac2-k8s, linux-k8s, gcp-k8s}
    """
    onto = RunnerOntology()

    # ═══════════════════════════════════════════════════════════
    # DOCKER EXECUTORS (4 runners, tag: docker-any)
    # ═══════════════════════════════════════════════════════════

    # ── GCP Cloud Runner (Stockholm e2-small) ─────────────────
    onto.add_runner(
        name="gitlab-runner-nordic",
        runner_id=51608579,
        capabilities=["docker", "shell", "gcp", "nordic", "linux", "x86_64"],
        tags=["docker-any", "shell-any", "nordic", "gcp", "gcp-any", "any-runner"],
        cost_per_minute=0.01,
        online=True,
        mab_tag="nordic"
    )

    # ── Local Mac Docker Runner ───────────────────────────────
    onto.add_runner(
        name="Mac Docker Runner",
        runner_id=51336735,
        capabilities=["docker", "macos", "arm64"],
        tags=["docker-any", "mac-docker", "mac-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac-docker"
    )

    # ── Local Mac2 Docker Runner ──────────────────────────────
    onto.add_runner(
        name="Mac2 Docker Runner",
        runner_id=51337424,
        capabilities=["docker", "macos", "arm64"],
        tags=["docker-any", "mac2-docker", "mac-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac2-docker"
    )

    # ── Local Linux Yoga Docker Runner ────────────────────────
    onto.add_runner(
        name="Linux Yoga Docker Runner",
        runner_id=51337426,
        capabilities=["docker", "shell", "linux", "x86_64"],
        tags=["docker-any", "linux-docker", "linux-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="linux-docker"
    )

    # ═══════════════════════════════════════════════════════════
    # SHELL EXECUTORS (3 runners, tag: shell-any)
    # Note: Nordic also has shell-any (defined above)
    # ═══════════════════════════════════════════════════════════

    # ── Local Mac Shell Runner ────────────────────────────────
    onto.add_runner(
        name="Mac Shell Runner",
        runner_id=51336483,
        capabilities=["shell", "macos", "arm64"],
        tags=["shell-any", "mac-group-shell", "mac-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac-shell"
    )

    # ── Local Mac2 Shell Runner ───────────────────────────────
    onto.add_runner(
        name="Mac2 Shell Runner",
        runner_id=51337423,
        capabilities=["shell", "macos", "arm64"],
        tags=["shell-any", "mac2-shell", "mac-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac2-shell"
    )

    # ── Local Linux Yoga Shell Runner ─────────────────────────
    onto.add_runner(
        name="Linux Yoga Shell Runner",
        runner_id=51337425,
        capabilities=["shell", "linux", "x86_64"],
        tags=["shell-any", "linux-shell", "linux-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="linux-shell"
    )

    # ═══════════════════════════════════════════════════════════
    # KUBERNETES EXECUTORS (4 runners, tag: k8s-any)
    # ═══════════════════════════════════════════════════════════

    # ── Local Mac K8s Runner ──────────────────────────────────
    onto.add_runner(
        name="Mac K8s Runner",
        runner_id=51336736,
        capabilities=["kubernetes", "macos", "arm64"],
        tags=["k8s-any", "mac-k8s", "mac-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac-k8s"
    )

    # ── Local Mac2 K8s Runner ─────────────────────────────────
    onto.add_runner(
        name="Mac2 K8s Runner",
        runner_id=51337457,
        capabilities=["kubernetes", "macos", "arm64"],
        tags=["k8s-any", "mac2-k8s", "mac-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac2-k8s"
    )

    # ── Local Linux Yoga K8s Runner ───────────────────────────
    onto.add_runner(
        name="Linux Yoga K8s Runner",
        runner_id=51337498,
        capabilities=["kubernetes", "linux", "x86_64"],
        tags=["k8s-any", "linux-k8s", "linux-any", "any-runner"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="linux-k8s"
    )

    # ── GCP Nordic K8s Runner (k3s, currently offline) ────────
    onto.add_runner(
        name="Nordic K8s Runner",
        runner_id=51408312,
        capabilities=["kubernetes", "gcp", "linux", "x86_64"],
        tags=["k8s-any", "gcp-k8s", "gcp-any", "nordic", "any-runner"],
        cost_per_minute=0.01,
        online=False,   # k3s not running on Nordic VM
        mab_tag="nordic-k8s"
    )

    return onto
