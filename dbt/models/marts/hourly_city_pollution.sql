select city, pollutant, date_trunc('hour', observed_at) as hour_utc,
       avg(value) as mean_value, count(*) as observation_count,
       bool_or(anomaly) as has_high_reading
from {{ ref('stg_air_quality') }}
group by 1,2,3
