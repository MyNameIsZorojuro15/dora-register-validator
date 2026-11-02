-- Cross-template completeness and consistency. Output columns: rule_id, template, row, key, col, value, message
-- Parameters: $tol (absolute tolerance for the expense reconciliation, in currency units)

WITH contract_provider AS (   -- who signs: B_03.02 is the source of truth for contract -> provider
    SELECT DISTINCT c0010 AS ref, c0020 AS provider FROM b_03_02
),
contract_fn AS (              -- contract -> functions it supports, with their criticality (inner join: unknown functions are DRV-33)
    SELECT DISTINCT s.c0010 AS ref, f.c0050 AS critical FROM b_02_02 s JOIN b_06_01 f ON f.c0010 = s.c0050
),
contract_crit AS (
    SELECT ref, bool_or(critical = 'Yes') AS is_critical FROM contract_fn GROUP BY ref
),
first_row AS (                -- one issue per contract, on its first B_02.02 row
    SELECT c0010 AS ref, min(_row) AS _row FROM b_02_02 GROUP BY c0010
),
spend AS (                    -- provider total vs the sum of its contracts, same currency only
    SELECT cp.provider,
           count(*) AS n_contracts,
           sum(TRY_CAST(k.c0050 AS DOUBLE)) AS contracts_sum,
           bool_and(k.c0040 = p.c0090) AS same_ccy,
           bool_and(TRY_CAST(k.c0050 AS DOUBLE) IS NOT NULL) AS all_numeric
    FROM contract_provider cp
    JOIN b_02_01 k ON k.c0010 = cp.ref
    JOIN b_05_01 p ON p.c0010 = cp.provider
    GROUP BY cp.provider
),
chain AS (
    SELECT *, TRY_CAST(c0050 AS INTEGER) AS rnk,
           dense_rank() OVER (PARTITION BY c0010, c0020, c0030 ORDER BY TRY_CAST(c0050 AS INTEGER)) AS dr
    FROM b_05_02
)
-- DRV-40: a contract must be listed in every template that is built around it
SELECT 'DRV-40' AS rule_id, 'B_02.01' AS template, k._row AS row, k.c0010 AS key, 'c0010' AS col, k.c0010 AS value,
       'Contract has no row in: ' || concat_ws(', ',
           CASE WHEN NOT EXISTS (SELECT 1 FROM b_03_01 x WHERE x.c0010 = k.c0010) THEN 'B_03.01' END,
           CASE WHEN NOT EXISTS (SELECT 1 FROM b_03_02 x WHERE x.c0010 = k.c0010) THEN 'B_03.02' END,
           CASE WHEN k.c0020 <> 'Overarching/master agreement' AND NOT EXISTS (SELECT 1 FROM b_02_02 x WHERE x.c0010 = k.c0010) THEN 'B_02.02' END,
           CASE WHEN k.c0020 <> 'Overarching/master agreement' AND NOT EXISTS (SELECT 1 FROM b_04_01 x WHERE x.c0010 = k.c0010) THEN 'B_04.01' END
       ) AS message
FROM b_02_01 k
WHERE NOT EXISTS (SELECT 1 FROM b_03_01 x WHERE x.c0010 = k.c0010)
   OR NOT EXISTS (SELECT 1 FROM b_03_02 x WHERE x.c0010 = k.c0010)
   OR (k.c0020 <> 'Overarching/master agreement'
       AND (NOT EXISTS (SELECT 1 FROM b_02_02 x WHERE x.c0010 = k.c0010)
         OR NOT EXISTS (SELECT 1 FROM b_04_01 x WHERE x.c0010 = k.c0010)))
UNION ALL   -- DRV-41: service provider differs from the signing provider
SELECT 'DRV-41', 'B_02.02', s._row, s.c0010, 'c0030', s.c0030,
       'Provider ' || s.c0030 || ' is not among the providers signing this contract in B_03.02'
FROM b_02_02 s
WHERE EXISTS (SELECT 1 FROM b_03_02 x WHERE x.c0010 = s.c0010)
  AND NOT EXISTS (SELECT 1 FROM contract_provider cp WHERE cp.ref = s.c0010 AND cp.provider = s.c0030)
