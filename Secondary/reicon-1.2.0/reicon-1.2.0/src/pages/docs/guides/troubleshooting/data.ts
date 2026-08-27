export interface TroubleshootingItemData {
  question: string;
  answer: string;
  copyText: string;
  copyField: string;
}

export const troubleshootingItems: TroubleshootingItemData[] = [
  {
    question: "Icons are not rendering (CDN)",
    answer: "Make sure the CDN script is loaded before any <re-icon> elements. Place the script tag in your <head> or before your markup.",
    copyText: '<!-- ✅ Place in <head> -->\n<script src="https://unpkg.com/reicon/cdn/reicon.js"></script>',
    copyField: "faq-cdn",
  },
  {
    question: "Wrong icon weight showing",
    answer: 'The weight prop is case-sensitive in the React/Vue packages. Use "Outline" or "Filled" (PascalCase). In the CDN, use lowercase: "outline" or "filled".',
    copyText: '// ✅ React / Vue — PascalCase\n<Star weight="Filled" />\n\n// ✅ CDN — lowercase\n<re-icon icon="star" weight="filled"></re-icon>\n\n// ❌ Wrong casing\n<Star weight="filled" />\n<re-icon icon="star" weight="Filled"></re-icon>',
    copyField: "faq-weight",
  },
  {
    question: "Icons look blurry or wrong size",
    answer: "The size prop accepts a number (pixels). Don't pass units like \"24px\" — just pass the number. For the CDN, pass the number as a string attribute.",
    copyText: '// ✅ Correct\n<Home size={24} />\n<re-icon icon="home" size="24"></re-icon>\n\n// ❌ Don\'t include units\n<Home size="24px" />',
    copyField: "faq-size",
  },
  {
    question: "TypeScript can't find icon names",
    answer: "Make sure you're importing from the correct package depending on your environment (e.g. \"reicon\" for vanilla JS or \"reicon-react\" for React). Both packages ship with full type definitions. If autocomplete isn't working, restart your TypeScript server.",
    copyText: "// ✅ For React projects\nimport { Home } from 'reicon-react';\n\n// ✅ For vanilla JS projects\nimport { Home } from 'reicon';",
    copyField: "faq-ts",
  },
  {
    question: "Bundle size is too large",
    answer: 'You might be using a wildcard import. Switch to named imports (tree-shakeable) or direct imports for the smallest possible bundle.',
    copyText: "// ❌ Pulls in everything\nimport * as Icons from 'reicon-react';\n\n// ✅ Tree-shakeable\nimport { Home, Bell } from 'reicon-react';\n\n// ✅ Smallest possible\nimport Home from 'reicon-react/icons/Home';",
    copyField: "faq-bundle",
  },
  {
    question: "Icon color not changing",
    answer: "Icons use currentColor by default. If you set a color prop, it overrides inheritance. Check that no parent CSS is overriding the color. For Tailwind, use text-* utilities on the icon's className.",
    copyText: '// Color via prop\n<Heart color="#ef4444" />\n\n// Color via Tailwind\n<Heart className="text-red-500" />\n\n// Color via parent inheritance\n<div style={{ color: "#ef4444" }}>\n  <Heart />  {/* inherits red */}\n</div>',
    copyField: "faq-color",
  },
];
