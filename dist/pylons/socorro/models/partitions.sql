--
-- Create partitions for reports, frames and dumps table based on reports.id.
--
-- Adjust the range of the series to change the # of partitions to be created or
-- to adjust the lower/upper bound as needed.
--

SELECT make_partition(1);
