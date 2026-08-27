import { useState, useRef } from 'react';
import { Helmet } from 'react-helmet-async';
import { motion } from 'motion/react';
import { Heart, HandHeart, Sparkles, Star, Code, Check } from 'reicon-react';
import BuyMeACoffeeIcon from '../../components/ui/BuyMeACoffeeIcon';
import { PAGE_META } from '../../data/page-meta';
import DocsActionsBar from '../../components/docs/ActionsBar';

const BUY_ME_A_COFFEE_URL = 'https://buymeacoffee.com/reicon';

const SUPPORT_TIERS = [
  {
    title: '1 Coffee',
    price: '$5',
    tagline: 'Fuel an Icon',
    description: 'Help cover domain renewal and basic server infrastructure costs.',
    coffees: 1,
    popular: false,
    url: `${BUY_ME_A_COFFEE_URL}`,
  },
  {
    title: '3 Coffees',
    price: '$15',
    tagline: 'Power a Release',
    description: 'Sponsor the design and precision vectoring of brand new icon sets.',
    coffees: 3,
    popular: true,
    url: `${BUY_ME_A_COFFEE_URL}`,
  },
  {
    title: '5 Coffees',
    price: '$25',
    tagline: 'Supercharge Development',
    description: 'Support ongoing maintenance for React, Vue, Svelte, Flutter & MCP tools.',
    coffees: 5,
    popular: false,
    url: `${BUY_ME_A_COFFEE_URL}`,
  },
];

const IMPACT_CARDS = [
  {
    icon: <HandHeart size={22} className="text-[#FFDD00]" />,
    title: '100% Free & Open Source',
    description: 'Reicon is released under the permissive MIT license. Your support keeps all 2,700+ icons accessible to everyone worldwide without paywalls.',
  },
  {
    icon: <Sparkles size={22} className="text-[#6C5CE7]" />,
    title: 'Handcrafted Precision',
    description: 'Every path and stroke is manually drawn on a 24×24 grid — never auto-generated. Contributions allow dedicated focus on icon detail and design quality.',
  },
  {
    icon: <Code size={22} className="text-[#61DAFB]" />,
    title: 'Multi-Ecosystem Tooling',
    description: 'We maintain 7 official packages (React, React Native, Vue, Svelte, Flutter, VS Code, MCP). Support funds ongoing integration updates and CLI tooling.',
  },
];

