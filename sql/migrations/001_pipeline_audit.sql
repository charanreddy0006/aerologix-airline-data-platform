USE AeroLogix;
GO
IF OBJECT_ID(N'etl.PipelineRun',N'U') IS NULL
BEGIN
    CREATE TABLE etl.PipelineRun(
        ExecutionId uniqueidentifier NOT NULL CONSTRAINT PK_PipelineRun PRIMARY KEY,
        StartedAt datetime2(3) NOT NULL,
        FinishedAt datetime2(3) NULL,
        Status varchar(12) NOT NULL,
        SourceRecordCount int NOT NULL CONSTRAINT DF_PipelineRun_Source DEFAULT 0,
        RejectedRecordCount int NOT NULL CONSTRAINT DF_PipelineRun_Rejected DEFAULT 0,
        InsertedRecordCount int NOT NULL CONSTRAINT DF_PipelineRun_Inserted DEFAULT 0,
        UpdatedRecordCount int NOT NULL CONSTRAINT DF_PipelineRun_Updated DEFAULT 0,
        FeedCountsJson nvarchar(max) NULL,
        DurationSeconds decimal(12,3) NULL,
        FailureDetails nvarchar(2000) NULL,
        CONSTRAINT CK_PipelineRun_Status CHECK(Status IN('RUNNING','SUCCEEDED','FAILED','AUDIT_FAILED')),
        CONSTRAINT CK_PipelineRun_FeedCountsJson CHECK(FeedCountsJson IS NULL OR ISJSON(FeedCountsJson)=1)
    );
    CREATE INDEX IX_PipelineRun_StartedAt ON etl.PipelineRun(StartedAt DESC) INCLUDE(Status,SourceRecordCount,RejectedRecordCount);
END;
GO
