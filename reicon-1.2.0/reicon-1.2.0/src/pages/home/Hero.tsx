import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { HandHeart, Search3, Book3, Confetti2, Doc, Doc2, PenSparkle } from 'reicon-react';
import { SiJavascript, SiReact } from 'react-icons/si';
import { FaReact } from 'react-icons/fa';
import Background from '../../components/layout/Background';
import ClayButton from '../../components/ui/Button';
import { FigmaIcon, VscodeIcon, VueIcon, SvelteIcon, McpIcon, FlutterIcon } from './icons';

interface Props {
    theme?: string;
    toggleTheme?: () => void;
    heroCardRef: React.RefObject<HTMLDivElement | null>;
    stars?: number | null;
}

export default function Hero({ heroCardRef }: Props) {
    const [newIconCount, setNewIconCount] = useState(0);
    useEffect(() => {
        import('../../data/new-icons-added.json').then(m => {
            setNewIconCount((m.default as string[]).length);
        });
    }, []);

    return (
        <div className="relative min-h-screen flex items-start justify-center">
            <div
                ref={heroCardRef}
                className="sticky top-0 w-full h-screen overflow-hidden origin-top will-change-transform"
                style={{ transformOrigin: 'top center' }}
            >
                <Background />

                <div className="absolute inset-0 z-[2] flex flex-col justify-between pt-20 sm:pt-24 md:pt-28 pb-6 px-[18px] md:px-[40px]">
                    {/* Center content */}
                    <div className="my-auto text-center px-3 max-w-4xl mx-auto flex flex-col items-center justify-center">
                        <div className="flex items-center justify-center gap-2 mb-5 flex-wrap">
                            <a
                                href="https://github.com/dqev/reicon"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-[6px] bg-text-base/[0.04] hover:bg-text-base/10 backdrop-blur-lg rounded-full px-[14px] py-[6px] text-[12px] text-text-base/90 transition-colors"
                            >
                                <HandHeart size={16} color="currentColor" />
                                <span>Open Source Library</span>
                            </a>
                            <Link
                                to="/illustration"
                                className="inline-flex items-center gap-[6px] bg-text-base/[0.04] hover:bg-text-base/10 backdrop-blur-lg rounded-full px-[14px] py-[6px] text-[12px] text-text-base/90 transition-colors group"
                            >
                                <span className="w-[6px] h-[6px] bg-[#6C5CE7] rounded-full shrink-0 animate-pulse" />
                                <span>71,000+ Illustrations</span>
                                <Confetti2 size={15} color="currentColor" className="text-text-base/70 group-hover:scale-110 transition-transform" />
                            </Link>
                        </div>

                        <h1 className="font-serif text-[clamp(30px,6.2vw,76px)] font-semibold text-text-base leading-[1.08] tracking-[-0.02em] mb-4">
                            The icon library<br />designers actually want.
                        </h1>
                        <p className="text-[clamp(13px,1.45vw,18px)] text-text-base/60 leading-[1.65] max-w-[480px] mx-auto mb-7">
                            Open‑source SVGs &amp; illustrations for React, Vue, Svelte, Figma, and the web, drawn with care.
                        </p>
                        <div className="flex items-center justify-center gap-[10px] flex-wrap">
                            <ClayButton to="/icons" variant="primary">
                                <Search3 size={16} />
                                Browse Icons
                            </ClayButton>
                            <Link to="/illustration" className="bg-text-base/[0.04] hover:bg-text-base/10 text-text-base text-[14px] font-medium px-6 py-3 rounded-full backdrop-blur-lg flex items-center gap-[6px] transition-all duration-150 shadow-2xs">
                                <PenSparkle size={16} />
                                 Illustrations
                            </Link>
                            <ClayButton to="/docs" variant="primary">
                                <Doc size={16} color="currentColor" />
                                Docs Guide
                            </ClayButton>
                        </div>

                        {/* Integrations row */}
                        <div className="mt-8 md:mt-10 flex flex-col items-center justify-center gap-3 select-none">
                            <span className="text-[10px] tracking-[0.15em] text-text-base/35 dark:text-text-base/30 uppercase font-semibold">Integrations</span>
                            <div className="flex items-center justify-center gap-x-5 gap-y-3 sm:gap-7 flex-wrap max-w-[250px] sm:max-w-[600px] mx-auto">
                                <Link to="/docs/react" title="React" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <SiReact className="text-[#61DAFB]/70 hover:text-[#61DAFB] transition-colors" size={18} />
                                    <span className="hidden sm:inline">React</span>
                                </Link>
                                <Link to="/docs/vue" title="Vue 3" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <VueIcon size={17} />
                                    <span className="hidden sm:inline">Vue</span>
                                </Link>
                                <Link to="/docs/figma" title="Figma" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <FigmaIcon size={16} />
                                    <span className="hidden sm:inline">Figma</span>
                                </Link>
                                <Link to="/docs/svelte" title="Svelte" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <SvelteIcon size={16} />
                                    <span className="hidden sm:inline">Svelte</span>
                                </Link>
                                <Link to="/docs/react-native" title="React Native" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <FaReact className="text-[#61DAFB]/60 hover:text-[#61DAFB] transition-colors" size={17} />
                                    <span className="hidden sm:inline">React Native</span>
                                </Link>
                                <Link to="/docs/vanilla" title="Vanilla JavaScript" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <SiJavascript className="text-[#F7DF1E]/80 hover:text-[#F7DF1E] transition-colors" size={16} />
                                    <span className="hidden sm:inline">JavaScript</span>
                                </Link>
                                <Link to="/docs/vscode" title="VS Code" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <VscodeIcon size={17} />
                                    <span className="hidden sm:inline">VS Code</span>
                                </Link>
                                <Link to="/docs/flutter" title="Flutter" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <FlutterIcon size={14} />
                                    <span className="hidden sm:inline">Flutter</span>
                                </Link>
                                <Link to="/docs/mcp" title="MCP Server" className="flex items-center gap-1.5 text-text-base/50 hover:text-text-base/90 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer text-[13px] font-medium">
                                    <McpIcon size={16} />
                                    <span className="hidden sm:inline">MCP Server</span>
                                </Link>
                            </div>
                        </div>
                    </div>

                    {/* Bottom stats bar */}
                    <div className="flex items-end justify-center pb-2">
                        <div className="inline-flex items-center gap-5 sm:gap-8 px-6 sm:px-8 py-2.5">
                            {[{ num: '2,700+', label: 'Icons' }, { num: '2', label: 'Weights' }, { num: 'MIT', label: 'License' }].map((s, idx) => (
                                <div key={s.label} className="flex items-center gap-5 sm:gap-8">
                                    <div className="flex items-baseline gap-1.5 sm:gap-2">
                                        <span className="font-serif text-[18px] sm:text-[21px] font-semibold text-text-base leading-none">{s.num}</span>
                                        <span className="text-[12px] text-text-base/60 font-medium">{s.label}</span>
                                    </div>
                                    {idx < 2 && <div className="w-[1px] h-3.5 bg-white/15" />}
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
