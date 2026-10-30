select f.weather_id, c.name as city, f.observed_at, f.temperature_c,
       f.relative_humidity, f.wind_speed_kmh, f.precipitation_mm, f.weather_code
from {{ source('warehouse', 'fact_weather') }} f
join {{ source('warehouse', 'dim_city') }} c using (city_id)
