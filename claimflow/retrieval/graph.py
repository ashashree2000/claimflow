"""Clause graph (NetworkX) and graph expansion for GraphRAG.

Nodes are clauses. Edges:
  references  A -> B when A's text names B ("subject to MOTOR-EXC-4.2", "amended by MOTOR-END-6.1")
  parent      clause -> its section header (MOTOR-EXC-4.2 -> MOTOR-EXC-4)
Expansion follows outgoing reference edges for up to `hops` steps, then incoming ones and adds the section
header of each retrieved clause, so section-wide rules ("these exclusions apply to every part ...") come along.
"""
from __future__ import annotations

import networkx as nx

from .. import config
from .documents import Clause, load_policies


def build_graph(clauses: dict[str, Clause] | None = None) -> nx.DiGraph:
    clauses = clauses if clauses is not None else load_policies()
    g = nx.DiGraph()
    for c in clauses.values():
        g.add_node(c.id, lob=c.lob, section=c.is_section)
    for c in clauses.values():
        for r in c.refs:
            if r in clauses:
                g.add_edge(c.id, r, kind="references")
        if c.parent and c.parent in clauses:
            g.add_edge(c.id, c.parent, kind="parent")
    return g


def expand(g: nx.DiGraph, seeds: list[str], hops: int = config.GRAPH_HOPS, max_extra: int = 10) -> list[dict]:
    """Return the added clauses as [{id, hop, via, relation}], capped at max_extra.

    Outgoing references ("subject to", "amended by", definitions used) are followed first, up to `hops`;
    clauses that point back at the seeds ("referenced_by") fill any remaining room.
    """
    seen = set(seeds)
    added: list[dict] = []
    for rel in ("references", "referenced_by"):
        frontier = list(seeds)
        for hop in range(1, hops + 1):
            nxt = []
            for node in frontier:
                if node not in g:
                    continue
                if rel == "references":
                    nbrs = [v for v in g.successors(node) if g[node][v]["kind"] == "references"]
                else:
                    nbrs = [u for u in g.predecessors(node) if g[u][node]["kind"] == "references"]
                for other in nbrs:
                    if other in seen or g.nodes[other]["section"]:
                        continue
                    seen.add(other)
                    added.append({"id": other, "hop": hop, "via": node, "relation": rel})
                    nxt.append(other)
            frontier = nxt
    added = added[:max_extra]
    # section headers of the seed clauses, as context (one parent hop, not counted in max_extra)
    for node in seeds:
        for p in g.successors(node) if node in g else []:
            if g[node][p]["kind"] == "parent" and p not in seen:
                seen.add(p)
                added.append({"id": p, "hop": 1, "via": node, "relation": "parent"})
    return added
