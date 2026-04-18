const AVATAR_PALETTES = [
  ['#002833', '#00a8cc', '#c3f5ff'],
  ['#24123f', '#7c3aed', '#f4e8ff'],
  ['#2a1c00', '#f59e0b', '#ffe7b8'],
  ['#0c2d24', '#14b8a6', '#d7fff8'],
];

function hashSeed(input: string): number {
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 31 + input.charCodeAt(index)) >>> 0;
  }
  return hash;
}

function escapeXml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&apos;');
}

function getInitials(label: string): string {
  const words = label
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  if (words.length === 0) {
    return 'HM';
  }

  if (words.length === 1) {
    return Array.from(words[0]).slice(0, 2).join('').toUpperCase();
  }

  return `${words[0][0] ?? ''}${words[1][0] ?? ''}`.toUpperCase();
}

function buildAvatarDataUri(seed: string, label: string): string {
  const palette = AVATAR_PALETTES[hashSeed(seed) % AVATAR_PALETTES.length];
  const initials = escapeXml(getInitials(label));
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="${escapeXml(label)}">
      <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${palette[0]}"/>
          <stop offset="100%" stop-color="${palette[1]}"/>
        </linearGradient>
      </defs>
      <rect width="96" height="96" rx="24" fill="url(#bg)"/>
      <circle cx="72" cy="24" r="12" fill="${palette[2]}" fill-opacity="0.18"/>
      <circle cx="22" cy="76" r="18" fill="${palette[2]}" fill-opacity="0.14"/>
      <text x="50%" y="54%" text-anchor="middle" font-family="Segoe UI, Microsoft YaHei UI, sans-serif" font-size="30" font-weight="700" fill="${palette[2]}">${initials}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

function isSafeLocalAvatar(src: string | undefined): src is string {
  if (!src) {
    return false;
  }

  return (
    src.startsWith('data:') ||
    src.startsWith('blob:') ||
    src.startsWith('/') ||
    src.startsWith('./') ||
    src.startsWith('../')
  );
}

export function resolveAvatarSrc(
  src: string | undefined,
  seed: string,
  label: string,
): string {
  if (isSafeLocalAvatar(src)) {
    return src;
  }

  return buildAvatarDataUri(seed, label);
}
