USE AeroLogix;
GO
CREATE OR ALTER PROCEDURE etl.usp_LoadWarehouse AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON; BEGIN TRAN;
 DECLARE @min date=(SELECT MIN(FlightDate) FROM ops.Flight),@max date=(SELECT MAX(FlightDate) FROM ops.Flight);
 IF @min IS NULL BEGIN COMMIT; RETURN; END;
 ;WITH d AS(SELECT @min dt UNION ALL SELECT DATEADD(day,1,dt) FROM d WHERE dt<@max)
 INSERT dw.DimDate(DateKey,FullDate,CalendarYear,CalendarQuarter,MonthNumber,MonthName,DayOfMonth,DayOfWeekName,IsWeekend)
 SELECT CONVERT(int,CONVERT(char(8),dt,112)),dt,YEAR(dt),DATEPART(quarter,dt),MONTH(dt),DATENAME(month,dt),DAY(dt),DATENAME(weekday,dt),IIF(DATEPART(weekday,dt) IN(1,7),1,0) FROM d WHERE NOT EXISTS(SELECT 1 FROM dw.DimDate x WHERE x.FullDate=d.dt) OPTION(MAXRECURSION 0);
 -- SCD2 airport history: close changed versions, then insert new current rows.
 UPDATE t SET IsCurrent=0,ValidTo=SYSUTCDATETIME() FROM dw.DimAirport t JOIN ref.Airport s ON s.AirportCode=t.AirportCode WHERE t.IsCurrent=1 AND (t.AirportName<>s.AirportName OR t.City<>s.City OR t.CountryCode<>s.CountryCode OR t.TimeZoneName<>s.TimeZoneName);
 INSERT dw.DimAirport(AirportCode,AirportName,City,CountryCode,TimeZoneName,IsCurrent,RowHash) SELECT s.AirportCode,s.AirportName,s.City,s.CountryCode,s.TimeZoneName,1,HASHBYTES('SHA2_256',CONCAT(s.AirportName,'|',s.City,'|',s.CountryCode,'|',s.TimeZoneName)) FROM ref.Airport s WHERE NOT EXISTS(SELECT 1 FROM dw.DimAirport t WHERE t.AirportCode=s.AirportCode AND t.IsCurrent=1);
 -- SCD1 aircraft type/capacity update plus SCD3 prior type.
 UPDATE t SET PreviousAircraftType=CASE WHEN t.AircraftType<>s.AircraftType THEN t.AircraftType ELSE t.PreviousAircraftType END,AircraftType=s.AircraftType,SeatCapacity=s.SeatCapacity,ManufactureYear=s.ManufactureYear,RowHash=HASHBYTES('SHA2_256',CONCAT(s.AircraftType,'|',s.SeatCapacity,'|',s.ManufactureYear)) FROM dw.DimAircraft t JOIN ref.Aircraft s ON s.AircraftId=t.AircraftId WHERE t.IsCurrent=1;
 INSERT dw.DimAircraft(AircraftId,AircraftType,SeatCapacity,ManufactureYear,IsCurrent,RowHash) SELECT s.AircraftId,s.AircraftType,s.SeatCapacity,s.ManufactureYear,1,HASHBYTES('SHA2_256',CONCAT(s.AircraftType,'|',s.SeatCapacity,'|',s.ManufactureYear)) FROM ref.Aircraft s WHERE NOT EXISTS(SELECT 1 FROM dw.DimAircraft t WHERE t.AircraftId=s.AircraftId AND t.IsCurrent=1);
 MERGE dw.DimPassenger t USING ops.Passenger s ON t.PassengerId=s.PassengerId WHEN MATCHED AND t.LoyaltyTier<>s.LoyaltyTier THEN UPDATE SET LoyaltyTier=s.LoyaltyTier WHEN NOT MATCHED THEN INSERT(PassengerId,LoyaltyTier) VALUES(s.PassengerId,s.LoyaltyTier);
 INSERT dw.DimRoute(OriginAirportKey,DestinationAirportKey,DistanceMiles) SELECT o.AirportKey,d.AirportKey,r.DistanceMiles FROM ref.Route r JOIN dw.DimAirport o ON o.AirportCode=r.OriginAirportCode AND o.IsCurrent=1 JOIN dw.DimAirport d ON d.AirportCode=r.DestinationAirportCode AND d.IsCurrent=1 WHERE NOT EXISTS(SELECT 1 FROM dw.DimRoute x WHERE x.OriginAirportKey=o.AirportKey AND x.DestinationAirportKey=d.AirportKey);
 -- Keep an existing airport version key when its natural airport remains the same;
 -- change the key only when the source event's airport relationship changes.
 MERGE dw.FactFlight t USING(SELECT f.FlightId,CONVERT(int,CONVERT(char(8),f.FlightDate,112)) DateKey,o.AirportKey OriginKey,o.AirportCode OriginCode,d.AirportKey DestKey,d.AirportCode DestCode,a.AircraftKey,f.FlightStatus,r.DistanceMiles,f.DepartureDelayMinutes FROM ops.Flight f JOIN ref.Route r ON r.RouteId=f.RouteId JOIN dw.DimAirport o ON o.AirportCode=r.OriginAirportCode AND o.IsCurrent=1 JOIN dw.DimAirport d ON d.AirportCode=r.DestinationAirportCode AND d.IsCurrent=1 JOIN dw.DimAircraft a ON a.AircraftId=f.AircraftId AND a.IsCurrent=1) s ON t.FlightId=s.FlightId WHEN MATCHED THEN UPDATE SET FlightDateKey=s.DateKey,OriginAirportKey=CASE WHEN EXISTS(SELECT 1 FROM dw.DimAirport x WHERE x.AirportKey=t.OriginAirportKey AND x.AirportCode=s.OriginCode) THEN t.OriginAirportKey ELSE s.OriginKey END,DestinationAirportKey=CASE WHEN EXISTS(SELECT 1 FROM dw.DimAirport x WHERE x.AirportKey=t.DestinationAirportKey AND x.AirportCode=s.DestCode) THEN t.DestinationAirportKey ELSE s.DestKey END,AircraftKey=s.AircraftKey,FlightStatus=s.FlightStatus,DistanceMiles=s.DistanceMiles,DepartureDelayMinutes=s.DepartureDelayMinutes,CompletedFlights=IIF(s.FlightStatus='COMPLETED',1,0),CancelledFlights=IIF(s.FlightStatus='CANCELLED',1,0) WHEN NOT MATCHED THEN INSERT(FlightId,FlightDateKey,OriginAirportKey,DestinationAirportKey,AircraftKey,FlightStatus,DistanceMiles,DepartureDelayMinutes,CompletedFlights,CancelledFlights) VALUES(s.FlightId,s.DateKey,s.OriginKey,s.DestKey,s.AircraftKey,s.FlightStatus,s.DistanceMiles,s.DepartureDelayMinutes,IIF(s.FlightStatus='COMPLETED',1,0),IIF(s.FlightStatus='CANCELLED',1,0));
 UPDATE dp SET LastSeenDate=x.LastDate,FirstSeenDate=IIF(dp.FirstSeenDate IS NULL OR x.FirstDate<dp.FirstSeenDate,x.FirstDate,dp.FirstSeenDate) FROM dw.DimPassenger dp JOIN (SELECT b.PassengerId,MIN(f.FlightDate) FirstDate,MAX(f.FlightDate) LastDate FROM ops.Booking b JOIN ops.Flight f ON f.FlightId=b.FlightId GROUP BY b.PassengerId) x ON x.PassengerId=dp.PassengerId;
 -- Booking grain is BookingId. Update every mutable source-event attribute, including
 -- relationship keys, so corrections and cancellation transitions are reflected.
 MERGE dw.FactBooking t USING(SELECT b.BookingId,b.FlightId,CONVERT(int,CONVERT(char(8),f.FlightDate,112)) DateKey,p.PassengerKey,o.AirportKey OriginKey,o.AirportCode OriginCode,d.AirportKey DestKey,d.AirportCode DestCode,b.BookingStatus,b.CabinClass,b.BaseFare FROM ops.Booking b JOIN ops.Flight f ON f.FlightId=b.FlightId JOIN ref.Route r ON r.RouteId=f.RouteId JOIN dw.DimPassenger p ON p.PassengerId=b.PassengerId JOIN dw.DimAirport o ON o.AirportCode=r.OriginAirportCode AND o.IsCurrent=1 JOIN dw.DimAirport d ON d.AirportCode=r.DestinationAirportCode AND d.IsCurrent=1) s ON t.BookingId=s.BookingId WHEN MATCHED THEN UPDATE SET FlightId=s.FlightId,FlightDateKey=s.DateKey,PassengerKey=s.PassengerKey,OriginAirportKey=CASE WHEN EXISTS(SELECT 1 FROM dw.DimAirport x WHERE x.AirportKey=t.OriginAirportKey AND x.AirportCode=s.OriginCode) THEN t.OriginAirportKey ELSE s.OriginKey END,DestinationAirportKey=CASE WHEN EXISTS(SELECT 1 FROM dw.DimAirport x WHERE x.AirportKey=t.DestinationAirportKey AND x.AirportCode=s.DestCode) THEN t.DestinationAirportKey ELSE s.DestKey END,BookingStatus=s.BookingStatus,CabinClass=s.CabinClass,BaseFare=s.BaseFare WHEN NOT MATCHED THEN INSERT(BookingId,FlightId,FlightDateKey,PassengerKey,OriginAirportKey,DestinationAirportKey,BookingStatus,CabinClass,BaseFare) VALUES(s.BookingId,s.FlightId,s.DateKey,s.PassengerKey,s.OriginKey,s.DestKey,s.BookingStatus,s.CabinClass,s.BaseFare);
 -- Service-date snapshot: one current aggregate per flight's service date. A rerun
 -- refreshes that service-date row; it does not create a load-date history series.
 ;WITH snapshot_source AS (
  SELECT CONVERT(int,CONVERT(char(8),f.FlightDate,112)) SnapshotDateKey,f.FlightId,f.FlightStatus,
   COUNT(b.BookingId) BookingCount,
   COALESCE(SUM(CASE WHEN b.BookingStatus<>'CANCELLED' THEN b.BaseFare ELSE 0 END),0) Revenue
  FROM ops.Flight f LEFT JOIN ops.Booking b ON b.FlightId=f.FlightId
  GROUP BY f.FlightDate,f.FlightId,f.FlightStatus
 )
 MERGE dw.FactDailyFlightSnapshot AS t USING snapshot_source AS s
 ON t.SnapshotDateKey=s.SnapshotDateKey AND t.FlightId=s.FlightId
 WHEN MATCHED THEN UPDATE SET FlightStatus=s.FlightStatus,BookingCount=s.BookingCount,Revenue=s.Revenue
 WHEN NOT MATCHED THEN INSERT(SnapshotDateKey,FlightId,FlightStatus,BookingCount,Revenue)
 VALUES(s.SnapshotDateKey,s.FlightId,s.FlightStatus,s.BookingCount,s.Revenue);
 COMMIT;
