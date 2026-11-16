"""Refresh AeroLogix warehouse dimensions, facts and marts."""
import logging
import os

import pyodbc
from dotenv import load_dotenv

from aerologix.load import connection_string


def main() -> None:
    load_dotenv()
    logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
    connection = pyodbc.connect(connection_string())
    try:
        cursor = connection.cursor()
        for option in (
            'SET ANSI_NULLS ON',
            'SET ANSI_PADDING ON',
            'SET ANSI_WARNINGS ON',
            'SET ARITHABORT ON',
            'SET CONCAT_NULL_YIELDS_NULL ON',
            'SET QUOTED_IDENTIFIER ON',
            'SET NUMERIC_ROUNDABORT OFF',
        ):
            cursor.execute(option)
        cursor.execute('EXEC etl.usp_LoadWarehouse')
        connection.commit()
        logging.info('Warehouse load committed')
    except Exception:
        connection.rollback()
        logging.exception('Warehouse load failed and was rolled back')
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    main()
