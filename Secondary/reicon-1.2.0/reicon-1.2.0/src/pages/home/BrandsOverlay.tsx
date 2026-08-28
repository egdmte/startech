import { useState, useEffect, useRef } from 'react';
import { ArrowRightUp } from 'reicon-react';

const STORAGE_KEY = 'reicon-brands-overlay-v2';
const COOKIE_KEY = 'reicon_cookie_consent';

export default function BrandsOverlay() {
  const [visible, setVisible] = useState(false);
  const [animateIn, setAnimateIn] = useState(false);
  const dismissedRef = useRef(false);

  useEffect(() => {
    const ownDismissed = (() => {
      try { return localStorage.getItem(STORAGE_KEY) === 'dismissed'; }
      catch { return false; }
    })();
    if (ownDismissed) { dismissedRef.current = true; return; }

    const checkCookie = () => {
      if (dismissedRef.current) return;
      const consented = (() => {
        try { return localStorage.getItem(COOKIE_KEY) !== null; }
        catch { return false; }
      })();
      if (consented) {
        requestAnimationFrame(() => {
          setVisible(true);
          requestAnimationFrame(() => setAnimateIn(true));
        });
      }
    };

    checkCookie();
    window.addEventListener('storage', checkCookie);
    const interval = setInterval(checkCookie, 500);
    return () => {
      window.removeEventListener('storage', checkCookie);
      clearInterval(interval);
    };
  }, []);

  const dismiss = () => {
    dismissedRef.current = true;
    setAnimateIn(false);
    setTimeout(() => setVisible(false), 400);
    try { localStorage.setItem(STORAGE_KEY, 'dismissed'); } catch {}
  };

  if (!visible) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-[9998] p-3 sm:p-5 pointer-events-none">
      <div
        className={`pointer-events-auto ml-auto w-full max-w-[360px] bg-bg-base border border-text-base/10 rounded-[16px] overflow-hidden shadow-[0_8px_40px_rgba(0,0,0,0.25)] transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${animateIn ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-8 scale-95'}`}
      >
        {/* Hero image */}
        <div className="relative aspect-[1200/400] overflow-hidden bg-gradient-to-br from-[#6C5CE7]/20 to-transparent">
          <img
            src="/new-launch.jpg"
            alt="brands.reicon.dev"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-bg-base via-bg-base/10 to-transparent" />
        </div>

        <div className="relative -mt-[2px] px-4 pb-4 pt-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-[10px] font-semibold tracking-[0.1em] uppercase text-[#6C5CE7] mb-0.5">
                New Launch
              </div>
              <h3 className="font-serif text-[16px] text-text-base leading-[1.2] tracking-[-0.01em]">
                brands.reicon.dev
              </h3>
              <p className="text-[12px] text-text-base/45 leading-[1.5] mt-1">
                4,900+ free brand logos in 3 variants.
              </p>
            </div>
            <div className="flex gap-1.5 shrink-0 pt-1">
              <a
                href="https://brands.reicon.dev"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 bg-[#6C5CE7] text-white text-[12px] font-medium px-3.5 py-2 rounded-full hover:bg-[#6C5CE7]/90 active:scale-[0.97] transition-all cursor-pointer whitespace-nowrap"
              >
                Browse
                <ArrowRightUp size={12} />
              </a>
              <button
                onClick={dismiss}
                aria-label="Dismiss"
                className="w-8 h-8 flex items-center justify-center rounded-full bg-text-base/5 hover:bg-text-base/10 transition-colors text-text-base/40 hover:text-text-base/70 cursor-pointer"
              >
                <re-icon icon="x" size="12" color="currentColor" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
