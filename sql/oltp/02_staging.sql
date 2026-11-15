USE AeroLogix;
GO
IF OBJECT_ID(N'stg.AirportLoad',N'U') IS NULL
CREATE TABLE stg.AirportLoad(AirportCode char(3),AirportName nvarchar(120),City nvarchar(80),CountryCode char(2),TimeZoneName nvarchar(64));
IF OBJECT_ID(N'stg.AircraftLoad',N'U') IS NULL
CREATE TABLE stg.AircraftLoad(AircraftId int,AircraftType varchar(30),SeatCapacity smallint,ManufactureYear smallint,AircraftStatus varchar(20));
IF OBJECT_ID(N'stg.RouteLoad',N'U') IS NULL
CREATE TABLE stg.RouteLoad(OriginAirportCode char(3),DestinationAirportCode char(3),DistanceMiles int);
IF OBJECT_ID(N'stg.FlightLoad',N'U') IS NULL
CREATE TABLE stg.FlightLoad(FlightId int,FlightNumber varchar(8),FlightDate date,OriginAirportCode char(3),DestinationAirportCode char(3),AircraftId int,ScheduledDeparture datetime2(0),ActualDeparture datetime2(0),FlightStatus varchar(12),DistanceMiles int,DepartureDelayMinutes smallint);
IF OBJECT_ID(N'stg.BookingLoad',N'U') IS NULL
CREATE TABLE stg.BookingLoad(BookingId int,FlightId int,PassengerId varchar(12),BookingReference varchar(12),SeatNumber varchar(4),BaseFare decimal(10,2),CabinClass varchar(12),BookingStatus varchar(12));
GO
