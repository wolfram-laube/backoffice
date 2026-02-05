"""
Tests for Runner Capability Ontology (#22)

pytest tests/test_ontology.py -v
"""

import pytest
from nsai.ontology import RunnerOntology
from nsai.ontology.runner_ontology import (
    Runner, RunnerCapability, CapabilityType, create_blauweiss_ontology
)


class TestRunnerCapability:
    """Tests for RunnerCapability dataclass."""
    
    def test_capability_creation(self):
        cap = RunnerCapability(
            name="docker",
            cap_type=CapabilityType.EXECUTOR,
            description="Docker executor"
        )
        assert cap.name == "docker"
        assert cap.cap_type == CapabilityType.EXECUTOR
    
    def test_capability_equality(self):
        cap1 = RunnerCapability(name="docker", cap_type=CapabilityType.EXECUTOR)
        cap2 = RunnerCapability(name="docker", cap_type=CapabilityType.EXECUTOR)
        assert cap1 == cap2
        assert cap1 == "docker"  # String comparison
    
    def test_capability_hash(self):
        cap = RunnerCapability(name="docker", cap_type=CapabilityType.EXECUTOR)
        cap_set = {cap}
        assert cap in cap_set


class TestRunner:
    """Tests for Runner dataclass."""
    
    def test_runner_creation(self):
        runner = Runner(name="test-runner", runner_id=123)
        assert runner.name == "test-runner"
        assert runner.runner_id == 123
        assert runner.online is True
    
    def test_has_capability(self):
        cap = RunnerCapability(name="docker", cap_type=CapabilityType.EXECUTOR)
        runner = Runner(name="test", capabilities={cap})
        
        assert runner.has_capability("docker") is True
        assert runner.has_capability("shell") is False
    
    def test_has_all_capabilities(self):
        caps = {
            RunnerCapability(name="docker", cap_type=CapabilityType.EXECUTOR),
            RunnerCapability(name="linux", cap_type=CapabilityType.PLATFORM),
        }
        runner = Runner(name="test", capabilities=caps)
        
        assert runner.has_all_capabilities(["docker", "linux"]) is True
        assert runner.has_all_capabilities(["docker", "gpu"]) is False
    
    def test_has_any_capability(self):
        cap = RunnerCapability(name="docker", cap_type=CapabilityType.EXECUTOR)
        runner = Runner(name="test", capabilities={cap})
        
        assert runner.has_any_capability(["docker", "shell"]) is True
        assert runner.has_any_capability(["shell", "kubernetes"]) is False


class TestRunnerOntology:
    """Tests for RunnerOntology class."""
    
    @pytest.fixture
    def ontology(self):
        return RunnerOntology()
    
    def test_standard_capabilities_loaded(self, ontology):
        assert "docker" in ontology.capabilities
        assert "shell" in ontology.capabilities
        assert "gcp" in ontology.capabilities
    
    def test_add_runner(self, ontology):
        runner = ontology.add_runner(
            name="test-runner",
            runner_id=123,
            capabilities=["docker", "linux"],
            tags=["docker-any"]
        )
        
        assert runner.name == "test-runner"
        assert runner.runner_id == 123
        assert runner.has_capability("docker")
        assert runner.has_capability("linux")
        assert "docker-any" in runner.tags
    
    def test_capability_implications(self, ontology):
        """Test that implied capabilities are added."""
        runner = ontology.add_runner(
            name="nordic-runner",
            capabilities=["nordic"]
        )
        
        # Nordic implies eu-west and gcp
        assert runner.has_capability("nordic")
        assert runner.has_capability("eu-west")
        assert runner.has_capability("gcp")
    
    def test_custom_capability(self, ontology):
        """Test that unknown tags become custom capabilities."""
        runner = ontology.add_runner(
            name="special-runner",
            capabilities=["my-custom-cap"]
        )
        
        assert "my-custom-cap" in ontology.capabilities
        assert runner.has_capability("my-custom-cap")
    
    def test_get_runners_with_capability(self, ontology):
        ontology.add_runner("r1", capabilities=["docker"])
        ontology.add_runner("r2", capabilities=["docker", "gpu"])
        ontology.add_runner("r3", capabilities=["shell"])
        
        docker_runners = ontology.get_runners_with_capability("docker")
        assert len(docker_runners) == 2
        assert all(r.has_capability("docker") for r in docker_runners)
    
    def test_get_feasible_runners(self, ontology):
        ontology.add_runner("r1", capabilities=["docker", "linux"])
        ontology.add_runner("r2", capabilities=["docker", "gpu"])
        ontology.add_runner("r3", capabilities=["shell"])
        
        # Require docker, exclude gpu
        feasible = ontology.get_feasible_runners(
            required=["docker"],
            excluded=["gpu"]
        )
        
        assert len(feasible) == 1
        assert feasible[0].name == "r1"
    
    def test_offline_runner_excluded(self, ontology):
        ontology.add_runner("online", capabilities=["docker"])
        runner = ontology.add_runner("offline", capabilities=["docker"])
        runner.online = False
        
        feasible = ontology.get_feasible_runners(required=["docker"])
        assert len(feasible) == 1
        assert feasible[0].name == "online"
    
    def test_serialization(self, ontology):
        ontology.add_runner("r1", capabilities=["docker"], tags=["test"])
        
        data = ontology.to_dict()
        assert "r1" in data["runners"]
        assert "docker" in data["runners"]["r1"]["capabilities"]
        
        json_str = ontology.to_json()
        assert '"r1"' in json_str
    
    def test_deserialization(self, ontology):
        ontology.add_runner("r1", capabilities=["docker"])
        data = ontology.to_dict()
        
        restored = RunnerOntology.from_dict(data)
        assert "r1" in restored.runners
        assert restored.runners["r1"].has_capability("docker")


class TestBlauweissOntology:
    """Tests for the production ontology."""
    
    def test_create_blauweiss_ontology(self):
        onto = create_blauweiss_ontology()
        
        # Should have the nordic runner
        assert "gitlab-runner-nordic" in onto.runners
        nordic = onto.runners["gitlab-runner-nordic"]
        
        assert nordic.has_capability("docker")
        assert nordic.has_capability("shell")
        assert nordic.has_capability("gcp")
        assert nordic.has_capability("nordic")
        assert nordic.online is True
    
    def test_local_runners_offline_by_default(self):
        onto = create_blauweiss_ontology()
        
        assert onto.runners["mac-local"].online is False
        assert onto.runners["linux-local"].online is False
