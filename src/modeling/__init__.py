"""Modeling package boundary.

Import concrete services from ``src.modeling.inference`` or
``src.modeling.training``.  Keeping package initialization side-effect free is
what prevents a runtime import from loading the training dependency graph.
"""
