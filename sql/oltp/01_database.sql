IF DB_ID(N'AeroLogix') IS NULL CREATE DATABASE AeroLogix;
GO
USE AeroLogix;
GO
IF SCHEMA_ID('ref') IS NULL EXEC('CREATE SCHEMA ref');
IF SCHEMA_ID('ops') IS NULL EXEC('CREATE SCHEMA ops');
IF SCHEMA_ID('stg') IS NULL EXEC('CREATE SCHEMA stg');
IF SCHEMA_ID('etl') IS NULL EXEC('CREATE SCHEMA etl');
GO
IF OBJECT_ID(N'ref.Airport',N'U') IS NULL
CREATE TABLE ref.Airport(AirportCode char(3) NOT NULL CONSTRAINT PK_Airport PRIMARY KEY, AirportName nvarchar(120) NOT NULL, City nvarchar(80) NOT NULL, CountryCode char(2) NOT NULL, TimeZoneName nvarchar(64) NOT NULL, IsActive bit NOT NULL DEFAULT 1);
IF OBJECT_ID(N'ref.Aircraft',N'U') IS NULL
CREATE TABLE ref.Aircraft(AircraftId int NOT NULL CONSTRAINT PK_Aircraft PRIMARY KEY, AircraftType varchar(30) NOT NULL, SeatCapacity smallint NOT NULL CHECK(SeatCapacity BETWEEN 1 AND 600), ManufactureYear smallint NOT NULL CHECK(ManufactureYear BETWEEN 1950 AND 2100), AircraftStatus varchar(20) NOT NULL CHECK(AircraftStatus IN('ACTIVE','MAINTENANCE','RETIRED')));
IF OBJECT_ID(N'ref.Route',N'U') IS NULL
CREATE TABLE ref.Route(RouteId int IDENTITY PRIMARY KEY, OriginAirportCode char(3) NOT NULL REFERENCES ref.Airport, DestinationAirportCode char(3) NOT NULL REFERENCES ref.Airport, DistanceMiles int NOT NULL CHECK(DistanceMiles>0), CONSTRAINT UQ_Route UNIQUE(OriginAirportCode,DestinationAirportCode), CHECK(OriginAirportCode<>DestinationAirportCode));
IF OBJECT_ID(N'ops.Passenger',N'U') IS NULL
CREATE TABLE ops.Passenger(PassengerId varchar(12) NOT NULL PRIMARY KEY, CreatedAt datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(), LoyaltyTier varchar(12) NOT NULL DEFAULT 'STANDARD' CHECK(LoyaltyTier IN('STANDARD','SILVER','GOLD','PLATINUM')));
IF OBJECT_ID(N'ops.Flight',N'U') IS NULL
CREATE TABLE ops.Flight(FlightId int NOT NULL PRIMARY KEY, FlightNumber varchar(8) NOT NULL, FlightDate date NOT NULL, RouteId int NOT NULL REFERENCES ref.Route, AircraftId int NOT NULL REFERENCES ref.Aircraft, ScheduledDeparture datetime2(0) NOT NULL, ActualDeparture datetime2(0) NULL, FlightStatus varchar(12) NOT NULL CHECK(FlightStatus IN('SCHEDULED','COMPLETED','CANCELLED','DIVERTED')), DepartureDelayMinutes smallint NOT NULL DEFAULT 0, CONSTRAINT UQ_Flight UNIQUE(FlightNumber,FlightDate), CHECK(DepartureDelayMinutes BETWEEN -120 AND 1440), CHECK(ActualDeparture IS NULL OR FlightStatus<>'CANCELLED'));
IF OBJECT_ID(N'ops.Booking',N'U') IS NULL
CREATE TABLE ops.Booking(BookingId int NOT NULL PRIMARY KEY, PassengerId varchar(12) NOT NULL REFERENCES ops.Passenger, FlightId int NOT NULL REFERENCES ops.Flight, BookingReference varchar(12) NOT NULL UNIQUE, SeatNumber varchar(4) NOT NULL, CabinClass varchar(12) NOT NULL CHECK(CabinClass IN('ECONOMY','PREMIUM','BUSINESS','FIRST')), BaseFare decimal(10,2) NOT NULL CHECK(BaseFare>=0), BookingStatus varchar(12) NOT NULL CHECK(BookingStatus IN('BOOKED','TICKETED','FLOWN','CANCELLED')), BookedAt datetime2(0) NOT NULL DEFAULT SYSUTCDATETIME(), CONSTRAINT UQ_FlightSeat UNIQUE(FlightId,SeatNumber));
IF OBJECT_ID(N'ops.MaintenanceEvent',N'U') IS NULL
CREATE TABLE ops.MaintenanceEvent(MaintenanceId bigint IDENTITY PRIMARY KEY, AircraftId int NOT NULL REFERENCES ref.Aircraft, EventType varchar(20) NOT NULL CHECK(EventType IN('INSPECTION','REPAIR','COMPONENT_REPLACEMENT')), StartedAt datetime2(0) NOT NULL, CompletedAt datetime2(0) NULL, Description nvarchar(250) NOT NULL, Cost decimal(12,2) NOT NULL CHECK(Cost>=0), CHECK(CompletedAt IS NULL OR CompletedAt>=StartedAt));
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'IX_Flight_DateStatus' AND object_id=OBJECT_ID(N'ops.Flight'))
CREATE INDEX IX_Flight_DateStatus ON ops.Flight(FlightDate,FlightStatus) INCLUDE(RouteId,AircraftId,DepartureDelayMinutes);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'IX_Booking_FlightStatus' AND object_id=OBJECT_ID(N'ops.Booking'))
CREATE INDEX IX_Booking_FlightStatus ON ops.Booking(FlightId,BookingStatus) INCLUDE(BaseFare,CabinClass);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'IX_Booking_Passenger' AND object_id=OBJECT_ID(N'ops.Booking'))
CREATE INDEX IX_Booking_Passenger ON ops.Booking(PassengerId,BookedAt DESC);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE name=N'IX_Maintenance_AircraftDate' AND object_id=OBJECT_ID(N'ops.MaintenanceEvent'))
CREATE INDEX IX_Maintenance_AircraftDate ON ops.MaintenanceEvent(AircraftId,StartedAt DESC);
GO
