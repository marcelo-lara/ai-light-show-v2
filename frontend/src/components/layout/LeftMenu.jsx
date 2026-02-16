import { Link } from 'preact-router/match'

function MenuIcon({ name }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: '0 0 24 24',
    fill: 'none',
    xmlns: 'http://www.w3.org/2000/svg',
  }

  if (name === 'home') {
    return (
      <svg {...common}>
        <path
          d="M3 10.5L12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10.5z"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linejoin="round"
        />
      </svg>
    )
  }

  if (name === 'dmx') {
    return (
      <svg {...common}>
        <path
          d="M4 7h16M4 12h16M4 17h16"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        />
        <path
          d="M8 7v10M16 12v5"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        />
      </svg>
    )
  }

  if (name === 'builder') {
    return (
      <svg {...common}>
        <path
          d="M4 6h16M4 12h10M4 18h16"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
        />
        <path
          d="M16.5 10.5l3 3-6 6H10.5v-3l6-6z"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linejoin="round"
        />
      </svg>
    )
  }

  return null
}

function MenuItem({ to, icon, label }) {
  return (
    <Link href={to} activeClassName="leftMenuItemActive" class="leftMenuItem" aria-label={label}>
      <MenuIcon name={icon} />
    </Link>
  )
}

export default function LeftMenu() {
  return (
    <nav class="leftMenu" aria-label="Main">
      <div class="leftMenuTop">
        <MenuItem to="/show" icon="home" label="Show Control" />
        <MenuItem to="/dmx" icon="dmx" label="DMX Controller" />
        <MenuItem to="/builder" icon="builder" label="Show Builder" />
      </div>
    </nav>
  )
}
