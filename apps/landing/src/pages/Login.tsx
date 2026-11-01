/**
 * Login Page — Premium Liquid Glass Experience
 *
 * Real authentication only:
 *   - Sign in / create account against the FastAPI backend.
 *   - No demo login, no SSO buttons, no remember-me, no fake success.
 *   - Login failures are reported generically to avoid account enumeration.
 *   - The workspace is entered only after AuthProvider confirms a session.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useExperience } from '@/core/ExperienceController';
import { EnterAtlasTransition } from '@/components/network/EnterAtlasTransition';
import { Glass, Button, Input } from '@/design/primitives';
import { useAuth } from '@/features/auth/AuthProvider';

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const navigate = useNavigate();
  const { enterAtlas, startLoader } = useExperience();
  const { signIn, signUp } = useAuth();

  // Mode state: 'login' | 'signup'
  const [mode, setMode] = useState<'login' | 'signup'>('login');

  // Form states
  const [name, setName] = useState('');
  const [nameError, setNameError] = useState('');
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState('');
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [confirmPasswordError, setConfirmPasswordError] = useState('');
  const [formError, setFormError] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFadingForm, setIsFadingForm] = useState(false);

  // Validation
  const validateName = (value: string) => {
    if (!value.trim()) {
      setNameError('Name is required');
      return false;
    }
    if (value.trim().length < 2) {
      setNameError('Name must be at least 2 characters');
      return false;
    }
    setNameError('');
    return true;
  };

  const validateEmail = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      setEmailError('Email is required');
      return false;
    }
    if (!EMAIL_PATTERN.test(trimmed)) {
      setEmailError('Enter a valid email address');
      return false;
    }
    setEmailError('');
    return true;
  };

  const validatePassword = (value: string) => {
    if (!value) {
      setPasswordError('Password is required');
      return false;
    }
    if (mode === 'signup' && value.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return false;
    }
    setPasswordError('');
    return true;
  };

  const validateConfirmPassword = (value: string) => {
    if (mode === 'signup') {
      if (!value) {
        setConfirmPasswordError('Confirm your password');
        return false;
      }
      if (value !== password) {
        setConfirmPasswordError('Passwords do not match');
        return false;
      }
    }
    setConfirmPasswordError('');
    return true;
  };

  const enterWorkspace = () => {
    setIsSuccess(true);
    setTimeout(() => {
      setIsFadingForm(true);
      const WORKSPACE_LOADER_STATES = [
        { text: 'Connecting to Atlas Core API...' },
        { text: 'Loading registered AI models...' },
        { text: 'Mounting evaluation workspaces...' },
        { text: 'Verifying active runtime loops...' },
        { text: 'Atlas Workspace ready.' },
      ];
      startLoader(WORKSPACE_LOADER_STATES, 500, () => {
        enterAtlas();
      });
    }, 700);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || isSuccess) return;

    setFormError('');

    let isValid = true;
    if (mode === 'signup' && !validateName(name)) isValid = false;
    if (!validateEmail(email)) isValid = false;
    if (!validatePassword(password)) isValid = false;
    if (mode === 'signup' && !validateConfirmPassword(confirmPassword)) isValid = false;
    if (!isValid) return;

    setIsSubmitting(true);

    try {
      const result =
        mode === 'login'
          ? await signIn(email.trim(), password)
          : await signUp({
              email: email.trim(),
              full_name: name.trim(),
              password,
            });

      if (result.error) {
        setFormError(result.error);
        setIsSubmitting(false);
        return;
      }

      // Only a verified session reaches this point.
      enterWorkspace();
    } catch {
      setFormError('Unable to sign in right now. Please try again.');
      setIsSubmitting(false);
    }
  };

  // Switch Mode Helper
  const toggleMode = (newMode: 'login' | 'signup') => {
    setMode(newMode);
    setName('');
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setNameError('');
    setEmailError('');
    setPasswordError('');
    setConfirmPasswordError('');
    setFormError('');
  };

  // Motion variants for form element staggering
  const containerVariants = {
    initial: {},
    animate: {
      transition: {
        staggerChildren: 0.05,
      },
    },
  };

  const itemVariants = {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const } },
  };

  return (
    <div className="relative min-h-screen w-screen overflow-hidden flex items-center justify-center p-4 bg-[#030712] font-sans">
      {/* Background Video */}
      <video
        src="/login-bg.mp4"
        poster="/loader-bg.jpg"
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover z-0 pointer-events-none"
      />

      {/* Dark gradient overlay for readability */}
      <div
        className="absolute inset-0 z-1 pointer-events-none"
        style={{
          background: 'linear-gradient(to bottom, rgba(3, 7, 18, 0.25) 0%, rgba(3, 7, 18, 0.65) 100%)',
        }}
      />

      {/* Ambient blue/violet glow matching the Atlas Intelligence Fabric */}
      <motion.div
        animate={{
          scale: [1, 1.15, 1],
          opacity: [0.4, 0.65, 0.4],
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] rounded-full filter blur-[120px] pointer-events-none z-2"
        style={{
          background:
            'radial-gradient(circle, rgba(79, 140, 255, 0.16) 0%, rgba(99, 102, 241, 0.05) 50%, transparent 100%)',
        }}
      />

      {/* Boundary transition overlay */}
      <EnterAtlasTransition />

      {/* Foreground Layer */}
      <motion.div
        animate={isFadingForm ? { opacity: 0, scale: 0.96 } : { opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full max-w-[440px] rounded-[24px]"
        style={{ perspective: 1000 }}
      >
        <Glass variant="liquid" className="p-8 md:p-10 rounded-[24px] pointer-events-auto">
          <motion.div
            variants={containerVariants}
            initial="initial"
            animate="animate"
            className="w-full flex flex-col"
            key={mode} // Re-staggers animation when switching mode
          >
            {/* Header */}
            <header className="mb-7 text-center">
              {/* Logo */}
              <motion.div
                variants={itemVariants}
                onClick={() => navigate('/')}
                className="inline-flex items-center gap-2 mb-4 cursor-pointer text-[#F8FAFC] hover:text-[#F8FAFC]/80 transition-colors"
              >
                <svg width="24" height="24" viewBox="0 0 28 28" fill="none" className="shrink-0">
                  <g stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="14" cy="11" r="2.5" fill="currentColor" opacity="0.15" />
                    <circle cx="14" cy="11" r="2.5" />
                    <line x1="14" y1="8.5" x2="7" y2="24" />
                    <line x1="14" y1="8.5" x2="21" y2="24" />
                    <line x1="9.5" y1="18" x2="18.5" y2="18" />
                    <line x1="14" y1="8.5" x2="14" y2="3" />
                    <line x1="14" y1="11" x2="6" y2="7" />
                    <line x1="14" y1="11" x2="22" y2="7" />
                    <circle cx="14" cy="3" r="1.25" />
                    <circle cx="6" cy="7" r="1.25" />
                    <circle cx="22" cy="7" r="1.25" />
                  </g>
                </svg>
                <span className="text-base font-bold tracking-tight">Atlas</span>
              </motion.div>

              <motion.h1
                variants={itemVariants}
                className="text-2xl font-bold tracking-tight text-[#F8FAFC] mb-1"
              >
                {mode === 'login' ? 'Welcome back' : 'Create account'}
              </motion.h1>

              <motion.p variants={itemVariants} className="text-xs text-[#94A3B8] font-sans">
                {mode === 'login' ? (
                  <>
                    Continue into your <span className="font-serif italic text-white/50">Workspace</span>.
                  </>
                ) : (
                  <>
                    Get started with <span className="font-serif italic text-white/50">Atlas</span>.
                  </>
                )}
              </motion.p>
            </header>

            {/* Form */}
            <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
              {/* Name (Sign Up only) */}
              {mode === 'signup' && (
                <motion.div variants={itemVariants}>
                  <Input
                    label="Full Name"
                    id="name"
                    type="text"
                    placeholder="Jane Doe"
                    autoComplete="name"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (nameError) setNameError('');
                    }}
                    onBlur={() => name && validateName(name)}
                    error={nameError}
                    disabled={isSubmitting || isSuccess}
                  />
                </motion.div>
              )}

              {/* Email */}
              <motion.div variants={itemVariants}>
                <Input
                  label="Email"
                  id="email"
                  type="email"
                  placeholder="you@company.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (emailError) setEmailError('');
                    if (formError) setFormError('');
                  }}
                  onBlur={() => email && validateEmail(email)}
                  error={emailError}
                  disabled={isSubmitting || isSuccess}
                />
              </motion.div>

              {/* Password */}
              <motion.div variants={itemVariants}>
                <Input
                  label="Password"
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder={mode === 'signup' ? 'At least 8 characters' : 'Enter password'}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (passwordError) setPasswordError('');
                    if (formError) setFormError('');
                  }}
                  onBlur={() => password && validatePassword(password)}
                  error={passwordError}
                  disabled={isSubmitting || isSuccess}
                  trailingAction={
                    <button
                      type="button"
                      onClick={() => setShowPassword((p) => !p)}
                      className="flex items-center justify-center w-8 h-8 rounded text-white/40 hover:text-[#F8FAFC]/70 hover:bg-white/[0.04] transition-colors cursor-pointer bg-transparent border-none"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  }
                />
              </motion.div>

              {/* Confirm Password (Sign Up only) */}
              {mode === 'signup' && (
                <motion.div variants={itemVariants}>
                  <Input
                    label="Confirm Password"
                    id="confirmPassword"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Re-enter password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value);
                      if (confirmPasswordError) setConfirmPasswordError('');
                    }}
                    onBlur={() => confirmPassword && validateConfirmPassword(confirmPassword)}
                    error={confirmPasswordError}
                    disabled={isSubmitting || isSuccess}
                  />
                </motion.div>
              )}

              {/* Form-level error (generic) */}
              {formError && (
                <motion.p
                  variants={itemVariants}
                  role="alert"
                  aria-live="polite"
                  className="text-[11px] text-error font-medium text-center"
                >
                  {formError}
                </motion.p>
              )}

              {/* Submit */}
              <motion.div variants={itemVariants} className="flex flex-col gap-2.5">
                <Button
                  type="submit"
                  variant="primary"
                  isLoading={isSubmitting && !isSuccess}
                  isSuccess={isSuccess}
                >
                  {mode === 'login' ? 'Sign in' : 'Create account'}
                  {!isSubmitting && !isSuccess && <ArrowRight className="w-4 h-4 shrink-0 text-white/70" />}
                </Button>
              </motion.div>
            </form>

            {/* Switch Mode Footer link */}
            <motion.div variants={itemVariants} className="text-center mt-5">
              <span className="text-[11px] text-[#94A3B8]">
                {mode === 'login' ? (
                  <>
                    Don't have an account?{' '}
                    <button
                      type="button"
                      onClick={() => toggleMode('signup')}
                      className="text-[#4F8CFF] hover:text-[#4F8CFF]/85 hover:underline transition-all cursor-pointer font-semibold bg-transparent border-none p-0"
                    >
                      Create one
                    </button>
                  </>
                ) : (
                  <>
                    Already have an account?{' '}
                    <button
                      type="button"
                      onClick={() => toggleMode('login')}
                      className="text-[#4F8CFF] hover:text-[#4F8CFF]/85 hover:underline transition-all cursor-pointer font-semibold bg-transparent border-none p-0"
                    >
                      Sign in
                    </button>
                  </>
                )}
              </span>
            </motion.div>
          </motion.div>
        </Glass>
      </motion.div>
    </div>
  );
}
