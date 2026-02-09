import { useEffect } from 'preact/hooks'
import { route } from 'preact-router'

export default function RedirectToShow() {
  useEffect(() => {
    route('/show', true)
  }, [])

  return null
}
