# DEPLOYMENT.md

# GridTrader Pro MVP - Deployment Guide

## 🚀 Quick Deployment

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)
- VPS or cloud server with 2GB+ RAM

### 1. Environment Setup

```bash
# Clone repository
git clone <your-repo-url>
cd gridtrader-pro-mvp

# Create environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 2. Required Environment Variables

```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFabcdefGHIJKLmnopQRSTuvwxyz123
ADMIN_TELEGRAM_ID=123456789

# Security
ENCRYPTION_KEY=your-32-character-encryption-key-here

# Environment  
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 3. Quick Start

```bash
# Make startup script executable
chmod +x startup.sh

# Run the application
./startup.sh
```

### 4. Docker Deployment (Recommended)

```bash
# Build and run with Docker Compose
docker-compose up -d

# Check status
docker-compose logs -f
```

### 5. Health Monitoring

```bash
# Check system health
python health_check.py

# View logs
tail -f data/logs/gridtrader.log
```

## 📊 MVP Validation Commands

### Check Analytics

```bash
# View conversion metrics
python -c "from analytics.conversion_tracker import ConversionTracker; ConversionTracker().print_mvp_report()"

# Check active users
python -c "from repositories.user_repository import UserRepository; print('Active users:', len(UserRepository().get_active_users()))"
```

### Database Queries

```bash
# Connect to database
sqlite3 data/gridtrader.db

# Check user registrations
SELECT COUNT(*) as total_users FROM users;

# Check trial conversions
SELECT subscription_status, COUNT(*) FROM users GROUP BY subscription_status;

# Check daily signups
SELECT DATE(created_at) as date, COUNT(*) as signups 
FROM users 
WHERE created_at >= datetime('now', '-7 days') 
GROUP BY DATE(created_at);
```

## 🎯 MVP Success Criteria

Monitor these metrics daily:

**Week 1 Targets:**

- 10+ user registrations
- 50%+ registration rate
- 5+ trial starts

**Week 2 Targets:**  

- 25+ user registrations
- 10+ active trials
- 3+ successful bot configurations

**Month 1 Targets:**

- 100+ user registrations
- 25+ trial starts  
- 25%+ trial-to-paid conversion
- $500+ MRR

## 🔧 Troubleshooting

### Common Issues

**Bot not responding:**

```bash
# Check if bot is running
ps aux | grep telegram_bot.py

# Check logs for errors
tail -f data/logs/gridtrader.log

# Restart bot
./startup.sh
```

**Database issues:**

```bash
# Reinitialize database
python database/db_setup.py

# Check database integrity
sqlite3 data/gridtrader.db "PRAGMA integrity_check;"
```

**High memory usage:**

```bash
# Check memory usage
python health_check.py

# Monitor active bots
python -c "from services.bot_orchestrator import BotOrchestrator; print('Active bots:', len(BotOrchestrator().active_bots))"
```

## 📈 Scaling Preparation

**When to scale (50+ users):**

1. Memory usage > 4GB
2. API rate limits hit
3. System instability

**Scaling checklist:**

- [ ] Monitor system resources daily
- [ ] Plan Phase 2 unified engine
- [ ] Prepare user migration strategy
- [ ] Set up advanced monitoring

---
