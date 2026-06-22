-- ============================================================================
-- Terra.OS — Baza Danych Przetargów i Budowy
-- Oparta na analizie: atlasprzetargow.pl (BZP, TED, e-Zamówienia)
-- Data: 2026-06-22 | Author: Terra.OS Team
-- ============================================================================
-- Architektura: PostgreSQL 16+ | Partycjonowanie | Full-text search
-- ============================================================================

-- ── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pg_trgm";          -- fuzzy matching (Trigram)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";        -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";-- query performance
CREATE EXTENSION IF NOT EXISTS "hstore";           -- key-value metadata
CREATE EXTENSION IF NOT EXISTS "pgcrypto";         -- hashing (PII anonymization)

-- ── Custom Types ────────────────────────────────────────────────────────────
CREATE TYPE source_type AS ENUM ('BZP', 'TED', 'BK', 'BIP', 'IMPORT');
CREATE TYPE tender_status AS ENUM ('new', 'analyzing', 'ready', 'accepted', 'rejected', 'archived');
CREATE TYPE document_type AS ENUM ('SWZ', 'projekt', 'STWiOR', 'przedmiar', 'zamówienie_uzupełniające', 'odwołanie', 'rozstrzygnięcie');
CREATE TYPE chunk_type AS ENUM ('text', 'table', 'clause', 'price', 'timeline', 'penalty', 'qualification');
CREATE TYPE estimate_variant AS ENUM ('A', 'B');   -- A=dokumentacja, P=Pana
CREATE TYPE violation_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE axiom_class AS ENUM ('A', 'B', 'C', 'D');  -- L1 axioms
CREATE TYPE risk_severity AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE decision_recommendation AS ENUM ('offer', 'reject', 'negotiate');
CREATE TYPE equipment_type AS ENUM ('excavator', 'dump_truck', 'roller', 'loader', 'crane', 'pump', 'other');
CREATE TYPE employee_role AS ENUM ('operator', 'mechanic', 'surveyor', 'site_manager', 'office');
CREATE TYPE shift_type AS ENUM ('day', 'night', 'rotating');

-- ── Schema: tenders (główna tabela przetargów) ─────────────────────────────
CREATE TABLE tenders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id TEXT NOT NULL,                          -- BZP/TED numer
    source source_type NOT NULL,                        -- źródło: BZP, TED, BK, BIP
    title TEXT NOT NULL,                                -- tytuł przetargu
    cpv_codes TEXT[] NOT NULL,                          -- kody CPV (Common Procurement Vocabulary)
    cpv_primary TEXT,                                   -- główny CPV (np. 45000000)
    voivodeship TEXT,                                   -- województwo (znormalizowane)
    county TEXT,                                        -- powiat
    city TEXT,                                          -- miejscowość
    address TEXT,                                       -- pełny adres
    contract_authority TEXT,                            -- zamawiający
    contract_authority_nip TEXT,                        -- NIP zamawiającego
    contract_authority_krs TEXT,                        -- KRS zamawiającego
    publish_date DATE,                                  -- data publikacji w źródle
    deadline TIMESTAMP WITH TIME ZONE,                  -- termin składania ofert
    estimated_value BIGINT,                             -- wartość szacunkowa w groszach
    currency TEXT DEFAULT 'PLN',                        -- waluta
    
    -- Status i score
    status tender_status DEFAULT 'new',
    match_score INTEGER DEFAULT 0,                      -- 0-100 score dopasowania do firmy
    priority INTEGER DEFAULT 0,                         -- priorytet (auto-wykrywany)
    
    -- Meta
    raw_data JSONB,                                     -- surowe dane z źródła (JSON)
    synced_at TIMESTAMP WITH TIME ZONE,                 -- ostatnia synchronizacja z BZP/TED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT chk_value CHECK (estimated_value >= 0),
    CONSTRAINT chk_score CHECK (match_score >= 0 AND match_score <= 100)
);

