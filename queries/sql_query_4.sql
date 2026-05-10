-- Predicates chain: g2 depends on 1_avg_quant, g3 depends on 2_avg_quant.
WITH g1 AS (
    SELECT
        cust,
        prod,
        SUM(quant) AS sum_quant_1,
        AVG(quant) AS avg_quant_1
    FROM sales
    WHERE state = 'NY'
    GROUP BY cust, prod
),
g2 AS (
    SELECT
        s.cust,
        s.prod,
        COUNT(s.quant) AS count_quant_2,
        AVG(s.quant)   AS avg_quant_2
    FROM sales s
    JOIN g1 ON s.cust = g1.cust AND s.prod = g1.prod
    WHERE s.state = 'NJ'
      AND s.quant > g1.avg_quant_1
    GROUP BY s.cust, s.prod
),
g3 AS (
    SELECT
        s.cust,
        s.prod,
        MIN(s.quant) AS min_quant_3,
        MAX(s.quant) AS max_quant_3
    FROM sales s
    JOIN g2 ON s.cust = g2.cust AND s.prod = g2.prod
    WHERE s.state = 'CT'
      AND s.quant > g2.avg_quant_2
    GROUP BY s.cust, s.prod
)
SELECT
    g1.cust,
    g1.prod,
    g1.sum_quant_1   AS "1_sum_quant",
    g1.avg_quant_1   AS "1_avg_quant",
    g2.count_quant_2 AS "2_count_quant",
    g2.avg_quant_2   AS "2_avg_quant",
    g3.min_quant_3   AS "3_min_quant",
    g3.max_quant_3   AS "3_max_quant"
FROM g1
JOIN g2 ON g1.cust = g2.cust AND g1.prod = g2.prod
JOIN g3 ON g1.cust = g3.cust AND g1.prod = g3.prod
WHERE g3.max_quant_3 > g1.avg_quant_1;
