export function PageLoader() {
  return (
    <div className="relative min-h-screen w-full overflow-hidden flex flex-col items-center justify-center bg-black font-sans">
      <img
        src="/loader-bg.jpg"
        alt=""
        loading="eager"
        className="absolute inset-0 w-full h-full object-cover z-0 select-none pointer-events-none"
      />
      <div className="absolute inset-0 bg-black/60 backdrop-blur-md z-10 pointer-events-none" />
      <div className="relative z-20 flex flex-col items-center gap-4" role="status" aria-live="polite">
        <div className="w-6 h-6 border-2 border-white/10 border-t-accent rounded-full animate-spin" />
        <span className="text-[10px] tracking-[0.25em] uppercase text-white/45 font-medium">Loading</span>
      </div>
    </div>
  );
}
