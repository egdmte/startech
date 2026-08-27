interface IllustrationPaginationProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export default function IllustrationPagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
}: IllustrationPaginationProps) {
  if (totalPages <= 1) return null;

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // Generate page numbers with ellipses
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5;

    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (currentPage > 3) pages.push('...');

      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      for (let i = start; i <= end; i++) {
        if (i > 1 && i < totalPages) pages.push(i);
      }

      if (currentPage < totalPages - 2) pages.push('...');
      pages.push(totalPages);
    }

    return pages;
  };

  return (
    <div className="mt-8 pt-6 border-t border-text-base/8 flex flex-col sm:flex-row items-center justify-between gap-4">
      {/* Items count summary */}
      <div className="text-xs font-mono text-text-base/40">
        Showing <span className="text-text-base/80 font-medium">{startItem.toLocaleString()}–{endItem.toLocaleString()}</span> of{' '}
        <span className="text-text-base/80 font-medium">{totalItems.toLocaleString()}</span> illustrations
      </div>

      {/* Pagination controls */}
      <div className="flex items-center gap-1.5">
        {/* Previous Button */}
        <button
          type="button"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
            currentPage <= 1
              ? 'opacity-40 pointer-events-none border-text-base/6 text-text-base/30'
              : 'border-text-base/10 bg-text-base/4 hover:bg-text-base/8 text-text-base/70 hover:text-text-base'
          }`}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span>Previous</span>
        </button>

        {/* Number Buttons */}
        <div className="hidden sm:flex items-center gap-1">
          {getPageNumbers().map((p, idx) => {
            if (typeof p === 'string') {
              return (
                <span key={`ellipsis-${idx}`} className="px-2 text-xs font-mono text-text-base/30 select-none">
                  ...
                </span>
              );
            }

            const isActive = p === currentPage;
            return (
              <button
                key={p}
                type="button"
                onClick={() => onPageChange(p)}
                className={`w-8 h-8 rounded-lg text-xs font-mono font-medium transition-colors cursor-pointer ${
                  isActive
                    ? 'bg-[#6C5CE7] text-white shadow-sm'
                    : 'bg-text-base/3 hover:bg-text-base/8 text-text-base/60 hover:text-text-base border border-text-base/6'
                }`}
              >
                {p}
              </button>
            );
          })}
        </div>

        {/* Mobile current indicator */}
        <span className="sm:hidden text-xs font-mono text-text-base/50 px-2">
          {currentPage} / {totalPages}
        </span>

        {/* Next Button */}
        <button
          type="button"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
          className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
            currentPage >= totalPages
              ? 'opacity-40 pointer-events-none border-text-base/6 text-text-base/30'
              : 'border-text-base/10 bg-text-base/4 hover:bg-text-base/8 text-text-base/70 hover:text-text-base'
          }`}
        >
          <span>Next</span>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
    </div>
  );
}
