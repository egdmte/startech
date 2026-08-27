/** Scoped CSS string for the Docs page sidebars. Injected via <style> tag. */
export const docsSidebarStyles = `
  #docs-sidebar {
    width: 14rem;
    height: calc(100vh - 3.5rem);
    position: sticky;
    top: 3.5rem;
    overflow-y: auto;
    padding: 1.25rem 0.75rem 2rem 1.5rem;
    margin-left: 1.5rem;
    z-index: 30;
    background-color: var(--bg-base);
    scrollbar-width: none;
    flex-shrink: 0;
    transition: background-color 0.3s ease;
  }
  #docs-sidebar::-webkit-scrollbar { display: none; }

  /* ── LEFT SIDEBAR GROUPS & CONNECTED LINE ── */
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
    width: 1.25rem; /* 20px */
    height: 1.25rem; /* 20px */
    border-radius: 5px;
    background-color: var(--surface-hover);
    border: none;
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
    left: 0.625rem; /* 10px = center of 20px icon box */
    top: -0.375rem;
    bottom: 0.5rem;
    width: 1px;
    background-color: var(--border-base);
    transform: translateX(-50%);
    pointer-events: none;
  }

  .sidebar-item {
    position: relative;
    display: flex;
    align-items: center;
    padding: 0.375rem 0.5rem 0.375rem 1.625rem;
    border-radius: 8px;
    cursor: pointer;
    background: transparent;
    min-height: 2rem;
    font-size: 13px;
    color: var(--text-muted);
    transition: color 0.15s ease;
    user-select: none;
    border: 0;
    width: 100%;
    text-align: left;
  }
  .sidebar-item:hover {
    color: var(--text-hover);
    background: transparent;
  }
  .sidebar-item.active {
    color: var(--text-base);
    font-weight: 600;
    background: transparent;
  }

  .sidebar-item-active-bar {
    position: absolute;
    left: 0.625rem;
    top: 22%;
    bottom: 22%;
    width: 3px;
    border-radius: 9999px;
    background-color: #6C5CE7;
    box-shadow: 0 0 8px rgba(108, 92, 231, 0.5);
    transform: translateX(-50%);
    z-index: 10;
  }
  .sidebar-item-hover-bar {
    position: absolute;
    left: 0.625rem;
    top: 22%;
    bottom: 22%;
    width: 3px;
    border-radius: 9999px;
    background-color: var(--text-more-muted);
    opacity: 0;
    transform: translateX(-50%);
    transition: opacity 0.15s ease;
    z-index: 5;
  }
  .sidebar-item:hover .sidebar-item-hover-bar { opacity: 0.6; }

  .sidebar-item-text {
    display: flex;
    align-items: center;
    width: 100%;
  }

  /* ── RIGHT SIDEBAR: ON THIS PAGE ── */
  #otp-sidebar {
    width: 14rem;
    height: calc(100vh - 3.5rem);
    position: sticky;
    top: 3.5rem;
    overflow-y: auto;
    padding: 1.25rem 1.5rem 2rem 0.75rem;
    margin-right: 1.5rem;
    z-index: 30;
    background-color: var(--bg-base);
    scrollbar-width: none;
    flex-shrink: 0;
    transition: background-color 0.3s ease;
  }
  #otp-sidebar::-webkit-scrollbar { display: none; }

  .otp-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-hover);
    margin-bottom: 1rem;
    padding-left: 0.5rem;
  }

  .otp-list {
    position: relative;
    padding-left: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .otp-list::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.5rem;
    bottom: 0.5rem;
    width: 1px;
    background-color: var(--border-base);
    transform: translateX(-50%);
  }

  .otp-item {
    position: relative;
    list-style: none;
  }

  .otp-indicator {
    position: absolute;
    left: 0;
    transform: translateX(-50%);
    width: 3px;
    border-radius: 9999px;
    background-color: #6C5CE7;
    transition: top 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), height 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.2s ease;
    box-shadow: 0 0 8px rgba(108, 92, 231, 0.5);
    pointer-events: none;
  }

  .otp-button {
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    padding: 0.25rem 0.5rem;
    font-size: 13px;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 0.15s ease;
    user-select: none;
  }

  .otp-button:hover {
    color: var(--text-hover);
  }

  .otp-button:hover {
    color: var(--text-hover);
  }

  .otp-item.active .otp-button {
    color: var(--text-base);
    font-weight: 600;
  }
`;
