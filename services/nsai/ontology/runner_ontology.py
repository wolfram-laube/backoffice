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
    Create the ontology with actual blauweiss_llc runners.

    Runner Mapping (2026-02):
        Ontology Name              MAB Tag        GitLab Tags
        ─────────────────────────  ─────────────  ──────────────────────
        gitlab-runner-nordic       nordic         docker-any, nordic
        Mac Docker Runner          mac-docker     docker-any, mac-docker
        Mac2 Docker Runner         mac2-docker    docker-any, mac2-docker
        Linux Yoga Docker Runner   linux-docker   docker-any, linux-docker
    """
    onto = RunnerOntology()

    # ── GCP Cloud Runner (Stockholm e2-small) ─────────────────
    onto.add_runner(
        name="gitlab-runner-nordic",
        capabilities=["docker", "shell", "gcp", "nordic", "linux", "x86_64"],
        tags=["docker-any", "shell", "nordic", "gcp"],
        cost_per_minute=0.01,
        online=True,
        mab_tag="nordic"
    )

    # ── Local Mac Docker Runner ───────────────────────────────
    onto.add_runner(
        name="Mac Docker Runner",
        capabilities=["docker", "macos"],
        tags=["docker-any", "mac-docker"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac-docker"
    )

    # ── Local Mac2 Docker Runner ──────────────────────────────
    onto.add_runner(
        name="Mac2 Docker Runner",
        capabilities=["docker", "macos"],
        tags=["docker-any", "mac2-docker"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="mac2-docker"
    )

    # ── Local Linux Yoga Docker Runner ────────────────────────
    onto.add_runner(
        name="Linux Yoga Docker Runner",
        capabilities=["docker", "shell", "linux", "x86_64"],
        tags=["docker-any", "linux-docker"],
        cost_per_minute=0.0,
        online=True,
        mab_tag="linux-docker"
    )

    return onto
