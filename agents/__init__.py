"""
agents/__init__.py
==================
Agents package initialisation.

Import this package to access the central AI agent:

    from agents import CollegeAdmissionAgent
    from agents.college_agent import CollegeAdmissionAgent
"""

from agents.college_agent import CollegeAdmissionAgent

__all__ = ["CollegeAdmissionAgent"]
