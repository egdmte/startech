import { useState, useEffect, useMemo } from 'react';
import { HexColorPicker } from 'react-colorful';
import { Restart } from 'reicon-react';
import {
  IllustrationItem,
  loadFeaturedIllustrations,
  getIllustrationUrl,
  fetchIllustrationSvgCode,
} from '../../../lib/illustration-data';

const GRID_COUNT = 80;
const HEX_RE = /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

const CATEGORIES = [
  { id: 'all', label: 'All' },
  { id: 'object', label: 'Objects' },
  { id: 'people', label: 'People' },
  { id: 'scene', label: 'Scenes' },
  { id: 'mark', label: 'Marks' },
];

function ColorPicker({
  color,
  onChange,
  theme,
}: {
  color: string;
  onChange: (c: string) => void;
  theme: string;
}) {
  const isLight = theme === 'light';
  const presets = isLight
    ? ['#111111', '#6C5CE7', '#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#ec4899', '#06b6d4']
    : ['#ffffff', '#6C5CE7', '#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#ec4899', '#06b6d4'];
  const safeColor = HEX_RE.test(color) ? color : isLight ? '#111111' : '#ffffff';
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <label className="text-[13px] text-text-base/50 mb-2 block">Color</label>
      <div className="grid grid-cols-8 gap-1.5 mb-2">
        {presets.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => onChange(c)}
            aria-label={`Set color ${c}`}
            title={c}
            className={`w-full aspect-square rounded-md transition-transform hover:scale-110 cursor-pointer ${
              color.toLowerCase() === c.toLowerCase()
                ? 'ring-2 ring-text-base/70 ring-offset-2 ring-offset-bg-base'
                : 'border border-text-base/15'
            }`}
            style={{ backgroundColor: c }}
          />
        ))}
      </div>
      <div className="flex items-center gap-1.5 relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Pick a custom color"
          className="w-9 h-9 shrink-0 rounded-lg border border-text-base/10 cursor-pointer bg-transparent flex items-center justify-center hover:bg-text-base/5"
        >
          <span className="w-5 h-5 rounded-md border border-text-base/20 shadow-sm" style={{ backgroundColor: safeColor }} />
        </button>
        <input
          type="text"
          value={color}
          onChange={(e) => onChange(e.target.value)}
          spellCheck={false}
          className="flex-1 min-w-0 h-9 bg-text-base/3 border border-text-base/10 rounded-lg px-2.5 font-mono text-xs text-text-base focus:outline-none focus:border-text-base/30"
        />
        {isOpen && (
          <div className="absolute left-0 bottom-11 z-50 p-3 bg-dropdown-bg border border-text-base/15 rounded-xl shadow-xl">
            <HexColorPicker color={safeColor} onChange={onChange} />
          </div>
        )}
      </div>
    </div>
  );
}

