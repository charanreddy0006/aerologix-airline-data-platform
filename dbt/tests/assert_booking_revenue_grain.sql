select flight_date, cabin_class
from {{ ref('fct_booking_revenue') }}
group by flight_date, cabin_class
having count(*) > 1
    or min(booking_count) < 1
    or min(booked_revenue_usd) < 0
