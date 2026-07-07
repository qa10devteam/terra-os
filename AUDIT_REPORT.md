# Terra-OS Database Deep Audit Report
Date: 2026-07-07

## 1. TABLE ROW COUNTS (54 tables)

### With Data:
- tender: 67 rows
- audit_log: 148 rows
- refresh_tokens: 84 rows
- calibration_coeff: 54 rows
- availability: 42 rows
- competency: 30 rows
- employee: 30 rows
- estimate: 22 rows
- calendar_events: 20 rows
- approval_request: 19 rows
- agent_run: 18 rows
- risk_run: 11 rows
- discrepancy: 9 rows
- analysis: 7 rows
- organizations: 4 rows
- tenant: 4 rows
- users: 4 rows
- bzp_documents: 12 rows
- mobile_device: 12 rows
- resource_equipment: 12 rows
- owner_profile: 1 row
- equipment: 1 row
- subcontractors: 1 row
- webhooks: 1 row

### Empty (30 tables):
api_keys, axiom, calendar_event, contract, daily_plan, dispatch, document_chunk,
email_configs, email_logs, entity_verifications, estimate_line, excel_imports,
field_status, gantt_tasks, gus_indicators, historical_bids, job_status,
kosztorys_items, notifications, przedmiar_item, rate_card, rfq, rfq_message,
ted_tenders, tender_comments, tender_document, tender_equipment, tender_subcontractors,
webhook_deliveries, alembic_version(2)

## 2. FOREIGN KEY INTEGRITY
All FK checks pass EXCEPT:
- users -> organizations: 1 user (test41@terra.os) has org_id = NULL

## 3. TENDER TABLE (67 rows, not 23!)
- status=new: 47 (44 with score=0, 2 with score=NULL, 16 missing value_pln)
- status=watching: 4 (1 with score=NULL)
- status=analyzing: 2 (1 with score=NULL)
- status=estimated: 3 (all OK)
- status=decided_go: 5 (2 have NO estimates!)
- status=decided_nogo: 3 (all OK)
- status=archived: 2 (all OK)
- status=matched: 1 (OK)

## 4. CRITICAL BUG: Demo user sees ZERO tenders
- demo@terra-os.pl org_id = ec3d1e16-2139-48c2-93b5-ffe0defd606d
- org.tenant_id = c4879c87-016c-4580-b913-212c904c20fd
- ALL tenders use tenant_id = c48186e2-599a-4c00-910d-9ed16cc5c86e (Default Tenant)
- API uses user.org_id as tenant filter -> 0 rows returned!

## 5. TENDER_DOCUMENT / ESTIMATE
- tender_document: 0 rows (EMPTY)
- estimate: 22 rows (all have total_net_pln, 2 missing overhead/profit)
- estimate_line: 0 rows (inline JSONB used instead)
- document_chunk: 0 rows (no docs parsed)

## 6. QUERY PERFORMANCE (EXPLAIN)
All queries are fast (0.1-0.2ms) due to small dataset.
Seq scans are appropriate at 67 rows.
GIN index on cpv exists but CPV LIKE filter doesn't use it.

## 7. SEQUENCES
Only 1 sequence: audit_log_id_seq, last_value=148, MAX(id)=148 -> IN SYNC

## 8. OTHER ISSUES
- 3 duplicate "QA10 Sp. z o.o." orgs (only ec3d1e16 used by users)
- RSK org has tenant_id=NULL
- test41@terra.os user has org_id=NULL
- All 4 orgs have nip=NULL
- Alembic has 2 active heads (0003_notifications, 0005_phases_41_60)
