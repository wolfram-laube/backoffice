"""
Runner Capability Ontology Module (#22)

Defines the semantic model for runner capabilities using OWL/RDF.
Provides the knowledge base for constraint-based runner filtering.
"""

from .runner_ontology import RunnerOntology, create_blauweiss_ontology

__all__ = ["RunnerOntology", "create_blauweiss_ontology"]

