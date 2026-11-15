{{ config(materialized='table') }}
select flight_date, flight_status, count(*) as flight_count, avg(cast(departure_delay_minutes as decimal(10,2))) as avg_delay_minutes
from {{ ref('stg_flight') }} group by flight_date, flight_status
