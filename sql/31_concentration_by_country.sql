-- Spend by country, three ways: headquarters of the provider, headquarters of its ultimate parent,
-- and country of provision (a contract reported in several countries is split equally between its rows).
WITH contract AS (
    SELECT k.c0010 AS ref, p.c0080 AS hq_country, g.c0080 AS parent_country,
           TRY_CAST(k.c0050 AS DOUBLE) * fx.eur_per_unit AS spend_eur
    FROM b_02_01 k
    JOIN (SELECT DISTINCT c0010 AS ref, c0020 AS provider FROM b_03_02) cp ON cp.ref = k.c0010
    JOIN b_05_01 p ON p.c0010 = cp.provider
    JOIN b_05_01 g ON g.c0010 = COALESCE(NULLIF(p.c0110, ''), p.c0010)
    JOIN fx_rates fx ON fx.currency = k.c0040
    WHERE k.c0020 <> 'Overarching/master agreement'
),
crit AS (
    SELECT DISTINCT s.c0010 AS ref FROM b_02_02 s JOIN b_06_01 f ON f.c0010 = s.c0050 WHERE f.c0050 = 'Yes'
),
basis AS (
    SELECT 'provider headquarters' AS basis, ref, hq_country AS country, spend_eur FROM contract
    UNION ALL SELECT 'ultimate parent headquarters', ref, parent_country, spend_eur FROM contract
    UNION ALL SELECT 'country of provision', c.ref, s.c0130, c.spend_eur / n.n
               FROM contract c JOIN b_02_02 s ON s.c0010 = c.ref
               JOIN (SELECT c0010, count(*) AS n FROM b_02_02 GROUP BY c0010) n ON n.c0010 = c.ref
)
SELECT b.basis, b.country,
       country IN (SELECT code FROM eu_members) AS in_eu,
       count(DISTINCT b.ref) AS contracts,
       count(DISTINCT CASE WHEN cr.ref IS NOT NULL THEN b.ref END) AS critical_contracts,
       round(sum(b.spend_eur), 0) AS spend_eur,
       round(sum(b.spend_eur) / sum(sum(b.spend_eur)) OVER (PARTITION BY b.basis), 4) AS spend_share
FROM basis b LEFT JOIN crit cr ON cr.ref = b.ref
GROUP BY b.basis, b.country
ORDER BY b.basis, spend_eur DESC
