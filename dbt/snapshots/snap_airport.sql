{% snapshot snap_airport %}
{{ config(target_schema='dbt_snap', unique_key='AirportCode', strategy='check', check_cols=['AirportName','City','CountryCode','TimeZoneName']) }}
select AirportCode,AirportName,City,CountryCode,TimeZoneName from {{ source('reference','Airport') }}
{% endsnapshot %}
