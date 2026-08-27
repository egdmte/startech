import { useState, useEffect, useMemo } from 'react';
import { motion } from 'motion/react';
import { Sparkles, PenSparkle } from 'reicon-react';
import { loadIconData } from '../../lib/icon-data';
import { waitForReicon } from '../../lib/reicon-loader';
import PlaygroundPreview from './playground/PlaygroundPreview';
import PlaygroundControls from './playground/PlaygroundControls';
import PlaygroundCode from './playground/PlaygroundCode';
import IllustrationPlayground from './playground/IllustrationPlayground';

const CONSISTENCY_COUNT = 80;
const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

export default function Playground({ theme }: { theme: string }) {
    const [mode, setMode] = useState<'icons' | 'illustrations'>('icons');

    const [iconNames, setIconNames] = useState<Record<string, string>>({});
    const [icons, setIcons] = useState<string[]>(['home']);
    const [selected, setSelected] = useState('home');
    const isLight = theme === 'light';
    const [color, setColor] = useState(isLight ? '#111111' : '#ffffff');
    const [size, setSize] = useState(32);
    const [weight, setWeight] = useState<'outline' | 'filled'>('outline');

    const allIconNames = useMemo(() => Object.keys(iconNames), [iconNames]);

    const initialShuffled = useMemo(() => {
        if (allIconNames.length === 0) return ['home'];
        const shuffled = [...allIconNames];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled.slice(0, CONSISTENCY_COUNT);
    }, [allIconNames]);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const data = await loadIconData();
                if (!active) return;
                setIconNames(data.iconNames);
            } catch {}
        })();
        return () => { active = false; };
    }, []);

    useEffect(() => {
        if (allIconNames.length === 0) return;
        setIcons(initialShuffled);
        setSelected(prev => initialShuffled.includes(prev) ? prev : initialShuffled[0]);
    }, [initialShuffled]);

    useEffect(() => {
        if (color === '#ffffff' && theme === 'light') setColor('#111111');
        else if (color === '#111111' && theme === 'dark') setColor('#ffffff');
    }, [theme, color]);

    useEffect(() => {
        if (allIconNames.length === 0) return;
        let active = true;
        (async () => {
            try {
                await waitForReicon();
                if (!active) return;
                const available = (window as any).Reicon?.icons as string[] | undefined;
                if (!available) return;
                const availableSet = new Set(available);
                const filtered = initialShuffled.filter((n) => availableSet.has(n));
                if (filtered.length < CONSISTENCY_COUNT && available.length > 0) {
                    const remaining = available.filter((n) => !filtered.includes(n));
                    const shuffled = [...remaining];
                    for (let i = shuffled.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
                    }
                    filtered.push(...shuffled.slice(0, CONSISTENCY_COUNT - filtered.length));
                }
                const finalIcons = filtered.slice(0, CONSISTENCY_COUNT);
                setIcons(finalIcons);
                if (!availableSet.has(selected) && finalIcons.length > 0) setSelected(finalIcons[0]);
            } catch {}
        })();
        return () => { active = false; };
    }, [initialShuffled, selected]);

    const displayColor = HEX_RE.test(color) ? color : (isLight ? '#111111' : '#ffffff');
    const pascalName = iconNames[selected] || selected;
    const reset = () => { setColor(isLight ? '#111111' : '#ffffff'); setSize(32); setWeight('outline'); };

    return (
        <section className="reveal max-w-[1160px] mx-auto px-5 md:px-10 py-13">
            <div className="text-center mb-8">
                <div className="text-[11px] font-semibold tracking-[0.1em] uppercase text-[#6C5CE7] mb-2">Playground</div>
                <h2 className="font-serif text-[clamp(26px,3.6vw,46px)] text-text-base leading-[1.15] tracking-[-0.02em] mb-3">Pick one. Make it yours.</h2>
                <p className="text-[15px] text-text-base/45 leading-[1.65] max-w-[490px] mx-auto mb-6">
                    Customize icons and handcrafted SVG illustrations in real-time.
                </p>

                {/* Top Toggle Switch */}
                <div className="relative inline-flex items-center p-1 rounded-full bg-text-base/[0.04] backdrop-blur-lg">
                    <button
                        type="button"
                        onClick={() => setMode('icons')}
                        className={`relative flex items-center gap-2 px-5 py-2 rounded-full text-[13px] font-sans font-medium transition-colors cursor-pointer select-none ${
                            mode === 'icons' ? 'text-bg-base font-semibold' : 'text-text-base/60 hover:text-text-base'
                        }`}
                    >
                        {mode === 'icons' && (
                            <motion.span
                                layoutId="pg-mode-bg"
                                className="absolute inset-0 bg-text-base rounded-full shadow-xs"
                                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            <Sparkles size={15} color="currentColor" />
                            <span>Icons</span>
                        </span>
                    </button>
                    <button
                        type="button"
                        onClick={() => setMode('illustrations')}
                        className={`relative flex items-center gap-2 px-5 py-2 rounded-full text-[13px] font-sans font-medium transition-colors cursor-pointer select-none ${
                            mode === 'illustrations' ? 'text-bg-base font-semibold' : 'text-text-base/60 hover:text-text-base'
                        }`}
                    >
                        {mode === 'illustrations' && (
                            <motion.span
                                layoutId="pg-mode-bg"
                                className="absolute inset-0 bg-text-base rounded-full shadow-xs"
                                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                            />
                        )}
                        <span className="relative z-10 flex items-center gap-2">
                            <PenSparkle size={15} color="currentColor" />
                            <span>Illustrations</span>
                        </span>
                    </button>
                </div>
            </div>

            {mode === 'icons' ? (
                <div className="bg-text-base/3 rounded-[14px] overflow-hidden">
                    <div className="grid lg:grid-cols-[300px_1fr]">
                        <div className="p-5 lg:p-6 lg:border-r border-b lg:border-b-0 border-text-base/6 flex flex-col gap-4">
                            <PlaygroundPreview
                                selected={selected}
                                size={size}
                                weight={weight}
                                displayColor={displayColor}
                                pascalName={pascalName}
                            />
                            <PlaygroundControls
                                color={color}
                                onChangeColor={setColor}
                                theme={theme}
                                size={size}
                                onChangeSize={setSize}
                                weight={weight}
                                onChangeWeight={setWeight}
                                onReset={reset}
                            />
                        </div>
                        <div className="p-3 sm:p-4">
                            <PlaygroundCode
                                selected={selected}
                                icons={icons}
                                pascalName={pascalName}
                                size={size}
                                weight={weight}
                                displayColor={displayColor}
                                onSelect={setSelected}
                                iconNamesData={iconNames}
                            />
                        </div>
                    </div>
                </div>
            ) : (
                <IllustrationPlayground theme={theme} />
            )}
        </section>
    );
}
