'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useStore } from '@/store/useStore';
import type { AuthUser } from '@/store/useStore';
import { AlertCircle, ArrowLeft, Eye, EyeOff, Loader2, Lock, LogIn, Mail, UserPlus } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

interface LoginFormProps {
  onSuccess: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function LoginForm({ onSuccess }: LoginFormProps) {
  const setAuth = useStore((s) => s.setAuth);

  const [tab,          setTab]          = useState<'login' | 'register'>('login');
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError, setForgotError] = useState('');
  const [email,        setEmail]        = useState('');
  const [password,     setPassword]     = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [name,         setName]         = useState('');
  const [orgName,      setOrgName]      = useState('');
  const [error,        setError]        = useState('');
  const [loading,      setLoading]      = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const endpoint = tab === 'login'
        ? '/api/v2/auth/login'
        : '/api/v2/auth/register';

      const body = tab === 'login'
        ? { email, password }
        : { email, password, name, org_name: orgName };

      const res  = await fetch(endpoint, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        // Human-readable error messages
        const detail = typeof (data.detail) === 'string'
          ? data.detail
          : Array.isArray(data.detail)
            ? (data.detail as { msg?: string }[]).map(d => d.msg || '').join('; ')
            : '';
        if (res.status === 401 || detail.toLowerCase().includes('invalid'))
          setError('Nieprawidłowy e-mail lub hasło. Spróbuj ponownie lub zresetuj hasło.');
        else if (res.status === 409 || detail.toLowerCase().includes('exist'))
          setError('Konto z tym adresem e-mail już istnieje. Zaloguj się lub odzyskaj dostęp.');
        else if (res.status >= 500)
          setError('Problem z serwerem — spróbuj ponownie za chwilę.');
        else
          setError(detail || 'Nie udało się wykonać operacji. Spróbuj ponownie.');
        return;
      }

      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);
      onSuccess();
    } catch {
      setError('Brak połączenia z serwerem. Sprawdź internet i spróbuj ponownie.');
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault();
    setForgotLoading(true);
    setForgotError('');
    try {
      const res = await fetch('/api/v2/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail }),
      });
      if (res.ok) {
        setForgotSuccess(true);
      } else {
        setForgotError('Wystąpił błąd. Spróbuj ponownie.');
      }
    } catch {
      setForgotError('Brak połączenia z serwerem.');
    } finally {
      setForgotLoading(false);
    }
  }

  function switchTab(next: 'login' | 'register') {
    setTab(next);
    setError('');
  }

  return (
    <div
      className="min-h-screen bg-ink-950 flex items-center justify-center p-4 relative overflow-hidden"
      style={{
        backgroundImage: [
          'radial-gradient(ellipse at 50% -20%, rgba(16,185,129,0.12) 0%, transparent 60%)',
          'linear-gradient(rgba(16,185,129,0.04) 1px, transparent 1px)',
          'linear-gradient(90deg, rgba(16,185,129,0.04) 1px, transparent 1px)',
        ].join(', '),
        backgroundSize: 'auto, 40px 40px, 40px 40px',
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="w-full max-w-md relative z-10"
      >
        {/* ── Brand mark ────────────────────────────────────────────── */}
        <div className="text-center mb-8">
          {/* Hexagon logo mark */}
          <div className="inline-flex items-center justify-center w-16 h-16 mb-4"
            style={{
              clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
              background: 'rgba(16,185,129,0.15)',
              boxShadow: 'inset 0 0 20px rgba(16,185,129,0.2), 0 0 40px rgba(16,185,129,0.1)',
              outline: '1px solid rgba(16,185,129,0.4)',
            }}
          >
            <span className="text-3xl font-bold text-em" style={{ fontFamily: 'var(--font-space)' }}>b</span>
          </div>

          {/* Brand name */}
          <h1 className="text-xl font-bold text-slate-100 tracking-tight" style={{ fontFamily: 'var(--font-space)' }}>
            budos
          </h1>
          <p className="text-slate-600 text-xs mt-0.5" style={{ fontFamily: 'var(--font-space)' }}>
            by YU-NA
          </p>
          <p className="text-slate-500 text-sm mt-2" style={{ fontFamily: 'var(--font-space)' }}>
            AI dla przetargów budowlanych
          </p>
        </div>

        {/* ── Card ──────────────────────────────────────────────────── */}
        <div
          className="relative rounded-2xl p-6 backdrop-blur-xl shadow-xl border border-ink-700/40 border-t-ink-600/60"
          style={{
            background: 'linear-gradient(135deg, rgba(15,13,10,0.8), rgba(28,26,22,0.6))',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.04), 0 25px 50px rgba(0,0,0,0.5)',
          }}
        >

          {/* Tabs */}
          <div className="flex rounded-md bg-ink-800/50 p-1 mb-6 gap-1">
            {(['login', 'register'] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => switchTab(t)}
                className={[
                  'flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-all duration-200',
                  tab === t
                    ? 'bg-em text-ink-950 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                {t === 'login'
                  ? <><LogIn    className="w-3.5 h-3.5" /> Logowanie</>
                  : <><UserPlus className="w-3.5 h-3.5" /> Rejestracja</>}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Register-only fields */}
            <AnimatePresence mode="popLayout">
              {tab === 'register' && (
                <motion.div
                  key="register-fields"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-4 overflow-hidden"
                >
                  <div>
                    <label className="label-base">Imię i nazwisko</label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      autoComplete="name"
                      placeholder="np. Jan Kowalski"
                      className="input-base"
                    />
                  </div>
                  <div>
                    <label className="label-base">Nazwa firmy</label>
                    <input
                      type="text"
                      value={orgName}
                      onChange={(e) => setOrgName(e.target.value)}
                      autoComplete="organization"
                      placeholder="np. Kowalski Budownictwo Sp. z o.o."
                      className="input-base"
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* E-mail */}
            <div>
              <label className="label-base">E-mail</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="twoj@firma.pl"
                  className="input-base pl-9"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="label-base">Hasło</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                  placeholder={tab === 'register' ? 'min. 8 znaków' : '••••••••'}
                  className="input-base pl-9 pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  aria-label={showPassword ? 'Ukryj hasło' : 'Pokaż hasło'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error */}
            <AnimatePresence mode="popLayout">
              {error && (
                <motion.div
                  key="error"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="flex items-start gap-2 px-3 py-2.5 bg-nogo/10 border border-nogo/20 rounded-md text-nogo text-sm">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-3 mt-2 font-semibold tracking-tight hover:brightness-110 transition-all duration-200"
              style={{
                background: loading
                  ? undefined
                  : 'linear-gradient(to right, #10b981, #34d399)',
              }}
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : tab === 'login'
                  ? <LogIn className="w-4 h-4" />
                  : <UserPlus className="w-4 h-4" />}
              {tab === 'login' ? 'Zaloguj się' : 'Zarejestruj się'}
            </button>

            {/* Forgot password link */}
            {tab === 'login' && (
              <button
                type="button"
                onClick={() => { setForgotMode(true); setForgotEmail(email); setForgotSuccess(false); setForgotError(''); }}
                className="w-full text-center text-sm text-slate-500 hover:text-em transition-colors mt-2"
              >
                Zapomniałeś hasła?
              </button>
            )}
          </form>

          {/* ── Forgot password modal overlay ─────────────────────────── */}
          <AnimatePresence>
            {forgotMode && (
              <motion.div
                key="forgot-overlay"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 z-20 flex items-center justify-center bg-ink-950/80 backdrop-blur-sm rounded-2xl"
              >
                <div className="w-full max-w-sm p-6">
                  {forgotSuccess ? (
                    <div className="text-center space-y-3">
                      <div className="w-12 h-12 mx-auto rounded-full bg-em/20 flex items-center justify-center">
                        <Mail className="w-6 h-6 text-em" />
                      </div>
                      <h3 className="text-lg font-semibold text-slate-100">Sprawdź skrzynkę</h3>
                      <p className="text-slate-400 text-sm">Jeśli konto istnieje, wysłaliśmy link do resetowania hasła.</p>
                      <button
                        type="button"
                        onClick={() => setForgotMode(false)}
                        className="btn-primary w-full py-2.5 mt-4"
                        style={{ background: 'linear-gradient(to right, #10b981, #34d399)' }}
                      >
                        Wróć do logowania
                      </button>
                    </div>
                  ) : (
                    <form onSubmit={handleForgotPassword} className="space-y-4">
                      <button
                        type="button"
                        onClick={() => setForgotMode(false)}
                        className="flex items-center gap-1 text-slate-500 hover:text-slate-300 text-sm transition-colors"
                      >
                        <ArrowLeft className="w-3.5 h-3.5" /> Wróć
                      </button>
                      <h3 className="text-lg font-semibold text-slate-100">Odzyskaj dostęp</h3>
                      <p className="text-slate-400 text-sm">Podaj adres e-mail powiązany z kontem.</p>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 pointer-events-none" />
                        <input
                          type="email"
                          value={forgotEmail}
                          onChange={(e) => setForgotEmail(e.target.value)}
                          required
                          autoFocus
                          placeholder="twoj@firma.pl"
                          className="input-base pl-9"
                        />
                      </div>
                      {forgotError && (
                        <div className="flex items-start gap-2 px-3 py-2 bg-nogo/10 border border-nogo/20 rounded-md text-nogo text-sm">
                          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                          <span>{forgotError}</span>
                        </div>
                      )}
                      <button
                        type="submit"
                        disabled={forgotLoading}
                        className="btn-primary w-full py-2.5 font-semibold"
                        style={{ background: forgotLoading ? undefined : 'linear-gradient(to right, #10b981, #34d399)' }}
                      >
                        {forgotLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                        Wyślij link resetujący
                      </button>
                    </form>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <p className="text-center text-slate-700 text-xs mt-4">
          budos &copy; 2026
        </p>
      </motion.div>
    </div>
  );
}
