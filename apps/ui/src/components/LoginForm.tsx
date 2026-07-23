'use client';

import { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useStore } from '@/store/useStore';
import type { AuthUser } from '@/store/useStore';
import {
  AlertCircle, CheckCircle2, Eye, EyeOff,
  Loader2, LogIn, UserPlus, ArrowRight,
} from 'lucide-react';

// ── YU-NA Login — light institutional ────────────────────────────────────────
const T = {
  bg:       '#F5F7FA',
  card:     '#FFFFFF',
  navy:     '#0A1628',
  indigo:   '#4F46E5',
  indigoL:  '#EEF2FF',
  border:   '#E2E8F0',
  borderFocus: '#4F46E5',
  muted:    '#64748B',
  faint:    '#94A3B8',
  ink:      '#0A1628',
  error:    '#DC2626',
  errorBg:  '#FEF2F2',
  sans:     'var(--font-space)',
  mono:     'var(--font-jetbrains)',
} as const;

interface LoginFormProps {
  onSuccess: () => void;
}

const FEATURES = [
  { text: 'Scoring AI w 30 sekund', sub: 'GO / NO-GO z uzasadnieniem' },
  { text: 'Kosztorys z jednego kliknięcia', sub: 'ATH / PDF / KNR gotowy' },
  { text: 'Win rate 67% avg u klientów', sub: 'Potwierdzone w 2026' },
] as const;