-- Full-text indexes
CREATE INDEX idx_tenders_title_fts ON tenders USING GIN (to_tsvector('polish', title));
CREATE INDEX idx_tenders_authority_fts ON tenders USING GIN (to_tsvector('polish', contract_authority));
CREATE INDEX idx_tenders_address_trgm ON tenders USING gin (address gin_trgm_ops);
CREATE INDEX idx_tenders_cpv ON tenders USING gin (cpv_codes);
CREATE INDEX idx_tenders_status ON tenders (status);
CREATE INDEX idx_tenders_deadline ON tenders (deadline);
CREATE INDEX idx_tenders_source ON tenders (source);
CREATE INDEX idx_tenders_city ON tenders (city);
CREATE INDEX idx_tenders_voivodeship ON tenders (voivodeship);
CREATE INDEX idx_tenders_score ON tenders (match_score DESC);

-- ============================================================================
-- TABELA: dokumenty (dokumentacja przetargowa)
-- ============================================================================
CREATE TABLE tender_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    doc_type document_type NOT NULL,                    -- typ dokumentu
    file_name TEXT,                                     -- nazwa pliku (SWZ.pdf, przedmiar.xlsx)
    file_size BIGINT,                                   -- rozmiar w bajtach
    file_url TEXT,                                      -- URL do pobrania z BZP
    local_path TEXT,                                    -- lokalna ścieżka po pobraniu
    parsed BOOLEAN DEFAULT FALSE,                       -- czy został przeanalizowany
    parsed_at TIMESTAMP WITH TIME ZONE,                 -- data analizy
    metadata HSTORE,                                    -- metadane: {page_count => '45', author => 'Jan Kowalski'}
    embedding_vector vector(768),                       -- embedding dla RAG (OpenAI/Local)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tender_docs_tender ON tender_documents (tender_id);
CREATE INDEX idx_tender_docs_type ON tender_documents (doc_type);

-- ============================================================================
-- TABELA: chunki (fragmenty przeanalizowanych dokumentów)
-- ============================================================================
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    document_id UUID REFERENCES tender_documents(id),   -- optional: link do dokumentu
    
    page INTEGER,                                       -- numer strony
    position TEXT,                                      -- pozycja w przedmiarze (np. "1.1.1")
    content TEXT NOT NULL,                              -- treść chunka
    chunk_type chunk_type NOT NULL,                     -- typ: text, table, clause, price...
    embedding_vector vector(768),                       -- embedding
    relevance_score FLOAT,                              -- relevancja dla danego tenderu
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunks_tender ON document_chunks (tender_id);
CREATE INDEX idx_chunks_type ON document_chunks (chunk_type);
CREATE INDEX idx_chunks_content_fts ON document_chunks USING GIN (to_tsvector('polish', content));

-- ============================================================================
-- TABELA: czerwone flagi (ryzyka wykryte przez analizę)
-- ============================================================================
CREATE TABLE red_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    
    flag_type TEXT NOT NULL,                            -- price, quantity, technical, legal, timeline
    severity risk_severity NOT NULL,                    -- low, medium, high, critical
    description TEXT NOT NULL,                          -- opis problemu
    source_page INTEGER,                                -- strona źródłowa
    source_position TEXT,                               -- pozycja w dokumencie
    potential_cost BIGINT,                              -- szacowana strata (grosze)
    recommended_action TEXT,                            -- rekomendowana akcja
    
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,                     -- czy zostało rozwiązane
    
    FOREIGN KEY (tender_id) REFERENCES tenders(id)
);

CREATE INDEX idx_red_flags_tender ON red_flags (tender_id);
CREATE INDEX idx_red_flags_severity ON red_flags (severity);

