# Authentication & Security

Authentication guide for the Corpus Collections API with JWT tokens and dual authentication methods.

---

## 🔐 Authentication Methods

### **Password-Based (Recommended)**
- **Setup**: Set password during signup or via OTP
- **Login**: Fast phone + password authentication
- **Security**: Strong password policies with bcrypt hashing
- **Convenience**: No SMS costs, works offline
- **Password Management**: Change password with current password OR OTP verification

### **OTP-Based (Alternative)**
- **Signup**: Phone verification → Account creation
- **Login**: Phone verification → JWT token  
- **Security**: SMS verification with rate limiting
- **Use Cases**: Users without password or forgotten password scenarios

---

## 📋 API Endpoints

### **OTP Authentication**

#### **Signup Flow**
```
POST /api/v1/auth/signup/send-otp      # Send signup OTP
POST /api/v1/auth/signup/verify-otp    # Verify OTP + create account
POST /api/v1/auth/signup/resend-otp    # Resend signup OTP
```

#### **Login Flow**
```
POST /api/v1/auth/login/send-otp       # Send login OTP
POST /api/v1/auth/login/verify-otp     # Verify OTP + get token
POST /api/v1/auth/login/resend-otp     # Resend login OTP
```

### **Password Authentication**
```
POST /api/v1/auth/login                # Phone + password login
POST /api/v1/auth/change-password      # Change password (requires current password)
POST /api/v1/auth/forgot-password/init # Initiate password reset via OTP
POST /api/v1/auth/forgot-password/confirm # Confirm password reset with OTP
```

### **Common**
```
GET  /api/v1/auth/me                   # Get current user
POST /api/v1/auth/refresh              # Refresh token
```

---

## 🚀 Usage Examples

### **OTP Signup**
```bash
# 1. Send OTP
curl -X POST http://localhost:8000/api/v1/auth/signup/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919999999999"}'

# 2. Verify & create account
curl -X POST http://localhost:8000/api/v1/auth/signup/verify-otp \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919999999999",
    "otp_code": "123456",
    "name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "has_given_consent": true
  }'
```

### **OTP Login**
```bash
# 1. Send OTP
curl -X POST http://localhost:8000/api/v1/auth/login/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919999999999"}'

# 2. Verify & get token
curl -X POST http://localhost:8000/api/v1/auth/login/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919999999999", "otp_code": "123456"}'
```

### **Password Login (Recommended)**
```bash
# Fast password-based login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919999999999", "password": "MySecurePass123!"}'
```

### **Reset Password with OTP (Forgot Password)**
```bash
# 1. Initiate password reset
curl -X POST http://localhost:8000/api/v1/auth/forgot-password/init \
  -H "Content-Type: application/json" \
  -d '{"phone": "+919999999999"}'

# 2. Confirm password reset with OTP
curl -X POST http://localhost:8000/api/v1/auth/forgot-password/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+919999999999",
    "otp_code": "123456",
    "new_password": "NewSecurePass123!",
    "confirm_password": "NewSecurePass123!"
  }'
```

### **Using Tokens**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <your-token>"
```

---

## 🔧 Configuration

### **Environment Variables**
```env
# JWT
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SMS Service
OTP_USER_NAME=sms_username
OTP_API_KEY=sms_api_key
OTP_SERVICE_URL=https://api.sms-provider.com/send
OTP_SMS_TEXT=Your OTP: {otp}. Valid for 5 minutes.

# OTP Security
OTP_EXPIRY_MINUTES=5
OTP_MAX_ATTEMPTS=3
OTP_RATE_LIMIT_MINUTES=1
```

---

## 🛡️ Security Features

### **Password Security (Recommended)**
- **bcrypt hashing** with salt for password storage
- **Strong password policies** (min 8 chars, complexity rules)
- **Anti-reuse protection** prevents using same password
- **Flexible password management**: Change with current password OR reset with OTP
- **Fast authentication**: No SMS delays or costs
- **No mobile network dependency**: Works with WiFi when cellular/SMS is unavailable

### **OTP Security (Fallback)**
- **HMAC-SHA256** hashing with phone number salts
- **Rate limiting** per phone number
- **Attempt tracking** with automatic invalidation
- **Time-based expiry** (5 minutes default)

### **User Experience**
- **Smart routing**: Login suggests signup for unknown users
- **Default roles**: All signups get regular user role
- **Admin-only**: Role changes require admin privileges
- **Password flexibility**: Set during signup, change with current password, or reset with OTP

### **Authorization**
- **Self-access**: Users can modify their own resources
- **Admin override**: Admins have full access where appropriate
- **RBAC**: Role-based access control throughout

---

## 📊 Security Status

**✅ All Critical Vulnerabilities Fixed:**
- Password change authorization bypass
- Password reset privilege escalation
- User profile update authorization bypass
- OTP status information disclosure

**Current Status**: SECURED with comprehensive authorization framework.

---

## 🧪 Testing

```bash
# Manual OTP testing
python test_signup_otp_manual.py

# Security tests
uv run pytest tests/test_password_security.py -v
uv run pytest tests/test_password_reset_security.py -v
```

---

## 🚀 Production Deployment

**Checklist:**
- [ ] JWT secrets configured
- [ ] SMS credentials configured  
- [ ] HTTPS enforced
- [ ] Rate limiting configured
- [ ] Database migrations applied
- [ ] Security monitoring enabled

---

*Last Updated: August 24, 2025 | Status: All Critical Issues Fixed ✅*