--
-- Create partitions for reports table from 2007 to some point in the future.
-- Change the start dates and series range to adjust how many partitions you
-- want to make.  If you make N partitions remember that it translates into N
-- check constraints and N indexes.  The check constraints seem to be checked
-- every time a query comes into the parent reports table, so be careful.
--
-- Note that the default is a btree type index.
--
-- You should also have constraint_exclusion turned on in your pgsql config.
-- This prevents unnecessary scanning of the date index on child tables.
--

select make_partition('reports',to_char(m,'YYYY_MM'),'date',
                      m::text, (m + interval '1 month')::text)
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;

-- Create index on date.
select exec(subst('create index idx_reports_$$_date on reports_$$ (date)',
                  ARRAY[to_char(m,'YYYY_MM'), to_char(m,'YYYY_MM')]))
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;

-- Create index on product, version, build.
select exec(subst('create index idx_reports_$$_product_version_build on reports_$$ (product, version, build)',
                  ARRAY[to_char(m,'YYYY_MM'), to_char(m,'YYYY_MM')]))
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;

-- Create a unique index on uuid.
select exec(subst('create unique index idx_reports_$$_uuid on reports_$$ (uuid)',
                  ARRAY[to_char(m,'YYYY_MM'), to_char(m,'YYYY_MM')]))
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;

-- Create an index on signature.
select exec(subst('create index idx_reports_$$_signature on reports_$$ (signature)',
                  ARRAY[to_char(m,'YYYY_MM'), to_char(m,'YYYY_MM')]))
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;

-- Create an index on url.
select exec(subst('create index idx_reports_$$_url on reports_$$ (url)',
                  ARRAY[to_char(m,'YYYY_MM'), to_char(m,'YYYY_MM')]))
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;