UNION ALL   -- DRV-42: provider used by no contract and not the ultimate parent of another provider
SELECT 'DRV-42', 'B_05.01', p._row, p.c0010, 'c0010', p.c0010, 'Provider is used by no contract and is nobody''s ultimate parent'
FROM b_05_01 p
WHERE NOT EXISTS (SELECT 1 FROM b_03_02 x WHERE x.c0020 = p.c0010)
  AND NOT EXISTS (SELECT 1 FROM b_02_02 x WHERE x.c0030 = p.c0010)
  AND NOT EXISTS (SELECT 1 FROM b_05_01 q WHERE q.c0110 = p.c0010 AND q._row <> p._row)
UNION ALL   -- DRV-43a: contract supports a critical function but has no assessment
SELECT 'DRV-43', 'B_02.02', fr._row, fr.ref, 'c0010', fr.ref, 'Contract supports a critical or important function but has no row in B_07.01'
FROM first_row fr JOIN contract_crit cc ON cc.ref = fr.ref
WHERE cc.is_critical AND NOT EXISTS (SELECT 1 FROM b_07_01 a WHERE a.c0010 = fr.ref)
UNION ALL   -- DRV-43b: assessment exists but the contract supports no critical function
SELECT 'DRV-43', 'B_07.01', a._row, a.c0010 || '|' || a.c0020 || '|' || a.c0040, 'c0010', a.c0010,
       'Assessment row for a contract that supports no critical or important function'
FROM b_07_01 a
WHERE EXISTS (SELECT 1 FROM contract_crit cc WHERE cc.ref = a.c0010 AND NOT cc.is_critical)
UNION ALL   -- DRV-44: level of reliance only for critical functions
SELECT 'DRV-44', 'B_02.02', s._row, s.c0010, 'c0180', s.c0180,
       CASE WHEN f.c0050 = 'Yes' THEN 'Critical function but level of reliance is blank'
            ELSE 'Level of reliance is filled for a function that is not critical' END
FROM b_02_02 s JOIN b_06_01 f ON f.c0010 = s.c0050
WHERE (f.c0050 = 'Yes' AND s.c0180 = '') OR (f.c0050 = 'No' AND s.c0180 <> '')
UNION ALL   -- DRV-45: critical + hard to substitute + no exit plan
SELECT 'DRV-45', 'B_07.01', a._row, a.c0010 || '|' || a.c0020 || '|' || a.c0040, 'c0080', a.c0080,
       a.c0050 || ' provider supporting a critical function, without an exit plan'
FROM b_07_01 a
WHERE a.c0050 IN ('Not substitutable', 'Highly complex substitutability') AND a.c0080 IN ('false', '0')
UNION ALL   -- DRV-46: provider total expense vs sum of its contracts
SELECT 'DRV-46', 'B_05.01', p._row, p.c0010, 'c0100', p.c0100,
       'Provider total ' || p.c0100 || ' ' || p.c0090 || ' but its ' || s.n_contracts || ' contract(s) add up to '
       || round(s.contracts_sum, 2)
FROM b_05_01 p JOIN spend s ON s.provider = p.c0010
WHERE TRY_CAST(p.c0100 AS DOUBLE) IS NOT NULL AND s.same_ccy AND s.all_numeric
  AND abs(TRY_CAST(p.c0100 AS DOUBLE) - s.contracts_sum) > $tol
UNION ALL   -- DRV-47a: ranks must run 1, 2, 3 ... without gaps
SELECT 'DRV-47', 'B_05.02', _row, c0010 || '|' || c0020 || '|' || c0030, 'c0050', c0050,
       'Rank ' || c0050 || ' follows a gap: ranks must run 1, 2, 3 without gaps'
FROM chain WHERE rnk IS NOT NULL AND rnk <> dr
UNION ALL   -- DRV-47b: a provider is not its own sub-contractor
SELECT 'DRV-47', 'B_05.02', _row, c0010 || '|' || c0020 || '|' || c0030, 'c0060', c0060,
       'The sub-contractor is the provider itself'
FROM b_05_02 WHERE c0060 <> '' AND c0060 = c0030