-- ============================================================================
-- TABELA: rozbieżności (discrepancies między przedmiarem a projektem)
-- ============================================================================
CREATE TABLE discrepancies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    
    disc_type TEXT NOT NULL,                            -- quantity, description, missing, extra
    description TEXT NOT NULL,
    beforemiar_item TEXT,                               -- pozycja w przedmiarze
    design_coverage BOOLEAN DEFAULT FALSE,              -- czy projekt to uwzględnia
    severity TEXT,                                      -- low, medium, high
    provenance JSONB,                                   -- {page, line, position}
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_discrepancies_tender ON discrepancies (tender_id);

-- ============================================================================
-- TABELA: kosztorysy (2 warianty)
-- ============================================================================
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    variant estimate_variant NOT NULL,                  -- A = z dokumentacji, B = Pana
    
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    total_net BIGINT,                                   -- netto (grosze)
    total_vat BIGINT,                                   -- VAT 23% (grosze)
    total_gross BIGINT,                                 -- brutto (grosze)
    labor_cost BIGINT,                                  -- robocizna
    equipment_cost BIGINT,                              -- sprzęt
    material_cost BIGINT,                               -- materiały
    overhead_cost BIGINT,                               -- nakład ogólny
    profit BIGINT                                       -- zysk/marża
);

CREATE INDEX idx_estimates_tender ON estimates (tender_id);
CREATE INDEX idx_estimates_variant ON estimates (variant);

-- ============================================================================
-- TABELA: pozycje kosztorysu
-- ============================================================================
CREATE TABLE estimate_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estimate_id UUID NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    
    position TEXT,                                      -- numer pozycji (np. "1.1.1")
    description TEXT NOT NULL,
    unit TEXT,                                          -- jednostka (m³, m², szt...)
    quantity FLOAT NOT NULL,                            -- ilość
    unit_price BIGINT NOT NULL,                         -- cena jednostkowa (grosze)
    total_price BIGINT NOT NULL,                        -- wartość pozycji (grosze)
    source TEXT                                         -- źródło: KNR, KNRiT, Pana Excel...
);

CREATE INDEX idx_lines_estimate ON estimate_lines (estimate_id);

-- ============================================================================
-- TABELA: analiza ryzyka (L1, L2, L3)
-- ============================================================================
CREATE TABLE risk_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    estimate_id UUID NOT NULL REFERENCES estimates(id) ON DELETE CASCADE,
    tender_id UUID NOT NULL REFERENCES tenders(id),
    
    -- L1: Reguły twarde
    l1_verdict TEXT,                                    -- feasible, risky, infeasible
    l1_violations JSONB,                                -- naruszenia reguł (array)
    l1_derived_facts JSONB,                             -- fakty wyprowadzone
    
    -- L2: Analiza stochastyczna
    l2_scenarios JSONB,                                 -- scenariusze (optymistyczny, realistyczny...)
    l2_dominant_drivers JSONB,                          -- dominujące czynniki ryzyka
    l2_target_margin_probability FLOAT,                 -- prawdopodobieństwo marży >= 10%
    
    -- L3: Wyjaśnienie AI
    l3_explanation TEXT,                                -- ludzkie wyjaśnienie
    l3_model TEXT,                                      -- model: Ollama/Qwen3, Claude...
    l3_tokens_used INTEGER,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_risk_tender ON risk_analysis (tender_id);
CREATE INDEX idx_risk_estimate ON risk_analysis (estimate_id);

-- ============================================================================
-- TABELA: decyzje i rekomendacje
-- ============================================================================
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    
    offer_price BIGINT,                                 -- rekomendowana cena (grosze)
    recommendation decision_recommendation,             -- offer, reject, negotiate
    confidence FLOAT,                                   -- pewność 0-1
    reasoning TEXT,                                     -- uzasadnienie
    key_factors JSONB,                                  -- kluczowe czynniki
    
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_decisions_tender ON decisions (tender_id);

