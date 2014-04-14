CREATE OR REPLACE FUNCTION transform_rules_update_order() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	-- if we've changed the order number, or category reorder
	IF NEW.rule_order <> OLD.rule_order 
		OR NEW.category <> OLD.category THEN
				
		-- insert a new gap
		UPDATE transform_rules
		SET rule_order = rule_order + 1
		WHERE category = NEW.category
			AND rule_order = NEW.rule_order
			AND transform_rule_id <> NEW.transform_rule_id;
	
	END IF;	
		
	RETURN NEW;
END;
$$;


