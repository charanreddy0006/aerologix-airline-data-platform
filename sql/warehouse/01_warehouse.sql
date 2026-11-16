SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;
GO
USE AeroLogix;
GO
IF SCHEMA_ID('dw') IS NULL EXEC('CREATE SCHEMA dw');
IF SCHEMA_ID('mart') IS NULL EXEC('CREATE SCHEMA mart');
GO
IF OBJECT_ID(N'dw.DimDate',N'U') IS NULL
CREATE TABLE dw.DimDate(DateKey int NOT NULL PRIMARY KEY, FullDate date NOT NULL UNIQUE, CalendarYear smallint NOT NULL, CalendarQuarter tinyint NOT NULL, MonthNumber tinyint NOT NULL, MonthName varchar(12) NOT NULL, DayOfMonth tinyint NOT NULL, DayOfWeekName varchar(10) NOT NULL, IsWeekend bit NOT NULL);
IF OBJECT_ID(N'dw.DimAirport',N'U') IS NULL
CREATE TABLE dw.DimAirport(AirportKey int IDENTITY PRIMARY KEY, AirportCode char(3) NOT NULL, AirportName nvarchar(120) NOT NULL, City nvarchar(80) NOT NULL, CountryCode char(2) NOT NULL, TimeZoneName nvarchar(64) NOT NULL, IsCurrent bit NOT NULL DEFAULT 1, ValidFrom datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), ValidTo datetime2 NULL, RowHash varbinary(32) NULL, CONSTRAINT UQ_DimAirport_Version UNIQUE(AirportCode,ValidFrom));
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'UX_DimAirport_Current' AND object_id=OBJECT_ID(N'dw.DimAirport'))
CREATE UNIQUE INDEX UX_DimAirport_Current ON dw.DimAirport(AirportCode) WHERE IsCurrent=1;
IF OBJECT_ID(N'dw.DimAircraft',N'U') IS NULL
CREATE TABLE dw.DimAircraft(AircraftKey int IDENTITY PRIMARY KEY, AircraftId int NOT NULL, AircraftType varchar(30) NOT NULL, SeatCapacity smallint NOT NULL, ManufactureYear smallint NOT NULL, IsCurrent bit NOT NULL DEFAULT 1, ValidFrom datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), ValidTo datetime2 NULL, PreviousAircraftType varchar(30) NULL, RowHash varbinary(32) NULL, CONSTRAINT UQ_DimAircraft_Version UNIQUE(AircraftId,ValidFrom));
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'UX_DimAircraft_Current' AND object_id=OBJECT_ID(N'dw.DimAircraft'))
CREATE UNIQUE INDEX UX_DimAircraft_Current ON dw.DimAircraft(AircraftId) WHERE IsCurrent=1;
IF OBJECT_ID(N'dw.DimPassenger',N'U') IS NULL
CREATE TABLE dw.DimPassenger(PassengerKey int IDENTITY PRIMARY KEY, PassengerId varchar(12) NOT NULL UNIQUE, LoyaltyTier varchar(12) NOT NULL, FirstSeenDate date NULL, LastSeenDate date NULL);
IF OBJECT_ID(N'dw.DimRoute',N'U') IS NULL
CREATE TABLE dw.DimRoute(RouteKey int IDENTITY PRIMARY KEY, OriginAirportKey int NOT NULL REFERENCES dw.DimAirport, DestinationAirportKey int NOT NULL REFERENCES dw.DimAirport, DistanceMiles int NOT NULL, CONSTRAINT UQ_DimRoute UNIQUE(OriginAirportKey,DestinationAirportKey));
IF OBJECT_ID(N'dw.FactFlight',N'U') IS NULL
CREATE TABLE dw.FactFlight(FlightFactKey bigint IDENTITY PRIMARY KEY, FlightId int NOT NULL UNIQUE, FlightDateKey int NOT NULL REFERENCES dw.DimDate, OriginAirportKey int NOT NULL REFERENCES dw.DimAirport, DestinationAirportKey int NOT NULL REFERENCES dw.DimAirport, AircraftKey int NOT NULL REFERENCES dw.DimAircraft, FlightStatus varchar(12) NOT NULL, DistanceMiles int NOT NULL, DepartureDelayMinutes smallint NOT NULL, ScheduledFlights int NOT NULL DEFAULT 1, CompletedFlights int NOT NULL DEFAULT 0, CancelledFlights int NOT NULL DEFAULT 0, LoadDts datetime2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID(N'dw.FactBooking',N'U') IS NULL
CREATE TABLE dw.FactBooking(BookingFactKey bigint IDENTITY PRIMARY KEY, BookingId int NOT NULL UNIQUE, FlightId int NOT NULL, FlightDateKey int NOT NULL REFERENCES dw.DimDate, PassengerKey int NOT NULL REFERENCES dw.DimPassenger, OriginAirportKey int NOT NULL REFERENCES dw.DimAirport, DestinationAirportKey int NOT NULL REFERENCES dw.DimAirport, BookingStatus varchar(12) NOT NULL, CabinClass varchar(12) NOT NULL, BaseFare decimal(10,2) NOT NULL, BookingCount int NOT NULL DEFAULT 1, LoadDts datetime2 NOT NULL DEFAULT SYSUTCDATETIME());
IF OBJECT_ID(N'dw.FactDailyFlightSnapshot',N'U') IS NULL
CREATE TABLE dw.FactDailyFlightSnapshot(SnapshotDateKey int NOT NULL REFERENCES dw.DimDate, FlightId int NOT NULL, FlightStatus varchar(12) NOT NULL, BookingCount int NOT NULL, Revenue decimal(12,2) NOT NULL, PRIMARY KEY(SnapshotDateKey,FlightId));
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'IX_FactFlight_DateRoute' AND object_id=OBJECT_ID(N'dw.FactFlight'))
CREATE INDEX IX_FactFlight_DateRoute ON dw.FactFlight(FlightDateKey,OriginAirportKey,DestinationAirportKey) INCLUDE(FlightStatus,DepartureDelayMinutes,DistanceMiles);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'IX_FactBooking_DateClass' AND object_id=OBJECT_ID(N'dw.FactBooking'))
CREATE INDEX IX_FactBooking_DateClass ON dw.FactBooking(FlightDateKey,CabinClass,BookingStatus) INCLUDE(BaseFare,PassengerKey);
GO
