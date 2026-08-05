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
        links: [
          {
            title: 'Districts',
            items: [
              {
                label: 'Website',
                href: 'https://districts.xyz',
              },
              {
                label: 'App',
                href: 'https://app.districts.xyz',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'Twitter',
                href: 'https://twitter.com/districts_xyz',
              },
              {
                label: 'Discord',
                href: 'https://discord.gg/districts',
              },
            ],
          },
          {
            title: 'More',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/realiotech/districts-docs',
              },
              {
                label: 'Realio Network',
                href: 'https://www.realio.network',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Districts`,
      },
      prism: {
        theme: lightCodeTheme,
        darkTheme: darkCodeTheme,
      },
    }),
};

module.exports = config;
