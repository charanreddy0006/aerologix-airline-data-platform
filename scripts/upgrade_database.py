"""Apply the repeatable baseline, then run each unapplied numbered migration once."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pyodbc
from dotenv import load_dotenv

from apply_sql import ROOT
import sys
sys.path.insert(0, str(ROOT / "src"))
from aerologix.load import connection_string


def main() -> None:
    load_dotenv(ROOT / ".env")
    password = os.getenv("SQLSERVER_PASSWORD")
    if not password:
        raise RuntimeError("Set SQLSERVER_PASSWORD in .env or the environment before upgrading")
    server = f"{os.getenv('SQLSERVER_HOST', 'localhost')},{os.getenv('SQLSERVER_PORT', '1433')}"
    user = os.getenv("SQLSERVER_USER", "sa")
    environment = os.environ.copy()
    environment["SQLCMDPASSWORD"] = password
    # Run the legacy baseline only when upgrading an older database or creating
    # the first instance. Once the ledger exists, never replay baseline DDL.
    master = pyodbc.connect(connection_string("master"))
    try:
        exists = master.cursor().execute("SELECT DB_ID(N'AeroLogix')").fetchone()[0] is not None
        ledger_exists = False
        if exists:
            ledger_exists = bool(master.cursor().execute(
                "SELECT OBJECT_ID(N'AeroLogix.etl.SchemaMigration',N'U')"
            ).fetchone()[0])
    finally:
        master.close()
    if not ledger_exists:
        from apply_sql import main as apply_baseline
        apply_baseline()

    connection = pyodbc.connect(connection_string("AeroLogix"))
    try:
        cursor = connection.cursor()
        lock_result = cursor.execute("""DECLARE @result int;
            EXEC @result=sys.sp_getapplock @Resource=N'AeroLogix.SchemaMigrations',
            @LockMode='Exclusive',@LockOwner='Session',@LockTimeout=60000;
            SELECT @result;""").fetchone()[0]
        if lock_result < 0:
            raise RuntimeError(f"Could not acquire SQL migration lock (result={lock_result})")
        cursor.execute("""IF OBJECT_ID(N'etl.SchemaMigration',N'U') IS NULL
            CREATE TABLE etl.SchemaMigration(MigrationVersion varchar(32) NOT NULL PRIMARY KEY,
            AppliedAt datetime2(0) NOT NULL CONSTRAINT DF_SchemaMigration_AppliedAt DEFAULT SYSUTCDATETIME());""")
        cursor.execute("IF NOT EXISTS(SELECT 1 FROM etl.SchemaMigration WHERE MigrationVersion='000_baseline') INSERT etl.SchemaMigration(MigrationVersion) VALUES('000_baseline')")
        connection.commit()
        applied = {row[0] for row in cursor.execute("SELECT MigrationVersion FROM etl.SchemaMigration")}
        for path in sorted((ROOT / "sql" / "migrations").glob("[0-9][0-9][0-9]_*.sql")):
            version = path.stem
            if version in applied:
                continue
            subprocess.run(["sqlcmd", "-C", "-S", server, "-d", "AeroLogix", "-U", user,
                            "-b", "-i", str(path)], check=True, cwd=ROOT, env=environment)
            cursor.execute("INSERT etl.SchemaMigration(MigrationVersion) VALUES(?)", version)
            connection.commit()
            print(f"Applied migration {version}")
    finally:
        try:
            connection.cursor().execute("EXEC sys.sp_releaseapplock @Resource=N'AeroLogix.SchemaMigrations',@LockOwner='Session'")
        except Exception:
            pass
        connection.close()


if __name__ == "__main__":
    main()
