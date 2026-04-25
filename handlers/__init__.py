from .start import register_start
from .bonus import register_bonus
from .user import register_user
from .withdraw import register_withdraw
from .admin import register_admin

def register_all_handlers(dp):
    register_start(dp)
    register_bonus(dp)
    register_user(dp)
    register_withdraw(dp)
    register_admin(dp)