END;
GO
CREATE OR ALTER VIEW mart.v_RoutePerformance AS SELECT d.FullDate,o.AirportCode Origin,dst.AirportCode Destination,COUNT_BIG(*) ScheduledFlights,SUM(f.CompletedFlights) CompletedFlights,SUM(f.CancelledFlights) CancelledFlights,AVG(CASE WHEN f.FlightStatus='COMPLETED' THEN CAST(f.DepartureDelayMinutes AS decimal(10,2)) END) AvgDepartureDelayMinutes,SUM(f.DistanceMiles) MilesFlown FROM dw.FactFlight f JOIN dw.DimDate d ON d.DateKey=f.FlightDateKey JOIN dw.DimAirport o ON o.AirportKey=f.OriginAirportKey JOIN dw.DimAirport dst ON dst.AirportKey=f.DestinationAirportKey GROUP BY d.FullDate,o.AirportCode,dst.AirportCode;
GO
CREATE OR ALTER VIEW mart.v_RevenueByCabin AS SELECT d.CalendarYear,d.MonthNumber,b.CabinClass,COUNT_BIG(*) BookingCount,SUM(CASE WHEN b.BookingStatus<>'CANCELLED' THEN b.BaseFare ELSE 0 END) GrossBookedRevenue,SUM(CASE WHEN b.BookingStatus='FLOWN' THEN b.BaseFare ELSE 0 END) FlownRevenue FROM dw.FactBooking b JOIN dw.DimDate d ON d.DateKey=b.FlightDateKey GROUP BY d.CalendarYear,d.MonthNumber,b.CabinClass;
GO
