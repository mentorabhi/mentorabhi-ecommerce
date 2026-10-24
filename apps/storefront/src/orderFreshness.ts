export type OrderFreshness = {
  state: 'CURRENT' | 'DELAYED' | 'BLOCKED' | 'UNAVAILABLE'
  checkedAt: string | null
  pendingOwnEvents: number
  gapSince: string | null
}

const messages = {
  CURRENT: 'Order updates are connected. Changes may take a moment.',
  DELAYED: 'Order updates are catching up. Showing current store records.',
  BLOCKED: 'Some order updates need attention. Showing current store records.',
  UNAVAILABLE: 'Live order updates are temporarily unavailable. Showing current store records.',
}

export function historyPresentation(freshness: OrderFreshness | undefined, orderCount: number) {
  const state = freshness?.state ?? 'UNAVAILABLE'
  return { state, message: messages[state], preferProjection: state === 'CURRENT' && orderCount > 0 }
}
