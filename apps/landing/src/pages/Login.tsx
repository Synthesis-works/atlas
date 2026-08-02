/**
 * Login Page — Premium Liquid Glass Experience
 *
 * Implements a luxurious, highly polished authentication screen.
 * - Custom styled checkbox (fully custom UI matching Liquid Glass).
 * - Symmetrical stacked button layout for Enter Atlas and Demo Login.
 * - Interactive mouse-tilt parallax and dynamic spotlight cursor reflections.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, EyeOff, ArrowRight } from 'lucide-react';
import { useExperience } from '@/core/ExperienceController';
import { EnterAtlasTransition } from '@/components/network/EnterAtlasTransition';
import { Glass, Button, Input } from '@/design/primitives';

export default function Login() {
  const navigate = useNavigate();
  const { enterAtlas, startLoader } = useExperience();

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
  
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [isFadingForm, setIsFadingForm] = useState(false);

  // Validation
  const validateEmail = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) {
      setEmailError('Email is required');
      return false;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) {
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
    if (value.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return false;
    }
    setPasswordError('');
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting || isSuccess) return;

    let isValid = true;

    // Sign Up Name validation
    if (mode === 'signup') {
      if (!name.trim()) {
        setNameError('Name is required');
        isValid = false;
      } else {
        setNameError('');
      }
    }

    // Email & Password validation
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);
    if (!isEmailValid || !isPasswordValid) isValid = false;

    // Sign Up Confirm Password validation
    if (mode === 'signup') {
      if (!confirmPassword) {
        setConfirmPasswordError('Confirm password is required');
        isValid = false;
      } else if (password !== confirmPassword) {
        setConfirmPasswordError('Passwords do not match');
        isValid = false;
      } else {
        setConfirmPasswordError('');
      }
    }

    if (!isValid) return;

    setIsSubmitting(true);

    // Simulate network authentication request
    try {
      await new Promise((resolve) => setTimeout(resolve, 1400));
      localStorage.setItem('atlas_logged_in', 'true');
      setIsSuccess(true);

      // Phase 1: Fade out the form elements first
      setTimeout(() => {
        setIsFadingForm(true);
        // Phase 2: Trigger Multi-Step Loader before boundary crossing
        const WORKSPACE_LOADER_STATES = [
          { text: "Connecting to Atlas Core API..." },
          { text: "Loading registered AI models..." },
          { text: "Mounting evaluation workspaces..." },
          { text: "Verifying active runtime loops..." },
          { text: "Atlas Workspace ready." }
        ];
        startLoader(WORKSPACE_LOADER_STATES, 500, () => {
          enterAtlas();
        });
      }, 800);
    } catch {
      setPasswordError('Authentication failed');
      setIsSubmitting(false);
    }
  };

  // Demo fast login bypass
  const handleDemoLogin = async () => {
    if (isSubmitting || isSuccess) return;
    setMode('login');
    setEmail('demo@atlas.io');
    setPassword('password123');
    setEmailError('');
    setPasswordError('');
    setIsSubmitting(true);

    try {
      await new Promise((resolve) => setTimeout(resolve, 900));
      localStorage.setItem('atlas_logged_in', 'true');
      setIsSuccess(true);

      setTimeout(() => {
        setIsFadingForm(true);
        const WORKSPACE_LOADER_STATES = [
          { text: "Connecting to Atlas Core API..." },
          { text: "Loading registered AI models..." },
          { text: "Mounting evaluation workspaces..." },
          { text: "Verifying active runtime loops..." },
          { text: "Atlas Workspace ready." }
        ];
        startLoader(WORKSPACE_LOADER_STATES, 500, () => {
          enterAtlas();
        });
      }, 600);
    } catch {
      setIsSubmitting(false);
    }
  };

  // Switch Mode Helper
  const toggleMode = (newMode: 'login' | 'signup') => {
    setMode(newMode);
    // Clear inputs and errors
    setName('');
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setNameError('');
    setEmailError('');
    setPasswordError('');
    setConfirmPasswordError('');
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
          background: 'linear-gradient(to bottom, rgba(3, 7, 18, 0.25) 0%, rgba(3, 7, 18, 0.65) 100%)'
        }}
      />

      {/* Ambient blue/violet glow matching the Atlas Intelligence Fabric */}
      <motion.div 
        animate={{
          scale: [1, 1.15, 1],
          opacity: [0.4, 0.65, 0.4]
        }}
        transition={{
          duration: 10,
          repeat: Infinity,
          ease: "easeInOut"
        }}
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[550px] rounded-full filter blur-[120px] pointer-events-none z-2"
        style={{
          background: 'radial-gradient(circle, rgba(79, 140, 255, 0.16) 0%, rgba(99, 102, 241, 0.05) 50%, transparent 100%)',
        }}
      />

      {/* Boundary transition overlay */}
      <EnterAtlasTransition />

      {/* Foreground Layer: Hover Card wrapper */}
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
                  {mode === 'login' ? 'Welcome back' : 'Create Account'}
                </motion.h1>

                <motion.p
                  variants={itemVariants}
                  className="text-xs text-[#94A3B8] font-sans"
                >
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
              <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                {/* Name (Sign Up only) */}
                {mode === 'signup' && (
                  <motion.div variants={itemVariants}>
                    <Input
                      label="Full Name"
                      id="name"
                      type="text"
                      placeholder="Jane Doe"
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value);
                        if (nameError) setNameError('');
                      }}
                      error={nameError}
                      disabled={isSubmitting}
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
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (emailError) validateEmail(e.target.value);
                    }}
                    onBlur={() => validateEmail(email)}
                    error={emailError}
                    disabled={isSubmitting}
                  />
                </motion.div>

                {/* Password */}
                <motion.div variants={itemVariants}>
                  <Input
                    label="Password"
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (passwordError) validatePassword(e.target.value);
                    }}
                    onBlur={() => validatePassword(password)}
                    error={passwordError}
                    disabled={isSubmitting}
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
                      value={confirmPassword}
                      onChange={(e) => {
                        setConfirmPassword(e.target.value);
                        if (confirmPasswordError) setConfirmPasswordError('');
                      }}
                      error={confirmPasswordError}
                      disabled={isSubmitting}
                    />
                  </motion.div>
                )}

                {/* Options (Sign In only) */}
                {mode === 'login' && (
                  <motion.div variants={itemVariants} className="flex items-center justify-between text-xs my-0.5">
                    {/* Custom Premium Styled Checkbox */}
                    <label className="flex items-center gap-2.5 cursor-pointer select-none text-xs text-[#94A3B8] hover:text-[#F8FAFC] transition-colors duration-200">
                      <div className="relative w-4 h-4 flex items-center justify-center">
                        <input
                          type="checkbox"
                          checked={rememberMe}
                          onChange={(e) => setRememberMe(e.target.checked)}
                          className="sr-only" // Hide default
                          disabled={isSubmitting}
                        />
                        {/* Custom visual container */}
                        <div className={`w-4 h-4 rounded border transition-all duration-200 flex items-center justify-center ${
                          rememberMe 
                            ? 'bg-[#4F8CFF] border-[#4F8CFF]' 
                            : 'border-white/20 bg-transparent hover:border-white/45'
                        }`}>
                          {rememberMe && (
                            <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="4 10 8 14 16 6"/>
                            </svg>
                          )}
                        </div>
                      </div>
                      <span>Remember me</span>
                    </label>

                    <a href="#" className="text-white/40 hover:text-white/60 transition-colors">
                      Forgot password?
                    </a>
                  </motion.div>
                )}

                {/* Submit Row (Vertical stack for symmetrical visual balance) */}
                <motion.div variants={itemVariants} className="flex flex-col gap-2.5">
                  <Button
                    type="submit"
                    variant="primary"
                    isLoading={isSubmitting && !isSuccess}
                    isSuccess={isSuccess}
                  >
                    {mode === 'login' ? 'Enter Atlas' : 'Create Account'}
                    {!isSubmitting && !isSuccess && <ArrowRight className="w-4 h-4 shrink-0 text-white/70" />}
                  </Button>

                  {mode === 'login' && (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={handleDemoLogin}
                      disabled={isSubmitting || isSuccess}
                    >
                      Demo Login (Fast Access)
                    </Button>
                  )}
                </motion.div>
              </form>

              {/* Footer Divider */}
              <motion.div 
                variants={itemVariants} 
                className="flex items-center gap-3.5 my-5 text-[10px] text-white/20 uppercase tracking-widest before:h-px before:flex-1 before:bg-white/[0.08] after:h-px after:flex-1 after:bg-white/[0.08]"
              >
                or continue with
              </motion.div>

              {/* SSO */}
              <motion.div variants={itemVariants} className="flex flex-col gap-2.5">
                <Button variant="sso">
                  <svg className="w-4 h-4 shrink-0" viewBox="0 0 16 16" fill="none">
                    <path d="M15.68 8.18c0-.57-.05-1.12-.14-1.64H8v3.1h4.31a3.68 3.68 0 0 1-1.6 2.42v2.01h2.59c1.51-1.39 2.38-3.44 2.38-5.89z" fill="#4285F4"/>
                    <path d="M8 16c2.16 0 3.97-.72 5.3-1.93l-2.59-2.01c-.72.48-1.63.76-2.71.76-2.08 0-3.85-1.41-4.48-3.3H.85v2.07A8 8 0 0 0 8 16z" fill="#34A853"/>
                    <path d="M3.52 9.52a4.8 4.8 0 0 1 0-3.04V4.41H.85a8 8 0 0 0 0 7.18l2.67-2.07z" fill="#FBBC05"/>
                    <path d="M8 3.18c1.17 0 2.23.4 3.06 1.2l2.29-2.3A8 8 0 0 0 .85 4.42l2.67 2.07C4.15 5.09 5.92 3.18 8 3.18z" fill="#EA4335"/>
                  </svg>
                  Google
                </Button>

                <Button variant="sso">
                  <svg className="w-4 h-4 shrink-0 text-white" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
                  </svg>
                  GitHub
                </Button>
              </motion.div>

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
                        Sign In
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
