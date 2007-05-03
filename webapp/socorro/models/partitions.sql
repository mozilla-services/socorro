--
-- Create partitions for reports table from 2007 to some point in the future.
-- Change the start dates and series range to adjust how many partitions you
-- want to make.  If you make N partitions remember that it translates into N
-- check constraints and N indexes.  The check constraints seem to be checked
-- every time a query comes into the parent reports table, so be careful.
--

select make_partition('reports',to_char(m,'YYYY_MM'),'date',
                      m::text, (m + interval '1 month')::text)
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;

-- and create indexes on them:

select exec(subst('create index reports_$$_idx on reports_$$ (date)',
                  ARRAY[to_char(m,'YYYY_MM'), to_char(m,'YYYY_MM')]))
  from (select timestamptz '2007-01-01' + i * interval '1 month' as m
          from generate_series(0,23) s(i)) s2;
