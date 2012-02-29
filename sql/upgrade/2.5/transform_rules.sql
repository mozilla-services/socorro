\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION transform_rules_insert_order ()
RETURNS TRIGGER
LANGUAGE plpgsql 
AS $f$
DECLARE order_num INT;
-- this trigger function makes sure that all rules have a unique order
-- within their category, and assigns an order number to new rules
BEGIN
	IF NEW.rule_order IS NULL or NEW.rule_order = 0 THEN
		-- no order supplied, add the rule to the end
		SELECT max(rule_order) 
		INTO order_num
		FROM transform_rules
		WHERE category = NEW.category;
		
		NEW.rule_order := COALESCE(order_num, 0) + 1;
	ELSE
		-- check if there's already a gap there
		PERFORM rule_order 
		FROM transform_rules
		WHERE category = NEW.category
			AND rule_order = NEW.rule_order;
		-- if not, then bump up
		IF FOUND THEN
			UPDATE transform_rules 
			SET rule_order = rule_order + 1
			WHERE category = NEW.category
				AND rule_order = NEW.rule_order;
		END IF;
	END IF;

	RETURN NEW;
END;
$f$;

CREATE OR REPLACE FUNCTION transform_rules_update_order()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $f$
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
$f$;


SELECT create_table_if_not_exists (
	'transform_rules',
$x$
CREATE TABLE transform_rules (
  transform_rule_id SERIAL NOT NULL PRIMARY KEY,
  category CITEXT NOT NULL,
  rule_order INT NOT NULL,
  predicate TEXT NOT NULL DEFAULT '',
  predicate_args TEXT NOT NULL DEFAULT '',
  predicate_kwargs TEXT NOT NULL DEFAULT '',
  action TEXT NOT NULL DEFAULT '',
  action_args TEXT NOT NULL DEFAULT '',
  action_kwargs TEXT NOT NULL DEFAULT '',
  constraint transform_rules_key UNIQUE (category, rule_order)
  	DEFERRABLE INITIALLY DEFERRED
);

insert into transform_rules 
(category, rule_order, predicate, predicate_args, predicate_kwargs, action, action_args, action_kwargs) values
('processor.json_rewrite', 1, 'socorro.processor.processor.json_equal_predicate', 
  '', 'key="ReleaseChannel", value="esr"',
  'socorro.processor.processor.json_reformat_action', 
  '', 'key="Version", format_str="%(Version)sesr"'),
('processor.json_rewrite',  2,    
  'socorro.processor.processor.json_ProductID_predicate','', '',
   'socorro.processor.processor.json_Product_rewrite_action', '', '');
   
CREATE TRIGGER transform_rules_insert_order 
BEFORE insert ON transform_rules
FOR EACH ROW EXECUTE PROCEDURE transform_rules_insert_order();

CREATE TRIGGER transform_rules_update_order 
AFTER update of rule_order, category ON transform_rules
FOR EACH ROW EXECUTE PROCEDURE transform_rules_update_order();

$x$, 'breakpad_rw');
