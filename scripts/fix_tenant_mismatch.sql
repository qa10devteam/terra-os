-- =====================================================
-- TERRA-OS DB FIX SCRIPT
-- Fix: demo user tenant_id mismatch (sees 0 tenders)
-- Strategy: Move all Default Tenant data to demo user's org_id
-- =====================================================
-- 
-- CONTEXT:
-- The API auth router stores user.org_id in JWT
-- The tenders router filters: WHERE tender.tenant_id = user.org_id
-- Demo user org_id = ec3d1e16-2139-48c2-93b5-ffe0defd606d
-- All tenders/data use tenant_id = c48186e2-599a-4c00-910d-9ed16cc5c86e
-- These DON'T match -> demo user sees nothing
--
-- FIX: Update all Default Tenant data to use demo user's org_id
-- =====================================================

BEGIN;

-- Constants
-- OLD tenant (Default Tenant): c48186e2-599a-4c00-910d-9ed16cc5c86e  
-- NEW tenant (demo user org_id): ec3d1e16-2139-48c2-93b5-ffe0defd606d

-- tender table
UPDATE tender 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- estimate table
UPDATE estimate 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- risk_run table
UPDATE risk_run 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- approval_request table
UPDATE approval_request 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- audit_log table
UPDATE audit_log 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- availability table
UPDATE availability 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- calibration_coeff table
UPDATE calibration_coeff 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- competency table
UPDATE competency 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- employee table
UPDATE employee 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- mobile_device table
UPDATE mobile_device 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- resource_equipment table
UPDATE resource_equipment 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- agent_run table
UPDATE agent_run 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- bzp_documents has tender_id FK (tender.tenant_id changed) - no tenant_id col
-- calendar_events - check
UPDATE calendar_events 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- discrepancy
UPDATE discrepancy 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- tender_document
UPDATE tender_document 
SET tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

-- VERIFY
SELECT 'tender' AS tbl, COUNT(*) FROM tender WHERE tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
UNION ALL
SELECT 'estimate', COUNT(*) FROM estimate WHERE tenant_id = 'ec3d1e16-2139-48c2-93b5-ffe0defd606d'
UNION ALL  
SELECT 'Default Tenant remaining', COUNT(*) FROM tender WHERE tenant_id = 'c48186e2-599a-4c00-910d-9ed16cc5c86e';

COMMIT;
