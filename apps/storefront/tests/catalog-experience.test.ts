import test from 'node:test'
import assert from 'node:assert/strict'
import { batches, catalogQuery, minimumPrice, productPhotos, ratingText, reviewBadge, uniqueSkuIds } from '../src/catalogExperience.ts'
import type { Product, PublicReview, RatingSummary } from '../src/catalogExperience.ts'

const product: Product = { id: 'model', categoryId: 'cricket', slug: 'bat', brand: 'Brand', title: 'Bat', description: 'Model', skus: [
  { id: 'small', code: 'S', attributes: { size: 'S' }, assetKey: 'photos/front.jpg', altText: 'Front' },
  { id: 'large', code: 'L', attributes: { size: 'L' }, assetKey: 'photos/back.jpg', altText: 'Back' },
] }

test('browse query preserves literal search, category and page', () => {
  const query = new URLSearchParams(catalogQuery(5, '  SG & 10%  ', 'cricket-equipment'))
  assert.equal(query.get('page'), '5'); assert.equal(query.get('pageSize'), '24')
  assert.equal(query.get('q'), 'SG & 10%'); assert.equal(query.get('category'), 'cricket-equipment')
  assert.equal(new URLSearchParams(catalogQuery(1, ' ', '')).has('q'), false)
})

test('saved and visible products share unique SKU batches bounded to owner API limits', () => {
  assert.deepEqual(uniqueSkuIds([product, product]), ['small', 'large'])
  const ids = Array.from({ length: 241 }, (_, index) => String(index))
  const chunks = batches(ids)
  assert.deepEqual(chunks.map(chunk => chunk.length), [100, 100, 41])
  assert.deepEqual(chunks.flat(), ids); assert.deepEqual(batches([]), [])
})

test('card starting price uses every known variant including zero, and never invents missing prices', () => {
  assert.equal(minimumPrice(product, { small: 4500, large: 3000 }), 3000)
  assert.equal(minimumPrice(product, { large: 0 }), 0)
  assert.equal(minimumPrice(product, {}), undefined)
})

test('unavailable ratings differ from a confirmed empty summary', () => {
  const summary: RatingSummary = { productId: 'model', mean: 4.25, count: 4, histogram: {} }
  assert.equal(ratingText(summary), '4.3 out of 5 · 4 reviews')
  assert.equal(ratingText({ ...summary, mean: null, count: 0 }), 'No reviews yet')
  assert.equal(ratingText(), 'Ratings unavailable')
})

test('demo origin cannot acquire a verified purchase badge', () => {
  const review: PublicReview = { reviewId: 'id', rating: 4, title: 'Demo', body: 'Demo', createdAt: '', origin: 'DEMO', verifiedDelivered: true }
  assert.equal(reviewBadge(review), 'Demo review')
  assert.equal(reviewBadge({ ...review, origin: 'CUSTOMER' }), 'Verified delivered purchase')
  assert.equal(reviewBadge({ ...review, origin: 'CUSTOMER', verifiedDelivered: false }), 'Customer review')
})

test('gallery starts at selected SKU and removes duplicate photo keys', () => {
  const detailed = { ...product, details: { gallery: [{ assetKey: 'photos/front.jpg', altText: 'Front', kind: 'photograph' }] } }
  assert.deepEqual(productPhotos(detailed, product.skus[0]).map(photo => photo.assetKey), ['photos/front.jpg'])
  assert.deepEqual(productPhotos(detailed, product.skus[1]).map(photo => photo.assetKey), ['photos/back.jpg', 'photos/front.jpg'])
})
