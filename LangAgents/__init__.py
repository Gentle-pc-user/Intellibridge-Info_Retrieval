"""LangAgents package

LangChain/LangGraph-based implementation of the Intellibridge-style
multi-agent workflow. This package does not modify the original
`agents` package; instead it provides an alternative implementation
built on top of LangChain and LangGraph.
"""

from .workflow import QueryState, build_intellibridge_graph

__all__ = ["QueryState", "build_intellibridge_graph"]
