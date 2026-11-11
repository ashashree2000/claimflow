import streamlit as st
from common import DECISION_TEXT, FOOTER, LOB_TEXT, MODE_HELP, MODES, ROOT, claim_title, claims, labels

from claimflow import audit, config
from claimflow.agents import triage
from claimflow.llm import QuotaExhausted, get_client
from claimflow.retrieval import load_policies, load_sops, vector
from claimflow.schemas import ClaimEmail, ClaimEvent, TriagePacket
from claimflow.sop_rules import DOC_LABELS


@st.cache_resource
def client():
    return get_client()


def docs(keys) -> str:
    return ", ".join(DOC_LABELS.get(k, k) for k in keys) or "none"


st.title("Triage a claim")
st.caption("Pick a claim, choose how policy clauses are found, and press Run.")

left, right = st.columns([2, 3], gap="large")
with left:
    source = st.radio("Claim", ["Choose a test claim", "Paste your own email"], horizontal=True,
                      label_visibility="collapsed")
    if source == "Choose a test claim":
        cid = st.selectbox("Test claim", list(claims()), format_func=claim_title)
        c = claims()[cid]
        email = ClaimEmail(**c["email"])
        events = [ClaimEvent(**e) for e in c["events"]]
        with st.container(border=True):
            st.markdown(f"**{email.subject}**  \nFrom {email.from_name}, {email.sent_at.replace('T', ' ')}")
            st.text(email.body)
            if email.attachments:
                st.caption("Attachments: " + ", ".join(email.attachments))
        with st.expander("Handling history for this claim"):
            st.dataframe([{"Event": e.event_id, "Time": e.timestamp.replace("T", " "), "Step": e.step} for e in events],
                         hide_index=True, width="stretch")
    else:
        cid = None
        subject = st.text_input("Subject")
        body = st.text_area("Email", height=240, placeholder="Describe a loss as a customer would ...")
        email, events = ClaimEmail(subject=subject, body=body or " "), []
        st.caption("A pasted email is always run live and has no handling history to check.")
    mode = st.radio("How to find policy clauses", list(MODES), format_func=MODES.get, help=MODE_HELP)
    live = st.toggle("Run live (calls Gemini)", value=cid is None, disabled=cid is None,
                     help="Off: show the stored result for this claim. On: run the agents again now.")
    run = st.button("Run", type="primary", width="stretch")

if run:
    stored = ROOT / f"eval/packets/{mode}/{cid}.json" if cid else None
    packet, note = None, ""
    if not live and stored and stored.exists():
        packet = TriagePacket.model_validate_json(stored.read_text())
    else:
        try:
            if not config.api_key():
                raise QuotaExhausted("no API key is configured")
            if not vector.ensure_index(client()):
                raise QuotaExhausted("the clause index could not be built")
            with st.spinner("Reading the email, checking clauses and the handling history ..."):
                packet = triage(client(), email, events, cid, mode=mode, save=False)
        except QuotaExhausted as e:
            if stored and stored.exists():
                packet = TriagePacket.model_validate_json(stored.read_text())
                note = f"The live model is not available right now ({e}), so the stored result is shown."
            else:
                st.error(f"The live model is not available right now ({e}). Try one of the test claims.")
    if packet:
        audit.save_packet(packet, f"{email.subject}\n{email.body}")
        st.session_state.update(packet=packet, note=note, packet_claim=cid)

packet: TriagePacket | None = st.session_state.get("packet")
with right:
    if packet is None:
        st.info("The recommendation will appear here.")
    else:
        if st.session_state.get("note"):
            st.warning(st.session_state["note"])
        cov, i = packet.coverage, packet.intake
        a, b, c3 = st.columns(3)
        a.metric("Recommendation", DECISION_TEXT[cov.decision] if cov else "No decision")
        b.metric("Confidence", packet.confidence.capitalize())
        c3.metric("Handler must review", "Yes" if packet.needs_human_review else "Optional")
        st.caption(f"Policy type: {LOB_TEXT[packet.route.line_of_business]} · "
                   f"Severity: {i.severity if i else 'n/a'} · Clauses found by: {MODES[packet.retrieval_mode]}")

        t1, t2, t3, t4, t5 = st.tabs(["Why", "Policy clauses", "Process check", "Extracted details",
                                      "Expected answer"])
        with t1:
            if cov:
                st.write(cov.reasoning)
            for r in packet.reasons + packet.errors:
                st.markdown(f"- {r}")
            st.markdown(f"- Routing: {packet.route.reason}")
        with t2:
            if cov:
                pol = load_policies()
                st.markdown("**Clauses the recommendation relies on**")
                if not cov.citations:
                    st.write("None. The claim is referred to a handler.")
                for ct in cov.citations:
                    with st.container(border=True):
                        st.markdown(f"**{ct.clause_id} · {pol[ct.clause_id].title}**  \n> {ct.quote}")
                        st.caption(pol[ct.clause_id].text)
                st.markdown("**Clauses the agent was given**")
                st.write("Found by similarity: " + ", ".join(cov.retrieved_ids))
                if cov.expanded_ids:
                    st.write("Added by following references: " + ", ".join(cov.expanded_ids))
        with t3:
            if packet.process is None:
                st.write("Not run.")
            elif not packet.process.flags:
                st.success("The handling history follows the procedures.")
            else:
                sops = load_sops()
                for f in packet.process.flags:
                    with st.container(border=True):
                        title = f.type.replace("_", " ").capitalize()
                        if f.document:
                            title += f" ({DOC_LABELS.get(f.document, f.document)})"
                        st.markdown(f"**{title}** · events {', '.join(f.event_ids)}  \n{f.fix}")
                        st.caption(f"{f.sop_id}: {sops[f.sop_id].text}")
        with t4:
            if i:
                st.table({"": ["Claimant", "Policy number", "Incident date", "Incident type", "Location", "Severity",
                               "Documents attached", "Documents still needed"],
                          "Extracted": [i.claimant_name, i.policy_number, i.incident_date, i.incident_type,
                                        i.location, f"{i.severity} ({i.severity_reason})", docs(i.documents_attached),
                                        docs(packet.documents_missing)]})
            else:
                st.write("The details could not be extracted, so the claim goes to a handler.")
        with t5:
            pid = st.session_state.get("packet_claim")
            if pid and pid in labels():
                lab = labels()[pid]
                cv = lab["coverage"]
                st.markdown(f"**Expected recommendation:** {DECISION_TEXT[cv['decision']]}")
                if cv["required_clause_ids"]:
                    st.markdown("**Clauses it should cite:** " + ", ".join(cv["required_clause_ids"]))
                if lab["process_flaws"]:
                    st.markdown("**Handling problems in this claim:**")
                    for fl in lab["process_flaws"]:
                        doc = f" ({DOC_LABELS[fl['document']]})" if fl.get("document") else ""
                        st.markdown(f"- {fl['type'].replace('_', ' ')}{doc}, fixed by {fl['sop_id']}")
                else:
                    st.markdown("**Handling problems in this claim:** none")
            else:
                st.write("Only the test claims have an expected answer.")

        st.divider()
        with st.form("review", border=False):
            st.markdown("**Your decision as the claims handler**")
            action = st.radio("Decision", ["approve", "reject"], horizontal=True, format_func=str.capitalize,
                              label_visibility="collapsed")
            note = st.text_input("Note (optional)")
            if st.form_submit_button("Save decision"):
                r = audit.record_review(packet.packet_id, action, note)
                st.success(f"Saved: {'approved' if r['action'] == 'approve' else 'rejected'}. It now appears in the Review log.")

st.divider()
st.caption(FOOTER)
