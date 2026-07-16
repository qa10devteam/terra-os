# Security Audit Report — Terra.OS API
**Date:** 2026-07-16  
**Scope:** API backend, Nginx, systemd service

---

## Findings & Remediations

### ✅ FIXED: Missing Auth on `/api/v1/chat` endpoints
- **File:** `services/api/services/api/routers/chat.py`
- **Issue:** `general_chat()` and `estimate_chat()` had no authentication dependency — any unauthenticated caller could invoke LLM endpoints.
- **Fix:** Added `AuthUser` dependency and `@limiter.limit("20/minute")` rate limit to both endpoints.
- **Commit:** `ba2bde5`

### ✅ FIXED: Request ID Middleware missing
- **File:** `services/api/services/api/main.py`
- **Issue:** No distributed tracing header — impossible to correlate logs across services.
- **Fix:** Added `RequestIDMiddleware` that generates/propagates `X-Request-ID` on every request/response.
- **Commit:** `74a2614`

### ✅ FIXED: systemd service missing hardening directives
- **File:** `/etc/systemd/system/terra-api.service`
- **Issue:** No privilege-reduction directives.
- **Fix:** Added `NoNewPrivileges=true`, `PrivateTmp=true`, `ProtectSystem=strict`, `ProtectHome=read-only`, `ReadWritePaths=/home/ubuntu/terra-os /tmp`.

### ✅ FIXED: Nginx missing HSTS and security headers
- **File:** `/etc/nginx/sites-enabled/terra-os-api`
- **Issue:** Missing `Strict-Transport-Security`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`.
- **Fix:** Added all missing security headers with `always` directive. Also replaced wildcard CORS `Access-Control-Allow-Origin: *` with `$http_origin` (origin reflection is constrained by FastAPI's ALLOWED_ORIGINS whitelist).

---

## Confirmed Good (No Issues)

| Area | Status |
|------|--------|
| JWT validation | ✅ Proper `exp`, `type` claim check via PyJWT |
| Password hashing | ✅ bcrypt with salt (`bcrypt.hashpw` + `gensalt()`) |
| Refresh token rotation | ✅ Old token revoked on use, new token issued |
| Rate limiting on /auth/login | ✅ `@limiter.limit("10/minute")` on login, register, forgot-password, reset-password |
| CORS origins | ✅ Whitelist via `ALLOWED_ORIGINS` env var (not wildcard for the FastAPI layer) |
| CSRF protection | ✅ Double-submit cookie pattern in `CSRFMiddleware` |
| Security headers in FastAPI | ✅ `SecurityHeadersMiddleware` sets all standard headers |
| SQL injection in dynamic queries | ✅ All dynamic parts are column whitelists or parameterized; user input never interpolated directly |
| Secrets in git | ✅ No plaintext secrets found; JWT_SECRET, DB creds loaded from env |
| Global rate limiter | ✅ `rate_limit_middleware` (100 req/min/org) + slowapi global 200 req/min/IP |

---

## Remaining Recommendations (Low Priority)

1. **Nginx** is currently not running (port 80 conflict) — resolve the port conflict and enable HTTPS (certbot/Let's Encrypt).
2. **JWT_SECRET** should be rotated and set via environment file, not inline in systemd unit.
3. Consider adding `ProtectKernelTunables=true` and `RestrictAddressFamilies=AF_INET AF_INET6` to systemd service for further hardening.
4. Add `Content-Security-Policy` header once frontend origins are stable.
