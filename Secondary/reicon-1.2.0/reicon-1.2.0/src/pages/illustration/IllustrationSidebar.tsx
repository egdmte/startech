import React, { useEffect, useState } from 'react';
import { IllustrationCategoriesMeta, loadIllustrationCategories } from '../../lib/illustration-data';

interface IllustrationSidebarProps {
  activeCategory: string;
  activeSubcategory: string;
  onCategoryChange: (category: string, subcategory?: string) => void;
  activeSize: string;
  onSizeChange: (size: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

const SIZE_OPTIONS = ['64', '80', '100', '120'];

function IllustrationSidebar({
  activeCategory,
  activeSubcategory,
  onCategoryChange,
  activeSize,
  onSizeChange,
  isOpen = false,
  onClose,
}: IllustrationSidebarProps) {
  const [meta, setMeta] = useState<IllustrationCategoriesMeta | null>(null);
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});

  useEffect(() => {
    loadIllustrationCategories().then((data) => {
      setMeta(data);
      if (activeCategory && activeCategory !== 'all') {
        setExpandedMap((prev) => ({ ...prev, [activeCategory]: true }));
      }
    });
  }, []);

  useEffect(() => {
    if (activeCategory && activeCategory !== 'all') {
      setExpandedMap((prev) => ({ ...prev, [activeCategory]: true }));
    }
  }, [activeCategory]);

  const toggleCategoryExpand = (catName: string) => {
    setExpandedMap((prev) => ({
      ...prev,
      [catName]: !prev[catName],
    }));
  };

