"""Builds the internal knowledge graph the agent reasons over: documents, extracted skills,
canonical mappings, requirement/evidence edges, sub-scores and the explanation — all derived
from the exact same MatchState the tools mutate, so the graph is never a separate fiction.

`build_full_graph` renders the whole graph from the current state (used for the final,
non-streamed result). `kg_delta` renders the same graph but returns only the nodes/edges whose
content changed since the last call for this state, keyed by a content hash in `st.kg_cache` —
this is what drives the live, step-by-step trace view in the UI.
"""
import hashlib

from app.agent.state import MatchState
from app.core.models import KGEdge, KGNode, KnowledgeGraph


def _n(id: str, kind, label: str, detail: str = "", group: str = "shared", weight: float = 1.0) -> KGNode:
    return KGNode(id=id, kind=kind, label=label, detail=detail, group=group, weight=weight)


def _e(id: str, source: str, target: str, kind, label: str = "", weight: float = 1.0) -> KGEdge:
    return KGEdge(id=id, source=source, target=target, kind=kind, label=label, weight=weight)


def build_full_graph(st: MatchState) -> KnowledgeGraph:
    nodes: dict[str, KGNode] = {}
    edges: dict[str, KGEdge] = {}

    nodes["doc:resume"] = _n("doc:resume", "resume_doc", "Resume", group="resume", weight=1.7)
    nodes["doc:jd"] = _n("doc:jd", "jd_doc", "Job description", group="jd", weight=1.7)

    if st.resume:
        for key, entry in st.resume.skills.items():
            nid = f"skill:resume:{key}"
            detail = ", ".join(sorted(entry.sources)) or "keyword"
            nodes[nid] = _n(nid, "resume_skill", key, detail=detail, group="resume")
            edges[f"e:contains:{nid}"] = _e(f"e:contains:{nid}", "doc:resume", nid, "contains")
        if st.resume.years_experience is not None:
            nodes["exp:resume"] = _n("exp:resume", "experience", f"{st.resume.years_experience:g} yrs", group="resume")
            edges["e:exp:resume"] = _e("e:exp:resume", "doc:resume", "exp:resume", "contains")
        if st.resume.education_level != "unknown":
            edu_label = st.resume.education_level.replace("_", " ")
            nodes["edu:resume"] = _n("edu:resume", "education", edu_label, group="resume")
            edges["e:edu:resume"] = _e("e:edu:resume", "doc:resume", "edu:resume", "contains")

    if st.jd:
        for key, entry in st.jd.skills.items():
            nid = f"skill:jd:{key}"
            detail = "required" if entry.required else "preferred"
            if entry.mandatory:
                detail += " · must-have"
            nodes[nid] = _n(nid, "jd_skill", key, detail=detail, group="jd", weight=1.3 if entry.mandatory else 1.0)
            edges[f"e:req:{nid}"] = _e(f"e:req:{nid}", "doc:jd", nid, "requires",
                                       label="must-have" if entry.mandatory else "")
        if st.jd.years_experience is not None:
            nodes["exp:jd"] = _n("exp:jd", "experience", f"{st.jd.years_experience:g}+ yrs", group="jd")
            edges["e:exp:jd"] = _e("e:exp:jd", "doc:jd", "exp:jd", "requires")
        if st.jd.education_level != "unknown":
            nodes["edu:jd"] = _n("edu:jd", "education", st.jd.education_level.replace("_", " "), group="jd")
            edges["e:edu:jd"] = _e("e:edu:jd", "doc:jd", "edu:jd", "requires")

    if st.breakdown:
        b = st.breakdown
        for m in b.matches:
            jd_nid = f"skill:jd:{m.jd_skill}"
            if m.kind == "missing":
                if jd_nid in nodes:
                    base = nodes[jd_nid]
                    if "not found" not in base.detail:
                        detail = (base.detail + " · not found in resume").strip(" ·")
                        nodes[jd_nid] = base.model_copy(update={"detail": detail})
                continue
            res_nid = f"skill:resume:{m.matched_with}"
            eid = f"e:match:{m.jd_skill}"
            edges[eid] = _e(eid, res_nid, jd_nid, m.kind, label=f"{m.credit:.0%}", weight=m.credit)

        nodes["result:score"] = _n("result:score", "score", f"{b.score} / 100", detail=f"{b.band} fit",
                                    group="result", weight=2.2)
        for key, val in b.sub_scores.items():
            sid = f"subscore:{key}"
            nodes[sid] = _n(sid, "sub_score", key.replace("_", " "), detail=f"{val:.0%}", group="result")
            edges[f"e:{sid}"] = _e(f"e:{sid}", sid, "result:score", "supports", weight=max(val, 0.05))

    if st.bullets:
        nodes["result:explanation"] = _n("result:explanation", "explanation", "Why this score",
                                          detail=f"{len(st.bullets)} justifications", group="result", weight=1.5)
        if "result:score" in nodes:
            edges["e:explains"] = _e("e:explains", "result:score", "result:explanation", "explains")

    return KnowledgeGraph(nodes=list(nodes.values()), edges=list(edges.values()))


def _sig(model) -> str:
    return hashlib.md5(model.model_dump_json().encode()).hexdigest()


def kg_delta(st: MatchState) -> tuple[list[KGNode], list[KGEdge]]:
    """New or changed nodes/edges since the last call for this state. Pure, repeatable, side-effect-free
    apart from updating st.kg_cache — call it once per step so the live view gets a real diff."""
    full = build_full_graph(st)
    new_nodes, new_edges = [], []
    for n in full.nodes:
        sig = _sig(n)
        if st.kg_cache.get(("n", n.id)) != sig:
            st.kg_cache[("n", n.id)] = sig
            new_nodes.append(n)
    for e in full.edges:
        sig = _sig(e)
        if st.kg_cache.get(("e", e.id)) != sig:
            st.kg_cache[("e", e.id)] = sig
            new_edges.append(e)
    return new_nodes, new_edges
