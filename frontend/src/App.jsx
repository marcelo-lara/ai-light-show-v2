import { Router } from 'preact-router'

import { AppStateProvider } from './app/state.jsx'
import AppShell from './layout/AppShell.jsx'
import RightPanel from './layout/RightPanel.jsx'

import RedirectToShow from './pages/RedirectToShow.jsx'
import ShowControlPage from './pages/ShowControlPage.jsx'
import DmxControllerPage from './pages/DmxControllerPage.jsx'
import ShowBuilderPage from './pages/ShowBuilderPage.jsx'

export function App() {
  return (
    <AppStateProvider>
      <AppShell rightPanel={<RightPanel />}>
        <Router>
          <RedirectToShow path="/" />
          <ShowControlPage path="/show" />
          <DmxControllerPage path="/dmx" />
          <ShowBuilderPage path="/builder" />
        </Router>
      </AppShell>
    </AppStateProvider>
  )
}
