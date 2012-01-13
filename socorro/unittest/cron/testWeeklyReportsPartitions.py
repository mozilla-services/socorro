import sys
print sys.path
from socorro.app.generic_app import main
from socorro.cron.weeklyReportsPartitions import WeeklyReportsPartitions

def test_run_app_basic():
    app = main(WeeklyReportsPartitions)
    
    
    
    
