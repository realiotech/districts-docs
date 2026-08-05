import React from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';
import data from './footerData.json';
import styles from './styles.module.css';

// Shadows the Docusaurus footer to reproduce the districts.xyz footer. Because
// this component replaces it, themeConfig.footer is not used.
//
// footerData.json is the content of the Strapi single-type districts.xyz itself
// renders (strapi.districts.xyz /api/footer). Links stored there as site paths
// are absolute here, since this site is not on that domain.

// districts.xyz posts this form to its own /api/send-email route. That route is
// same-origin and sends no CORS headers, and this site is static, so the block
// is presentational and sends visitors to the real signup instead.
const SUBSCRIBE_URL = 'https://districts.xyz/blogs';

const SOCIAL_LABEL = {
  x: 'X',
  facebook: 'Facebook',
  instagram: 'Instagram',
  telegram: 'Telegram',
};

export default function Footer() {
  const logo = useBaseUrl('/img/districts-logo-white.svg');
  // Resolved once: hooks cannot be called inside the socials map below.
  const socialBase = useBaseUrl('/img/social/');

  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.top}>
          <a href="https://districts.xyz" className={styles.logoLink}>
            <img src={logo} alt="Districts" className={styles.logo} />
          </a>

          <div className={styles.row}>
            <div className={styles.columns}>
              {data.columns.map((column) => (
                <div className={styles.column} key={column.title}>
                  <span className={styles.columnTitle}>{column.title}</span>
                  {column.items.map((item) => (
                    <a
                      className={styles.link}
                      href={item.href}
                      key={item.label}
                      target="_blank"
                      rel="noopener noreferrer">
                      {item.label}
                    </a>
                  ))}
                </div>
              ))}
            </div>

            <div className={styles.subscribe}>
              <span className={styles.subscribeLabel}>Districts Digest</span>
              <a
                className={styles.field}
                href={SUBSCRIBE_URL}
                target="_blank"
                rel="noopener noreferrer">
                <span className={styles.fieldPlaceholder}>EMAIL</span>
                <span className={styles.subscribeButton}>Subscribe</span>
              </a>
            </div>
          </div>
        </div>

        <div className={styles.bottom}>
          <div className={styles.meta}>
            <span className={styles.copyright}>{data.copyright}</span>
            <div className={styles.socials}>
              {data.socials.map((social) => {
                const label = SOCIAL_LABEL[social.name] || social.name;
                return (
                  <a
                    className={styles.social}
                    href={social.href}
                    key={social.name}
                    aria-label={label}
                    target="_blank"
                    rel="noopener noreferrer">
                    <img src={`${socialBase}${social.name}.svg`} alt={label} />
                  </a>
                );
              })}
            </div>
          </div>
          <div className={styles.divider} />
          <span className={styles.disclaimer}>{data.disclaimer}</span>
        </div>
      </div>
    </footer>
  );
}
