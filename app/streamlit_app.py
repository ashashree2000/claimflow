"""ClaimFlow - Triage page. Run: streamlit run app/streamlit_app.py"""
from __future__ import annotations

import json

import streamlit as st
from common import ROOT, SYNTHETIC_NOTE, load_secrets

load_secrets()

from claimflow import audit, config  # noqa: E402
from claimflow.agents import triage  # noqa: E402
from claimflow.llm import QuotaExhausted, get_client  # noqa: E402
from claimflow.retrieval import load_policies, load_sops, vector  # noqa: E402
from claimflow.schemas import ClaimEmail, ClaimEvent, TriagePacket  # noqa: E402

st.set_page_config(page_title="ClaimFlow - Triage", layout="wide")
st.title("ClaimFlow: claims-intake triage")
st.caption(SYNTHETIC_NOTE)


@st.cache_resource
def client():
    return get_client()


claims = {p.stem: json.loads(p.read_text()) for p in sorted((ROOT / "data/claims").glob("*.json"))}
labels = {json.loads(x)["claim_id"]: json.loads(x) for x in (ROOT / "data/labels.jsonl").read_text().splitlines()}

left, right = st.columns([2, 3])
with left:
    source = st.radio("Input", ["Sample claim", "Paste an email"], horizontal=True)
    mode = st.selectbox("Retrieval mode", ["graph", "vector", "vector_wide"],
                        help="graph = vector top-k plus clause-graph expansion; vector_wide = vector search with the "
                             "same number of clauses as graph mode")
    if source == "Sample claim":
        cid = st.selectbox("Claim", list(claims), format_func=lambda c: f"{c} - {claims[c]['email']['subject']}")
        email = ClaimEmail(**claims[cid]["email"])
        events = [ClaimEvent(**e) for e in claims[cid]["events"]]
        use_cache = st.checkbox("Use the saved evaluation result (no API call)", value=True)
        st.text_area("Email", email.body, height=260, disabled=True)
        with st.expander("Claim event log"):
            st.table([{"id": e.event_id, "time": e.timestamp, "step": e.step} for e in events])
    else:
        cid, use_cache = None, False
        subject = st.text_input("Subject")
        body = st.text_area("Email body", height=260, placeholder="Paste a synthetic FNOL email ...")
        email, events = ClaimEmail(subject=subject, body=body or " "), []
    run = st.button("Run triage", type="primary")

if run:
    packet, note = None, ""
    saved = ROOT / f"eval/packets/{mode}/{cid}.json" if cid else None
    if use_cache and saved and saved.exists():
        packet, note = TriagePacket.model_validate_json(saved.read_text()), "Saved result from the evaluation run."
    else:
        try:
            if not config.api_key():
                raise QuotaExhausted("no GEMINI_API_KEY configured")
            if not vector.ensure_index(client()):
                raise QuotaExhausted("retrieval index could not be built")
            with st.spinner("Running intake, router, coverage and process agents ..."):
                packet = triage(client(), email, events, cid, mode=mode, save=False)
            note = "Live run."
        except QuotaExhausted as e:
            if saved and saved.exists():
                packet = TriagePacket.model_validate_json(saved.read_text())
                note = f"Live model unavailable ({e}). Showing the saved evaluation result instead."
            else:
                st.error(f"Live model unavailable ({e}). Choose a sample claim to see a saved result.")
    if packet:
        audit.save_packet(packet, f"{email.subject}\n{email.body}")
        st.session_state["packet"], st.session_state["note"] = packet, note

packet: TriagePacket | None = st.session_state.get("packet")
with right:
    if packet is None:
        st.info("Choose a claim and press **Run triage**.")
    else:
        st.caption(f"{st.session_state.get('note', '')} Packet `{packet.packet_id}`, model `{packet.model}`, "
                   f"retrieval `{packet.retrieval_mode}`.")
        cov = packet.coverage
        c1, c2, c3 = st.columns(3)
        c1.metric("Coverage", cov.decision.replace("_", " ") if cov else "failed")
        c2.metric("Confidence (rule-based)", packet.confidence)
        c3.metric("Needs human review", "yes" if packet.needs_human_review else "no")
        if packet.intake:
            i = packet.intake
            st.subheader("Extracted facts")
            st.table({"field": ["claimant", "policy", "line", "incident date", "type", "location", "severity",
                                "attached", "missing (checklist)"],
                      "value": [i.claimant_name, i.policy_number, i.line_of_business, i.incident_date, i.incident_type,
                                i.location, f"{i.severity} - {i.severity_reason}", ", ".join(i.documents_attached),
                                ", ".join(packet.documents_missing)]})
        st.subheader("Route")
        st.write(f"**{packet.route.line_of_business}** -> {', '.join(packet.route.specialists)} "
                 f"({packet.route.method}): {packet.route.reason}")
        if cov:
            st.subheader("Coverage decision and citations")
            st.write(cov.reasoning)
            pol = load_policies()
            for c in cov.citations:
                with st.expander(f"{c.clause_id} - {pol[c.clause_id].title}"):
                    st.markdown(f"> {c.quote}")
                    st.caption(pol[c.clause_id].text)
            st.caption(f"Retrieved: {', '.join(cov.retrieved_ids)}" +
                       (f" | Graph expansion: {', '.join(cov.expanded_ids)}" if cov.expanded_ids else ""))
        if packet.process:
            st.subheader("Process flags (SOP-grounded)")
            if not packet.process.flags:
                st.write("No departures from the SOPs found.")
            sops = load_sops()
            for f in packet.process.flags:
                st.markdown(f"- **{f.type}**{' (' + f.document + ')' if f.document else ''}, events "
                            f"{', '.join(f.event_ids)}: {f.fix}  \n  _{f.sop_id}: {sops[f.sop_id].text}_")
        if packet.reasons or packet.errors:
            st.subheader("Reasons and guardrail notes")
            for r in packet.reasons + packet.errors:
                st.write("-", r)
        if cid and cid in labels:
            with st.expander("Gold label for this synthetic claim (for comparison)"):
                st.json({k: labels[cid][k] for k in ("coverage", "process_flaws", "fields")})
        st.subheader("Human review")
        with st.form("review"):
            action = st.radio("Decision", ["approve", "reject"], horizontal=True)
            note = st.text_input("Note (optional)")
            if st.form_submit_button("Record decision"):
                r = audit.record_review(packet.packet_id, action, note)
                st.success(f"Recorded {r['action']} at {r['ts']} in the audit log.")
