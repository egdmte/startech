import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Ghost, ArrowLeft, Search3 } from 'reicon-react';

export default function NotFound() {
  return (
    <div>
      <Helmet>
        <title>404 — Page Not Found | Reicon</title>
        <meta name="robots" content="noindex" />
      </Helmet>

      <main className="flex-1 flex flex-col items-center justify-center px-4 text-center">
        <Ghost size={52} className="text-text-base/35 mb-5" />

        <h2 className="text-[clamp(18px,2.5vw,28px)] font-semibold text-text-base leading-[1.2] mb-2">
          This page doesn't exist.
        </h2>

        <p className="text-[clamp(13px,1.1vw,15px)] text-text-base/40 leading-[1.6] max-w-[380px] mb-8">
          The page you're looking for might have been moved, deleted, or never existed.
        </p>

        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="bg-[#6C5CE7] hover:bg-[#5A4BD1] text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors inline-flex items-center gap-2"
          >
            <ArrowLeft size={16} />
            Go Home
          </Link>
          <Link
            to="/icons"
            className="bg-text-base/6 hover:bg-text-base/10 text-text-base/70 hover:text-text-base text-sm font-medium px-5 py-2.5 rounded-lg transition-colors inline-flex items-center gap-2"
          >
            <Search3 size={16} />
            Browse Icons
          </Link>
        </div>
      </main>
    </div>
  );
}
