import IllustrationCard, { IllustrationCardSkeleton } from './IllustrationCard';
import { Highlight } from '../../components/ui/Highlight';
import { IconTooltipProvider } from '../../components/ui/IconTooltip';
import { IllustrationItem } from '../../lib/illustration-data';

interface IllustrationGridProps {
  items: IllustrationItem[];
  displaySize: number;
  ready: boolean;
  searchQuery: string;
  onSearchClear: () => void;
}

export default function IllustrationGrid({
  items,
  displaySize,
  ready,
  searchQuery,
  onSearchClear,
}: IllustrationGridProps) {
  if (!ready) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {Array.from({ length: 24 }).map((_, i) => (
          <IllustrationCardSkeleton key={i} size={displaySize} />
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <>
        <div role="status" aria-live="polite" className="sr-only">No illustrations found</div>
        <div className="flex flex-col items-center justify-center py-20 text-text-base/30">
          <svg className="w-12 h-12 text-text-base/20 mx-auto mb-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <p className="text-sm mt-4">No illustrations found for &quot;{searchQuery}&quot;</p>
          <button
            onClick={onSearchClear}
            className="mt-2 text-[#6C5CE7] text-sm hover:underline cursor-pointer"
          >
            Clear search
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      <div role="status" aria-live="polite" className="sr-only">
        Showing {items.length} illustrations
      </div>
      <IconTooltipProvider openDelay={500} closeDelay={200}>
        <Highlight
          className="absolute inset-0 rounded-2xl ring-1 ring-text-base/20 bg-text-base/7 pointer-events-none"
        >
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {items.map((item) => (
              <IllustrationCard key={item.slug} item={item} size={displaySize} />
            ))}
          </div>
        </Highlight>
      </IconTooltipProvider>
    </>
  );
}
