import { strict as assert } from 'node:assert'
import { test } from 'node:test'
import { historyPresentation } from '../src/orderFreshness.ts'

test('only a connected caught-up nonempty projection is preferred over current store records', () => {
  assert.equal(historyPresentation({ state: 'CURRENT', checkedAt: null, pendingOwnEvents: 0, gapSince: null }, 1).preferProjection, true)
  assert.equal(historyPresentation({ state: 'CURRENT', checkedAt: null, pendingOwnEvents: 0, gapSince: null }, 0).preferProjection, false)
  for (const state of ['DELAYED', 'BLOCKED', 'UNAVAILABLE'] as const) {
    const view = historyPresentation({ state, checkedAt: null, pendingOwnEvents: 1, gapSince: null }, 2)
    assert.equal(view.preferProjection, false)
    assert.match(view.message, /Showing current store records/)
  }
})

test('missing streaming status is explicit and does not masquerade as an empty order list', () => {
  const view = historyPresentation(undefined, 0)
  assert.equal(view.state, 'UNAVAILABLE')
  assert.equal(view.preferProjection, false)
  assert.match(view.message, /temporarily unavailable/)
})