-- ============================================================================
-- TABELA: sprzęt (fleet management)
-- ============================================================================
CREATE TABLE equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,                                 -- nazwa (CAT 320, Scania P320...)
    type equipment_type NOT NULL,
    capacity TEXT,                                      -- pojemność/moc
    availability BOOLEAN DEFAULT TRUE,                  -- dostępny/nie
    location TEXT,                                      -- lokalizacja
    purchase_date DATE,                                 -- data zakupu
    last_maintenance DATE,                              -- ostatni przegląd
    notes TEXT,                                         -- uwagi
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_equip_availability ON equipment (availability);

-- ============================================================================
-- TABELA: pracownicy (zespół)
-- ============================================================================
CREATE TABLE employees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    name_short TEXT,                                    -- inicjały (MK, PZ...)
    competencies TEXT[],                                -- kompetencje
    available BOOLEAN DEFAULT TRUE,                     -- dostępny
    current_project TEXT,                               -- aktualny projekt
    role employee_role,                                 -- rola
    phone TEXT,                                         -- numer telefonu
    notes TEXT,                                         
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_employees_available ON employees (available);

-- ============================================================================
-- TABELA: harmonogram prac (daily plan)
-- ============================================================================
CREATE TABLE work_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    
    date DATE NOT NULL,                                 -- data planu
    start_time TIME,                                    -- godzina rozpoczęcia
    end_time TIME,                                      -- godzina zakończenia
    task TEXT NOT NULL,                                 -- zadanie (Wykop ziemny, Nasyp...)
    equipment_ids UUID[],                               -- sprzęt potrzebny
    employee_ids UUID[],                                -- pracownicy potrzebni
    location TEXT,                                      -- lokalizacja
    notes TEXT,                                         -- uwagi
    status TEXT DEFAULT 'planned',                      -- planned, in_progress, done, cancelled
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_work_plans_tender ON work_plans (tender_id);
CREATE INDEX idx_work_plans_date ON work_plans (date);

-- ============================================================================
-- TABELA: activity_log (audit trail)
-- ============================================================================
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action TEXT NOT NULL,                               -- akcja (zwiad_analizuj, kosztorys_generuj...)
    tender_id UUID REFERENCES tenders(id),              -- optional: powiązany tender
    user TEXT,                                          -- user/system
    details JSONB,                                      -- szczegóły akcji
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_tender ON activity_log (tender_id);
CREATE INDEX idx_activity_timestamp ON activity_log (timestamp DESC);

-- ============================================================================
-- TABELA: saved_searches (alerty email)
-- ============================================================================
CREATE TABLE saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_email TEXT NOT NULL,                           -- email użytkownika
    search_params JSONB NOT NULL,                       -- parametry wyszukiwania
    active BOOLEAN DEFAULT TRUE,                        -- czy alert aktywny
    last_sent TIMESTAMP WITH TIME ZONE,                 -- ostatnia wysyłka
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- VIEWS (widoki pomocnicze)
-- ============================================================================

-- Widok: wszystkie aktywnych przetargów z metrykami
CREATE VIEW v_active_tenders AS
SELECT 
    t.*,
    COALESCE(
        (SELECT COUNT(*) FROM red_flags rf WHERE rf.tender_id = t.id AND rf.severity IN ('high','critical')),
        0
    ) AS critical_flags,
    COALESCE(
        (SELECT COUNT(*) FROM tender_docs td WHERE td.tender_id = t.id),
        0
    ) AS document_count
FROM tenders t
WHERE t.status IN ('new', 'analyzing', 'ready')
  AND t.deadline > NOW()
ORDER BY t.deadline ASC;

-- Widok: statystyki firmowe
CREATE VIEW v_company_stats AS
SELECT 
    ca AS contract_authority,
    COUNT(*) AS total_tenders,
    AVG(match_score) AS avg_score,
    SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) AS won_tenders,
    SUM(estimated_value) AS total_value
FROM tenders
GROUP BY ca
ORDER BY total_value DESC;

