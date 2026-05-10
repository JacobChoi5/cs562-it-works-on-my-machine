SELECT
    cust,
    prod,
    SUM(CASE WHEN state = 'NY' THEN quant END) AS "1_sum_quant",
    AVG(CASE WHEN state = 'NY' THEN quant END) AS "1_avg_quant",
    SUM(CASE WHEN state = 'NJ' THEN quant END) AS "2_sum_quant",
    AVG(CASE WHEN state = 'NJ' THEN quant END) AS "2_avg_quant",
    SUM(CASE WHEN state = 'CT' THEN quant END) AS "3_sum_quant",
    MIN(CASE WHEN state = 'CT' THEN quant END) AS "3_min_quant"
FROM sales
GROUP BY cust, prod
HAVING SUM(CASE WHEN state = 'NY' THEN quant END) >
       SUM(CASE WHEN state = 'NJ' THEN quant END);
