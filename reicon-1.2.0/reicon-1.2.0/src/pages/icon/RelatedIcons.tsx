import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { EASE } from './utils';

interface RelatedIconsProps {
  relatedIcons: string[];
}

export default function RelatedIcons({ relatedIcons }: RelatedIconsProps) {
  return (
    <section className="max-w-[1160px] mx-auto w-full px-5 md:px-10 pb-16">
      <h2 className="text-lg font-serif text-text-base mb-4">Related icons</h2>
      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-12 gap-1.5">
        {relatedIcons.map((iconName, i) => (
          <motion.div key={iconName}
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, margin: '-40px' }}
            transition={{ duration: 0.3, delay: Math.min(i * 0.025, 0.3), ease: EASE }}
          >
            <Link to={`/icon/${iconName}`}
              className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-text-base/2 border border-text-base/5 hover:bg-text-base/5 hover:border-text-base/10 transition-colors group"
              title={`${iconName} icon`}>
              <re-icon icon={iconName} size={24} color="currentColor" className="text-text-base/60 group-hover:text-text-base" aria-label={`${iconName} icon`} />
              <span className="text-[10px] text-text-base/30 group-hover:text-text-base/50 truncate w-full text-center transition-colors">{iconName}</span>
            </Link>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
