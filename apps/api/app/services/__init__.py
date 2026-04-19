"""Service layer for domain workflows.

Services sit between HTTP routes (which own transport + auth) and
the DB / adapter layer (which owns persistence + external systems).
Anything the UI does not map 1:1 to a single SQL statement belongs
here — generation pipelines, state transitions, compound workflows.
"""
