# Contributing to NSAI

## 🧪 Testing Requirements

### Imperative: All Code Must Have Tests

**This is non-negotiable.** Every contribution MUST include:

1. **Unit Tests** in `tests/` directory
2. **Smoke Tests** in notebooks (if applicable)
3. **Integration Tests** for cross-module functionality

### Unit Tests (`tests/`)

```bash
# Run all tests
pytest services/nsai/tests/ -v

# Run with coverage
pytest services/nsai/tests/ -v --cov=nsai --cov-report=term-missing

# Run specific test file
pytest services/nsai/tests/test_interface.py -v
```

**Minimum coverage: 80%**

### Notebook Smoke Tests

Every Jupyter notebook in `notebooks/` MUST include a **Smoke Tests** section:

```python
def run_smoke_tests():
    """Run all smoke tests. Raises AssertionError if any fail."""
    
    # Test 1: Basic functionality
    assert some_function() is not None, "Should not be None"
    
    # Test 2: Edge cases
    assert handles_edge_case(), "Should handle edge case"
    
    # ... more tests ...
    
    print("✅ All smoke tests passed!")

# Run the tests!
run_smoke_tests()
```

**Why?**
- Notebooks are documentation AND executable code
- Stale notebooks with broken examples hurt users
- Smoke tests catch API changes early
- CI can validate notebooks automatically

### Test Structure

```
services/nsai/
├── tests/
│   ├── __init__.py
│   ├── test_ontology.py      # Ontology unit tests
│   ├── test_parser.py        # Parser unit tests
│   ├── test_csp.py           # CSP Solver unit tests
│   ├── test_interface.py     # NeurosymbolicBandit tests
│   └── fixtures/             # Shared test fixtures
│       └── sample_jobs.py
└── notebooks/
    └── demo.ipynb            # MUST have smoke tests section
```

### Writing Good Tests

```python
class TestMyFeature:
    """Tests for MyFeature."""
    
    @pytest.fixture
    def setup(self):
        """Create test fixtures."""
        return MyFeature()
    
    def test_basic_functionality(self, setup):
        """Test that basic case works."""
        result = setup.do_thing()
        assert result is not None
        assert result.value == expected
    
    def test_edge_case(self, setup):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            setup.do_thing(invalid_input)
    
    def test_integration(self, setup):
        """Test integration with other components."""
        other = OtherComponent()
        result = setup.work_with(other)
        assert result.is_valid
```

### CI Integration

Tests run automatically on:
- Every push to feature branches
- Every merge request
- Nightly on `main`

Failed tests block merges.

---

## 📝 Documentation Requirements

### Code Documentation

All public functions/classes MUST have docstrings:

```python
def select_runner(self, job_definition: Dict[str, Any]) -> Tuple[str, Explanation]:
    """
    Select optimal runner using neurosymbolic reasoning.
    
    Args:
        job_definition: Job definition from .gitlab-ci.yml
    
    Returns:
        Tuple of (selected_runner, explanation)
        If no feasible runner exists, selected_runner is None
    
    Example:
        >>> nsai = NeurosymbolicBandit.create_default()
        >>> runner, exp = nsai.select_runner({"tags": ["docker-any"]})
    """
```

### README Updates

If you change the API, update `README.md`:
- Quick Start examples
- API Reference table
- Module descriptions

### ADR Updates

Significant architectural changes require ADR updates:
- `corporate/docs/adr/ai/AI-001-neurosymbolic-runner-selection.md`

---

## 🔀 Git Workflow

1. Create feature branch: `git checkout -b feature/XX-description`
2. Make changes with tests
3. Run tests locally: `pytest services/nsai/tests/ -v`
4. Commit with conventional commits: `feat(nsai): add new feature (#XX)`
5. Push and create MR
6. Wait for CI to pass
7. Request review
8. Squash merge after approval

---

## 📋 Checklist for PRs

- [ ] Unit tests added/updated
- [ ] Notebook smoke tests pass
- [ ] Coverage >= 80%
- [ ] Docstrings for public API
- [ ] README updated if API changed
- [ ] ADR updated if architecture changed
- [ ] Conventional commit messages
- [ ] No linting errors