-- ============================================================================
-- MIGRACJA DANYCH: import z BZP/TED (przykładowe dane)
-- ============================================================================

-- Insert sample tenders (from atlasprzetargow.pl analysis)
INSERT INTO tenders (external_id, source, title, cpv_codes, cpv_primary, voivodeship, county, city, address, contract_authority, contract_authority_nip, publish_date, deadline, estimated_value, match_score, raw_data)
VALUES 
    ('BZP-2026-001', 'BZP', 'Budowa drogi gminnej nr 1234B', ARRAY['45232000-7', '45233000-4'], '45232000-7', 'dolnośląskie', 'dzierżoniowski', 'Dzierżoniów', 'ul. Budowlana 15', 'Gmina Dzierżoniów', '8991234567', '2026-06-15', '2026-07-07 14:00:00+02', 285000000, 85, '{"source": "BZP", "procedure_type": "otwarty"}'::jsonb),
    ('BZP-2026-002', 'BZP', 'Przebudowa placu zabaw', ARRAY['45236100-0', '32430000-3'], '45236100-0', 'dolnośląskie', 'wałbrzyski', 'Wałbrzych', 'ul. Parkowa 5', 'Miasto Wałbrzych', '8997654321', '2026-06-18', '2026-06-30 12:00:00+02', 48500000, 62, '{"source": "BZP", "procedure_type": "ograniczony"}'::jsonb),
    ('TED-2026-001', 'TED', 'Budowa jednostek wytwórczych + akumulator ciepła', ARRAY['45111300-6', '40300000-3'], '45111300-6', 'dolnośląskie', 'wrocławski', 'Wrocław', 'ul. Energetyczna 10', 'Wrocławskie Cieplownie Sp. z o.o.', '8991112222', '2026-06-20', '2026-07-28 10:00:00+02', 1500000000, 45, '{"source": "TED", "procedure_type": "otwarty"}'::jsonb),
    ('BZP-2026-003', 'BZP', 'Dostawy artykułów spożywczych dla DPS', ARRAY['44332000-7', '44310000-5'], '44332000-7', 'mazowieckie', 'pułtuski', 'Pułtusk', 'ul. Słowackiego 12', 'DPS "Pod Sosnami"', '8993334444', '2026-06-19', '2026-06-29 15:00:00+02', 12000000, 30, '{"source": "BZP"}'::jsonb),
    ('BZP-2026-004', 'BZP', 'Pielęgnacja zieleni w Połońcu', ARRAY['81300000-6', '01610000-5'], '81300000-6', 'świętokrzyskie', 'starachowicki', 'Połaniec', 'ul. Parkowa 3', 'Gmina Połaniec', '8995556666', '2026-06-17', '2026-07-20 14:00:00+02', 34000000, 55, '{"source": "BZP"}'::jsonb);

-- Insert sample equipment
INSERT INTO equipment (name, type, capacity, availability, location) VALUES
    ('CAT 320', 'excavator', '20 ton', TRUE, 'Dzierżoniów, ul. Budowlana'),
    ('Scania P320', 'dump_truck', '32 m³', TRUE, 'Dzierżoniów, magazyn'),
    ('Bomag BW 213', 'roller', '12 ton', FALSE, 'Wałbrzych, plac zabaw'),
    ('JCB 3CX', 'excavator', '9 ton', TRUE, 'Warszawa, budowa'),
    ('Volvo FMX', 'dump_truck', '28 m³', TRUE, 'Wrocław, port'),
    ('Liebherr LTM 1100', 'crane', '100 ton', TRUE, 'Dzierżoniów, magazyn'),
    ('Pompa Grundfos', 'pump', '500 m³/h', TRUE, 'Magazyn centralny');

