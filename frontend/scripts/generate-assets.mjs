// Generates the placeholder destination / hero SVGs in public/assets.
// Run: node scripts/generate-assets.mjs
// These are original gradient illustrations (no third-party imagery) so the app ships
// without photo licensing concerns. Replace with real photography by dropping files with
// the same names (.jpg/.png are mapped to .svg by <CoverImage/>; see public/assets/README.md).
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'assets')
const W = 800
const H = 500

const wrap = (id, defs, body) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${id}">
<defs>${defs}</defs>
${body}
</svg>
`

const sky = (id, stops) =>
  `<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">${stops.map(([o, c]) => `<stop offset="${o}" stop-color="${c}"/>`).join('')}</linearGradient>`

const sun = (x, y, r, c) => `<circle cx="${x}" cy="${y}" r="${r * 2.2}" fill="${c}" opacity=".18"/><circle cx="${x}" cy="${y}" r="${r}" fill="${c}" opacity=".9"/>`

function waves(y, colors) {
  return colors
    .map((c, i) => {
      const yy = y + i * 34
      return `<path d="M0 ${yy} Q100 ${yy - 22} 200 ${yy} T400 ${yy} T600 ${yy} T800 ${yy} V${H} H0Z" fill="${c}"/>`
    })
    .join('')
}

function mountains(base, colors, snow = false) {
  return colors
    .map((c, i) => {
      const peaks = [[60 + i * 40, 150 + i * 50], [260 + i * 30, 70 + i * 60], [470 - i * 20, 130 + i * 40], [680 - i * 40, 80 + i * 55]]
      const pts = [`0 ${base}`, ...peaks.flatMap(([x, y]) => [`${x} ${y + base * 0.25}`, `${x + 90} ${base - 20 + i * 10}`]), `${W} ${base}`, `${W} ${H}`, `0 ${H}`].join(' ')
      return `<polygon points="${pts}" fill="${c}"/>`
    })
    .join('') + (snow ? `<polygon points="255 150 285 178 262 172 240 182" fill="#fff" opacity=".85"/><polygon points="665 160 700 190 676 184 650 196" fill="#fff" opacity=".85"/>` : '')
}

function palms(x, scale = 1) {
  return `<g transform="translate(${x} 330) scale(${scale})" fill="#14532d"><path d="M0 170 Q8 90 0 0" stroke="#7c4a1e" stroke-width="7" fill="none"/><path d="M0 0 Q-60 -10 -85 40 Q-40 5 0 6Z"/><path d="M0 0 Q60 -12 90 38 Q44 4 0 6Z"/><path d="M0 0 Q-30 -45 -70 -40 Q-25 -25 0 4Z"/><path d="M0 0 Q30 -48 72 -42 Q28 -26 0 4Z"/></g>`
}

function arches(base, c) {
  const items = []
  for (let i = 0; i < 7; i++) {
    const x = 40 + i * 110
    const h = 120 + (i % 3) * 40
    items.push(`<path d="M${x} ${base} V${base - h} Q${x + 35} ${base - h - 60} ${x + 70} ${base - h} V${base}Z" fill="${c}"/>`)
  }
  return items.join('')
}

function hills(base, colors) {
  return colors.map((c, i) => `<path d="M0 ${base + i * 40} Q200 ${base - 60 + i * 20} 400 ${base + i * 40} T800 ${base + i * 40} V${H} H0Z" fill="${c}"/>`).join('')
}

function stars(n) {
  let s = ''
  for (let i = 0; i < n; i++) s += `<circle cx="${(i * 97) % W}" cy="${(i * 53) % 220}" r="${1 + (i % 3) * 0.6}" fill="#fff" opacity="${0.4 + (i % 4) * 0.15}"/>`
  return s
}

