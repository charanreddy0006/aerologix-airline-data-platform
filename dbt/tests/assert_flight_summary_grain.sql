select flight_date, flight_status
from {{ ref('fct_flight_summary') }}
group by flight_date, flight_status
having count(*) > 1 or min(flight_count) < 1
