-- For every critical or important function: how many providers carry it, how hard they are to replace, and what it costs.
-- A contract that supports several functions is counted in full for each of them (spend is not split here).
WITH cf AS (
    SELECT DISTINCT s.c0050 AS fid, s.c0010 AS ref, cp.provider,
           TRY_CAST(k.c0050 AS DOUBLE) * fx.eur_per_unit AS spend_eur
    FROM b_02_02 s
    JOIN (SELECT DISTINCT c0010 AS ref, c0020 AS provider FROM b_03_02) cp ON cp.ref = s.c0010
    JOIN b_02_01 k ON k.c0010 = s.c0010
    JOIN fx_rates fx ON fx.currency = k.c0040
)
SELECT f.c0010 AS function_id, f.c0030 AS function_name, f.c0040 AS entity_lei,
       count(DISTINCT cf.provider) AS providers,
       count(DISTINCT cf.ref) AS contracts,
       count(DISTINCT CASE WHEN a.c0050 IN (SELECT label FROM hard) THEN cf.provider END) AS hard_to_substitute_providers,
       round(sum(cf.spend_eur), 0) AS spend_eur,
       count(DISTINCT cf.provider) = 1 AS single_provider
FROM b_06_01 f
JOIN cf ON cf.fid = f.c0010
LEFT JOIN b_07_01 a ON a.c0010 = cf.ref AND a.c0020 = cf.provider
WHERE f.c0050 = 'Yes'
GROUP BY f.c0010, f.c0030, f.c0040
ORDER BY providers, f.c0010
