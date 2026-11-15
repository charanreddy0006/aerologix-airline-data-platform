{{ config(materialized='table') }}
select f.flight_date, b.cabin_class, count(*) as booking_count,
 sum(case when b.booking_status <> 'CANCELLED' then b.base_fare_usd else 0 end) as booked_revenue_usd
from {{ ref('stg_booking') }} b join {{ ref('stg_flight') }} f on f.flight_id=b.flight_id
group by f.flight_date,b.cabin_class
