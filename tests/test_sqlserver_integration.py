"""Optional integration checks; set AEROLOGIX_TEST_DSN to enable."""
import os,unittest
try: import pyodbc
except ImportError: pyodbc=None
@unittest.skipUnless(os.getenv('AEROLOGIX_TEST_DSN') and pyodbc,'requires AEROLOGIX_TEST_DSN and pyodbc')
class SqlServerIntegration(unittest.TestCase):
 def test_load_populates_coherent_grains(self):
  with pyodbc.connect(os.environ['AEROLOGIX_TEST_DSN']) as c:
   q=c.cursor()
   self.assertEqual(q.execute('select count(*) from ops.Flight').fetchone()[0],120)
   self.assertEqual(q.execute('select count(*) from ops.Booking').fetchone()[0],1200)
   self.assertEqual(q.execute('select count(*) from dw.FactFlight').fetchone()[0],120)
   self.assertEqual(q.execute('select count(*) from dw.FactBooking').fetchone()[0],1200)
   self.assertEqual(q.execute('select count(*) from dw.DimAirport where IsCurrent=1').fetchone()[0],8)
