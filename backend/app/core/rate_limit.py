from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Default rate limiting based on IP address
# For a production app this could be customized to group by user ID
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
