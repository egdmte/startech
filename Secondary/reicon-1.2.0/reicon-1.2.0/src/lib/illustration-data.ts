export interface IllustrationItem {
  slug: string;
  title: string;
  keywords: string;
  name: string;
  score: number;
  category: string;
  subcategory: string;
}

export interface IllustrationSubcategory {
  name: string;
  count: number;
}

export interface IllustrationCategory {
  name: string;
  count: number;
  subcategories: IllustrationSubcategory[];
}

export interface IllustrationCategoriesMeta {
  total_icons: number;
  categories: IllustrationCategory[];
}

type RawItem = [string, string, string, string, number, string, string];

export function parseRawItem(raw: RawItem): IllustrationItem {
  return {
    slug: raw[0],
    title: raw[1],
    keywords: raw[2],
    name: raw[3] || raw[0],
    score: raw[4],
    category: raw[5],
    subcategory: raw[6],
  };
}

const CDN_BASE = 'https://cdn.reicon.dev';

export function getIllustrationUrl(slug: string): string {
  return `${CDN_BASE}/${slug}.svg`;
}

// In-memory cache
let categoriesMetaCache: IllustrationCategoriesMeta | null = null;
let featuredCache: IllustrationItem[] | null = null;
const groupCache = new Map<string, IllustrationItem[]>();
const itemDetailCache = new Map<string, IllustrationItem>();
const svgCodeCache = new Map<string, string>();

/**
 * Fetch categories metadata (total_icons and list of categories with subcategory counts)
 */
export async function loadIllustrationCategories(): Promise<IllustrationCategoriesMeta> {
  if (categoriesMetaCache) return categoriesMetaCache;
  try {
    const res = await fetch('/illustration-data/categories.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data: IllustrationCategoriesMeta = await res.json();
    categoriesMetaCache = data;
    return data;
  } catch (err) {
    console.error('Failed to load illustration categories:', err);
    return { total_icons: 71262, categories: [] };
  }
}

/**
 * Fetch initial / featured items (~1,000 top illustrations) for instant rendering
 */
export async function loadFeaturedIllustrations(): Promise<IllustrationItem[]> {
  if (featuredCache) return featuredCache;
  try {
    const res = await fetch('/illustration-data/featured.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const rawList: RawItem[] = await res.json();
    const items = rawList.map(parseRawItem);
    items.forEach((item) => itemDetailCache.set(item.slug, item));
    featuredCache = items;
    return items;
  } catch (err) {
    console.error('Failed to load featured illustrations:', err);
    return [];
  }
}

/**
 * Fetch grouped illustrations by category or subcategory
 */
export async function loadIllustrationGroup(category: string, subcategory?: string): Promise<IllustrationItem[]> {
  if (!category || category === 'all') {
    return loadFeaturedIllustrations();
  }

  const groupKey = subcategory && subcategory !== 'all' ? `${category}--${subcategory}` : category;
  if (groupCache.has(groupKey)) {
    return groupCache.get(groupKey)!;
  }

  try {
    const res = await fetch(`/illustration-data/groups/${groupKey}.json`);
    if (!res.ok) {
      if (subcategory && subcategory !== 'all') {
        return loadIllustrationGroup(category, 'all');
      }
      throw new Error(`HTTP ${res.status}`);
    }
    const data = await res.json();
    const rawList: RawItem[] = Array.isArray(data) ? data : (data.entries || []);
    const items = rawList.map(parseRawItem);
    items.forEach((item) => itemDetailCache.set(item.slug, item));
    groupCache.set(groupKey, items);
    return items;
  } catch (err) {
    console.error(`Failed to load group ${groupKey}:`, err);
    return [];
  }
}

/**
 * Search items across full 71,000+ dataset using letter-indexed search buckets
 */
export async function searchIllustrations(
  query: string,
  currentItems: IllustrationItem[],
  activeCategory: string = 'all'
): Promise<IllustrationItem[]> {
  const q = query.trim().toLowerCase();
  if (!q) return currentItems;

  const firstChar = q[0];
  const bucketKey = /^[a-z0-9]$/.test(firstChar) ? firstChar : 'misc';

  // 1. Fetch letter search bucket containing ALL items matching first character
  let bucketItems: IllustrationItem[] = [];
  if (groupCache.has(`search_${bucketKey}`)) {
    bucketItems = groupCache.get(`search_${bucketKey}`)!;
  } else {
    try {
      const res = await fetch(`/illustration-data/search/${bucketKey}.json`);
      if (res.ok) {
        const data = await res.json();
        const rawList: RawItem[] = Array.isArray(data) ? data : (data.entries || []);
        bucketItems = rawList.map(parseRawItem);
        bucketItems.forEach((item) => itemDetailCache.set(item.slug, item));
        groupCache.set(`search_${bucketKey}`, bucketItems);
      }
    } catch {}
  }

  // Filter across ALL items in search bucket matching query
  if (bucketItems.length > 0) {
    return bucketItems.filter(
      (item) =>
        (activeCategory === 'all' || item.category === activeCategory) &&
        (item.slug.toLowerCase().includes(q) ||
          item.name.toLowerCase().includes(q) ||
          item.keywords.toLowerCase().includes(q))
    );
  }

  // Fallback to filtering current items
  return currentItems.filter(
    (item) =>
      item.slug.toLowerCase().includes(q) ||
      item.name.toLowerCase().includes(q) ||
      item.keywords.toLowerCase().includes(q)
  );
}

/**
 * Get details for a single illustration by slug
 */
export async function getIllustrationDetail(slug: string): Promise<IllustrationItem | null> {
  if (itemDetailCache.has(slug)) {
    return itemDetailCache.get(slug)!;
  }

  const featured = await loadFeaturedIllustrations();
  const foundInFeatured = featured.find((i) => i.slug === slug);
  if (foundInFeatured) return foundInFeatured;

  try {
    const firstChar = slug[0];
    const bucket = /^[a-z0-9]$/.test(firstChar) ? firstChar : 'misc';
    const res = await fetch(`/illustration-data/slugmap/${bucket}.json`);
    if (res.ok) {
      const data: Record<string, RawItem> = await res.json();
      if (data[slug]) {
        const item = parseRawItem(data[slug]);
        itemDetailCache.set(slug, item);
        return item;
      }
    }
  } catch {}

  return {
    slug,
    title: slug.replace(/-/g, ' '),
    keywords: slug.replace(/-/g, ' '),
    name: slug.replace(/-/g, ' '),
    score: 10,
    category: 'object',
    subcategory: 'misc',
  };
}

/**
 * Fetch raw SVG XML content using same-origin proxy first to eliminate CORS console errors
 */
export async function fetchIllustrationSvgCode(slug: string): Promise<string> {
  if (!slug) return '';
  if (svgCodeCache.has(slug)) {
    return svgCodeCache.get(slug)!;
  }

  // 1. Try same-origin proxy endpoint first (avoids browser CORS console errors)
  try {
    const res = await fetch(`/cdn-proxy/${slug}.svg`);
    if (res.ok) {
      const text = await res.text();
      if (text.trim().startsWith('<svg')) {
        svgCodeCache.set(slug, text);
        return text;
      }
    }
  } catch {}

  // 2. Fallback to direct CDN fetch
  try {
    const res = await fetch(getIllustrationUrl(slug));
    if (res.ok) {
      const text = await res.text();
      if (text.trim().startsWith('<svg')) {
        svgCodeCache.set(slug, text);
        return text;
      }
    }
  } catch {}

  return '';
}