  const fmt = (str: string) =>
    str
      .replace(/-/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

  function renderNavItem(
    id: string,
    label: string,
    isActive: boolean,
    count?: number,
    onClickHandler?: () => void
  ) {
    return (
      <button
        key={id}
        type="button"
        onClick={() => {
          if (onClickHandler) {
            onClickHandler();
          } else if (id.startsWith('size-')) {
            onSizeChange(id.replace('size-', ''));
          }
          if (onClose) onClose();
        }}
        className={`sidebar-item ${isActive ? 'active' : ''}`}
      >
        <span className="truncate">{label}</span>
        {count !== undefined && (
          <span className="text-[10px] font-mono opacity-50 ml-2">
            {count.toLocaleString()}
          </span>
        )}
      </button>
    );
  }

  const sidebarContent = (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      {/* Overview */}
      <div className="reicon-sidebar-group">
        <div className="sidebar-section-header">
          <div className="sidebar-icon-box">
            <re-icon icon="star" size="13" />
          </div>
          <span>Overview</span>
        </div>
        <div className="sidebar-items-container">
          <div className="sidebar-section-line" style={{ background: 'linear-gradient(to bottom, var(--border-base) 0%, var(--border-base) 60%, transparent 100%)' }} />
          {renderNavItem(
            'cat-all',
            'All Illustrations',
            activeCategory === 'all',
            meta?.total_icons,
            () => onCategoryChange('all', 'all')
          )}
        </div>
      </div>

      {/* Sizing */}
      <div className="reicon-sidebar-group">
        <div className="sidebar-section-header">
          <div className="sidebar-icon-box">
            <re-icon icon="size" size="13" />
          </div>
          <span>Sizing</span>
        </div>
        <div className="sidebar-items-container">
          <div className="sidebar-section-line" style={{ background: 'linear-gradient(to bottom, var(--border-base) 0%, var(--border-base) 60%, transparent 100%)' }} />
          {SIZE_OPTIONS.map((size) =>
            renderNavItem(`size-${size}`, `${size}px Grid`, activeSize === size)
          )}
        </div>
      </div>

      {/* Categories */}
      <div className="reicon-sidebar-group">
        <div className="sidebar-section-header">
          <div className="sidebar-icon-box">
            <re-icon icon="category2" size="13" />
          </div>
          <span>Categories</span>
        </div>
        <div className="sidebar-items-container">
          <div className="sidebar-section-line" style={{ background: 'linear-gradient(to bottom, var(--border-base) 0%, var(--border-base) 60%, transparent 100%)' }} />

          {meta?.categories.map((cat) => {
            const isCatActive = activeCategory === cat.name;
            const isExpanded = Boolean(expandedMap[cat.name]);

            return (
              <div key={cat.name} className="flex flex-col">
                <button
                  type="button"
                  onClick={() => {
                    onCategoryChange(cat.name, 'all');
                    toggleCategoryExpand(cat.name);
                    if (onClose && (!cat.subcategories || cat.subcategories.length === 0)) {
                      onClose();
                    }
                  }}
                  className={`sidebar-item ${isCatActive && activeSubcategory === 'all' ? 'active' : ''}`}
                >
                  <span className="truncate flex items-center gap-1.5 min-w-0">
                    <span>{fmt(cat.name)}</span>
                  </span>
                  <span className="flex items-center gap-1.5 ml-2 shrink-0">
                    <span className="text-[10px] font-mono opacity-50">
                      {cat.count.toLocaleString()}
                    </span>
                    {cat.subcategories && cat.subcategories.length > 0 && (
                      <span
                        className={`inline-flex items-center justify-center transition-transform duration-200 opacity-60 ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                      >
                        <re-icon icon="chevron-down" size="10" color="currentColor" />
                      </span>
                    )}
                  </span>
                </button>

                {isExpanded && cat.subcategories && cat.subcategories.length > 0 && (
                  <div className="flex flex-col">
                    {cat.subcategories.map((sub) => {
                      const isSubActive = isCatActive && activeSubcategory === sub.name;
                      return (
                        <button
                          key={sub.name}
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onCategoryChange(cat.name, sub.name);
                            if (onClose) onClose();
                          }}
                          className={`sidebar-item ${isSubActive ? 'active' : ''}`}
                          style={{ paddingLeft: '2.5rem', fontSize: '12px' }}
                        >
                          <span className="truncate">{fmt(sub.name)}</span>
                          <span className="text-[9.5px] font-mono opacity-40 ml-1">
                            {sub.count.toLocaleString()}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <style>{`
        #nd-sidebar-illustration {
          width: 13.5rem;
          height: calc(100vh - 3.5rem);
          position: sticky;
          top: 3.5rem;
          overflow-y: auto;
          padding: 1.25rem 0.5rem 2rem 0.75rem;
          margin-left: 0.5rem;
          z-index: 30;
          background-color: var(--bg-base);
          scrollbar-width: none;
          flex-shrink: 0;
        }
        #nd-sidebar-illustration::-webkit-scrollbar { display: none; }

        .reicon-sidebar-group {
          position: relative;
          display: flex;
          flex-direction: column;
          margin-top: 1.25rem;
        }
        .reicon-sidebar-group:first-child {
          margin-top: 0;
        }
        .sidebar-section-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.375rem;
          font-size: 11px;
          font-weight: 600;
          color: var(--text-more-muted);
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
        .sidebar-icon-box {
          width: 1.25rem;
          height: 1.25rem;
          border-radius: 5px;
          background-color: var(--surface-hover);
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
          flex-shrink: 0;
        }
        .sidebar-items-container {
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 0.125rem;
        }
        .sidebar-section-line {
          position: absolute;
          left: 0.625rem;
          top: -0.375rem;
          bottom: 0.5rem;
          width: 1px;
          transform: translateX(-50%);
          pointer-events: none;
        }
        .sidebar-item {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.375rem 0.5rem 0.375rem 1.625rem;
          border-radius: 8px;
          cursor: pointer;
          background: transparent;
          min-height: 2rem;
          font-size: 13px;
          color: var(--text-base);
          transition: color 0.15s ease;
          user-select: none;
          border: 0;
          width: 100%;
          text-align: left;
        }
        .sidebar-item:hover {
          color: var(--text-muted);
          background: transparent;
        }
        .sidebar-item.active {
          color: #6C5CE7;
          font-weight: 600;
          background: transparent;
        }

        .reicon-sidebar-backdrop {
          position: fixed; inset: 0; z-index: 40;
          background: var(--shadow-color); backdrop-filter: blur(6px);
        }
        .reicon-sidebar-drawer {
          position: fixed; top: 0; left: 0; bottom: 0; z-index: 50; width: 16rem;
          background: var(--bg-base); border-right: 1px solid var(--border-muted);
          padding: 1rem; display: flex; flex-direction: column; gap: 0.5rem;
          overflow-y: auto; transform: translateX(-100%);
          transition: transform 0.28s cubic-bezier(0.25,0.46,0.45,0.94);
          scrollbar-width: none;
        }
        .reicon-sidebar-drawer::-webkit-scrollbar { display: none; }
        .reicon-sidebar-drawer.is-open { transform: translateX(0); }
        .reicon-sidebar-drawer-head {
          display: flex; align-items: center; justify-content: space-between;
          padding-bottom: 0.75rem; margin-bottom: 0.25rem;
          border-bottom: 1px solid var(--border-muted);
        }
        .reicon-sidebar-close {
          display: inline-flex; align-items: center; justify-content: center;
          width: 28px; height: 28px; border-radius: 8px;
          background: var(--surface-base); border: 1px solid var(--border-base);
          color: var(--text-muted); cursor: pointer;
          transition: color 0.15s, background-color 0.15s;
        }
        .reicon-sidebar-close:hover { background: var(--surface-hover); color: var(--text-base); }
        @media(min-width: 1024px) { .reicon-sidebar-backdrop,.reicon-sidebar-drawer{display:none;} }
        @media(max-width: 1023.98px) { #nd-sidebar-illustration{display:none;} }
      `}</style>

      <aside id="nd-sidebar-illustration" className="hidden lg:flex" data-lenis-prevent>
        {sidebarContent}
      </aside>

      {isOpen && <div onClick={onClose} className="reicon-sidebar-backdrop" aria-hidden />}

      <aside className={`reicon-sidebar-drawer ${isOpen ? 'is-open' : ''}`} data-lenis-prevent>
        <div className="reicon-sidebar-drawer-head">
          <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-base)' }}>Filters</span>
          {onClose && (
            <button onClick={onClose} className="reicon-sidebar-close" aria-label="Close sidebar">
              <re-icon icon="x" size="16" color="currentColor" style={{ color: 'var(--text-muted)' }} />
            </button>
          )}
        </div>
        {sidebarContent}
      </aside>
    </>
  );
}

export default React.memo(IllustrationSidebar);
