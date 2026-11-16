# AeroLogix Project Closure Checklist

This checklist records Phase 2 closure on 2026-11-15. For current Phase 3
changes and test results, see
[PHASE_3_IMPLEMENTATION_REPORT.md](PHASE_3_IMPLEMENTATION_REPORT.md).

**Review date:** 2026-11-15  
**Decision:** **READY WITH INFRASTRUCTURE LIMITATIONS**

## Complete and verified

- [x] Existing project reviewed without recreation or Git operations.
- [x] Python source, loader transaction handling and generator behavior reviewed.
- [x] Python compilation passed.
- [x] pytest passed: 9 passed, 1 skipped.
- [x] unittest passed: 4 tests, 1 skipped.
- [x] Checked-in CSV relationships and generator repeatability passed.
- [x] Isolated CSV validation confirmed 8/6/10/120/1,200 records.
- [x] dbt generic-test deprecation arguments migrated to `arguments`.
- [x] dbt parse passed with no deprecation warnings.
- [x] Docker Compose configuration passed with a validation-only environment value.
- [x] All YAML files parsed successfully.
- [x] All checked Markdown local links resolved.
- [x] Dangling legacy warehouse conditional removed so fact-index initialization is
      not gated by the presence of `BridgeFlightCrew`.
- [x] README links and documentation index updated.
- [x] No real credentials or API keys found in project files.
- [x] Generated caches and runtime logs excluded by `.gitignore` and removed
      after validation.
- [x] No commit, push, remote repository or Git history was modified.

## Blocked by external infrastructure

- [ ] Start SQL Server 2022 and verify `sqlcmd -C -S localhost,1433 -U sa ...`.
- [ ] Execute `python scripts/apply_sql.py` twice and capture SQL output.
- [ ] Load all five feeds with `python -m aerologix.load --data data/raw`.
- [ ] Compare CSV and SQL Server counts and run live constraint/rollback tests.
- [ ] Run `python scripts/load_warehouse.py` twice and compare dimensions, facts
      and snapshots.
- [ ] Execute controlled airport, aircraft and passenger SCD scenarios.
- [ ] Execute `sql/analytics/data_quality.sql` and controlled invalid-record tests.
- [ ] Run dbt `debug`, `compile`, `test` and `run` against the configured database.
- [ ] Install Airflow with matching constraints and import/render/execute the DAG.
- [ ] Complete the end-to-end pipeline with live SQL Server.

## Exact infrastructure completion commands

From the project directory, after setting a strong local password in `.env`:

```powershell
docker compose up -d
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python scripts/apply_sql.py
python -m aerologix.load --data data/raw --batch-size 1000
python scripts/load_warehouse.py
sqlcmd -C -S localhost,1433 -U sa -P "$env:SQLSERVER_PASSWORD" -b -i sql/analytics/data_quality.sql
```

Then configure `dbt/profiles.yml`, run the dbt commands from the `dbt/`
directory, and deploy Airflow with the `aerologix_sqlserver` connection and
`AEROLOGIX_PROJECT_DIR`.

## Manual approval

- [ ] Review [FINAL_PROJECT_REPORT.md](FINAL_PROJECT_REPORT.md).
- [ ] Confirm the infrastructure-blocked status is acceptable.
- [ ] Run the blocked SQL Server and Airflow checks in an isolated environment.
- [ ] Review all resulting SQL errors and record counts.
- [ ] Approve the project for publication only after live results are captured.
