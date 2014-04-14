CREATE OR REPLACE FUNCTION product_version_sort_number(sproduct text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
-- reorders the product-version list for a specific
-- product after an update
-- we just reorder the whole group rather than doing
-- something more fine-tuned because it's actually less
-- work for the database and more foolproof.

UPDATE productdims SET sort_key = new_sort
FROM  ( SELECT product, version, 
row_number() over ( partition by product
order by sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
sec1_num1 ASC NULLS FIRST,
sec1_string1 ASC NULLS LAST,
sec1_num2 ASC NULLS FIRST,
sec1_string2 ASC NULLS LAST,
extra ASC NULLS FIRST)
as new_sort
 FROM productdims_version_sort
 WHERE product = sproduct )
AS product_resort
WHERE productdims.product = product_resort.product
AND productdims.version = product_resort.version
AND ( sort_key <> new_sort OR sort_key IS NULL );

RETURN TRUE;
END;$$;


