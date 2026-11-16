"""Apply SQL Server scripts in dependency order using sqlcmd."""
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ROOT / 'sql/oltp/01_database.sql',
    ROOT / 'sql/oltp/02_staging.sql',
    ROOT / 'sql/oltp/03_logic.sql',
    ROOT / 'sql/warehouse/01_warehouse.sql',
    ROOT / 'sql/warehouse/02_load.sql',
)


def main() -> None:
    load_dotenv(ROOT / '.env')
    password = os.getenv('SQLSERVER_PASSWORD')
    if not password:
        raise RuntimeError('Set SQLSERVER_PASSWORD in .env or the environment before applying scripts')
    server = f"{os.getenv('SQLSERVER_HOST', 'localhost')},{os.getenv('SQLSERVER_PORT', '1433')}"
    environment = os.environ.copy()
    environment['SQLCMDPASSWORD'] = password
    for script in SCRIPTS:
        print(f'Applying {script.relative_to(ROOT)}')
        subprocess.run(['sqlcmd', '-C', '-S', server, '-U', os.getenv('SQLSERVER_USER', 'sa'),
                        '-b', '-i', str(script)], check=True, cwd=ROOT, env=environment)


if __name__ == '__main__':
    main()
