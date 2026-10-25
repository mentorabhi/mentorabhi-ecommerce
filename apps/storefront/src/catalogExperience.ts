export type Currency = 'INR' | 'USD'
export type Sku = { id: string; code: string; attributes: Record<string, string>; assetKey: string; altText: string }
export type ProductDetails = {
  model?: string; equipmentType?: string; highlights?: string[]; material?: string; intendedUse?: string
  fit?: string; care?: string; packageContents?: string[]; commerceProvenance?: string
  provenance?: { sourceUrl: string; capturedOn: string; rightsStatement: string }
  gallery?: { assetKey: string; altText: string; kind: string }[]
}
export type Product = { id: string; categoryId: string; sportId?: string; slug: string; title: string; brand: string; description: string; details?: ProductDetails; skus: Sku[] }
export type CatalogPage = { items: Product[]; page: number; pageSize: number; total: number; hasNext: boolean }
export type RatingSummary = { productId: string; mean: number | null; count: number; histogram: Record<string, number> }
export type PublicReview = { reviewId: string; rating: number; title: string; body: string; createdAt: string; origin: 'CUSTOMER' | 'DEMO'; verifiedDelivered: boolean }

export function batches<T>(items: T[]): T[][] {
  const result: T[][] = []
  for (let index = 0; index < items.length; index += 100) result.push(items.slice(index, index + 100))
  return result
}

export function catalogQuery(page: number, query: string, category: string): string {
  const params = new URLSearchParams({ page: String(page), pageSize: '24' })
  if (query.trim()) params.set('q', query.trim())
  if (category) params.set('category', category)
  return params.toString()
}

export function uniqueSkuIds(products: Product[]): string[] {
  return [...new Set(products.flatMap(product => product.skus.map(sku => sku.id)))]
}

export function minimumPrice(product: Product, prices: Record<string, number>): number | undefined {
  const values = product.skus.map(sku => prices[sku.id]).filter(value => Number.isFinite(value))
  return values.length ? Math.min(...values) : undefined
}

export function ratingText(summary?: RatingSummary): string {
  if (!summary) return 'Ratings unavailable'
  return summary.count > 0 && summary.mean !== null ? `${summary.mean.toFixed(1)} out of 5 · ${summary.count} reviews` : 'No reviews yet'
}

export function reviewBadge(review: PublicReview): string {
  return review.origin === 'DEMO' ? 'Demo review' : review.verifiedDelivered ? 'Verified delivered purchase' : 'Customer review'
}

export function productPhotos(product: Product, sku?: Sku): { assetKey: string; altText: string }[] {
  const photos = [...(sku ? [{ assetKey: sku.assetKey, altText: sku.altText }] : []), ...(product.details?.gallery ?? [])]
  return photos.filter((photo, index) => photos.findIndex(other => other.assetKey === photo.assetKey) === index)
}
