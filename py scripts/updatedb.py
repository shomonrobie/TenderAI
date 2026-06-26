
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from database.db_manager import DatabaseManager
from modules.auth import login_user, logout_user, is_admin, is_company_admin
from modules.subscription import render_subscription_page, render_checkout
from modules.user_management import render_user_management

from database.db_manager import DatabaseManager
db = DatabaseManager()
db.update_subscription(1, 'professional', 'monthly', 'system', 'ADMIN_UPGRADE')
