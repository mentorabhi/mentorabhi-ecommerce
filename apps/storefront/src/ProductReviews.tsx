import { useEffect, useState } from 'react'
import { ratingText, reviewBadge } from './catalogExperience'
import type { Product, PublicReview, RatingSummary } from './catalogExperience'
import { request } from './storeApi'

type ReviewOrder = { id: string; createdAt: string; lines?: { productId: string; skuId: string; productTitle: string }[] }

export function Rating({ summary }: { summary?: RatingSummary }) {
  return <span className="product-rating" aria-label={ratingText(summary)}>
    {summary && summary.count > 0 && summary.mean !== null ? <><b>{summary.mean.toFixed(1)} ★</b><span>({summary.count})</span></> : <span>{ratingText(summary)}</span>}
  </span>
}

export default function ProductReviews({ product, token, signIn, onSummary }: {
  product: Product; token?: string; signIn: () => Promise<void>; onSummary: (summary: RatingSummary) => void
}) {
  const [reviews, setReviews] = useState<PublicReview[]>([])
  const [summary, setSummary] = useState<RatingSummary>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [writing, setWriting] = useState(false)
  const [orders, setOrders] = useState<ReviewOrder[]>([])
  const [order, setOrder] = useState<ReviewOrder | null>(null)
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')

  const refresh = async () => {
    setLoading(true); setError('')
    try {
      const [rows, summaries] = await Promise.all([
        request<PublicReview[]>(`/api/reviews/reviews/products/${product.id}`),
        request<RatingSummary[]>(`/api/reviews/reviews/products/summaries?productIds=${product.id}`),
      ])
      setReviews(rows); setSummary(summaries[0]); if (summaries[0]) onSummary(summaries[0])
    } catch { setError('Reviews are temporarily unavailable. You can still browse and shop.') }
    finally { setLoading(false) }
  }
  useEffect(() => { void refresh() }, [product.id])
  useEffect(() => { setWriting(false); setOrders([]); setOrder(null); setMessage('') }, [token, product.id])

  const startWriting = async () => {
    if (!token) { await signIn(); return }
    setPending(true); setError('')
    try { setOrders(await request<ReviewOrder[]>('/api/orders', token)); setWriting(true) }
    catch { setError('Your orders could not be loaded. Please try again.') }
    finally { setPending(false) }
  }
  const selectOrder = async (id: string) => {
    setOrder(null); setMessage(''); if (!id || !token) return
    setPending(true)
    try { setOrder(await request<ReviewOrder>(`/api/orders/${id}`, token)) }
    catch { setError('That order could not be loaded.') }
    finally { setPending(false) }
  }
  const eligibleLines = order?.lines?.filter(line => line.productId === product.id) ?? []

  return <section className="product-reviews" id="reviews" aria-label="Ratings and reviews">
    <div className="reviews-heading"><div><span className="store-kicker">FROM THE COMMUNITY</span><h2>Ratings & reviews</h2><Rating summary={summary}/></div><div><button className="shop-secondary" disabled={loading} onClick={() => void refresh()}>Refresh reviews</button><button className="shop-primary" disabled={pending} onClick={() => void startWriting()}>Write a review</button></div></div>
    <p className="review-integrity">Demo reviews are labelled. Customer reviews require a delivered purchase and store moderation.</p>
    {error && <p role="alert" className="review-error">{error}</p>}
    {summary && summary.count > 0 && <div className="rating-histogram" aria-label="Rating distribution">{[5, 4, 3, 2, 1].map(star => <div key={star}><span>{star} ★</span><meter min="0" max={summary.count} value={summary.histogram[String(star)] ?? 0} aria-label={`${star} star reviews`}/><span>{summary.histogram[String(star)] ?? 0}</span></div>)}</div>}
    {loading ? <p role="status">Loading reviews…</p> : !reviews.length && !error ? <p>No published reviews yet. Share your experience after delivery.</p> : <div className="review-list">{reviews.map(review => <article className="review-card" key={review.reviewId}><div><b aria-label={`${review.rating} out of 5`}>{review.rating} ★</b><span className={`review-badge ${review.origin === 'DEMO' ? 'demo' : ''}`}>{reviewBadge(review)}</span><time dateTime={review.createdAt}>{new Date(review.createdAt).toLocaleDateString('en-IN')}</time></div><h3>{review.title}</h3><p>{review.body}</p></article>)}</div>}
    {writing && <div className="write-review"><h3>Review your delivered item</h3><p>Choose your own order containing this model. Delivery and ownership are checked before submission; each purchased SKU can be reviewed once.</p><label>Purchase order<select aria-label="Review purchase order" defaultValue="" disabled={pending} onChange={event => void selectOrder(event.target.value)}><option value="">Select an order</option>{orders.map(item => <option key={item.id} value={item.id}>{item.id.slice(0, 8).toUpperCase()} · {new Date(item.createdAt).toLocaleDateString('en-IN')}</option>)}</select></label>{!orders.length && <p>No orders are available on this account yet.</p>}
      {order && !eligibleLines.length && <p>This order does not contain this model. Choose another order.</p>}
      {!!eligibleLines.length && <form className="review-form" onSubmit={event => {
        event.preventDefault(); const form = event.currentTarget; const data = new FormData(form)
        setPending(true); setError(''); setMessage('')
        void request('/api/reviews/customer/reviews', token, { method: 'POST', body: JSON.stringify({ orderId: order?.id, productId: product.id, skuId: data.get('skuId'), rating: Number(data.get('rating')), title: data.get('title'), body: data.get('body') }) })
          .then(() => { form.reset(); setMessage('Review submitted for moderation. It will appear publicly after publication.') })
          .catch(() => setError('Review could not be submitted. Check that delivery is complete and this item has not already been reviewed.'))
          .finally(() => setPending(false))
      }}><label>Purchased option<select name="skuId">{eligibleLines.map(line => <option key={line.skuId} value={line.skuId}>{product.skus.find(sku => sku.id === line.skuId)?.code ?? line.skuId.slice(0, 8)}</option>)}</select></label><label>Rating<select name="rating" defaultValue="5">{[5, 4, 3, 2, 1].map(rating => <option key={rating} value={rating}>{rating} out of 5</option>)}</select></label><label>Review title<input name="title" maxLength={120} required/></label><label>Your experience<textarea name="body" maxLength={2000} rows={4} required/></label><button className="shop-primary" disabled={pending}>Submit review</button></form>}
      {message && <p role="status" className="review-success">{message}</p>}
    </div>}
  </section>
}