export function LoginForm({ onSuccess }: LoginFormProps) {
  const setAuth = useStore((s) => s.setAuth);

  const [tab,           setTab]           = useState<'login' | 'register'>('login');
  const [email,         setEmail]         = useState('');
  const [password,      setPassword]      = useState('');
  const [showPassword,  setShowPassword]  = useState(false);
  const [name,          setName]          = useState('');
  const [orgName,       setOrgName]       = useState('');
  const [error,         setError]         = useState('');
  const [loading,       setLoading]       = useState(false);

  // Forgot password
  const [forgotMode,    setForgotMode]    = useState(false);
  const [forgotEmail,   setForgotEmail]   = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotError,   setForgotError]   = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const endpoint = tab === 'login' ? '/api/v2/auth/login' : '/api/v2/auth/register';
      const body = tab === 'login'
        ? { email, password }
        : { email, password, name, org_name: orgName };

      const res  = await fetch(endpoint, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const detail = typeof data.detail === 'string'
          ? data.detail
          : Array.isArray(data.detail)
            ? (data.detail as { msg?: string }[]).map(d => d.msg || '').join('; ')
            : '';
        if (res.status === 401 || detail.toLowerCase().includes('invalid'))
          setError('Nieprawidłowy e-mail lub hasło.');
        else if (res.status === 409 || detail.toLowerCase().includes('exist'))
          setError('Konto z tym adresem już istnieje. Zaloguj się.');
        else if (res.status >= 500)
          setError('Problem z serwerem — spróbuj za chwilę.');
        else
          setError(detail || 'Nie udało się. Spróbuj ponownie.');
        return;
      }

      setAuth(data.user as AuthUser, data.access_token, data.refresh_token);
      onSuccess();
    } catch {
      setError('Brak połączenia z serwerem.');
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
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email: forgotEmail }),
      });
      if (res.ok) setForgotSuccess(true);
      else setForgotError('Wystąpił błąd. Spróbuj ponownie.');
    } catch {
      setForgotError('Brak połączenia z serwerem.');
    } finally {
      setForgotLoading(false);
    }
  }

  const inputStyle = (focused?: boolean): React.CSSProperties => ({
    width: '100%',
    fontFamily: T.sans, fontSize: 14,
    color: T.ink,
    background: T.card,
    border: `1.5px solid ${focused ? T.borderFocus : T.border}`,
    borderRadius: 8,
    padding: '10px 14px',
    outline: 'none',
    transition: 'border-color 120ms ease',
    boxSizing: 'border-box',
  });

  // ── Forgot password flow ──────────────────────────────────────────────────
  if (forgotMode) {
    return (
      <div style={{ minHeight: '100dvh', background: T.bg, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
        <div style={{ width: '100%', maxWidth: 400 }}>
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <Link href="/">
              <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={36} height={36} style={{ objectFit: 'contain', margin: '0 auto 12px' }} />
            </Link>
            <h1 style={{ fontFamily: T.sans, fontWeight: 800, fontSize: 24, color: T.navy, letterSpacing: '-0.02em', margin: '0 0 8px' }}>
              Odzyskaj dostęp
            </h1>
            <p style={{ fontFamily: T.sans, fontSize: 14, color: T.muted, margin: 0 }}>Wyślemy link resetujący na Twój e-mail.</p>
          </div>

          {!forgotSuccess ? (
            <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 16, padding: '28px 28px' }}>
              <form onSubmit={handleForgotPassword} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div>
                  <label style={{ fontFamily: T.sans, fontSize: 12.5, fontWeight: 600, color: T.muted, display: 'block', marginBottom: 6 }}>
                    Adres e-mail
                  </label>
                  <input
                    type="email" required
                    value={forgotEmail}
                    onChange={e => setForgotEmail(e.target.value)}
                    placeholder="jan@firma.pl"
                    style={inputStyle()}
                  />
                </div>
                {forgotError && (
                  <div style={{ display: 'flex', gap: 8, background: T.errorBg, border: `1px solid #FECACA`, borderRadius: 8, padding: '10px 12px' }}>
                    <AlertCircle size={15} color={T.error} style={{ flexShrink: 0, marginTop: 1 }} />
                    <span style={{ fontFamily: T.sans, fontSize: 13, color: T.error }}>{forgotError}</span>
                  </div>
                )}
                <button type="submit" disabled={forgotLoading} style={{
                  fontFamily: T.sans, fontWeight: 600, fontSize: 14,
                  color: '#fff', background: T.indigo,
                  border: 'none', borderRadius: 8, padding: '11px 0',
                  cursor: forgotLoading ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  opacity: forgotLoading ? 0.7 : 1,
                }}>
                  {forgotLoading ? <Loader2 size={16} className="animate-spin" /> : null}
                  Wyślij link resetujący
                </button>
              </form>
              <button type="button" onClick={() => setForgotMode(false)} style={{
                marginTop: 16, background: 'none', border: 'none', cursor: 'pointer',
                fontFamily: T.sans, fontSize: 13, color: T.muted, display: 'block', width: '100%', textAlign: 'center',
              }}>
                ← Wróć do logowania
              </button>
            </div>
          ) : (
            <div style={{ background: T.card, border: `1px solid #BBF7D0`, borderRadius: 16, padding: '28px', textAlign: 'center' }}>
              <CheckCircle2 size={40} color="#16a34a" style={{ margin: '0 auto 16px' }} />
              <p style={{ fontFamily: T.sans, fontSize: 14, color: T.ink, margin: '0 0 16px' }}>
                Wysłaliśmy link resetujący na <strong>{forgotEmail}</strong>. Sprawdź skrzynkę.
              </p>
              <button type="button" onClick={() => { setForgotMode(false); setForgotSuccess(false); }} style={{
                fontFamily: T.sans, fontSize: 13, color: T.indigo, background: 'none', border: 'none', cursor: 'pointer',
              }}>
                Wróć do logowania
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── Main login/register ───────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100dvh', background: T.bg, display: 'flex' }}>

      {/* Left panel — YU-NA brand (desktop only) */}
      <div style={{
        flex: '0 0 52%',
        background: T.navy,
        display: 'none',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 64px',
        position: 'relative',
        overflow: 'hidden',
      }}
        className="lg-left-panel"
      >
        {/* Subtle grid */}
        <div style={{
          position: 'absolute', inset: 0, pointerEvents: 'none',
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }} />

        <div style={{ position: 'relative', maxWidth: 480 }}>
          {/* Logo */}
          <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 10, textDecoration: 'none', marginBottom: 56 }}>
            <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={32} height={32} style={{ objectFit: 'contain', filter: 'brightness(0) invert(1)' }} />
            <span style={{ fontFamily: T.sans, fontWeight: 800, fontSize: 16, color: '#fff', letterSpacing: '-0.02em' }}>YU-NA Intelligence</span>
          </Link>

          <h1 style={{
            fontFamily: T.sans, fontWeight: 800, fontSize: 42,
            color: '#fff', letterSpacing: '-0.04em', lineHeight: 1.05,
            margin: '0 0 16px',
          }}>
            Wygrywaj<br />przetargi.<br />
            <span style={{ color: '#34d399' }}>Szybciej.</span>
          </h1>

          <p style={{ fontFamily: T.sans, fontSize: 16, color: 'rgba(255,255,255,0.55)', lineHeight: 1.65, margin: '0 0 48px' }}>
            Platforma AI dla firm budowlanych. Jeden login — dostęp do całego ekosystemu narzędzi przetargowych.
          </p>

          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 20 }}>
            {FEATURES.map(({ text, sub }) => (
              <li key={text} style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                <CheckCircle2 size={18} color="#34d399" style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <div style={{ fontFamily: T.sans, fontSize: 14, fontWeight: 600, color: '#f1f5f9' }}>{text}</div>
                  <div style={{ fontFamily: T.sans, fontSize: 12.5, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{sub}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Right panel — form */}
      <div style={{
        flex: 1,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '40px 24px',
        background: T.bg,
      }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          {/* Mobile logo */}
          <div style={{ textAlign: 'center', marginBottom: 32 }} className="lg-hide-logo">
            <Link href="/">
              <Image src="/brand/01-logo-concept.png" alt="YU-NA" width={36} height={36} style={{ objectFit: 'contain', margin: '0 auto 10px', display: 'block' }} />
            </Link>
            <span style={{ fontFamily: T.sans, fontWeight: 800, fontSize: 18, color: T.navy, letterSpacing: '-0.02em' }}>YU-NA Intelligence</span>
          </div>

          {/* Card */}
          <div style={{
            background: T.card,
            border: `1px solid ${T.border}`,
            borderRadius: 18,
            padding: '32px 28px',
            boxShadow: '0 4px 24px rgba(10,22,40,0.06)',
          }}>
            {/* Tabs */}
            <div style={{
              display: 'flex', gap: 4,
              background: T.bg, border: `1px solid ${T.border}`,
              borderRadius: 10, padding: 4,
              marginBottom: 24,
            }}>
              {(['login', 'register'] as const).map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => { setTab(t); setError(''); }}
                  style={{
                    flex: 1, fontFamily: T.sans, fontSize: 13, fontWeight: 600,
                    color: tab === t ? '#fff' : T.muted,
                    background: tab === t ? T.indigo : 'transparent',
                    border: 'none', borderRadius: 7, padding: '8px 0',
                    cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                    transition: 'background 150ms ease, color 150ms ease',
                  }}
                >
                  {t === 'login'
                    ? <><LogIn size={13} /> Logowanie</>
                    : <><UserPlus size={13} /> Rejestracja</>}
                </button>
              ))}
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

              {/* Register extra fields */}
              {tab === 'register' && (
                <>
                  <div>
                    <label style={{ fontFamily: T.sans, fontSize: 12.5, fontWeight: 600, color: T.muted, display: 'block', marginBottom: 6 }}>Imię i nazwisko</label>
                    <input
                      type="text" required
                      value={name}
                      onChange={e => setName(e.target.value)}
                      placeholder="Jan Kowalski"
                      style={inputStyle()}
                      onFocus={e => (e.currentTarget.style.borderColor = T.borderFocus)}
                      onBlur={e => (e.currentTarget.style.borderColor = T.border)}
                    />
                  </div>
                  <div>
                    <label style={{ fontFamily: T.sans, fontSize: 12.5, fontWeight: 600, color: T.muted, display: 'block', marginBottom: 6 }}>Nazwa firmy</label>
                    <input
                      type="text"
                      value={orgName}
                      onChange={e => setOrgName(e.target.value)}
                      placeholder="Kowalski Budownictwo Sp. z o.o."
                      style={inputStyle()}
                      onFocus={e => (e.currentTarget.style.borderColor = T.borderFocus)}
                      onBlur={e => (e.currentTarget.style.borderColor = T.border)}
                    />
                  </div>
                </>
              )}

              {/* Email */}
              <div>
                <label style={{ fontFamily: T.sans, fontSize: 12.5, fontWeight: 600, color: T.muted, display: 'block', marginBottom: 6 }}>Adres e-mail</label>
                <input
                  type="email" required
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="jan@firma.pl"
                  autoComplete="email"
                  style={inputStyle()}
                  onFocus={e => (e.currentTarget.style.borderColor = T.borderFocus)}
                  onBlur={e => (e.currentTarget.style.borderColor = T.border)}
                />
              </div>

              {/* Password */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <label style={{ fontFamily: T.sans, fontSize: 12.5, fontWeight: 600, color: T.muted }}>Hasło</label>
                  {tab === 'login' && (
                    <button type="button" onClick={() => setForgotMode(true)} style={{
                      fontFamily: T.sans, fontSize: 12, color: T.indigo, background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                    }}>Zapomniałem hasła</button>
                  )}
                </div>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                    style={{ ...inputStyle(), paddingRight: 44 }}
                    onFocus={e => (e.currentTarget.style.borderColor = T.borderFocus)}
                    onBlur={e => (e.currentTarget.style.borderColor = T.border)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(v => !v)}
                    style={{
                      position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                      background: 'none', border: 'none', cursor: 'pointer', color: T.faint, padding: 2,
                    }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Error */}
              {error && (
                <div style={{
                  display: 'flex', gap: 8,
                  background: T.errorBg, border: `1px solid #FECACA`,
                  borderRadius: 8, padding: '10px 12px',
                }}>
                  <AlertCircle size={15} color={T.error} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span style={{ fontFamily: T.sans, fontSize: 13, color: T.error }}>{error}</span>
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                style={{
                  fontFamily: T.sans, fontWeight: 600, fontSize: 14,
                  color: '#fff', background: loading ? '#6366f1' : T.indigo,
                  border: 'none', borderRadius: 8, padding: '12px 0',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
                  marginTop: 4,
                  transition: 'background 120ms ease',
                }}
                onMouseEnter={e => { if (!loading) e.currentTarget.style.background = '#4338CA'; }}
                onMouseLeave={e => { if (!loading) e.currentTarget.style.background = T.indigo; }}
              >
                {loading
                  ? <Loader2 size={16} className="animate-spin" />
                  : tab === 'login'
                    ? <><LogIn size={15} /> Zaloguj się</>
                    : <><ArrowRight size={15} /> Utwórz konto</>
                }
              </button>
            </form>
          </div>

          {/* Footer links */}
          <p style={{ textAlign: 'center', fontFamily: T.sans, fontSize: 12.5, color: T.faint, marginTop: 20 }}>
            <Link href="/" style={{ color: T.muted, textDecoration: 'none' }}>← YU-NA Intelligence</Link>
            {' · '}
            <Link href="/budos" style={{ color: T.muted, textDecoration: 'none' }}>Bud.OS</Link>
          </p>
        </div>
      </div>

      {/* CSS for responsive left panel */}
      <style>{`
        @media (min-width: 1024px) {
          .lg-left-panel { display: flex !important; }
          .lg-hide-logo { display: none !important; }
        }
      `}</style>
    </div>
  );
}
