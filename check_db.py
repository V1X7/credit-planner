from database import execute_query
r = execute_query("SELECT name FROM sqlite_master WHERE type='table'", fetch='all')
for x in r: print(dict(x))