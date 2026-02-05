"""
Runner Capability Ontology

OWL-based semantic model for GitLab CI runner capabilities.
Enables reasoning about runner suitability for specific jobs.

Classes:
    RunnerOntology: Main ontology manager for runner capabilities

Example:
    >>> onto = RunnerOntology()
    >>> onto.add_runner("nordic", capabilities=["docker", "shell", "gcp"])
    >>> onto.add_runner("mac-local", capabilities=["shell", "macos"])
    >>> runners = onto.get_runners_with_capability("docker")
    >>> print(runners)  # ["nordic"]
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
    cost_per_minute: float = 0.0  # For cost-aware selection
    
    def has_capability(self, cap_name: str) -> bool:
        """Check if runner has a specific capability."""
        return any(c.name == cap_name for c in self.capabilities)
    
    def has_all_capabilities(self, cap_names: List[str]) -> bool:
        """Check if runner has ALL specified capabilities."""
        return all(self.has_capability(c) for c in cap_names)
    
    def has_any_capability(self, cap_names: List[str]) -> bool:
        """Check if runner has ANY of the specified capabilities."""
        return any(self.has_capability(c) for c in cap_names)


class RunnerOntology:
    """
    OWL-inspired ontology for runner capabilities.
    
    Provides semantic reasoning about runner suitability based on
    declared capabilities and job requirements.
    
    Attributes:
        runners: Dictionary of registered runners
        capabilities: Dictionary of defined capabilities
        capability_hierarchy: Parent-child relationships between capabilities
    """
    
    # Predefined capability taxonomy
    STANDARD_CAPABILITIES = {
        # Executors
        "docker": CapabilityType.EXECUTOR,
        "shell": CapabilityType.EXECUTOR,
        "kubernetes": CapabilityType.EXECUTOR,
        "docker-machine": CapabilityType.EXECUTOR,
        
        # Platforms
        "linux": CapabilityType.PLATFORM,
        "macos": CapabilityType.PLATFORM,
        "windows": CapabilityType.PLATFORM,
        
        # Cloud providers
        "gcp": CapabilityType.CLOUD,
        "aws": CapabilityType.CLOUD,
        "azure": CapabilityType.CLOUD,
        
        # Hardware
        "gpu": CapabilityType.HARDWARE,
        "arm64": CapabilityType.HARDWARE,
        "x86_64": CapabilityType.HARDWARE,
        
        # Regions
        "nordic": CapabilityType.NETWORK,
        "eu-west": CapabilityType.NETWORK,
        "us-east": CapabilityType.NETWORK,
    }
    
    # Capability implications (A implies B)
    CAPABILITY_IMPLICATIONS = {
        "docker": ["linux"],           # Docker runners typically run Linux
        "gcp": ["cloud"],
        "aws": ["cloud"],
        "azure": ["cloud"],
        "nordic": ["eu-west", "gcp"],  # Nordic runner is in GCP EU
    }
    
    def __init__(self):
        self.runners: Dict[str, Runner] = {}
        self.capabilities: Dict[str, RunnerCapability] = {}
        self._init_standard_capabilities()
    
    def _init_standard_capabilities(self):
        """Initialize the standard capability taxonomy."""
        for name, cap_type in self.STANDARD_CAPABILITIES.items():
            self.capabilities[name] = RunnerCapability(
                name=name,
                cap_type=cap_type
            )
    
    def add_capability(self, name: str, cap_type: CapabilityType, 
                       description: str = "", **constraints) -> RunnerCapability:
        """Define a new capability in the ontology."""
        cap = RunnerCapability(
            name=name,
            cap_type=cap_type,
            description=description,
            constraints=constraints
        )
        self.capabilities[name] = cap
        return cap
    
    def add_runner(self, name: str, runner_id: int = None,
                   capabilities: List[str] = None, 
                   tags: List[str] = None,
                   cost_per_minute: float = 0.0,
                   online: bool = True) -> Runner:
        """
        Register a runner with its capabilities.
        
        Args:
            name: Unique runner identifier
            runner_id: GitLab runner ID
            capabilities: List of capability names
            tags: GitLab runner tags
            cost_per_minute: Cost for billing calculations
            
        Returns:
            The registered Runner object
        """
        caps = set()
        for cap_name in (capabilities or []):
            if cap_name in self.capabilities:
                caps.add(self.capabilities[cap_name])
                # Add implied capabilities
                for implied in self.CAPABILITY_IMPLICATIONS.get(cap_name, []):
                    if implied in self.capabilities:
                        caps.add(self.capabilities[implied])
            else:
                # Create custom capability on-the-fly
                new_cap = self.add_capability(cap_name, CapabilityType.CUSTOM)
                caps.add(new_cap)
        
        runner = Runner(
            name=name,
            runner_id=runner_id,
            capabilities=caps,
            tags=tags or [],
            cost_per_minute=cost_per_minute,
            online=online
        )
        self.runners[name] = runner
        return runner
    
    def get_runners_with_capability(self, cap_name: str) -> List[Runner]:
        """Find all runners that have a specific capability."""
        return [r for r in self.runners.values() if r.has_capability(cap_name)]
    
    def get_runners_with_all_capabilities(self, cap_names: List[str]) -> List[Runner]:
        """Find runners that have ALL specified capabilities."""
        return [r for r in self.runners.values() if r.has_all_capabilities(cap_names)]
    
    def get_feasible_runners(self, required: List[str], 
                             excluded: List[str] = None) -> List[Runner]:
        """
        Get runners that satisfy requirements and don't have exclusions.
        
        This is the main query method for the CSP layer.
        
        Args:
            required: Capabilities the runner MUST have
            excluded: Capabilities the runner must NOT have
            
        Returns:
            List of feasible runners
        """
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
        """Serialize ontology to dictionary."""
        return {
            "runners": {
                name: {
                    "runner_id": r.runner_id,
                    "capabilities": [c.name for c in r.capabilities],
                    "tags": r.tags,
                    "online": r.online,
                    "cost_per_minute": r.cost_per_minute
                }
                for name, r in self.runners.items()
            },
            "capabilities": list(self.capabilities.keys())
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize ontology to JSON."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: dict) -> "RunnerOntology":
        """Deserialize ontology from dictionary."""
        onto = cls()
        for name, rdata in data.get("runners", {}).items():
            onto.add_runner(
                name=name,
                runner_id=rdata.get("runner_id"),
                capabilities=rdata.get("capabilities", []),
                tags=rdata.get("tags", []),
                cost_per_minute=rdata.get("cost_per_minute", 0.0)
            )
        return onto


# Convenience function to create production ontology
def create_blauweiss_ontology() -> RunnerOntology:
    """
    Create the ontology with actual blauweiss_llc runners.
    
    Current runners (as of 2026-02):
        - gitlab-runner-nordic: GCP Stockholm, docker + shell
        - (local runners as backup)
    """
    onto = RunnerOntology()
    
    # Production runner in Stockholm
    onto.add_runner(
        name="gitlab-runner-nordic",
        capabilities=["docker", "shell", "gcp", "nordic", "linux"],
        tags=["docker-any", "shell", "nordic", "gcp"],
        cost_per_minute=0.01  # e2-small pricing estimate
    )
    
    # Local backup runners (when available)
    onto.add_runner(
        name="mac-local",
        capabilities=["shell", "macos"],
        tags=["shell", "macos", "local"],
        cost_per_minute=0.0,  # No cloud cost
        online=False  # Mark as offline by default
    )
    
    onto.add_runner(
        name="linux-local", 
        capabilities=["docker", "shell", "linux"],
        tags=["docker", "shell", "linux", "local"],
        cost_per_minute=0.0,
        online=False
    )
    
    return onto
