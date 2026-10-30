select city, pollutant, date_trunc('day', observed_at) as day_utc,
       avg(value) as mean_value, min(value) as minimum_value,
       max(value) as maximum_value, count(*) as observation_count,
       bool_or(anomaly) as has_high_reading
from {{ ref('stg_air_quality') }}
group by 1,2,3
