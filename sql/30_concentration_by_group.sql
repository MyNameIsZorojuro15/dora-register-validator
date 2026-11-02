-- Spend and criticality by ultimate-parent group (DORA Art. 29: concentration risk at group level).
-- Inputs: the register tables, fx_rates(currency, eur_per_unit) and hard(label). Master agreements carry no spend and are left out.
WITH contract AS (
    SELECT k.c0010 AS ref, cp.provider,
           COALESCE(NULLIF(p.c0110, ''), p.c0010) AS group_id,
           TRY_CAST(k.c0050 AS DOUBLE) * fx.eur_per_unit AS spend_eur
    FROM b_02_01 k
    JOIN (SELECT DISTINCT c0010 AS ref, c0020 AS provider FROM b_03_02) cp ON cp.ref = k.c0010
    JOIN b_05_01 p ON p.c0010 = cp.provider
    JOIN fx_rates fx ON fx.currency = k.c0040
    WHERE k.c0020 <> 'Overarching/master agreement'
),
spend AS (
    SELECT group_id, count(DISTINCT provider) AS providers, count(DISTINCT ref) AS contracts, sum(spend_eur) AS spend_eur
    FROM contract GROUP BY group_id
),
crit AS (
    SELECT c.group_id, count(DISTINCT f.c0010) AS critical_functions, count(DISTINCT c.ref) AS critical_contracts
    FROM contract c JOIN b_02_02 s ON s.c0010 = c.ref JOIN b_06_01 f ON f.c0010 = s.c0050
    WHERE f.c0050 = 'Yes' GROUP BY c.group_id
),
hardc AS (
    SELECT c.group_id, count(DISTINCT c.ref) AS hard_to_substitute_contracts
    FROM contract c JOIN b_07_01 a ON a.c0010 = c.ref
    WHERE a.c0050 IN (SELECT label FROM hard) GROUP BY c.group_id
)
SELECT s.group_id,
       g.c0050 AS group_name,
       g.c0080 AS group_country,
       s.providers, s.contracts,
       round(s.spend_eur, 0) AS spend_eur,
       round(s.spend_eur / sum(s.spend_eur) OVER (), 4) AS spend_share,
       COALESCE(c.critical_functions, 0) AS critical_functions,
       COALESCE(c.critical_contracts, 0) AS critical_contracts,
       COALESCE(h.hard_to_substitute_contracts, 0) AS hard_to_substitute_contracts
FROM spend s
JOIN b_05_01 g ON g.c0010 = s.group_id
LEFT JOIN crit c ON c.group_id = s.group_id
LEFT JOIN hardc h ON h.group_id = s.group_id
ORDER BY s.spend_eur DESC
