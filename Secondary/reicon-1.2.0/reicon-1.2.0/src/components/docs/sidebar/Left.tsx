import { useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { ChevronExpandY } from 'reicon-react';
import { FrameworkIcon } from '../framework/icons';
import { FRAMEWORKS, NAV_ITEMS, Framework } from '../framework/constants';

interface NavItem { id: string; label: string }

interface Props {
    framework: Framework;
    fwParam?: string;
    frameworkSectionId: string;
    frameworkLabel: string;
    dropdownOpen: boolean;
    setDropdownOpen: (v: boolean) => void;
    dropdownRef: React.RefObject<HTMLDivElement | null>;
    introItems: NavItem[];
    activeSection: string;
    onNavClick: (id: string) => void;
    onFrameworkSwitch: (fw: Framework) => void;
}

export default function DocsLeftSidebar({
    framework, fwParam, frameworkSectionId, frameworkLabel,
    dropdownOpen, setDropdownOpen, dropdownRef,
    introItems, activeSection, onNavClick, onFrameworkSwitch,
}: Props) {
    const navigate = useNavigate();
    const [hoveredId, setHoveredId] = useState<string | null>(null);
    const selectedFw = FRAMEWORKS.find((f) => f.id === framework)!;

    const allVisibleItems: NavItem[] = useMemo(() => [
        ...introItems,
        { id: frameworkSectionId, label: frameworkLabel },
        ...NAV_ITEMS.basics,
        ...NAV_ITEMS.guides,
        ...NAV_ITEMS.advanced,
    ], [introItems, frameworkSectionId, frameworkLabel]);

    const renderNavItem = (item: NavItem) => {
        const isActive = activeSection === item.id;
        const hoveredIndex = hoveredId ? allVisibleItems.findIndex((it) => it.id === hoveredId) : -1;
        const itemIndex = allVisibleItems.findIndex((it) => it.id === item.id);
        const distance = (hoveredIndex !== -1 && itemIndex !== -1) ? Math.abs(hoveredIndex - itemIndex) : -1;

        let offsetX = 0;
        let hoverOpacity = 0;
        if (distance === 0) {
            offsetX = 4;
            hoverOpacity = 0.6;
        } else if (distance === 1) {
            offsetX = 2;
            hoverOpacity = 0;
        }

        return (
            <div
                key={item.id}
                onClick={() => onNavClick(item.id)}
                onMouseEnter={() => setHoveredId(item.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={`sidebar-item ${isActive ? 'active' : ''}`}
            >
                {isActive ? (
                    <motion.div
                        initial={{ opacity: 0, scaleY: 0.6 }}
                        animate={{ opacity: 1, scaleY: 1 }}
                        className="sidebar-item-active-bar"
                        transition={{ duration: 0.15, ease: 'easeOut' }}
                    />
                ) : (
                    <motion.div
                        className="sidebar-item-hover-bar"
                        animate={{ opacity: hoverOpacity }}
                        transition={{ type: 'spring', stiffness: 450, damping: 28 }}
                    />
                )}
                <motion.span
                    animate={{ x: offsetX }}
                    transition={{ type: 'spring', stiffness: 450, damping: 28 }}
                    className="sidebar-item-text"
                >
                    {item.label}
                </motion.span>
            </div>
        );
    };

    return (
        <aside id="docs-sidebar" className="hidden lg:block" data-lenis-prevent>
            {/* Top Back Button */}
            <button
                onClick={() => {
                    if (fwParam) {
                        navigate('/docs');
                    } else {
                        navigate('/');
                    }
                }}
                className="flex items-center gap-1.5 mb-3 px-2 py-1 rounded-lg text-[12px] font-medium text-text-base/60 hover:text-text-base bg-text-base/3 hover:bg-text-base/6 border border-text-base/6 transition-all cursor-pointer group w-fit"
            >
                <svg
                    aria-hidden="true"
                    viewBox="0 0 24 24"
                    fill="none"
                    className="w-3.5 h-3.5 transition-transform group-hover:-translate-x-0.5 shrink-0"
                >
                    <path
                        d="M9.70711 4.70711C10.0976 4.31658 10.0976 3.68342 9.70711 3.29289C9.31658 2.90237 8.68342 2.90237 8.29289 3.29289L3.29289 8.29289C2.90237 8.68342 2.90237 9.31658 3.29289 9.70711L8.29289 14.7071C8.68342 15.0976 9.31658 15.0976 9.70711 14.7071C10.0976 14.3166 10.0976 13.6834 9.70711 13.2929L6.41421 10H10.4C12.0967 10 13.309 10.0008 14.2594 10.0784C15.198 10.1551 15.7927 10.3018 16.27 10.545C17.2108 11.0243 17.9757 11.7892 18.455 12.73C18.6982 13.2073 18.8449 13.802 18.9216 14.7406C18.9992 15.691 19 16.9033 19 18.6V20C19 20.5523 19.4477 21 20 21C20.5523 21 21 20.5523 21 20V18.5556C21 16.913 21 15.6191 20.9149 14.5778C20.8281 13.5154 20.6478 12.6283 20.237 11.8221C19.5659 10.5049 18.4951 9.43407 17.1779 8.76295C16.3717 8.35217 15.4846 8.17186 14.4222 8.08507C13.3809 7.99999 12.087 7.99999 10.4444 8L6.41421 8L9.70711 4.70711Z"
                        fill="currentColor"
                    />
                </svg>
                <span>Back</span>
            </button>

            {/* Getting Started */}
            <div className="reicon-sidebar-group">
                <div className="sidebar-section-header">
                    <div className="sidebar-icon-box">
                        <re-icon icon="compass" size="13" />
                    </div>
                    <span>Getting Started</span>
                </div>
                <div className="sidebar-items-container">
                    <div className="sidebar-section-line" />
                    {introItems.map(renderNavItem)}
                </div>
            </div>

            {/* Framework Dropdown */}
            <div className="reicon-sidebar-group">
                <div className="sidebar-section-header">
                    <div className="sidebar-icon-box">
                        <re-icon icon="code" size="13" />
                    </div>
                    <span>Framework</span>
                </div>
                <div className="sidebar-items-container">
                    <div className="sidebar-section-line" />
                    <div ref={dropdownRef} className="relative mb-2 pl-6 pr-1">
                        <button
                            onClick={() => setDropdownOpen(!dropdownOpen)}
                            className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg border border-text-base/10 bg-text-base/3 hover:bg-text-base/6 transition-colors cursor-pointer"
                        >
                            <div className="flex items-center gap-2">
                                {fwParam ? (
                                    <>
                                        <FrameworkIcon id={selectedFw.id} size={14} />
                                        <span className="text-[12px] text-text-base/80 font-medium">{selectedFw.label}</span>
                                    </>
                                ) : (
                                    <>
                                        <re-icon icon="code" size="14" className="text-text-base/40" />
                                        <span className="text-[12px] text-text-base/40 font-medium">Select</span>
                                    </>
                                )}
                            </div>
                            <ChevronExpandY className="w-3.5 h-3.5 text-text-base/30" />
                        </button>

                        {dropdownOpen && (
                            <div className="absolute top-full left-6 right-1 mt-1 bg-[var(--dropdown-bg)] border border-text-base/10 rounded-xl shadow-none overflow-hidden z-50">
                                {FRAMEWORKS.map((fw) => (
                                    <button
                                        key={fw.id}
                                        onClick={() => onFrameworkSwitch(fw.id)}
                                        className={`w-full flex items-center justify-between px-3 py-2 text-[12px] transition-colors cursor-pointer ${framework === fw.id ? 'bg-text-base/6 text-text-base' : 'text-text-base/60 hover:bg-text-base/4 hover:text-text-base/80'
                                            }`}
                                    >
                                        <div className="flex items-center gap-2">
                                            <FrameworkIcon id={fw.id} size={14} />
                                            <span className={framework === fw.id ? 'font-medium' : ''}>{fw.label}</span>
                                        </div>
                                        {framework === fw.id && (
                                            <svg className="w-3.5 h-3.5 text-[#6C5CE7]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                                <polyline points="20 6 9 17 4 12" />
                                            </svg>
                                        )}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {renderNavItem({ id: frameworkSectionId, label: frameworkLabel })}
                </div>
            </div>

            {/* Basics */}
            <div className="reicon-sidebar-group">
                <div className="sidebar-section-header">
                    <div className="sidebar-icon-box">
                        <re-icon icon="settings" size="13" />
                    </div>
                    <span>Basics</span>
                </div>
                <div className="sidebar-items-container">
                    <div className="sidebar-section-line" />
                    {NAV_ITEMS.basics.map(renderNavItem)}
                </div>
            </div>

            {/* Guides */}
            <div className="reicon-sidebar-group">
                <div className="sidebar-section-header">
                    <div className="sidebar-icon-box">
                        <re-icon icon="palette" size="13" />
                    </div>
                    <span>Guides</span>
                </div>
                <div className="sidebar-items-container">
                    <div className="sidebar-section-line" />
                    {NAV_ITEMS.guides.map(renderNavItem)}
                </div>
            </div>

            {/* Advanced */}
            <div className="reicon-sidebar-group">
                <div className="sidebar-section-header">
                    <div className="sidebar-icon-box">
                        <re-icon icon="help-circle" size="13" />
                    </div>
                    <span>Advanced</span>
                </div>
                <div className="sidebar-items-container">
                    <div className="sidebar-section-line" />
                    {NAV_ITEMS.advanced.map(renderNavItem)}
                </div>
            </div>
        </aside>
    );
}