export default function SupportPage() {
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedPage, setCopiedPage] = useState(false);
  const [openDropdown, setOpenDropdown] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const openDropdownRef = useRef<HTMLDivElement>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(BUY_ME_A_COFFEE_URL);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      // fallback
    }
  };

  const getPageMarkdown = () => {
    return `# Support Reicon Development\n\nReicon is 100% free and open-source under the MIT license. If Reicon helps you ship faster apps or craft cleaner designs, consider buying a coffee to support its future.\n\nBuy a coffee: ${BUY_ME_A_COFFEE_URL}`;
  };

  const handleCopyPageMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(getPageMarkdown());
      setCopiedPage(true);
      showToast('Support page markdown copied!');
      setTimeout(() => setCopiedPage(false), 2000);
    } catch {
      showToast('Failed to copy');
    }
  };

  const openInLLM = async (platform: 'chatgpt' | 'claude' | 't3') => {
    const md = getPageMarkdown();
    try { await navigator.clipboard.writeText(md); } catch { /* silent */ }
    const promptText = `Here is the Reicon Support page details. Please read it and help answer my questions:\n\n${md}`;
    const urls = {
      chatgpt: `https://chatgpt.com/?hints=search&q=${encodeURIComponent(promptText)}`,
      claude: `https://claude.ai/new?q=${encodeURIComponent(promptText)}`,
      t3: `https://t3.chat/new?q=${encodeURIComponent(promptText)}`,
    };
    setOpenDropdown(false);
    showToast('Markdown copied! Opening AI Chat...');
    window.open(urls[platform], '_blank');
  };

  return (
    <motion.div
      className="flex-1 pt-24 pb-16 px-4 sm:px-6 md:px-8 max-w-5xl mx-auto w-full overflow-x-hidden"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Helmet>
        <title>{PAGE_META['/support'].title}</title>
        <meta name="description" content={PAGE_META['/support'].description} />
        <link rel="canonical" href={PAGE_META['/support'].url} />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={PAGE_META['/support'].url} />
        <meta property="og:site_name" content="Reicon" />
        <meta property="og:title" content={PAGE_META['/support'].title} />
        <meta property="og:description" content={PAGE_META['/support'].description} />
        <meta property="og:image" content={PAGE_META['/support'].ogImage} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="@reicon_dev" />
        <meta name="twitter:title" content={PAGE_META['/support'].title} />
        <meta name="twitter:description" content={PAGE_META['/support'].description} />
        <meta name="twitter:image" content={PAGE_META['/support'].ogImage} />
        <script type="application/ld+json">
          {JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            itemListElement: [
              { '@type': 'ListItem', position: 1, name: 'Reicon', item: 'https://reicon.dev' },
              { '@type': 'ListItem', position: 2, name: 'Support', item: 'https://reicon.dev/support' },
            ],
          })}
        </script>
      </Helmet>

      {/* Hero Header */}
      <div className="text-center max-w-2xl mx-auto mb-14">

        <h1 className="text-3xl sm:text-4xl md:text-5xl font-serif text-text-base font-semibold leading-tight tracking-tight mb-4">
          Support Reicon Development
        </h1>

        <p className="text-text-base/60 text-base sm:text-lg leading-relaxed mb-6">
          Reicon is 100% free and open-source under the MIT license. If Reicon helps you ship faster apps or craft cleaner designs, consider buying a coffee to support its future.
        </p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <a
            href={BUY_ME_A_COFFEE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 bg-[#FFDD00] hover:bg-[#ffe533] text-[#0D0C22] font-semibold text-sm px-6 py-3 rounded-full transition-all shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98]"
          >
            <BuyMeACoffeeIcon size={18} />
            <span>Buy Me a Coffee</span>
          </a>
          <button
            onClick={handleShare}
            className="inline-flex items-center gap-1.5 bg-text-base/6 hover:bg-text-base/10 text-text-base/80 text-sm px-5 py-3 rounded-full transition-colors border border-text-base/10 cursor-pointer"
          >
            {copiedLink ? <><Check size={16} /> Link Copied!</> : <><Heart size={16} className="text-rose-500" /> Share Link</>}
          </button>
        </div>
      </div>

      {/* Support Tiers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        {SUPPORT_TIERS.map((tier) => (
          <div
            key={tier.title}
            className={`relative rounded-2xl p-6 transition-all duration-200 flex flex-col justify-between ${
              tier.popular
                ? 'bg-gradient-to-b from-[#FFDD00]/10 via-text-base/4 to-text-base/2 shadow-lg scale-[1.02]'
                : 'bg-text-base/3 hover:bg-text-base/5'
            }`}
          >
            {tier.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#FFDD00] text-[#0D0C22] text-[11px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full shadow-sm">
                Most Popular
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-text-base/50 uppercase tracking-wider">{tier.tagline}</span>
                <div className="flex items-center gap-0.5">
                  {Array.from({ length: tier.coffees }).map((_, i) => (
                    <BuyMeACoffeeIcon key={i} size={15} />
                  ))}
                </div>
              </div>

              <div className="flex items-baseline gap-2 mb-3">
                <span className="text-3xl font-serif font-bold text-text-base">{tier.price}</span>
                <span className="text-xs text-text-base/50">/ one-time</span>
              </div>

              <p className="text-text-base/60 text-sm leading-relaxed mb-6">
                {tier.description}
              </p>
            </div>

            <a
              href={tier.url}
              target="_blank"
              rel="noopener noreferrer"
              className={`w-full text-center font-medium text-xs py-2.5 rounded-xl transition-all flex items-center justify-center gap-1.5 ${
                tier.popular
                  ? 'bg-[#FFDD00] hover:bg-[#ffe533] text-[#0D0C22] font-semibold shadow-md'
                  : 'bg-text-base/8 hover:bg-text-base/15 text-text-base'
              }`}
            >
              <BuyMeACoffeeIcon size={14} />
              <span>Support {tier.title}</span>
            </a>
          </div>
        ))}
      </div>

      {/* Impact Cards */}
      <div className="mb-16">
        <div className="text-center max-w-xl mx-auto mb-10">
          <h2 className="text-2xl font-serif text-text-base font-semibold mb-2">Why Your Support Matters</h2>
          <p className="text-text-base/50 text-sm">
            Your contributions directly enable sustainable open-source development.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {IMPACT_CARDS.map((card) => (
            <div
              key={card.title}
              className="bg-text-base/3 rounded-2xl p-6 transition-all hover:bg-text-base/5"
            >
              <div className="w-10 h-10 rounded-xl bg-text-base/6 flex items-center justify-center mb-4">
                {card.icon}
              </div>
              <h3 className="text-base font-semibold text-text-base mb-2">{card.title}</h3>
              <p className="text-text-base/60 text-xs sm:text-sm leading-relaxed">{card.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Creator Note */}
      <div className="bg-gradient-to-r from-text-base/4 via-text-base/3 to-text-base/4 rounded-3xl p-6 sm:p-8 flex flex-col md:flex-row items-center justify-between gap-6 mb-12">
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center gap-1 text-xs text-[#FFDD00] font-semibold">
            <Star size={14} weight="Filled" />
            <span>A note from the creator</span>
          </div>
          <h3 className="text-xl font-serif font-semibold text-text-base">Built with passion by @devchauhan</h3>
          <p className="text-text-base/60 text-sm max-w-lg leading-relaxed">
            Thank you for using Reicon! Building and perfecting over 2,700+ vector icons across multiple frameworks has been an incredible labor of love. Every coffee purchased gives direct motivation to keep expanding the collection.
          </p>
        </div>

        <a
          href={BUY_ME_A_COFFEE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="shrink-0 bg-[#FFDD00] hover:bg-[#ffe533] text-[#0D0C22] font-semibold text-sm px-6 py-3 rounded-full transition-all shadow-md flex items-center gap-2"
        >
          <BuyMeACoffeeIcon size={18} />
          <span>buymeacoffee.com/reicon</span>
        </a>
      </div>

      <hr className="border-text-base/6 my-12" />

      <DocsActionsBar
        copiedPage={copiedPage}
        openDropdown={openDropdown}
        openDropdownRef={openDropdownRef}
        githubEditUrl="https://github.com/dqev/reicon/edit/main/src/pages/support/SupportPage.tsx"
        githubUrl="https://github.com/dqev/reicon"
        onCopyMarkdown={handleCopyPageMarkdown}
        onOpenDropdown={setOpenDropdown}
        onOpenInLLM={openInLLM}
      />

      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-[999] bg-[var(--dropdown-bg)] border border-text-base/8 text-text-base text-sm px-4 py-2.5 rounded-xl flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>{toastMessage}</span>
        </div>
      )}
    </motion.div>
  );
}
