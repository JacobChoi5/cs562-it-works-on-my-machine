-- Predicate for grouping var 2 references 1_avg_quant, so g1 must be computed first.
WITH g1 AS (
    SELECT
        cust,
        SUM(quant) AS sum_quant_1,
        AVG(quant) AS avg_quant_1
    FROM sales
    WHERE state = 'NY'
    GROUP BY cust
),
g2 AS (
    SELECT
        s.cust,
        COUNT(s.quant) AS count_quant_2,
        SUM(s.quant)   AS sum_quant_2
    FROM sales s
    JOIN g1 ON s.cust = g1.cust
    WHERE s.state = 'NJ'
      AND s.quant > g1.avg_quant_1
    GROUP BY s.cust
    HAVING COUNT(s.quant) > 2
)
SELECT
    g1.cust,
    g1.sum_quant_1   AS "1_sum_quant",
    g1.avg_quant_1   AS "1_avg_quant",
    g2.count_quant_2 AS "2_count_quant",
    g2.sum_quant_2   AS "2_sum_quant"
FROM g1
JOIN g2 ON g1.cust = g2.cust;
