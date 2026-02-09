import LeftMenu from '../components/layout/LeftMenu.jsx'

export default function AppShell({ rightPanel, children }) {
  return (
    <div class="appShell">
      <LeftMenu />
      <main class="appMain" role="main">
        {children}
      </main>
      <aside class="rightPanel" aria-label="Right panel">
        {rightPanel}
      </aside>
    </div>
  )
}