-- Insert sample employees
INSERT INTO employees (name, name_short, competencies, available, current_project) VALUES
    ('Michał Kowalski', 'MK', ARRAY['koparka', 'wykopy', 'nadzór'], TRUE, NULL),
    ('Piotr Ziemiański', 'PZ', ARRAY['wywrotka', 'transport', 'logistyka'], TRUE, NULL),
    ('Tomasz Lewandowski', 'TL', ARRAY['walcowanie', 'zagęszczanie'], FALSE, 'Dzierżoniów'),
    ('Andrzej Mazur', 'AM', ARRAY['betonowanie', 'formy'], TRUE, NULL),
    ('Krzysztof Nowak', 'KN', ARRAY['pomiar', 'geodezja', 'poziomica'], TRUE, NULL),
    ('Jacek Wiśniewski', 'JW', ARRAY['mechanik', 'serwis'], TRUE, NULL),
    ('Robert Kowalczyk', 'RK', ARRAY['kierownik', 'zarządzanie'], TRUE, NULL);

-- Insert sample red flags for tender BZP-2026-001
INSERT INTO red_flags (tender_id, flag_type, severity, description, source_page, potential_cost, recommended_action)
SELECT 
    t.id,
    'price',
    'high',
    'Cena ofertowa poniżej średniej rynkowej o 15% — ryzyko niskiej marży',
    NULL,
    42750000,  -- 15% of 285M groszy
    'Negocjuj przedmiot lub sprawdź kosztorys'
FROM tenders t WHERE t.external_id = 'BZP-2026-001'
UNION ALL
SELECT 
    t.id,
    'timeline',
    'medium',
    'Skrócony termin realizacji — ryzyko kół karalnych',
    NULL,
    15000000,
    'Wymagaj przedłużenia terminu'
FROM tenders t WHERE t.external_id = 'BZP-2026-001';

-- Insert sample cost estimates (variant A - documentation)
INSERT INTO estimates (tender_id, variant, total_net, total_vat, total_gross, labor_cost, equipment_cost, material_cost, overhead_cost, profit)
SELECT 
    t.id, 'A', 220000000, 50600000, 270600000, 95000000, 65000000, 55000000, 5000000, 14000000
FROM tenders t WHERE t.external_id = 'BZP-2026-001';

-- Insert sample cost estimates (variant B - Pana)
INSERT INTO estimates (tender_id, variant, total_net, total_vat, total_gross, labor_cost, equipment_cost, material_cost, overhead_cost, profit)
SELECT 
    t.id, 'B', 235000000, 54050000, 289050000, 100000000, 72000000, 62000000, 1050000, 14050000
FROM tenders t WHERE t.external_id = 'BZP-2026-001';

-- Insert sample estimate lines (variant A - first 5 positions)
INSERT INTO estimate_lines (estimate_id, position, description, unit, quantity, unit_price, total_price, source)
SELECT 
    e.id,
    '1.1.1', 'Przygotowanie terenu', 'm²', 2500.0, 4500, 11250000, 'KNR 0102'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.1.2', 'Wykop ziemny (grunty I-IV)', 'm³', 1200.0, 6500, 7800000, 'KNR 0111'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.1.3', 'Wykop ziemny (grunty V-VI)', 'm³', 400.0, 12000, 4800000, 'KNR 0111'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '1.2.1', 'Podsypka żwirowa', 'm³', 300.0, 8500, 2550000, 'KNR 0121'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'A'
UNION ALL
SELECT 
    e.id,
    '2.1.1', 'Asfaltowanie warstwa bazowa', 'm²', 2200.0, 18000, 39600000, 'KNR 0151'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'A';

-- Insert sample estimate lines (variant B - Pana — same positions, higher prices)
INSERT INTO estimate_lines (estimate_id, position, description, unit, quantity, unit_price, total_price, source)
SELECT 
    e.id,
    '1.1.1', 'Przygotowanie terenu', 'm²', 2500.0, 5200, 13000000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.1.2', 'Wykop ziemny (grunty I-IV)', 'm³', 1200.0, 7200, 8640000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.1.3', 'Wykop ziemny (grunty V-VI)', 'm³', 400.0, 13500, 5400000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '1.2.1', 'Podsypka żwirowa', 'm³', 300.0, 9200, 2760000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'B'
