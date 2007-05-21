from sqlalchemy import *
import models

reports = models.reports_table

print type(reports)

s = select(["signature", func.count("*").label("total"),
           func.count(case([(reports.os_name == "Windows NT", 1)], else_=None)).label("windows"),
           func.count(case([(reports.os_name == "Windows NT", 1)], else_=None)).label("mac")])

print str(s)


#from  GROUP BY signature ORDER BY total DESC;
