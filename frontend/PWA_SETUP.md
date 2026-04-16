# PWA Setup Instructions

The frontend is now configured as a Progressive Web App (PWA) using vite-plugin-pwa.

## What's Been Done

1. ✅ Installed `vite-plugin-pwa` package
2. ✅ Updated `vite.config.ts` with PWA configuration
3. ✅ Added theme-color meta tag to `index.html`

## What You Need to Add

### App Icons
Add the following icon files to the `public/` directory:
- `icon-192x192.png` - 192x192 pixel PNG icon
- `icon-512x512.png` - 512x512 pixel PNG icon

You can generate these icons from your logo using tools like:
- https://realfavicongenerator.net/
- https://www.favicon-generator.org/

### Optional Assets
For better PWA experience, you can also add:
- `favicon.ico` - Traditional favicon
- `apple-touch-icon.png` - iOS home screen icon
- `masked-icon.svg` - Android adaptive icon

## How to Test

1. Build the app: `npm run build`
2. Preview the build: `npm run preview`
3. Open in Chrome DevTools > Application tab
4. Check "Manifest" and "Service Workers" sections
5. Test on mobile device for install prompt

## Development vs Production

- **Development**: PWA features are available but service worker may not work fully
- **Production**: Run `npm run build` to generate the full PWA with service worker

## Configuration

PWA settings are in `vite.config.ts`. You can customize:
- App name and description
- Theme color
- Display mode (standalone, fullscreen, etc.)
- Icons and assets

## Note

The manual `manifest.json` and `sw.js` files in `public/` are not needed - vite-plugin-pwa generates them automatically during build.
