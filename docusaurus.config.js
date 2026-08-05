// @ts-check

const lightCodeTheme = require('prism-react-renderer/themes/github');
const darkCodeTheme = require('prism-react-renderer/themes/dracula');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Districts Documentation',
  tagline: 'A decentralized, open-source virtual world',
  url: 'https://doc.districts.xyz',
  baseUrl: '/districts/',
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  favicon: 'img/favicon.png',
  organizationName: 'realiotech',
  projectName: 'districts-docs',

  // GitBook sets Inter as its body font; match it so text metrics line up.
  stylesheets: [
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
  ],

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: require.resolve('./sidebars.js'),
          sidebarCollapsible: true,
          editUrl: 'https://github.com/realiotech/districts-docs/tree/main/',
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],

  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        indexBlog: false,
        docsRouteBasePath: '/',
      },
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      colorMode: {
        defaultMode: 'dark',
        respectPrefersColorScheme: true,
      },
      navbar: {
        title: '',
        logo: {
          alt: 'Districts Logo',
          src: 'img/districts-logo-black.svg',
          srcDark: 'img/districts-logo-white.svg',
        },
        items: [
          {
            type: 'doc',
            docId: 'introduction',
            position: 'left',
            label: 'Documentation',
          },
          {
            href: 'https://github.com/realiotech/districts-docs',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        logo: {
          alt: 'Districts',
          src: 'img/districts-logo-white.svg',
          href: 'https://districts.xyz',
        },
        links: [
          {
            title: "Resources",
            items: [
              {
                label: "Support Center",
                href: "https://support.realio.network/hc/en-us/categories/31512838658715-Districts",
              },
              {
                label: "Team",
                href: "https://realio.network/about",
              },
              {
                label: "Press",
                href: "https://support.realio.network/hc/en-us/requests/new?ticket_form_id=34409612652315",
              },
              {
                label: "Become a Partner",
                href: "https://support.realio.network/hc/en-us/requests/new?ticket_form_id=34409612652315",
              },
            ],
          },
          {
            title: "Other Realio Websites",
            items: [
              {
                label: "Freehold",
                href: "https://freehold.finance/",
              },
              {
                label: "Liquid Mining Fund",
                href: "https://liquidmining.fund/",
              },
              {
                label: "Realio Fund",
                href: "https://realio.fund/",
              },
              {
                label: "Realio Network",
                href: "https://realio.network/",
              },
            ],
          },
          {
            title: "Legal",
            items: [
              {
                label: "Privacy Policy",
                href: "https://districts.xyz/privacy-policy",
              },
              {
                label: "Terms of Use",
                href: "https://districts.xyz/terms-conditions",
              },
            ],
          },
          {
            title: "Learn Hub",
            items: [
              {
                label: "Documentation",
                href: "https://docs.districts.xyz/districts",
              },
              {
                label: "Whitepaper",
                href: "https://districts.xyz/files/Districts_Token_Economy_Whitepaper.pdf",
              },
              {
                label: "EBook",
                href: "https://districts.xyz/files/Districts_Digital_Horizons_eBook.pdf",
              },
            ],
          },
          {
            title: "Follow",
            items: [
              {
                label: "X",
                href: "https://x.com/districts_xyz",
              },
              {
                label: "Facebook",
                href: "https://www.facebook.com/districts.xyz",
              },
              {
                label: "Instagram",
                href: "https://www.instagram.com/districts_xyz/",
              },
              {
                label: "Telegram",
                href: "https://t.me/districts_xyz",
              },
            ],
          },
        ],
        copyright:
          '<p class="footer__disclaimer">' +
          "While Land Pixels correspond to real-world locations, they carry no rights with respect to the real property at such locations. Land Pixels do not represent any tangible assets. Participants in the Districts community should not claim Land Pixels or hold them as investments, and should not assume they will appreciate in value or retain value. The ability to resell Land Pixels on the Marketplace depends on the interest and enthusiasm of other community members. You may be unable to sell Land Pixels on the Marketplace, and if you can do so the price you are offered for them may be significantly less than your original purchase price. While reclaiming Land Pixels will provide an opportunity to sell your Land Pixels to the Land Bank, the price paid will be based on a numerical formula and the amount of assets available in the Land Bank, which could be significantly less than you paid and could be negligible. While purchasers in the Marketplace may place a premium on Land Pixels that correspond certain addresses or locations, Land Bank repurchases will be based on the number of Land Pixels held as a fraction of total outstanding Land Pixels, without assigning value based on location." +
          '</p>' +
          '<p>&copy; Districts 2026, All Rights Reserved</p>',
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
    }),
};

module.exports = config;
