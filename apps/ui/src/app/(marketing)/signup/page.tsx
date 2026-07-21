'use client';

import { LoginForm } from '@/components/LoginForm';
import { useRouter } from 'next/navigation';

export default function SignupPage() {
  const router = useRouter();

  return (
    <LoginForm
      onSuccess={() => router.push('/app')}
    />
  );
}
