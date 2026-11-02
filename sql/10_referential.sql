-- Cross-template referential integrity (EBA technical check 807: key / foreign-key constraints of the data point model).
-- Every table is loaded as text with a _row column (CSV line number, header = line 1). A blank foreign key is a
-- completeness problem (DRV-02), not a referential one, so blanks are skipped here.
-- Output columns: rule_id, template, row, key, col, value, message

WITH contract_refs AS (      -- every column that must point to B_02.01
    SELECT 'B_02.02' AS template, _row, 'c0010' AS col, c0010 AS val FROM b_02_02
    UNION ALL SELECT 'B_03.01', _row, 'c0010', c0010 FROM b_03_01
    UNION ALL SELECT 'B_03.02', _row, 'c0010', c0010 FROM b_03_02
    UNION ALL SELECT 'B_04.01', _row, 'c0010', c0010 FROM b_04_01
    UNION ALL SELECT 'B_05.02', _row, 'c0010', c0010 FROM b_05_02
    UNION ALL SELECT 'B_07.01', _row, 'c0010', c0010 FROM b_07_01
),
entity_refs AS (             -- every column that must point to B_01.02
    SELECT 'B_01.01' AS template, _row, 'c0010' AS col, c0010 AS val FROM b_01_01
    UNION ALL SELECT 'B_01.03', _row, 'c0020', c0020 FROM b_01_03
    UNION ALL SELECT 'B_02.02', _row, 'c0020', c0020 FROM b_02_02
    UNION ALL SELECT 'B_03.01', _row, 'c0020', c0020 FROM b_03_01
    UNION ALL SELECT 'B_04.01', _row, 'c0020', c0020 FROM b_04_01
    UNION ALL SELECT 'B_06.01', _row, 'c0040', c0040 FROM b_06_01
),
provider_refs AS (          -- every column that must point to B_05.01
    SELECT 'B_02.02' AS template, _row, 'c0030' AS col, c0030 AS val FROM b_02_02
    UNION ALL SELECT 'B_03.02', _row, 'c0020', c0020 FROM b_03_02
    UNION ALL SELECT 'B_05.01', _row, 'c0110', c0110 FROM b_05_01
    UNION ALL SELECT 'B_05.02', _row, 'c0030', c0030 FROM b_05_02
    UNION ALL SELECT 'B_05.02', _row, 'c0060', c0060 FROM b_05_02
    UNION ALL SELECT 'B_07.01', _row, 'c0020', c0020 FROM b_07_01
)
SELECT 'DRV-30' AS rule_id, template, _row AS row, val AS key, col, val AS value,
       'Contract reference ' || val || ' is not in B_02.01' AS message
FROM contract_refs WHERE val <> '' AND val NOT IN (SELECT c0010 FROM b_02_01)
UNION ALL
SELECT 'DRV-31', template, _row, val, col, val, 'Entity LEI ' || val || ' is not in B_01.02'
FROM entity_refs WHERE val <> '' AND val NOT IN (SELECT c0010 FROM b_01_02)
UNION ALL
SELECT 'DRV-32', template, _row, val, col, val, 'Provider code ' || val || ' is not in B_05.01'
FROM provider_refs WHERE val <> '' AND val NOT IN (SELECT c0010 FROM b_05_01)
UNION ALL
SELECT 'DRV-33', 'B_02.02', _row, c0050, 'c0050', c0050, 'Function ' || c0050 || ' is not in B_06.01'
FROM b_02_02 WHERE c0050 <> '' AND c0050 NOT IN (SELECT c0010 FROM b_06_01)
UNION ALL   -- an assessment or a supply-chain row must match a contract / provider / service row of B_02.02
SELECT 'DRV-34', 'B_07.01', a._row, a.c0010 || '|' || a.c0020 || '|' || a.c0040, 'c0020', a.c0020,
       'No B_02.02 row has this contract, provider and type of ICT services'
FROM b_07_01 a
WHERE NOT EXISTS (SELECT 1 FROM b_02_02 c WHERE c.c0010 = a.c0010 AND c.c0030 = a.c0020 AND c.c0060 = a.c0040)
UNION ALL
SELECT 'DRV-34', 'B_05.02', s._row, s.c0010 || '|' || s.c0020 || '|' || s.c0030, 'c0030', s.c0030,
       'No B_02.02 row has this contract, provider and type of ICT services'
FROM b_05_02 s
WHERE NOT EXISTS (SELECT 1 FROM b_02_02 c WHERE c.c0010 = s.c0010 AND c.c0030 = s.c0030 AND c.c0060 = s.c0020)
UNION ALL   -- the overarching reference of a subsequent contract must be a master agreement
SELECT 'DRV-35', 'B_02.01', k._row, k.c0010, 'c0030', k.c0030,
       'Overarching reference ' || k.c0030 || ' is not a contract of type Overarching/master agreement'
FROM b_02_01 k
WHERE k.c0030 <> ''
  AND NOT EXISTS (SELECT 1 FROM b_02_01 m WHERE m.c0010 = k.c0030 AND m.c0020 = 'Overarching/master agreement')
UNION ALL   -- branch code must exist under the same head office
SELECT 'DRV-36', 'B_04.01', u._row, u.c0010 || '|' || u.c0040, 'c0040', u.c0040,
       'Branch ' || u.c0040 || ' is not in B_01.03 for this entity'
FROM b_04_01 u
WHERE u.c0040 <> '' AND NOT EXISTS (SELECT 1 FROM b_01_03 b WHERE b.c0010 = u.c0040 AND b.c0020 = u.c0020)