const scenes = {
  'destinations/goa': () => wrap('Goa beach', sky('s', [[0, '#fbc2eb'], [0.55, '#fdd6a5'], [1, '#ffe9c7']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(560, 190, 46, '#fff3b0')}${waves(300, ['#7dd3fc', '#38bdf8', '#0ea5e9'])}<path d="M0 420 Q200 390 420 425 T800 410 V${H} H0Z" fill="#fde68a"/>${palms(110, 1)}${palms(690, 0.8)}`),
  'destinations/manali': () => wrap('Manali mountains', sky('s', [[0, '#c7d2fe'], [1, '#e0f2fe']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${mountains(300, ['#a5b4fc', '#818cf8', '#4f46e5'], true)}<path d="M0 430 Q200 400 400 430 T800 420 V${H} H0Z" fill="#166534"/>`),
  'destinations/jaipur': () => wrap('Jaipur heritage', sky('s', [[0, '#fed7aa'], [1, '#fecdd3']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(400, 170, 52, '#fde68a')}${arches(420, '#fb7185')}<rect y="420" width="${W}" height="80" fill="#be123c"/>`),
  'destinations/udaipur': () => wrap('Udaipur lake palace', sky('s', [[0, '#fdba74'], [0.6, '#f9a8d4'], [1, '#c4b5fd']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(620, 200, 40, '#fff7ed')}${arches(330, '#fff1e6')}${waves(340, ['#6366f1', '#4f46e5', '#4338ca'])}`),
  'destinations/munnar': () => wrap('Munnar tea hills', sky('s', [[0, '#bbf7d0'], [1, '#ecfccb']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${hills(280, ['#4ade80', '#22c55e', '#16a34a', '#15803d'])}`),
  'destinations/kerala': () => wrap('Kerala backwaters', sky('s', [[0, '#a7f3d0'], [1, '#fef9c3']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(150, 150, 38, '#fef08a')}${hills(250, ['#34d399', '#10b981'])}${waves(350, ['#2dd4bf', '#14b8a6', '#0f766e'])}${palms(620, 0.9)}${palms(710, 0.7)}`),
  'destinations/darjeeling': () => wrap('Darjeeling', sky('s', [[0, '#e0e7ff'], [1, '#fce7f3']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${mountains(260, ['#c7d2fe', '#a5b4fc'], true)}${hills(350, ['#86efac', '#4ade80', '#22c55e'])}`),
  'destinations/rishikesh': () => wrap('Rishikesh', sky('s', [[0, '#bae6fd'], [1, '#d9f99d']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${hills(230, ['#86efac', '#4ade80'])}${waves(340, ['#22d3ee', '#06b6d4', '#0891b2'])}`),
  'destinations/generic': () => wrap('Travel destination', sky('s', [[0, '#c7d2fe'], [0.6, '#a5f3fc'], [1, '#bbf7d0']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(600, 160, 42, '#fff')}${hills(300, ['#818cf8', '#6366f1', '#4f46e5'])}`),
  'hero/beach': () => wrap('Beach hero', sky('s', [[0, '#c7d2fe'], [0.5, '#fbcfe8'], [1, '#fde68a']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(620, 170, 54, '#fff7cc')}${waves(290, ['#7dd3fc', '#38bdf8', '#0ea5e9'])}${palms(660, 1.1)}${palms(740, 0.8)}<path d="M0 440 Q200 410 420 445 T800 425 V${H} H0Z" fill="#fde68a"/>`),
  'auth/mountains': () => wrap('Mountain lake', sky('s', [[0, '#a5b4fc'], [0.5, '#bae6fd'], [1, '#e0f2fe']]), `<rect width="${W}" height="${H * 1.2}" fill="url(#s)"/>${mountains(260, ['#c7d2fe', '#818cf8', '#4338ca'], true)}<path d="M0 340 H800 V500 H0Z" fill="#0e7490"/><path d="M0 340 H800 V380 H0Z" fill="#22d3ee" opacity=".5"/>${hills(380, ['#166534'])}`),
  'auth/beach': () => wrap('Beach sunset', sky('s', [[0, '#818cf8'], [0.5, '#f9a8d4'], [1, '#fdba74']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(400, 250, 60, '#fff1b8')}${waves(300, ['#38bdf8', '#0ea5e9', '#0369a1'])}${palms(90, 1.2)}<path d="M0 440 Q200 410 420 445 T800 425 V${H} H0Z" fill="#fcd34d"/>`),
  'auth/lake': () => wrap('Calm lake', sky('s', [[0, '#c7d2fe'], [1, '#a7f3d0']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${mountains(300, ['#a5b4fc', '#6366f1'])}<path d="M0 320 H800 V500 H0Z" fill="#0f766e"/>`),
  'auth/santorini': () => wrap('Santorini', sky('s', [[0, '#fbcfe8'], [0.5, '#c4b5fd'], [1, '#93c5fd']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${sun(600, 150, 44, '#fff7ed')}${waves(300, ['#3b82f6', '#2563eb', '#1d4ed8'])}<g fill="#fff"><rect x="60" y="300" width="150" height="140"/><rect x="230" y="330" width="120" height="110"/><rect x="370" y="310" width="140" height="130"/></g><g fill="#2563eb"><path d="M85 300 a50 50 0 0 1 100 0Z"/><path d="M255 330 a35 35 0 0 1 70 0Z"/></g><circle cx="40" cy="440" r="40" fill="#ec4899"/><circle cx="120" cy="470" r="34" fill="#f472b6"/>`),
}

// dark-theme subtle texture for studio hero cards
scenes['studio/night'] = () => wrap('Night sky', sky('s', [[0, '#0b0e17'], [1, '#1e1b4b']]), `<rect width="${W}" height="${H}" fill="url(#s)"/>${stars(60)}`)

for (const [name, build] of Object.entries(scenes)) {
  const file = join(root, `${name}.svg`)
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, build())
}
console.log(`Wrote ${Object.keys(scenes).length} SVG assets to ${root}`)
