CREATE TABLE signaturedims(
    id SERIAL NOT NULL PRIMARY KEY,
    signature CHARACTER VARYING(255) NOT NULL
);

CREATE UNIQUE INDEX signaturedims_signature_key ON signaturedims USING btree (signature);

INSERT INTO signaturedims (signature) VALUES ('ALL');

CREATE TABLE urldims(
    id SERIAL NOT NULL PRIMARY KEY,
    domain CHARACTER VARYING(255) NOT NULL,
    url    CHARACTER VARYING(255) NOT NULL
);
CREATE UNIQUE INDEX urldims_url_domain_key ON urldims USING btree (url, domain);

CREATE TABLE productdims (
        id SERIAL NOT NULL PRIMARY KEY,
        product CHARACTER VARYING(30) NOT NULL,
        version CHARACTER VARYING(16) NOT NULL,
        os_name CHARACTER VARYING(100),
        release CHARACTER VARYING(50) NOT NULL
);

CREATE UNIQUE INDEX productdims_product_version_os_name_release_key ON productdims USING btree (product, version, release, os_name);
CREATE INDEX productdims_product_version_key ON productdims USING btree (product, version);

INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4', 'ALL','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4', 'Win','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4', 'Mac','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.5', 'ALL','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.5', 'Win','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.5', 'Mac','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.6', 'ALL','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.6', 'Win','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.6', 'Mac','major');

INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b2', 'ALL','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b2', 'Win','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b2', 'Mac','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b1', 'ALL','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b1', 'Win','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b1', 'Mac','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1a2', 'ALL','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1a2', 'Win','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1a2', 'Mac','milestone');

INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.6pre', 'ALL','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.6pre', 'Win','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.6pre', 'Mac','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.5pre', 'ALL','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.5pre', 'Win','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.5pre', 'Mac','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4pre', 'ALL','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4pre', 'Win','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.0.4pre', 'Mac','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b3pre', 'ALL','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b3pre', 'Mac','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Firefox', '3.1b3pre', 'Win','development');

INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '2.0.0.18', 'ALL','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '2.0.0.18', 'Mac','major');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '2.0.0.18', 'Win','major');

INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '3.0b1', 'ALL','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '3.0b1', 'Mac','milestone');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '3.0b1', 'Win','milestone');

INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '3.0b2pre', 'ALL','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '3.0b2pre', 'Mac','development');
INSERT INTO productdims (product, version, os_name, release) VALUES ('Thunderbird', '3.0b2pre', 'Win','development');


CREATE TABLE mtbffacts(
        id SERIAL NOT NULL PRIMARY KEY,
        avg_seconds INTEGER NOT NULL,
        report_count INTEGER NOT NULL,
        unique_users INTEGER NOT NULL,
        day DATE,
        productdims_id INTEGER REFERENCES productdims (id)
    );

CREATE INDEX mtbffacts_day_key ON mtbffacts USING btree (day);
CREATE INDEX mtbffacts_product_id_key ON mtbffacts USING btree (productdims_id);

CREATE TABLE mtbfconfig(
  id SERIAL NOT NULL PRIMARY KEY,
  productdims_id INTEGER REFERENCES productdims (id),
  start_dt DATE,
  end_dt DATE
);

CREATE INDEX mtbfconfig_start_dt_key ON mtbfconfig USING btree (start_dt);
CREATE INDEX mtbfconfig_end_dt_key ON mtbfconfig USING btree (end_dt);


INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-16', '2008-02-16' FROM productdims WHERE product = 'Firefox' AND version = '3.0.5';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-04', '2009-02-04' FROM productdims WHERE product = 'Firefox' AND version = '3.0.6pre';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-09', '2008-02-09' FROM productdims WHERE product = 'Thunderbird' AND version = '3.0b2pre';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-09', '2008-02-09' FROM productdims WHERE product = 'Thunderbird' AND version = '3.0b1';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-08', '2008-02-08' FROM productdims WHERE product = 'Firefox' AND version = '3.1b3pre';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-08', '2008-02-08' FROM productdims WHERE product = 'Firefox' AND version = '3.1b2';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-11-19', '2008-01-19' FROM productdims WHERE product = 'Thunderbird' AND version = '2.0.0.18';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-11-12', '2008-01-14' FROM productdims WHERE product = 'Firefox' AND version = '3.0.4';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-10-14', '2008-12-14' FROM productdims WHERE product = 'Firefox' AND version = '3.1b1';
INSERT INTO mtbfconfig (productdims_id, start_dt, end_dt)
  SELECT id, '2008-12-08', '2008-02-08' FROM productdims WHERE product = 'Firefox' AND version = '3.1a2';

CREATE TABLE topcrashurlfacts(
    id SERIAL NOT NULL PRIMARY KEY,
    
    count INTEGER NOT NULL,
    rank INTEGER,

    day DATE NOT NULL,
    productdims_id INTEGER REFERENCES productdims (id),
    urldims_id     INTEGER REFERENCES urldims (id),
    signaturedims_id   INTEGER REFERENCES signaturedims (id)
)WITH (OIDS=TRUE);

CREATE INDEX topcrashurlfacts_count_key ON topcrashurlfacts USING btree (count);
CREATE INDEX topcrashurlfacts_day_key ON topcrashurlfacts USING btree (day);
CREATE INDEX topcrashurlfacts_productdims_key ON topcrashurlfacts USING btree (productdims_id);
CREATE INDEX topcrashurlfacts_urldims_key ON topcrashurlfacts USING btree (urldims_id);
CREATE INDEX topcrashurlfacts_signaturedims_key ON topcrashurlfacts USING btree (signaturedims_id);

CREATE TABLE topcrashurlfactsreports(
  id SERIAL NOT NULL PRIMARY KEY,
  uuid CHARACTER VARYING(50) NOT NULL,  
  comments CHARACTER VARYING(500),
  topcrashurlfacts_id INTEGER REFERENCES topcrashurlfacts (id) ON DELETE CASCADE
);

CREATE INDEX topcrashurlfactsreports_topcrashurlfacts_id_key ON topcrashurlfactsreports USING btree (topcrashurlfacts_id);

CREATE TABLE tcbyurlconfig(
  id SERIAL NOT NULL PRIMARY KEY,
  productdims_id INTEGER REFERENCES productdims (id),
  enabled BOOLEAN
);

INSERT INTO tcbyurlconfig (productdims_id, enabled) 
  SELECT id, 'Y' FROM productdims WHERE product = 'Firefox' AND version = '3.0.5' AND os_name = 'ALL';
INSERT INTO tcbyurlconfig (productdims_id, enabled) 
  SELECT id, 'Y' FROM productdims WHERE product = 'Firefox' AND version = '3.1b2' AND os_name = 'ALL';
INSERT INTO tcbyurlconfig (productdims_id, enabled) 
  SELECT id, 'Y' FROM productdims WHERE product = 'Firefox' AND version = '3.0.6pre' AND os_name = 'ALL';
INSERT INTO tcbyurlconfig (productdims_id, enabled) 
  SELECT id, 'Y' FROM productdims WHERE product = 'Firefox' AND version = '3.1b3pre' AND os_name = 'ALL';