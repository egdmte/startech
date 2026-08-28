import { ChevronExpandY } from 'reicon-react';
import { SiClaude, SiGithub } from 'react-icons/si';

interface Props {
    copiedPage: boolean;
    openDropdown: boolean;
    openDropdownRef: React.RefObject<HTMLDivElement | null>;
    githubEditUrl: string;
    githubUrl: string;
    onCopyMarkdown: () => void;
    onOpenDropdown: (v: boolean) => void;
    onOpenInLLM: (platform: 'chatgpt' | 'claude' | 't3') => void;
}

export default function DocsActionsBar({
    copiedPage, openDropdown, openDropdownRef,
    githubEditUrl, githubUrl,
    onCopyMarkdown, onOpenDropdown, onOpenInLLM,
}: Props) {
    return (
        <div className="relative grid grid-cols-2 gap-2.5 w-full sm:flex sm:w-auto sm:items-center">
            {/* Edit on GitHub */}
            <div className="flex justify-end sm:justify-start w-full sm:w-auto">
                <a
                    href={githubEditUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg sm:rounded-xl text-xs sm:text-[13px] font-medium text-text-base/70 hover:text-text-base bg-text-base/4 border border-text-base/10 hover:bg-text-base/8 transition-colors whitespace-nowrap"
                >
                    <re-icon icon="pen" size={14}></re-icon>
                    Edit on GitHub
                </a>
            </div>

            {/* Copy Markdown */}
            <div className="flex justify-start w-full sm:w-auto">
                <button
                    onClick={onCopyMarkdown}
                    className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg sm:rounded-xl text-xs sm:text-[13px] font-medium text-text-base/70 hover:text-text-base bg-text-base/4 border border-text-base/10 hover:bg-text-base/8 transition-colors cursor-pointer whitespace-nowrap"
                >
                    {copiedPage ? (
                        <svg className="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M20 6 9 17l-5-5" />
                        </svg>
                    ) : (
                        <re-icon icon="copy" size={14}></re-icon>
                    )}
                    Copy Markdown
                </button>
            </div>

            {/* Open in AI / GitHub dropdown */}
            <div ref={openDropdownRef} className="col-span-2 flex justify-center sm:block relative">
                <button
                    onClick={() => onOpenDropdown(!openDropdown)}
                    className="flex items-center gap-1.5 px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg sm:rounded-xl text-xs sm:text-[13px] font-medium text-text-base/70 hover:text-text-base bg-text-base/4 border border-text-base/10 hover:bg-text-base/8 transition-colors cursor-pointer whitespace-nowrap"
                >
                    Open
                    <ChevronExpandY size={14} className="text-text-base/40" />
                </button>

                {openDropdown && (
                    <div className="absolute left-1/2 -translate-x-1/2 sm:translate-x-0 sm:left-auto sm:right-0 mb-2 bottom-full w-52 bg-[var(--dropdown-bg)] border border-text-base/8 rounded-xl shadow-none z-50 overflow-hidden py-1">
                        <a
                            href={githubUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between px-4 py-2 text-[13px] text-text-base/70 hover:text-text-base hover:bg-text-base/4 transition-colors"
                        >
                            <span className="flex items-center gap-2">
                                <SiGithub size={14} />
                                Open in GitHub
                            </span>
                            <re-icon icon="arrow-up-right" size={12} className="text-text-base/30"></re-icon>
                        </a>

                        <button
                            onClick={() => onOpenInLLM('chatgpt')}
                            className="w-full flex items-center justify-between px-4 py-2 text-[13px] text-text-base/70 hover:text-text-base hover:bg-text-base/4 transition-colors text-left cursor-pointer"
                        >
                            <span className="flex items-center gap-2">
                                {/* ChatGPT logo */}
                                <svg width={14} height={14} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                                    <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08-4.778 2.758a.795.795 0 0 0-.393.681zm1.097-2.365 2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" />
                                </svg>
                                Open in ChatGPT
                            </span>
                            <re-icon icon="arrow-up-right" size={12} className="text-text-base/30"></re-icon>
                        </button>

                        <button
                            onClick={() => onOpenInLLM('claude')}
                            className="w-full flex items-center justify-between px-4 py-2 text-[13px] text-text-base/70 hover:text-text-base hover:bg-text-base/4 transition-colors text-left cursor-pointer"
                        >
                            <span className="flex items-center gap-2">
                                <SiClaude size={14} />
                                Open in Claude
                            </span>
                            <re-icon icon="arrow-up-right" size={12} className="text-text-base/30"></re-icon>
                        </button>

                        <button
                            onClick={() => onOpenInLLM('t3')}
                            className="w-full flex items-center justify-between px-4 py-2 text-[13px] text-text-base/70 hover:text-text-base hover:bg-text-base/4 transition-colors text-left cursor-pointer"
                        >
                            <span className="flex items-center gap-2">
                                <re-icon icon="chat" size={14}></re-icon>
                                Open in T3 Chat
                            </span>
                            <re-icon icon="arrow-up-right" size={12} className="text-text-base/30"></re-icon>
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
