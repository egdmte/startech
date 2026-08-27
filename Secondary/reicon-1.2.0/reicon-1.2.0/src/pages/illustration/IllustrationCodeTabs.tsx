import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { FaReact } from 'react-icons/fa';
import { IoLogoJavascript } from 'react-icons/io5';
import { VueLogo } from '../icon/Snippets';
import { fetchIllustrationSvgCode } from '../../lib/illustration-data';

interface IllustrationCodeTabsProps {
  slug: string;
  title: string;
  cdnUrl: string;
  svgCode: string;
  copiedField: string | null;
  onCopy: (text: string, field: string) => void;
}

// Tokenize & highlight code syntax matching IconDetail Snippets 100%
function HighlightedCode({ code }: { code: string }) {
  if (!code) return null;

  // Split tokens by quoted strings, XML tags/brackets, attributes
  const tokens = code.split(/("[^"]*"|'[^']*'|<\/?[a-zA-Z0-9_-]+|\/>|>|<|\{|\})/g);

  return (
    <>
      {tokens.map((token, i) => {
        if (!token) return null;

        // Quoted String Values -> Green (#98c379)
        if (/^["'].*["']$/.test(token)) {
          return <span key={i} className="text-[#98c379]">{token}</span>;
        }
        // XML / Tag Name -> Coral (#e06c75)
        if (/^<\/?[a-zA-Z0-9_-]+/i.test(token)) {
          return <span key={i} className="text-[#e06c75]">{token}</span>;
        }
        // Tag brackets -> Coral (#e06c75)
        if (token === '>' || token === '/>' || token === '<') {
          return <span key={i} className="text-[#e06c75]">{token}</span>;
        }
        // JSX Braces -> Blue (#61afef)
        if (token === '{' || token === '}') {
          return <span key={i} className="text-[#61afef]">{token}</span>;
        }
        // Attribute names -> Orange (#d19a66)
        if (token.includes('=')) {
          const parts = token.split(/([a-zA-Z0-9_-]+=)/g);
          return (
            <span key={i}>
              {parts.map((p, idx) => {
                if (p.endsWith('=')) {
                  return (
                    <span key={idx}>
                      <span className="text-[#d19a66]">{p.slice(0, -1)}</span>
                      <span className="text-text-base/40">=</span>
                    </span>
                  );
                }
                return <span key={idx} className="text-text-base/80">{p}</span>;
              })}
            </span>
          );
        }

        return <span key={i} className="text-text-base/80">{token}</span>;
      })}
    </>
  );
}

export default function IllustrationCodeTabs({
  slug,
  title,
  cdnUrl,
  svgCode,
  copiedField,
  onCopy,
}: IllustrationCodeTabsProps) {
  const [activeTab, setActiveTab] = useState<'react' | 'vue' | 'html' | 'svg'>('react');
  const [fetchedSvg, setFetchedSvg] = useState(svgCode);

  useEffect(() => {
    if (svgCode) {
      setFetchedSvg(svgCode);
      return;
    }
    if (!slug) return;
    let cancelled = false;

    fetchIllustrationSvgCode(slug).then((code) => {
      if (!cancelled && code) {
        setFetchedSvg(code);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [slug, svgCode]);

  const reactCode = `<img\n  src="${cdnUrl}"\n  alt="${title}"\n  width={180}\n  height={180}\n/>`;
  const vueCode = `<template>\n  <img src="${cdnUrl}" alt="${title}" width="180" height="180" />\n</template>`;
  const htmlCode = `<img src="${cdnUrl}" alt="${title}" width="180" height="180" />`;
  const formattedSvg = fetchedSvg || `<!-- Loading SVG source code... -->`;

  const tabs = [
    {
      id: 'react',
      label: 'React',
      icon: <FaReact size={14} className="text-[#61DAFB]" />,
      raw: reactCode,
    },
    {
      id: 'vue',
      label: 'Vue',
      icon: <VueLogo />,
      raw: vueCode,
    },
    {
      id: 'html',
      label: 'HTML',
      icon: <IoLogoJavascript size={14} className="text-[#F7DF1E]" />,
      raw: htmlCode,
    },
    {
      id: 'svg',
      label: 'SVG Code',
      icon: <img src="/readme-assets/svg.svg" alt="SVG" className="w-3.5 h-3.5 shrink-0 object-contain" />,
      raw: formattedSvg,
    },
  ] as const;

  const currentTabObj = tabs.find((t) => t.id === activeTab) || tabs[0];
  const isCopied =
    copiedField === activeTab ||
    copiedField === `code-${activeTab}` ||
    (activeTab === 'svg' && (copiedField === 'svg' || copiedField === 'code-svg'));

  return (
    <figure className="relative rounded-xl bg-text-base/3 border border-text-base/8 text-sm max-w-full overflow-hidden">
      {/* Code Header Tabs matching CodeTabs.tsx */}
      <div className="flex items-center w-full h-11 pl-3 border-b border-text-base/8 overflow-x-auto scrollbar-none">
        <div className="flex items-center h-full gap-1 shrink-0">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as any)}
                className={`relative flex items-center gap-1.5 h-full px-2.5 text-[13px] font-medium whitespace-nowrap transition-colors cursor-pointer ${
                  isActive ? 'text-text-base' : 'text-text-base/40 hover:text-text-base/70'
                }`}
              >
                <span className={isActive ? '' : 'opacity-50'}>{tab.icon}</span>
                {tab.label}
                {isActive && (
                  <motion.span
                    layoutId="illustration-tab-underline"
                    className="absolute bottom-0 left-2 right-2 h-[2px] rounded-t-full bg-[#6C5CE7]"
                    style={{ boxShadow: '0 0 8px rgba(108,92,231,0.45)' }}
                  />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Code Box Container matching CodeTabs.tsx 100% */}
      <div className="px-1.5 py-1.5 overflow-x-auto">
        <div className="bg-bg-base rounded-md min-h-[92px] max-h-[140px] relative overflow-hidden flex flex-col">
          {/* Copy Button matching IconDetail CodeTabs 100% */}
          <button
            type="button"
            onClick={() => onCopy(currentTabObj.raw, activeTab)}
            aria-label="Copy code"
            className="absolute top-1.5 right-1.5 z-10 inline-flex items-center justify-center w-7 h-7 rounded-md bg-bg-base text-text-base/30 hover:text-text-base hover:bg-text-base/8 transition-colors cursor-pointer"
          >
            {isCopied ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
              </svg>
            )}
          </button>

          {/* Pre Box with Horizontal & Vertical Scroll matching IconDetail */}
          <AnimatePresence mode="wait">
            <motion.pre
              key={activeTab}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18 }}
              className="p-4 text-[13px] font-mono leading-[1.7] overflow-x-auto overflow-y-auto max-h-[135px] whitespace-pre focus-visible:outline-none text-text-base select-text"
            >
              <HighlightedCode code={currentTabObj.raw} />
            </motion.pre>
          </AnimatePresence>
        </div>
      </div>
    </figure>
  );
}