UNION ALL
SELECT 
    e.id,
    '2.1.1', 'Asfaltowanie warstwa bazowa', 'm²', 2200.0, 20000, 44000000, 'Pana Excel'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001' AND e.variant = 'B';

-- Insert risk analysis for BZP-2026-001
INSERT INTO risk_analysis (estimate_id, tender_id, l1_verdict, l1_violations, l1_derived_facts, l2_scenarios, l2_dominant_drivers, l2_target_margin_probability, l3_explanation, l3_model)
SELECT 
    e.id, e.tender_id,
    'risky',
    '[{"type": "price_margin", "description": "Wariant B droższy o 6.8% niż A"}]',
    '["realizacja wykonywana w sezonie", "dostępność sprzętu ograniczona"]',
    '[{"name": "optymistyczny", "probability": 0.25, "margin": 0.12}, {"name": "realistyczny", "probability": 0.45, "margin": 0.05}, {"name": "pesymistyczny", "probability": 0.20, "margin": -0.02}, {"name": "krytyczny", "probability": 0.10, "margin": -0.08}]',
    '["fluktuacja cen asfaltu", "dostępność koparki CAT 320", "opady deszczu"]',
    0.70,
    'Analiza wykazała, że przy obecnych kosztach Pana (wariant B) marża jest niskia (5%). Ryzyko spada do 20% w przypadku pesymistycznych scenariuszy. Rekomendujemy: 1) negocjacje przedmiaru, 2) korektę kosztorysu o odwodnienie.',
    'Ollama/Qwen3-14B'
FROM estimates e JOIN tenders t ON e.tender_id = t.id WHERE t.external_id = 'BZP-2026-001';

-- Insert decision for BZP-2026-001
INSERT INTO decisions (tender_id, offer_price, recommendation, confidence, reasoning, key_factors)
SELECT 
    t.id,
    285000000,
    'negotiate',
    0.65,
    'Przetarg wykonalny, ale wymaga negocjacji przedmiaru. Wariant B jest droższy — konieczna korekta. Czerwone flagi sugerują ryzyko marży poniżej 5%.',
    '["delta kosztów 6.8%", "2 czerwone flagi", "marża szacowana 5-8%", "dostępność sprzętu ograniczona"]'
FROM tenders t WHERE t.external_id = 'BZP-2026-001';

-- ============================================================================
-- TABELA: audit log
-- ============================================================================
INSERT INTO activity_log (action, tender_id, user, details)
SELECT 
    'zwiad_analizuj', t.id, 'system',
    '{"tender": "BZP-2026-001", "score": 85}'::jsonb
FROM tenders t WHERE t.external_id = 'BZP-2026-001'
UNION ALL
SELECT 
    'kosztorys_generuj', t.id, 'system',
    '{"variant": "A", "gross": 270600000}'::jsonb
FROM tenders t WHERE t.external_id = 'BZP-2026-001'
UNION ALL
SELECT 
    'risk_analyze', t.id, 'system',
    '{"verdict": "risky", "margin_prob": 0.70}'::jsonb
FROM tenders t WHERE t.external_id = 'BZP-2026-001';

-- ============================================================================
-- INDEXES PERFORMANCE
-- ============================================================================
-- Materialized view for dashboard metrics
CREATE MATERIALIZED VIEW m_dashboard_stats AS
SELECT 
    COUNT(*) FILTER (WHERE status = 'new') AS new_tenders,
    COUNT(*) FILTER (WHERE status = 'analyzing') AS analyzing_tenders,
    COUNT(*) FILTER (WHERE status = 'ready') AS ready_tenders,
    COUNT(*) FILTER (WHERE status = 'accepted') AS won_tenders,
    COUNT(*) FILTER (WHERE status = 'rejected') AS lost_tenders,
    SUM(CASE WHEN status = 'accepted' THEN estimated_value ELSE 0 END) AS total_won_value,
    AVG(match_score) FILTER (WHERE match_score > 0) AS avg_match_score,
    COUNT(DISTINCT voivodeship) AS voivodeships_covered
