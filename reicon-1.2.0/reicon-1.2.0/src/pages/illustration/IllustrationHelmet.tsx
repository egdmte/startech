import { Helmet } from 'react-helmet-async';

export default function IllustrationHelmet() {
  const title = "71,000+ Free SVG Illustrations — Open-Source Vector Graphics | Reicon";
  const description = "Browse 71,000+ free open-source SVG vector illustrations for React, Vue, HTML, and Figma. Download high-resolution PNG & customizable SVGs. MIT licensed.";
  const url = "https://reicon.dev/illustration";
  const ogImage = "https://reicon.dev/og/illustration.jpg";
  const keywords = "free SVG illustrations, free vector illustrations, open source illustrations, React SVG illustrations, Vue illustrations, Figma vector graphics, MIT license illustrations, doodle SVG, UI illustrations library, vector art SVG, free web graphics, 71000 illustrations";

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={url} />
      <meta name="keywords" content={keywords} />
      <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />
      <meta name="image" content={ogImage} />
      <meta name="ai-content-declaration" content="human-curated" />

      {/* OpenGraph */}
      <meta property="og:type" content="website" />
      <meta property="og:url" content={url} />
      <meta property="og:site_name" content="Reicon" />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:image:width" content="1200" />
      <meta property="og:image:height" content="630" />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content="@reicon_dev" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImage} />

      {/* Breadcrumbs Schema */}
      <script type="application/ld+json">{JSON.stringify({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
          { "@type": "ListItem", "position": 1, "name": "Reicon", "item": "https://reicon.dev" },
          { "@type": "ListItem", "position": 2, "name": "Illustrations", "item": url }
        ]
      })}</script>

      {/* Collection Page Schema */}
      <script type="application/ld+json">{JSON.stringify({
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "description": description,
        "url": url,
        "isPartOf": { "@type": "WebSite", "name": "Reicon", "url": "https://reicon.dev" }
      })}</script>

      {/* Dataset Schema for Google Search indexing */}
      <script type="application/ld+json">{JSON.stringify({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "Reicon 71,000+ Free SVG Illustrations",
        "description": description,
        "url": url,
        "license": "https://opensource.org/licenses/MIT",
        "creator": { "@type": "Organization", "name": "Reicon", "url": "https://reicon.dev" },
        "keywords": ["SVG illustrations", "vector graphics", "free illustrations", "React SVG illustrations", "Figma illustrations"],
        "isAccessibleForFree": true
      })}</script>

      {/* Image Gallery Schema */}
      <script type="application/ld+json">{JSON.stringify({
        "@context": "https://schema.org",
        "@type": "ImageGallery",
        "name": "71,000+ Free Open-Source SVG Illustrations",
        "url": url,
        "description": description
      })}</script>
    </Helmet>
  );
}
