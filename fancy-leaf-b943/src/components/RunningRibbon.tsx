import { useToolCalls } from '../store/toolCalls.state'
import '../styles/ribbon.css'

export function RunningRibbon() {
  const ribbonCount = useToolCalls((state) => state.ribbonCount)
  
  if (ribbonCount <= 0) return null
  
  return (
    <div 
      className="ribbon fixed top-0 left-0 right-0 h-[3px] z-50 pointer-events-none"
      aria-hidden="true"
    />
  )
}