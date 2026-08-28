import { memo, useState } from 'react';
import { Link } from 'react-router-dom';
import { HighlightItem } from '../../components/ui/Highlight';
import { IconTooltipTrigger } from '../../components/ui/IconTooltip';
import { IllustrationItem, getIllustrationUrl } from '../../lib/illustration-data';
import { useTheme } from '../../components/layout/ThemeContext';

interface IllustrationCardProps {
  item: IllustrationItem;
  size?: number;
}

function IllustrationCard({ item, size = 100 }: IllustrationCardProps) {
  const { theme } = useTheme();
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const url = getIllustrationUrl(item.slug);

  return (
    <HighlightItem value={`${item.slug}-illustration`}>
      <IconTooltipTrigger label={item.name} side="bottom" sideOffset={14}>
        <Link
          to={`/illustration/${item.slug}`}
          className="cv-auto group relative flex items-center justify-center aspect-square bg-text-base/3 border border-text-base/6 hover:border-text-base/20 rounded-2xl transition-all cursor-pointer p-4 overflow-hidden"
          title={item.name}
        >
          {/* Skeleton Placeholder - Always 100% Dead-Center */}
          {!loaded && !error && (
            <div className="absolute inset-0 flex items-center justify-center p-4 pointer-events-none">
              <div
                className="rounded-xl bg-text-base/7 animate-pulse"
                style={{ width: size, height: size }}
              />
            </div>
          )}

          {!error && (
            <img
              src={url}
              alt={item.title || item.name}
              loading="lazy"
              onLoad={() => setLoaded(true)}
              onError={() => setError(true)}
              className={`object-contain transition-all duration-200 ${
                theme === 'dark' ? 'invert brightness-150' : ''
              } ${
                loaded
                  ? 'opacity-85 group-hover:opacity-100 group-hover:scale-105 transition-transform duration-200'
                  : 'opacity-0'
              }`}
              style={{ width: size, height: size }}
            />
          )}

          {error && (
            <div className="text-[11px] text-text-base/40 text-center select-none font-mono px-1">
              {item.name}
            </div>
          )}
        </Link>
      </IconTooltipTrigger>
    </HighlightItem>
  );
}

export default memo(IllustrationCard);

export const IllustrationCardSkeleton = memo(function IllustrationCardSkeleton({ size = 100 }: { size?: number }) {
  return (
    <div
      className="cv-auto relative flex items-center justify-center aspect-square bg-text-base/3 border border-text-base/6 rounded-2xl p-4 overflow-hidden"
      aria-hidden="true"
    >
      <div
        className="rounded-xl bg-text-base/7 animate-pulse"
        style={{ width: size, height: size }}
      />
    </div>
  );
});
