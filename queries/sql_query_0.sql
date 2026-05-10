SELECT
    cust,
    SUM(CASE WHEN state = 'NY' THEN quant END) AS "1_sum_quant",
    SUM(CASE WHEN state = 'NJ' THEN quant END) AS "2_sum_quant"
FROM sales
GROUP BY cust;