// Inline SVG renderer component that color-tints using fill=currentColor
function IllustrationSvgItem({
  slug,
  size,
  color,
  fallbackUrl,
  className = '',
}: {
  slug: string;
  size: number;
  color: string;
  fallbackUrl: string;
  className?: string;
}) {
  const [svgContent, setSvgContent] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchIllustrationSvgCode(slug).then((code) => {
      if (!cancelled && code && code.includes('<svg')) {
        // Strip height/width from svg root tag to allow clean size overriding
        const cleanSvg = code.replace(/<svg\b[^>]*>/i, (match) => {
          return match
            .replace(/\bwidth="[^"]*"/gi, '')
            .replace(/\bheight="[^"]*"/gi, '');
        });
        setSvgContent(cleanSvg);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (svgContent) {
    return (
      <div
        className={`flex items-center justify-center transition-colors duration-150 ${className}`}
        style={{ width: size, height: size, color }}
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        WebkitMaskImage: `url(${fallbackUrl})`,
        maskImage: `url(${fallbackUrl})`,
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
        transition: 'background-color 0.15s ease',
      }}
      className={className}
    />
  );
}

export default function IllustrationPlayground({ theme }: { theme: string }) {
  const isLight = theme === 'light';
  const [allItems, setAllItems] = useState<IllustrationItem[]>([]);
  const [activeCategory, setActiveCategory] = useState('all');
  const [selectedSlug, setSelectedSlug] = useState('3d-printer');
  const [size, setSize] = useState(90);
  const [color, setColor] = useState(isLight ? '#111111' : '#ffffff');

  // Load featured items (fixed deterministic order)
  useEffect(() => {
    loadFeaturedIllustrations().then((data) => {
      setAllItems(data);
      if (data.length > 0) {
        setSelectedSlug(data[0].slug);
      }
    });
  }, []);

  useEffect(() => {
    if (color === '#ffffff' && theme === 'light') setColor('#111111');
    else if (color === '#111111' && theme === 'dark') setColor('#ffffff');
  }, [theme]);

  // Filter items predictably by category
  const displayItems = useMemo(() => {
    if (activeCategory === 'all') return allItems.slice(0, GRID_COUNT);
    return allItems.filter((i) => i.category === activeCategory).slice(0, GRID_COUNT);
  }, [allItems, activeCategory]);

  // Ensure selected slug is valid in displayItems if category changes
  useEffect(() => {
    if (displayItems.length === 0) return;
    if (!displayItems.find((i) => i.slug === selectedSlug)) {
      setSelectedSlug(displayItems[0].slug);
    }
    // Batch pre-fetch displayItems SVGs to populate cache
    displayItems.forEach((item) => {
      fetchIllustrationSvgCode(item.slug);
    });
  }, [displayItems, selectedSlug]);

  const selectedItem = allItems.find((i) => i.slug === selectedSlug) || {
    slug: selectedSlug,
    title: selectedSlug.replace(/-/g, ' '),
    name: selectedSlug.replace(/-/g, ' '),
    category: 'object',
    subcategory: 'misc',
  };

  const cdnUrl = getIllustrationUrl(selectedSlug);
  const displayColor = HEX_RE.test(color) ? color : isLight ? '#111111' : '#ffffff';

  const reset = () => {
    setSize(90);
    setColor(isLight ? '#111111' : '#ffffff');
    setActiveCategory('all');
  };

  return (
    <div className="bg-text-base/3 rounded-[14px] overflow-hidden">
      <div className="grid lg:grid-cols-[300px_1fr]">
        {/* Left Column: Preview & Controls */}
        <div className="p-5 lg:p-6 lg:border-r border-b lg:border-b-0 border-text-base/6 flex flex-col gap-4">
          {/* Preview Box Matching Icon Detail Preview 100% */}
          <div className="flex flex-col">
            <div className="relative w-full aspect-square max-w-[220px] mx-auto bg-text-base/2 border border-text-base/8 rounded-2xl flex items-center justify-center overflow-hidden">
              <div
                className="absolute inset-0 pointer-events-none"
                style={{
                  backgroundImage:
                    'linear-gradient(to right, var(--border-muted) 1px, transparent 1px), linear-gradient(to bottom, var(--border-muted) 1px, transparent 1px)',
                  backgroundSize: '20px 20px',
                }}
              />
              <span className="absolute bottom-2.5 right-3 text-[8px] font-mono text-text-base/35 tabular-nums select-none">
                {size}px
              </span>

              {/* Tinted Illustration SVG Preview */}
              <IllustrationSvgItem
                slug={selectedSlug}
                size={size}
                color={displayColor}
                fallbackUrl={cdnUrl}
              />
            </div>

            <div className="flex items-center justify-start mt-3">
              <span className="text-[15px] font-serif font-semibold text-text-base truncate capitalize">
                {selectedItem.name}
              </span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex flex-col gap-4 pt-2 border-t border-text-base/6">
            {/* Color Accent Picker */}
            <ColorPicker color={color} onChange={setColor} theme={theme} />

            {/* Category Filter Pills */}
            <div>
              <label className="text-[13px] text-text-base/50 mb-2 block">Category</label>
              <div className="flex items-center gap-1 overflow-x-auto scrollbar-none pb-1">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setActiveCategory(cat.id)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all cursor-pointer shrink-0 ${
                      activeCategory === cat.id
                        ? 'bg-[#6C5CE7] text-white font-semibold'
                        : 'bg-text-base/4 text-text-base/60 hover:text-text-base'
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Size Slider */}
            <div>
              <div className="flex items-center justify-between text-[13px] text-text-base/50 mb-2">
                <span>Size</span>
                <span className="font-mono text-[12px]">{size}px</span>
              </div>
              <input
                type="range"
                min="60"
                max="180"
                step="10"
                value={size}
                onChange={(e) => setSize(Number(e.target.value))}
                className="w-full accent-[#6C5CE7] cursor-pointer"
              />
            </div>

            {/* Reset Button */}
            <div className="pt-2 border-t border-text-base/6">
              <button
                type="button"
                onClick={reset}
                className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-text-base/4 hover:bg-text-base/8 text-text-base/60 hover:text-text-base text-[12px] font-medium transition-colors cursor-pointer"
              >
                <Restart size={14} />
                <span>Reset Settings</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Illustrations Grid */}
        <div className="p-3 sm:p-4 flex flex-col gap-4">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] uppercase tracking-[0.08em] text-text-base/30 font-semibold">
                Illustrations ({displayItems.length})
              </span>
            </div>

            <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 border-l border-t border-text-base/4">
              {displayItems.map((item) => {
                const url = getIllustrationUrl(item.slug);
                const isSelected = item.slug === selectedSlug;
                return (
                  <button
                    key={item.slug}
                    type="button"
                    onClick={() => setSelectedSlug(item.slug)}
                    title={item.name}
                    className={`aspect-square flex items-center justify-center p-1.5 border-r border-b transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#6C5CE7]/15 border-[#6C5CE7]/30'
                        : 'border-text-base/4 hover:bg-text-base/3'
                    }`}
                  >
                    <IllustrationSvgItem
                      slug={item.slug}
                      size={36}
                      color={isSelected ? displayColor : 'var(--text-base)'}
                      fallbackUrl={url}
                      className="opacity-75 hover:opacity-100"
                    />
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
