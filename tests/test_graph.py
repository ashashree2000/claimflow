from claimflow.retrieval import graph
from claimflow.retrieval.documents import load_policies


def test_parsing_counts_and_parents():
    pol = load_policies()
    assert len(pol) == 78
    assert pol["MOTOR-EXC-4.2"].parent == "MOTOR-EXC-4"
    assert "MOTOR-END-6.1" in pol["MOTOR-EXC-4.2"].refs


def test_graph_has_reference_and_parent_edges():
    g = graph.build_graph()
    assert g["MOTOR-COV-2.1"]["MOTOR-EXC-4.2"]["kind"] == "references"
    assert g["MOTOR-COV-2.1"]["MOTOR-COV-2"]["kind"] == "parent"


def test_expansion_follows_cross_reference_chain():
    g = graph.build_graph()
    ids = [a["id"] for a in graph.expand(g, ["MOTOR-COV-2.1"], hops=2)]
    assert "MOTOR-EXC-4.2" in ids            # hop 1: "subject to"
    assert {"MOTOR-DEF-1.3", "MOTOR-END-6.1"} <= set(ids)  # hop 2: definition and endorsement
    assert "MOTOR-COV-2" in ids              # section header of the seed


def test_expansion_respects_hops_and_cap():
    g = graph.build_graph()
    one = [a for a in graph.expand(g, ["MOTOR-COV-2.1"], hops=1) if a["relation"] != "parent"]
    assert all(a["hop"] == 1 for a in one) and "MOTOR-END-6.1" not in {a["id"] for a in one}
    capped = [a for a in graph.expand(g, ["MOTOR-COV-2.1"], hops=2, max_extra=3) if a["relation"] != "parent"]
    assert len(capped) == 3
