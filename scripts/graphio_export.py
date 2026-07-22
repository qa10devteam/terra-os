"""
graphio_export.py — eksportuje dane terra-os do Neo4j przez graphio.

Graf:
  (:Tenant {id, name})
  (:Tender {id, title, cpv, value_pln, match_score, status, voivodeship})
  (:Analysis {id, tender_id, summary, red_flags_count, score})
  (:Buyer {name})
  (:CPV {code, label})
  (:Voivodeship {name})

Relacje:
  (Tenant)-[:WATCHES]->(Tender)
  (Tender)-[:HAS_ANALYSIS]->(Analysis)
  (Tender)-[:ISSUED_BY]->(Buyer)
  (Tender)-[:CLASSIFIED_AS]->(CPV)
  (Tender)-[:IN_REGION]->(Voivodeship)

Run:
    .venv/bin/python3.12 scripts/graphio_export.py
"""
from __future__ import annotations
import sys, os, json, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("graphio_export")

sys.path.insert(0, "/home/ubuntu/terra-os")
sys.path.insert(0, "/home/ubuntu/terra-os/services")
sys.path.insert(0, "/home/ubuntu/terra-os/packages/db")

with open("/home/ubuntu/terra-os/.env") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)
os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_NAME"] = "terraos"
os.environ["DB_USER"] = "terraos"

import sqlalchemy as sa
from terra_db.session import get_engine
from graphio import NodeSet, RelationshipSet
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "TerraOS2026!"

def main():
    engine = get_engine()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with engine.connect() as conn:
        # Fetch tenders
        tenders = conn.execute(sa.text("""
            SELECT t.id, t.tenant_id, t.title, t.buyer, t.cpv,
                   t.voivodeship, t.value_pln, t.match_score, t.status,
                   t.published_at, t.deadline_at
            FROM tender t
            ORDER BY t.created_at DESC
            LIMIT 2000
        """)).fetchall()
        log.info("tenders: %d", len(tenders))

        # Fetch analyses
        analyses = conn.execute(sa.text("""
            SELECT a.id, a.tender_id, a.summary_md, a.red_flags, a.key_facts
            FROM analysis a
        """)).fetchall()
        log.info("analyses: %d", len(analyses))

        # Fetch tenants
        tenants = conn.execute(sa.text("SELECT id, name FROM tenant")).fetchall()
        log.info("tenants: %d", len(tenants))

    # ── NodeSets ──────────────────────────────────────────────────────────────
    ns_tenant = NodeSet(["Tenant"], merge_keys=["id"])
    ns_tender = NodeSet(["Tender"], merge_keys=["id"])
    ns_analysis = NodeSet(["Analysis"], merge_keys=["id"])
    ns_buyer = NodeSet(["Buyer"], merge_keys=["name"])
    ns_cpv = NodeSet(["CPV"], merge_keys=["code"])
    ns_voiv = NodeSet(["Voivodeship"], merge_keys=["name"])

    for t in tenants:
        ns_tenant.add_node({"id": str(t[0]), "name": str(t[1] or "")})

    tender_ids = set()
    for t in tenders:
        tid = str(t[0])
        tender_ids.add(tid)
        cpv_list = t[4] if isinstance(t[4], list) else ([t[4]] if t[4] else [])
        cpv_str = ",".join(str(c) for c in cpv_list)

        ns_tender.add_node({
            "id": tid,
            "tenant_id": str(t[1]),
            "title": str(t[2] or "")[:200],
            "buyer": str(t[3] or "")[:120],
            "cpv": cpv_str,
            "voivodeship": str(t[5] or ""),
            "value_pln": float(t[6]) if t[6] else None,
            "match_score": float(t[7]) if t[7] else None,
            "status": str(t[8] or ""),
            "published_at": str(t[9]) if t[9] else None,
            "deadline_at": str(t[10]) if t[10] else None,
        })

        # Buyer node
        if t[3]:
            ns_buyer.add_node({"name": str(t[3])[:120]})

        # CPV nodes
        for cpv in cpv_list:
            if cpv:
                ns_cpv.add_node({"code": str(cpv)[:8]})

        # Voivodeship
        if t[5]:
            ns_voiv.add_node({"name": str(t[5]).lower().strip()})

    for a in analyses:
        key_facts = {}
        if a[4]:
            try:
                key_facts = json.loads(a[4]) if isinstance(a[4], str) else (a[4] or {})
            except Exception:
                pass
        red_flags = a[3] or []
        score = None
        if isinstance(key_facts, dict):
            try:
                score = float(key_facts.get("score") or 0) or None
            except Exception:
                pass

        ns_analysis.add_node({
            "id": str(a[0]),
            "tender_id": str(a[1]),
            "summary": str(a[2] or "")[:500],
            "red_flags_count": len(red_flags) if isinstance(red_flags, list) else 0,
            "score": score,
        })

    # ── RelationshipSets ──────────────────────────────────────────────────────
    rs_watches = RelationshipSet("WATCHES", ["Tenant"], ["Tender"], ["id"], ["id"])
    rs_analysis = RelationshipSet("HAS_ANALYSIS", ["Tender"], ["Analysis"], ["id"], ["id"])
    rs_issued = RelationshipSet("ISSUED_BY", ["Tender"], ["Buyer"], ["id"], ["name"])
    rs_cpv = RelationshipSet("CLASSIFIED_AS", ["Tender"], ["CPV"], ["id"], ["code"])
    rs_region = RelationshipSet("IN_REGION", ["Tender"], ["Voivodeship"], ["id"], ["name"])

    for t in tenders:
        tid = str(t[0])
        tenant_id = str(t[1])
        rs_watches.add_relationship({"id": tenant_id}, {"id": tid}, {})

        if t[3]:
            rs_issued.add_relationship({"id": tid}, {"name": str(t[3])[:120]}, {})

        cpv_list = t[4] if isinstance(t[4], list) else ([t[4]] if t[4] else [])
        for cpv in cpv_list:
            if cpv:
                rs_cpv.add_relationship({"id": tid}, {"code": str(cpv)[:8]}, {})

        if t[5]:
            rs_region.add_relationship({"id": tid}, {"name": str(t[5]).lower().strip()}, {})

    for a in analyses:
        if str(a[1]) in tender_ids:
            rs_analysis.add_relationship({"id": str(a[1])}, {"id": str(a[0])}, {})

    # ── Write to Neo4j ────────────────────────────────────────────────────────
    log.info("Writing to Neo4j...")
    with driver.session() as session:
        for ns in [ns_tenant, ns_tender, ns_analysis, ns_buyer, ns_cpv, ns_voiv]:
            ns.create_index(driver)
            ns.merge(driver)
            log.info("  %s: %d nodes", ns.labels, len(ns.nodes))

        for rs in [rs_watches, rs_analysis, rs_issued, rs_cpv, rs_region]:
            rs.merge(driver)
            log.info("  %s: %d rels", rs.rel_type, len(rs.relationships))

    # Verify
    with driver.session() as session:
        counts = session.run("MATCH (n) RETURN labels(n)[0] as label, COUNT(*) as cnt ORDER BY cnt DESC").data()
        log.info("=== Neo4j node counts ===")
        for r in counts:
            log.info("  %s: %d", r["label"], r["cnt"])

    driver.close()
    log.info("Done.")


if __name__ == "__main__":
    main()