FROM tenders
WHERE status != 'archived';

-- Refresh materialized view
CREATE INDEX idx_dashboard_stats ON m_dashboard_stats USING btree (new_tenders);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_dashboard_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY m_dashboard_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: fuzzy search tenders
CREATE OR REPLACE FUNCTION search_tenders(query TEXT, limit_count INTEGER DEFAULT 20)
RETURNS TABLE (
    id UUID,
    external_id TEXT,
    title TEXT,
    cpv_codes TEXT[],
    voivodeship TEXT,
    city TEXT,
    contract_authority TEXT,
    deadline TIMESTAMP WITH TIME ZONE,
    match_score INTEGER,
    relevance FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id, t.external_id, t.title, t.cpv_codes, t.voivodeship, 
        t.city, t.contract_authority, t.deadline, t.match_score,
        (ts_rank(to_tsvector('polish', t.title || ' ' || COALESCE(t.contract_authority, '')), 
                 plainto_tsquery('polish', query)) +
         ts_rank(to_tsvector('polish', t.address), 
                 plainto_tsquery('polish', query))) AS relevance
    FROM tenders t
    WHERE to_tsvector('polish', t.title || ' ' || COALESCE(t.contract_authority, '')) 
          @@ plainto_tsquery('polish', query)
       OR t.address % query  -- trigram similarity
       OR t.voivodeship % query
    ORDER BY relevance DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Function: get tender delta (variant A vs B)
CREATE OR REPLACE FUNCTION get_estimate_delta(tender_uuid UUID)
RETURNS TABLE (
    variant_a_gross BIGINT,
    variant_b_gross BIGINT,
    delta_gross BIGINT,
    delta_percent FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.total_gross,
        b.total_gross,
        b.total_gross - a.total_gross,
        CASE WHEN a.total_gross > 0 
             THEN ((b.total_gross - a.total_gross) * 100.0 / a.total_gross)
             ELSE 0 
        END
    FROM estimates a
    JOIN estimates b ON b.tender_id = a.tender_id AND b.variant = 'B'
    WHERE a.tender_id = tender_uuid AND a.variant = 'A';
END;
$$ LANGUAGE plpgsql;

-- Function: anonymize PII (for data export)
CREATE OR REPLACE FUNCTION anonymize_pii(text_input TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(
        hmac(text_input, 'terra-os-secret-key', 'sha256'),
        'hex'
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TABLE tenders IS 'Główna tabela przetargów — agregacja z BZP, TED, BK, BIP';
COMMENT ON COLUMN tenders.cpv_codes IS 'Kody CPV (Common Procurement Vocabulary) — klasyfikacja branżowa';
COMMENT ON COLUMN tenders.match_score IS 'Score 0-100: dopasowanie oferty firmy do przetargu';
COMMENT ON COLUMN document_chunks.chunk_type IS 'Typ chunka: text, table, clause, price, timeline, penalty, qualification';
COMMENT ON TABLE estimates IS 'Kosztorysy: A=z dokumentacji (KNR), B=z Pana Excel';
COMMENT ON TABLE risk_analysis IS '3-warstwowa analiza: L1(reguły), L2(ryzyko), L3(AI)';
COMMENT ON TABLE decisions IS 'Rekomendacje decyzji: offer/reject/negotiate z pewnością';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
-- Generated: 2026-06-22
-- Compatible: PostgreSQL 16+
-- Data sources: BZP (ezamowienia.gov.pl), TED (ted.europa.eu)
-- Based on analysis: atlasprzetargow.pl
-- ============================================================================
