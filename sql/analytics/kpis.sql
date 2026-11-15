USE AeroLogix;
GO
-- On-time departure rate (departure within 15 minutes).
SELECT FlightDate,COUNT(*) CompletedFlights,100.0*SUM(IIF(DepartureDelayMinutes<=15,1,0))/NULLIF(COUNT(*),0) OnTimeDeparturePct FROM ops.Flight WHERE FlightStatus='COMPLETED' GROUP BY FlightDate ORDER BY FlightDate;
-- Completion and cancellation by route.
SELECT Origin,Destination,COUNT(*) Scheduled,SUM(IIF(FlightStatus='COMPLETED',1,0)) Completed,SUM(IIF(FlightStatus='CANCELLED',1,0)) Cancelled,AVG(IIF(FlightStatus='COMPLETED',CAST(DepartureDelayMinutes AS decimal(10,2)),NULL)) AvgDelayMin FROM ops.v_FlightOperations GROUP BY Origin,Destination ORDER BY Scheduled DESC;
-- Fare yield per available seat mile using seat capacity and completed flights.
SELECT SUM(CASE WHEN b.BookingStatus='FLOWN' THEN b.BaseFare ELSE 0 END)/NULLIF(SUM(CAST(a.SeatCapacity AS decimal(18,2))*r.DistanceMiles),0) RevenuePerAvailableSeatMile FROM ops.Booking b JOIN ops.Flight f ON f.FlightId=b.FlightId JOIN ref.Aircraft a ON a.AircraftId=f.AircraftId JOIN ref.Route r ON r.RouteId=f.RouteId WHERE f.FlightStatus='COMPLETED';
GO
