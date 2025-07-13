from datetime import datetime

class MessageFormatter:
    @staticmethod
    def format_user_dashboard(user, bot_status, performance):
        return f"""🤖 **Trading Dashboard**
Status: {bot_status.get('status', 'inactive')}
Capital: ${user.total_capital:.2f}"""
    
    @staticmethod
    def format_trial_expiry(trial_expires):
        if not trial_expires:
            return "No trial"
        time_left = trial_expires - datetime.now()
        return f"{time_left.days} days left" if time_left.days > 0 else "Expires soon"
