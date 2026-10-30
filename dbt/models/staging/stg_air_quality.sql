select f.air_quality_id, c.name as city, s.name as station, p.code as pollutant,
       f.observed_at, f.value, f.unit, f.anomaly
from {{ source('warehouse', 'fact_air_quality') }} f
join {{ source('warehouse', 'dim_city') }} c using (city_id)
join {{ source('warehouse', 'dim_station') }} s using (station_id)
join {{ source('warehouse', 'dim_pollutant') }} p using (pollutant_id)
join {{ source('warehouse', 'raw_api_response') }} r on r.raw_id = f.raw_id
where r.source = 'xkdr'
