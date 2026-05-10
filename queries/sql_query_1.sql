SELECT
    cust,
    prod,
    SUM(CASE WHEN month BETWEEN 1 AND 3 THEN quant END) AS "1_sum_quant",
    COUNT(CASE WHEN month BETWEEN 1 AND 3 THEN quant END) AS "1_count_quant",
    SUM(CASE WHEN month BETWEEN 7 AND 9 THEN quant END) AS "2_sum_quant",
    COUNT(CASE WHEN month BETWEEN 7 AND 9 THEN quant END) AS "2_count_quant"
FROM sales
GROUP BY cust, prod
HAVING SUM(CASE WHEN month BETWEEN 1 AND 3 THEN quant END) >
       SUM(CASE WHEN month BETWEEN 7 AND 9 THEN quant END);
