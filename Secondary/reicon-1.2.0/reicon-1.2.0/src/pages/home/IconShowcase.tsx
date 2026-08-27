const ORBIT_INNER = ['home', 'star', 'heart', 'search', 'settings', 'bell'];
const ORBIT_MIDDLE = ['camera', 'cloud', 'lightning', 'palette', 'code', 'eye', 'bookmark', 'gift'];
const ORBIT_OUTER = ['compass', 'mic', 'wifi', 'pen', 'folder', 'lamp', 'clock', 'calendar', 'flag', 'rocket'];

function OrbitRing({ icons, className, counterClassName, size }: {
    icons: string[];
    className: string;
    counterClassName: string;
    size: string;
}) {
    return (
        <div className="absolute inset-0 flex items-center justify-center">
            <div className={`relative ${size} aspect-square ${className}`}>
                {icons.map((name, i) => {
                    const rad = ((360 / icons.length) * i * Math.PI) / 180;
                    const x = 50 + 50 * Math.cos(rad);
                    const y = 50 + 50 * Math.sin(rad);
                    return (
                        <div key={name} className="absolute -translate-x-1/2 -translate-y-1/2" style={{ top: `${y}%`, left: `${x}%` }}>
                            <div className={`w-7 h-7 sm:w-9 sm:h-9 md:w-10 md:h-10 rounded-lg sm:rounded-xl bg-text-base/4 border border-text-base/6 flex items-center justify-center shadow-2xs ${counterClassName}`}>
                                <re-icon icon={name} size={14} color="currentColor" className="text-text-base/60 sm:hidden" weight="outline" />
                                <re-icon icon={name} size={18} color="currentColor" className="text-text-base/60 hidden sm:block" weight="outline" />
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function IconShowcase({ theme }: { theme: string }) {
    return (
        <section className="reveal max-w-[1160px] mx-auto px-4 sm:px-6 md:px-10 py-10 md:py-16 overflow-hidden">
            <div className="text-center mb-8 sm:mb-12 px-4">
                <div className="text-[11px] font-semibold tracking-[0.1em] uppercase text-[#6C5CE7] mb-2">Icon Library</div>
                <h2 className="font-serif text-[clamp(26px,3.6vw,46px)] text-text-base leading-[1.15] tracking-[-0.02em] mb-3">2700+ icons. Every one handcrafted.</h2>
                <p className="text-[14px] sm:text-[15px] text-text-base/45 leading-[1.65] max-w-[490px] mx-auto">
                    From UI essentials to expressive details — find exactly what you need.
                </p>
            </div>

            <div className="relative w-full aspect-square max-w-[540px] mx-auto [mask-image:radial-gradient(circle,black_45%,transparent_82%)]">
                {/* Center logo */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
                    <div className="w-12 h-12 sm:w-16 sm:h-16 md:w-20 md:h-20 flex items-center justify-center bg-text-base/[0.04] backdrop-blur-md rounded-full border border-text-base/10 shadow-xs">
                        <img src={theme === 'dark' ? '/icon-light.webp' : '/icon-dark.webp'} alt="Reicon" loading="lazy" className="w-6 h-6 sm:w-8 sm:h-8 md:w-10 md:h-10" />
                    </div>
                </div>

                {/* Ring guides */}
                {['38%', '66%', '94%'].map((w, i) => (
                    <div key={i} className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="aspect-square rounded-full border border-[#6C5CE7]/[0.14]" style={{ width: w, opacity: 1 - i * 0.02 }} />
                    </div>
                ))}

                <OrbitRing icons={ORBIT_INNER} size="w-[38%]" className="animate-orbit-slow" counterClassName="animate-orbit-counter-slow" />
                <OrbitRing icons={ORBIT_MIDDLE} size="w-[66%]" className="animate-orbit-mid" counterClassName="animate-orbit-counter-mid" />
                <OrbitRing icons={ORBIT_OUTER} size="w-[94%]" className="animate-orbit-fast" counterClassName="animate-orbit-counter-fast" />
            </div>
        </section>
    );
}
