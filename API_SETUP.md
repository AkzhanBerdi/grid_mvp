# API_SETUP.md
# Binance API Setup Guide

## 🔐 Creating Your Binance API Keys

### Step 1: Login to Binance
1. Go to [Binance.com](https://binance.com)
2. Log into your account
3. Complete 2FA if prompted

### Step 2: Navigate to API Management
1. Click on your **profile icon** (top right)
2. Select **"API Management"**
3. You may need to verify your identity

### Step 3: Create New API Key
1. Click **"Create API"**
2. Choose **"System Generated"** (recommended)
3. Enter a label like "GridTrader Pro"
4. Complete the verification process

### Step 4: Configure Permissions ⚠️ IMPORTANT
**Enable ONLY these permissions:**
- ✅ **"Enable Reading"** - Required for checking balances
- ✅ **"Enable Spot & Margin Trading"** - Required for trading
- ❌ **"Enable Withdrawals"** - NEVER enable this!
- ❌ **"Enable Internal Transfer"** - Not needed

### Step 5: IP Restrictions (Optional but Recommended)
- Add your VPS IP address for extra security
- This prevents API usage from other locations

### Step 6: Save Your Keys
1. **Copy your API Key** - You'll need this first
2. **Copy your Secret Key** - You'll need this second
3. **Store them securely** - You won't be able to see the Secret Key again

## 🛡️ Security Best Practices

### What We CAN Do:
- ✅ Check your account balance
- ✅ Place buy/sell orders
- ✅ Cancel orders
- ✅ View trade history

### What We CANNOT Do:
- ❌ Withdraw funds from your account
- ❌ Transfer funds externally
- ❌ Change your account settings
- ❌ Access your personal information

### Additional Security:
- 🔒 Your API keys are encrypted before storage
- 🔒 Keys are never logged or transmitted unencrypted
- 🔒 You can revoke API access anytime
- 🔒 We recommend using a separate trading account

## ⚠️ Important Notes

1. **Start Small**: Begin with a small amount for testing
2. **Monitor Regularly**: Check your trades and balances
3. **Revoke if Needed**: You can disable API keys anytime
4. **Use Testnet**: We recommend testing on Binance Testnet first

## 🔧 Testing Your Setup

After entering your API keys in GridTrader Pro:

1. The bot will verify your credentials
2. Check your account balance
3. Ensure trading permissions work
4. Start with a small capital amount

## ❓ Troubleshooting

**"Invalid API Key" Error:**
- Double-check you copied the key correctly
- Ensure no extra spaces or characters
- Verify the key hasn't been disabled

**"Insufficient Permissions" Error:**
- Ensure "Spot & Margin Trading" is enabled
- Check that the API key is active
- Verify IP restrictions aren't blocking access

**"Balance Too Low" Error:**
- Ensure you have USDT in your Spot wallet
- Minimum recommended: $100 for testing
- Transfer funds from other wallets if needed

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Contact GridTrader Pro support via Telegram
3. Never share your API keys with anyone

---

**Remember: Your security is our top priority! 🔒**
