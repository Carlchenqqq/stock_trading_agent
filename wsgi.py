import sys
import os

project_home = '/home/chenqi/stock_trading_agent'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

activate_this = os.path.join(project_home, 'venv/bin/activate_this.py')
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

from app import app as application
