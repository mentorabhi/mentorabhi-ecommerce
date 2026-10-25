import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { User, UserManager, WebStorageStateStore } from 'oidc-client-ts'
import { historyPresentation } from './orderFreshness'
import type { OrderFreshness } from './orderFreshness'
import { batches, catalogQuery, minimumPrice, productPhotos, uniqueSkuIds } from './catalogExperience'
import type { CatalogPage, Currency, Product, RatingSummary, Sku } from './catalogExperience'
import ProductReviews, { Rating } from './ProductReviews'
import { request } from './storeApi'
import './customer.css'

const customerIdentity = new UserManager({
  authority: 'http://localhost:8180/realms/supersports-customers',
  client_id: 'supersports-customer-web',
  redirect_uri: `${window.location.origin}/signin-callback`,
  post_logout_redirect_uri: window.location.origin,
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
})

type Category = { id: string; slug: string; name: string }
type CartItem = { skuId: string; quantity: number; revision: number }
type Profile = { fullName: string; phone: string; line1: string; line2: string; city: string; state: string; postalCode: string; country: string; revision: number }

const formattedMoney = (minor: number, currency: Currency) => new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(minor / 100)
type Order = { id: string; state: string; currency: Currency; totalMinor: number; createdAt: string }
type OrderDetail = Order & { subtotalMinor: number; discountMinor: number; taxMinor: number; shippingMinor: number; addressSnapshot: Profile; lines: { skuId: string; productId:string; productTitle: string; quantity: number; unitPriceMinor: number; lineTotalMinor: number; currency: Currency }[] }
type CancellationEligibility = { eligible: boolean; reasonCode: string; shipmentRevision?: number }
type CancellationOperation = { operationId: string; status: string; currentStep?: string; errorCode?: string }
type ShipmentTracking={state:string;trackingId?:string;revision?:number;estimatedDeliveryAt?:string;transitions?:{state:string;reason?:string;createdAt?:string}[]}
type ReturnEligibility = { eligible: boolean; reasonCode: string; windowDays: number; policyRevision: number; returnableLines: { skuId: string; productTitle: string; returnableQuantity: number }[] }
type ReturnOperation = { returnId: string; status: string; currentStep?: string; amountMinor: number; currency: Currency; errorCode?: string }
const pageFromPath = () => window.location.pathname === '/cart' ? 'cart' : window.location.pathname === '/wishlist' ? 'wishlist' : window.location.pathname === '/account' ? 'account' : window.location.pathname === '/orders' ? 'orders' : 'shop'

export default function CustomerStore() {
  const [user, setUser] = useState<User | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [productCache, setProductCache] = useState<Record<string, Product>>({})
  const [ratings, setRatings] = useState<Record<string, RatingSummary>>({})
  const [detail, setDetail] = useState<Product | null>(null)
  const [similar, setSimilar] = useState<Product[]>([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [catalogLoading, setCatalogLoading] = useState(false)
  const [catalogPage, setCatalogPage] = useState(Math.max(1, Number(new URLSearchParams(location.search).get('page')) || 1))
  const [catalogTotal, setCatalogTotal] = useState(0)
  const [hasNextPage, setHasNextPage] = useState(false)
  const [routePath, setRoutePath] = useState(location.pathname)
  const similarRail = useRef<HTMLDivElement>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [metadataReady, setMetadataReady] = useState(false)
  const [priceBooks, setPriceBooks] = useState<Partial<Record<Currency, Record<string, number>>>>({})
  const [availability, setAvailability] = useState<Record<string, number>>({})
  const [currency, setCurrency] = useState<Currency>('INR')
  const [cart, setCart] = useState<CartItem[]>([])
  const [wishlist, setWishlist] = useState<string[]>([])
  const [profile, setProfile] = useState<Profile | null>(null)
  const [couponCode, setCouponCode] = useState('')
  const [orders, setOrders] = useState<Order[]>([])
  const [orderFreshness, setOrderFreshness] = useState<OrderFreshness>()
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null)
  const [selectedTracking, setSelectedTracking] = useState<ShipmentTracking|null>(null)
  const [cancellationEligibility, setCancellationEligibility] = useState<CancellationEligibility | null>(null)
  const [cancellationOperation, setCancellationOperation] = useState<CancellationOperation | null>(null)
  const [returnEligibility, setReturnEligibility] = useState<ReturnEligibility | null>(null)
  const [returnOperation, setReturnOperation] = useState<ReturnOperation | null>(null)
  const [page, setPage] = useState(pageFromPath)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState(new URLSearchParams(location.search).get('q') ?? '')
  const [appliedSearch, setAppliedSearch] = useState(new URLSearchParams(location.search).get('q') ?? '')
  const [categoryFilter, setCategoryFilter] = useState(new URLSearchParams(location.search).get('category') ?? '')
  const [sort, setSort] = useState('featured')
  const token = user?.access_token
  const activeToken = useRef(token)
  activeToken.current = token
  const prices = priceBooks[currency] ?? {}
  const detailSlug = routePath.startsWith('/products/') ? decodeURIComponent(routePath.slice('/products/'.length)) : ''
  const selectedCategory = categories.find((category) => category.id === categoryFilter || category.slug === categoryFilter)

  useEffect(() => {
    void Promise.all([request<Category[]>('/api/catalog/categories'), request<{ code: Currency }>('/api/pricing/currency')])
      .then(([cats, active]) => { setCategories(cats); setCurrency(active.code); setMetadataReady(true) })
      .catch(() => setError('Store settings could not be loaded. Refresh to try again.'))
  }, [])

  useEffect(() => {
    const restore = async () => {
      try {
        if (location.pathname === '/signin-callback') {
          setUser(await customerIdentity.signinRedirectCallback())
          history.replaceState({}, document.title, '/')
        } else setUser(await customerIdentity.getUser())
      } catch { setError('Sign-in could not be completed. Please try again.') }
      finally { setAuthReady(true) }
    }
    void restore()
    const loaded = (next: User) => setUser(next)
    const unloaded = () => setUser(null)
    customerIdentity.events.addUserLoaded(loaded)
    customerIdentity.events.addUserUnloaded(unloaded)
    return () => { customerIdentity.events.removeUserLoaded(loaded); customerIdentity.events.removeUserUnloaded(unloaded) }
  }, [])

  const rememberProducts = (items: Product[]) => setProductCache(current => ({ ...current, ...Object.fromEntries(items.map(item => [item.id, item])) }))
  const hydrate = async (items: Product[], code: Currency) => {
    rememberProducts(items)
    const ids = uniqueSkuIds(items)
    const summaryWork = Promise.all(batches([...new Set(items.map(item => item.id))]).map(async batch => {
      try {
        const rows = await request<RatingSummary[]>(`/api/reviews/reviews/products/summaries?productIds=${batch.join(',')}`)
        setRatings(current => ({ ...current, ...Object.fromEntries(rows.map(row => [row.productId, row])) }))
      } catch { setError('Ratings are temporarily unavailable. Product browsing is still available.') }
    }))
    const stockWork = (async () => {
      for (const batch of batches(ids)) {
        const joined = encodeURIComponent(batch.join(','))
        const [batchPrices, batchStock] = await Promise.all([
          request<{ skuId: string; amountMinor: number; currency: Currency }[]>(`/api/pricing/public/skus?skuIds=${joined}`),
          request<{ skuId: string; available: number }[]>(`/api/inventory/availability?skuIds=${joined}`),
        ])
        if (batchPrices.some(price => price.currency !== code)) throw new Error('Store currency changed. Refresh to see current prices.')
        setPriceBooks(current => ({ ...current, [code]: { ...current[code], ...Object.fromEntries(batchPrices.map(price => [price.skuId, price.amountMinor])) } }))
        setAvailability(current => ({ ...current, ...Object.fromEntries(batchStock.map(stock => [stock.skuId, stock.available])) }))
      }
    })()
    await Promise.all([summaryWork, stockWork])
  }

  useEffect(() => {
    if (!metadataReady || page !== 'shop' || detailSlug) return
    let current = true
    setCatalogLoading(true)
    void (async () => {
      const result = await request<CatalogPage>(`/api/catalog/public/products?${catalogQuery(catalogPage, appliedSearch, categoryFilter)}`)
      if (!current) return
      setProducts(result.items); setCatalogTotal(result.total); setHasNextPage(result.hasNext)
      await hydrate(result.items, currency)
    })().catch((e: Error) => { if (current) setError(e.message) }).finally(() => { if (current) setCatalogLoading(false) })
    return () => { current = false }
  }, [categoryFilter, appliedSearch, catalogPage, metadataReady, currency, page, detailSlug])

  useEffect(() => {
    let current = true
    setDetail(null); setSimilar([])
    if (!detailSlug || !metadataReady) return
    setDetailLoading(true)
    void (async () => {
      const [model, related] = await Promise.all([
        request<Product>(`/api/catalog/public/products/${encodeURIComponent(detailSlug)}`),
        request<Product[]>(`/api/catalog/public/products/${encodeURIComponent(detailSlug)}/similar?limit=12`),
      ])
      if (!current) return
      setDetail(model); setSimilar(related)
      await hydrate([model, ...related], currency)
    })().catch(() => { if (current) setError('This product could not be loaded. It may no longer be available.') }).finally(() => { if (current) setDetailLoading(false) })
    return () => { current = false }
  }, [detailSlug, currency, metadataReady])

  const refreshCustomer = async (accessToken = token) => {
    if (!accessToken) { setCart([]); setWishlist([]); setProfile(null); return }
    const [items, saved, address] = await Promise.all([
      request<CartItem[]>('/api/customer/cart', accessToken),
      request<{ skuId: string }[]>('/api/customer/wishlist', accessToken),
      request<Profile>('/api/customer/profile', accessToken),
    ])
    if (accessToken !== activeToken.current) return
    setCart(items); setWishlist(saved.map((item) => item.skuId)); setProfile(address)
    const ids = [...new Set([...items.map(item => item.skuId), ...saved.map(item => item.skuId)])]
    for (const batch of batches(ids)) {
      const models = await request<Product[]>(`/api/catalog/public/products/by-skus?skuIds=${batch.join(',')}`)
      const returned = new Set(models.map(model => model.id))
      setProductCache(current => Object.fromEntries(Object.entries(current).filter(([id, model]) => returned.has(id) || !model.skus.some(sku => batch.includes(sku.id)))))
      await hydrate(models, currency)
    }
  }

  useEffect(() => { if (authReady && metadataReady) void refreshCustomer().catch((e: Error) => setError(e.message)) }, [token, authReady, metadataReady, currency])

  const visibleProducts = useMemo(() => {
    const selected = products.filter((product) => !selectedCategory || product.categoryId === selectedCategory.id)
    if (sort === 'price-low') return [...selected].sort((a, b) => (minimumPrice(a, prices) ?? Infinity) - (minimumPrice(b, prices) ?? Infinity))
    if (sort === 'price-high') return [...selected].sort((a, b) => (minimumPrice(b, prices) ?? -Infinity) - (minimumPrice(a, prices) ?? -Infinity))
    if (sort === 'name') return [...selected].sort((a, b) => a.title.localeCompare(b.title))
    return selected
  }, [products, categoryFilter, selectedCategory, sort, prices])

  const act = async (work: () => Promise<void>, success?: string) => {
    setBusy(true); setError(''); setMessage('')
    try { await work(); if (success) setMessage(success); await refreshCustomer() }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save your changes.') }
    finally { setBusy(false) }
  }

  const synchronizeRoute = () => {
    setRoutePath(location.pathname); setPage(pageFromPath())
    const params = new URLSearchParams(location.search)
    setSearch(params.get('q') ?? ''); setAppliedSearch(params.get('q') ?? ''); setCategoryFilter(params.get('category') ?? '')
    setCatalogPage(Math.max(1, Number(params.get('page')) || 1))
  }
  const navigate = (next: string, href: string) => {
    history.pushState({}, '', href); synchronizeRoute(); setPage(next); setMessage(''); setError(''); window.scrollTo(0, 0)
  }
  useEffect(() => { addEventListener('popstate', synchronizeRoute); return () => removeEventListener('popstate', synchronizeRoute) }, [])
  const allSkus = Object.values(productCache).flatMap((product) => product.skus.map((sku) => ({ product, sku })))
  const savedItems = allSkus.filter(({ sku }) => wishlist.includes(sku.id))
  const cartItems: (CartItem & { product: Product; sku: Sku })[] = cart.flatMap((item) => {
    const match = allSkus.find(({ sku }) => sku.id === item.skuId)
    return match ? [{ ...item, ...match }] : []
  })
  const unavailableCartItems = cart.filter((item) => !allSkus.some(({ sku }) => sku.id === item.skuId))

  const refreshOrders = async () => {
    if (!token) { setOrders([]); setOrderFreshness(undefined); return }
    try {
      const result = await request<{ orders: Order[]; freshness: OrderFreshness }>('/api/order-history', token)
      setOrderFreshness(result.freshness)
      if (historyPresentation(result.freshness, result.orders.length).preferProjection) { setOrders(result.orders); return }
    } catch { setOrderFreshness(undefined) }
    setOrders(await request<Order[]>('/api/orders', token))
  }
  const historyView = historyPresentation(orderFreshness, orders.length)
  const openOrder = async (orderId: string) => { if (!token) return; const detail = await request<OrderDetail>(`/api/orders/${orderId}`, token); const tracking = await request<{tracking:ShipmentTracking}>(`/api/orders/${orderId}/tracking`, token); setSelectedTracking(tracking.tracking); const visibleDetail = tracking.tracking?.state === 'DELIVERED' ? { ...detail, state: 'DELIVERED' } : detail; setSelectedOrder(visibleDetail); setOrders((current) => current.map((order) => order.id === orderId ? { ...order, state: visibleDetail.state } : order)); setCancellationOperation(null); setReturnOperation(null); setCancellationEligibility(detail.state === 'FULFILLMENT_SCHEDULED' ? await request<CancellationEligibility>(`/api/orders/${orderId}/cancellation-eligibility`, token) : null); setReturnEligibility(tracking.tracking?.state === 'DELIVERED' ? await request<ReturnEligibility>(`/api/orders/${orderId}/returns/eligibility`, token) : null) }
  const requestCancellation = async () => {
    if (!token || !selectedOrder) return
    const keySlot = `supersports-cancel-${selectedOrder.id}`
    let idempotencyKey = sessionStorage.getItem(keySlot)
    if (!idempotencyKey) { idempotencyKey = crypto.randomUUID(); sessionStorage.setItem(keySlot, idempotencyKey) }
    const result = await request<CancellationOperation & { orderId: string }>(`/api/orders/${selectedOrder.id}/cancellations`, token, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ reasonCode: 'CUSTOMER_REQUEST' }) })
    setCancellationOperation(result); setCancellationEligibility({ eligible: false, reasonCode: 'CANCELLATION_PENDING' })
  }
  const requestReturn = async (skuId: string) => {
    if (!token || !selectedOrder) return
    const keySlot = `supersports-return-${selectedOrder.id}-${skuId}`
    let idempotencyKey = sessionStorage.getItem(keySlot)
    if (!idempotencyKey) { idempotencyKey = crypto.randomUUID(); sessionStorage.setItem(keySlot, idempotencyKey) }
    const result = await request<ReturnOperation>(`/api/orders/${selectedOrder.id}/returns`, token, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify({ lines: [{ skuId, quantity: 1 }] }) })
    sessionStorage.removeItem(keySlot)
    setReturnOperation(result)
    setSelectedOrder(await request<OrderDetail>(`/api/orders/${selectedOrder.id}`, token))
    setReturnEligibility(await request<ReturnEligibility>(`/api/orders/${selectedOrder.id}/returns/eligibility`, token))
  }
  const checkout = async () => {
    if (!token) { await customerIdentity.signinRedirect(); return }
    if (!cart.length || unavailableCartItems.length) throw new Error('Remove unavailable items before checkout.')
    if (!profile?.fullName || !profile.line1 || !profile.city || !profile.state || !profile.postalCode) throw new Error('Add your Indian delivery address in Account before checkout.')
    const payload = { lines: cart.map((item) => ({ skuId: item.skuId, quantity: item.quantity })), couponCode: couponCode.trim() || null }
    const keySlot = `supersports-checkout-${JSON.stringify(payload)}`
    let idempotencyKey = sessionStorage.getItem(keySlot)
    if (!idempotencyKey) { idempotencyKey = crypto.randomUUID(); sessionStorage.setItem(keySlot, idempotencyKey) }
    const result = await request<{ orderId: string; state: string; totalMinor: number }>('/api/orders/checkout', token, { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: JSON.stringify(payload) })
    await refreshOrders(); navigate('orders', '/orders'); setMessage(`Order accepted for processing · ${result.state} · ${formattedMoney(result.totalMinor, currency)}`)
  }
  useEffect(() => { if (page === 'orders' && token) void refreshOrders().catch((e: Error) => setError(e.message)) }, [page, token])
  useEffect(() => { if (page !== 'orders' || !token) return; const timer = window.setInterval(() => void refreshOrders().catch((e: Error) => setError(e.message)), 1500); return () => window.clearInterval(timer) }, [page, token])
  useEffect(() => {
    if (!selectedOrder || !token || ['CANCELLED', 'FAILED', 'MANUAL_REVIEW'].includes(selectedOrder.state)) return
    const orderId = selectedOrder.id
    const timer = window.setInterval(() => {
      void Promise.all([request<OrderDetail>(`/api/orders/${orderId}`,token),request<{tracking:ShipmentTracking}>(`/api/orders/${orderId}/tracking`,token)]).then(([updated,result])=>{
        setSelectedTracking(result.tracking);const view=result.tracking?.state==='DELIVERED'?{...updated,state:'DELIVERED'}:updated
        setSelectedOrder((current)=>current?.id===orderId?view:current);setOrders((current)=>current.map((order)=>order.id===orderId?{...order,state:view.state}:order))
      }).catch(()=>undefined)
    }, 1500)
    return () => window.clearInterval(timer)
  }, [selectedOrder?.id, selectedOrder?.state, token])
  useEffect(() => {
    if (!selectedOrder || !token || !cancellationOperation || ['COMPLETED', 'REJECTED', 'MANUAL_REVIEW'].includes(cancellationOperation.status)) return
    const orderId = selectedOrder.id, operationId = cancellationOperation.operationId
    const timer = window.setInterval(() => { void request<CancellationOperation>(`/api/orders/${orderId}/cancellations/${operationId}`, token).then(async (status) => { setCancellationOperation(status); if (status.status === 'COMPLETED') { const updated = await request<OrderDetail>(`/api/orders/${orderId}`, token); setSelectedOrder((current) => current?.id === orderId ? updated : current); setOrders((current) => current.map((order) => order.id === orderId ? { ...order, state: updated.state } : order)) } }).catch(() => undefined) }, 1500)
    return () => window.clearInterval(timer)
  }, [selectedOrder?.id, token, cancellationOperation?.operationId, cancellationOperation?.status])
  useEffect(() => {
    if (!selectedOrder || !token || !returnOperation || ['COMPLETED', 'MANUAL_REVIEW'].includes(returnOperation.status)) return
    const orderId = selectedOrder.id, returnId = returnOperation.returnId
    const timer = window.setInterval(() => { void request<ReturnOperation>(`/api/orders/${orderId}/returns/${returnId}`, token).then(async (status) => { setReturnOperation(status); if (status.status === 'COMPLETED') { setSelectedOrder(await request<OrderDetail>(`/api/orders/${orderId}`, token)); setReturnEligibility(await request<ReturnEligibility>(`/api/orders/${orderId}/returns/eligibility`, token)) } }).catch(() => undefined) }, 1500)
    return () => window.clearInterval(timer)
  }, [selectedOrder?.id, token, returnOperation?.returnId, returnOperation?.status])

  if (!authReady) return <main className="store-loading" aria-live="polite">Loading SuperSports…</main>

  return <div className="shop-shell">
    <div className="shop-topline">FREE LOCAL DELIVERY SIMULATION <span>·</span> PLAY. TRAIN. LIVE BETTER.</div>
    <header className="shop-header">
      <a href="/" className="shop-brand" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}><img src="/brand/supersports-icon.jpg" alt=""/><span>Super<strong>Sports</strong></span></a>
      <form className="shop-search" onSubmit={(e) => { e.preventDefault(); const params = new URLSearchParams(); if (search) params.set('q', search); if (categoryFilter) params.set('category', categoryFilter); navigate('shop', `/?${params}`) }}><label className="sr-only" htmlFor="store-search">Search sports gear</label><input id="store-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search cricket, football and more"/><button aria-label="Search products">⌕</button></form>
      <nav aria-label="Shopping" className="shop-actions"><a href="/wishlist" onClick={(e) => { e.preventDefault(); navigate('wishlist', '/wishlist') }}>Wishlist <span>{wishlist.length}</span></a><a href="/cart" onClick={(e) => { e.preventDefault(); navigate('cart', '/cart') }}>Cart <span>{cart.length}</span></a>{user && <><a href="/orders" onClick={(e) => { e.preventDefault(); navigate('orders', '/orders') }}>Orders</a><a href="/account#support" onClick={(e) => { e.preventDefault(); navigate('account', '/account#support') }}>Support</a></>}<a href="/account" onClick={(e) => { e.preventDefault(); navigate('account', '/account') }}>{user ? 'Account' : 'Sign in'}</a></nav>
    </header>
    <nav className="category-nav" aria-label="Sports categories"><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }} className={!categoryFilter ? 'active' : ''}>All gear</a>{categories.map((category) => <a key={category.id} href={`/?category=${category.slug}`} className={categoryFilter === category.id || categoryFilter === category.slug ? 'active' : ''} onClick={(e) => { e.preventDefault(); navigate('shop', `/?category=${category.slug}`) }}>{category.name}</a>)}<span className="store-currency">Prices in {currency}</span></nav>
    <main className="shop-content">
      {error && <div className="store-alert error" role="alert">{error}<button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
      {message && <div className="store-alert success" role="status">{message}<button onClick={() => setMessage('')} aria-label="Dismiss message">×</button></div>}
      {page === 'orders' && token && <div className={`order-update-status status-${historyView.state.toLowerCase()}`} role="status" aria-live="polite" data-freshness-state={historyView.state}><strong>{historyView.message}</strong>{orderFreshness?.checkedAt && <small>Checked {new Date(orderFreshness.checkedAt).toLocaleTimeString('en-IN')}</small>}</div>}
      {detailSlug ? detail ? <><ProductDetail key={detail.id} product={detail} summary={ratings[detail.id]} currency={currency} prices={prices} availability={availability} wishlist={wishlist} busy={busy} addCart={(skuId) => act(async () => { if (!user) { await customerIdentity.signinRedirect(); return } const currentQuantity = cart.find((item) => item.skuId === skuId)?.quantity ?? 0; if (currentQuantity >= 99) throw new Error('A maximum of 99 units can be added per item.'); await request(`/api/customer/cart/items/${skuId}`, token, { method: 'PUT', body: JSON.stringify({ quantity: currentQuantity + 1 }) }) }, 'Added to your cart.')} toggleWishlist={(skuId) => act(async () => { if (!user) { await customerIdentity.signinRedirect(); return } await request(`/api/customer/wishlist/items/${skuId}`, token, { method: wishlist.includes(skuId) ? 'DELETE' : 'POST' }) }, wishlist.includes(skuId) ? 'Removed from wishlist.' : 'Saved to your wishlist.')} />
        <ProductReviews key={`${detail.id}:${user?.profile.sub ?? 'guest'}`} product={detail} token={token} signIn={() => customerIdentity.signinRedirect()} onSummary={summary => setRatings(current => ({ ...current, [summary.productId]: summary }))}/>
        {!!similar.length && <section className="similar-products" aria-label="Similar products"><div className="similar-heading"><div><span className="store-kicker">KEEP EXPLORING</span><h2>Similar products</h2></div><div><button className="similar-arrow" aria-label="Previous similar products" onClick={() => similarRail.current?.scrollBy({ left: -600, behavior: 'smooth' })}>←</button><button className="similar-arrow" aria-label="Next similar products" onClick={() => similarRail.current?.scrollBy({ left: 600, behavior: 'smooth' })}>→</button></div></div><div className="similar-rail" ref={similarRail} tabIndex={0} role="list" aria-label="Similar products; use arrow keys to scroll" onKeyDown={event => { if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') { event.preventDefault(); similarRail.current?.scrollBy({ left: event.key === 'ArrowRight' ? 300 : -300, behavior: 'smooth' }) } }}>{similar.map(model => <div role="listitem" className="similar-item" key={model.id}><ProductCard product={model} summary={ratings[model.id]} currency={currency} price={minimumPrice(model, prices)} availability={availability[model.skus[0]?.id]} open={() => navigate('detail', `/products/${model.slug}`)}/></div>)}</div></section>}
        </> : <p className="store-empty" role="status">{detailLoading ? 'Loading product…' : 'That product is not available.'}</p>
      : page === 'shop' ? <>
        <div className="collection-heading" id="products"><div><span>THE SUPERSPORTS EDIT</span><h1>{appliedSearch ? `Results for “${appliedSearch}”` : selectedCategory?.name ?? 'Ready when you are.'}</h1><p>{catalogTotal} products · Page {catalogPage} · Free local delivery simulation</p></div><label>Sort this page <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="featured">Featured</option><option value="name">Name</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></label></div>
        {visibleProducts.length ? <div className="store-product-grid">{visibleProducts.map((product) => <ProductCard key={product.id} product={product} currency={currency} summary={ratings[product.id]} price={minimumPrice(product, prices)} availability={availability[product.skus[0]?.id]} open={() => { navigate('detail', `/products/${product.slug}`) }} />)}</div> : <div className="store-empty"><h2>No matching gear yet</h2><p>Try another search or category.</p></div>}
        <nav className="catalog-pagination" aria-label="Product pages"><button className="shop-secondary" disabled={catalogPage === 1 || catalogLoading} onClick={() => { const params = new URLSearchParams(location.search); params.set('page', String(catalogPage - 1)); navigate('shop', `/?${params}`) }}>← Previous</button><span role="status">{catalogLoading ? 'Loading gear…' : `Page ${catalogPage} of ${Math.max(1, Math.ceil(catalogTotal / 24))}`}</span><button className="shop-secondary" disabled={!hasNextPage || catalogLoading} onClick={() => { const params = new URLSearchParams(location.search); params.set('page', String(catalogPage + 1)); navigate('shop', `/?${params}`) }}>Next →</button></nav>
      </> : page === 'cart' ? <section className="customer-page"><span className="store-kicker">YOUR PICKS</span><h1>Your cart</h1><p className="store-lede">Prices and availability are snapshots; checkout revalidates them before creating an order.</p>{cart.length ? <><div className="cart-summary"><span>Estimated subtotal · display only</span><strong>{formattedMoney(cartItems.reduce((sum, item) => sum + (prices[item.skuId] ?? 0) * item.quantity, 0), currency)}</strong></div><div className="saved-list">{cartItems.map((item) => <article key={item.skuId} className="saved-row"><img src={`/${item.sku.assetKey}`} alt={item.sku.altText}/><div><a href={`/products/${item.product.slug}`} onClick={(e) => { e.preventDefault(); navigate('detail', `/products/${item.product.slug}`) }}>{item.product.title}</a><span>{item.sku.code} · {formattedMoney(prices[item.skuId] ?? 0, currency)}</span><label>Quantity <input type="number" min="1" max="99" value={item.quantity} onChange={(e) => { const quantity = Number(e.target.value); if (quantity >= 1 && quantity <= 99) void act(async () => { await request(`/api/customer/cart/items/${item.skuId}`, token, { method: 'PUT', body: JSON.stringify({ quantity }) }) }) }}/></label></div><button className="link-button" onClick={() => void act(async () => { await request(`/api/customer/cart/items/${item.skuId}`, token, { method: 'DELETE' }) }, 'Removed from cart.')}>Remove</button></article>)}</div>{unavailableCartItems.map((item) => <div className="stale-cart" key={item.skuId}><span>This product is no longer available · {item.skuId}</span><button className="link-button" onClick={() => void act(async () => { await request(`/api/customer/cart/items/${item.skuId}`, token, { method: 'DELETE' }) }, 'Removed unavailable item.')}>Remove</button></div>)}</> : <div className="store-empty"><h2>Your cart is ready for a first pick.</h2><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}>Explore sports gear</a></div>}</section>
      : page === 'wishlist' ? <section className="customer-page"><span className="store-kicker">SAVED FOR LATER</span><h1>Your wishlist</h1>{savedItems.length ? <div className="store-product-grid">{savedItems.map(({ product, sku }) => <ProductCard key={sku.id} product={{ ...product, skus: [sku] }} currency={currency} summary={ratings[product.id]} price={prices[sku.id]} availability={availability[sku.id]} open={() => { navigate('detail', `/products/${product.slug}`) }} action={<button className="link-button" onClick={() => void act(async () => { await request(`/api/customer/wishlist/items/${sku.id}`, token, { method: 'DELETE' }) }, 'Removed from wishlist.')}>Remove</button>} />)}</div> : <div className="store-empty"><h2>Keep your favourites close.</h2><p>Save gear from a product page and it will be here next time.</p><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}>Browse gear</a></div>}</section>
      : <section className="customer-page"><span className="store-kicker">YOUR DETAILS</span><h1>Your profile</h1>{!user ? <div className="profile-prompt"><p>Sign in or create a customer account to save your cart, wishlist and Indian delivery address.</p><button className="shop-primary" onClick={() => void customerIdentity.signinRedirect()}>Sign in or create account</button><small>Local self-registration · No payment information needed</small></div> : profile && <form className="address-form" onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); void act(async () => { const saved = await request<{ revision: number }>('/api/customer/profile', token, { method: 'PUT', body: JSON.stringify({ fullName: f.get('fullName'), phone: f.get('phone'), line1: f.get('line1'), line2: f.get('line2'), city: f.get('city'), state: f.get('state'), postalCode: f.get('postalCode'), country: 'IN', expectedRevision: profile.revision }) }); setProfile({ ...profile, fullName: String(f.get('fullName')), phone: String(f.get('phone')), line1: String(f.get('line1')), line2: String(f.get('line2')), city: String(f.get('city')), state: String(f.get('state')), postalCode: String(f.get('postalCode')), revision: saved.revision }) }, 'Your profile was saved.') }}><label>Full name<input name="fullName" required defaultValue={profile.fullName}/></label><label>Phone<input name="phone" type="tel" defaultValue={profile.phone}/></label><label>Address line 1<input name="line1" required defaultValue={profile.line1}/></label><label>Address line 2<input name="line2" defaultValue={profile.line2}/></label><label>City<input name="city" required defaultValue={profile.city}/></label><label>State<input name="state" required defaultValue={profile.state}/></label><label>PIN code<input name="postalCode" inputMode="numeric" pattern="[1-9][0-9]{5}" required defaultValue={profile.postalCode}/></label><label>Country<select value="IN" disabled><option value="IN">India</option></select></label><button className="shop-primary" disabled={busy}>Save profile and address</button><button type="button" className="link-button" onClick={() => void customerIdentity.signoutRedirect()}>Sign out</button></form>}</section>}
      {page === 'cart' && cart.length > 0 && <section className="checkout-actions"><label>Coupon code (optional)<input value={couponCode} onChange={(e) => setCouponCode(e.target.value)} placeholder="WELCOME10"/></label><button className="shop-primary" disabled={busy || !token || !profile?.fullName || !profile.line1 || !profile.city || !profile.state || !profile.postalCode || unavailableCartItems.length > 0} onClick={() => void act(checkout)}>{!token ? 'Sign in to checkout' : !profile?.line1 ? 'Add delivery address first' : busy ? 'Submitting…' : 'Place simulated order'}</button><small>No payment details are collected. Payment and delivery are local simulations.</small></section>}
      {page === 'orders' && <section className="customer-page"><span className="store-kicker">YOUR ACTIVITY</span><h1>Your orders</h1>{!token ? <div className="profile-prompt"><p>Sign in to view your orders.</p><button className="shop-primary" onClick={() => void customerIdentity.signinRedirect()}>Sign in</button></div> : selectedOrder ? <><button className="link-button" onClick={() => { setSelectedOrder(null); setCancellationEligibility(null); setCancellationOperation(null); setReturnEligibility(null); setReturnOperation(null) }}>← Back to orders</button><div className="order-detail"><span>Order {selectedOrder.id}</span><h2>{selectedOrder.state.replaceAll('_', ' ')}</h2>{selectedOrder.lines.map((line) => <div className="order-line" key={line.skuId}><span>{line.productTitle} × {line.quantity}</span><strong>{formattedMoney(line.lineTotalMinor, line.currency)}</strong></div>)}<div className="order-totals"><span>Subtotal <b>{formattedMoney(selectedOrder.subtotalMinor, selectedOrder.currency)}</b></span><span>Discount <b>−{formattedMoney(selectedOrder.discountMinor, selectedOrder.currency)}</b></span><span>Simulated tax <b>{formattedMoney(selectedOrder.taxMinor, selectedOrder.currency)}</b></span><span>Simulated shipping <b>{formattedMoney(selectedOrder.shippingMinor, selectedOrder.currency)}</b></span><strong>Total <b>{formattedMoney(selectedOrder.totalMinor, selectedOrder.currency)}</b></strong></div><address>{selectedOrder.addressSnapshot.fullName}<br/>{selectedOrder.addressSnapshot.line1}<br/>{selectedOrder.addressSnapshot.city}, {selectedOrder.addressSnapshot.state} {selectedOrder.addressSnapshot.postalCode}<br/>India</address>{cancellationEligibility?.eligible && !cancellationOperation && <button className="shop-primary" onClick={() => void act(requestCancellation)}>Cancel order</button>}{cancellationOperation && <p className="history-freshness" role="status">Cancellation {cancellationOperation.status.toLowerCase().replaceAll('_', ' ')}{cancellationOperation.currentStep ? ` · ${cancellationOperation.currentStep.toLowerCase().replaceAll('_', ' ')}` : ''}{cancellationOperation.errorCode ? ` · ${cancellationOperation.errorCode}` : ''}</p>}{returnEligibility?.eligible && <div className="returnable-lines"><h3>Return items · within {returnEligibility.windowDays} days</h3>{returnEligibility.returnableLines.filter((line) => line.returnableQuantity > 0).map((line) => <div className="order-line" key={line.skuId}><span>{line.productTitle} · {line.returnableQuantity} returnable</span><button className="link-button" onClick={() => void act(() => requestReturn(line.skuId))}>Return 1 unit</button></div>)}</div>}{returnOperation && <p className="return-status" role="status">Return {returnOperation.status.toLowerCase().replaceAll('_', ' ')} · simulated refund {formattedMoney(returnOperation.amountMinor, returnOperation.currency)}{returnOperation.errorCode ? ` · ${returnOperation.errorCode}` : ''}</p>}</div></> : orders.length ? <><p className="history-freshness">Order status updates arrive asynchronously.</p><div className="saved-list">{orders.map((order) => <button className="order-row" key={order.id} onClick={() => void openOrder(order.id)}><div><strong>Order {order.id.slice(0, 8).toUpperCase()}</strong><span>{new Date(order.createdAt).toLocaleString('en-IN')}</span></div><span className="order-state">{order.state.replaceAll('_', ' ')}</span><strong>{formattedMoney(order.totalMinor, order.currency)}</strong></button>)}</div></> : <div className="store-empty"><h2>No orders yet.</h2><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}>Browse sports gear</a></div>}</section>}
      {page==='orders'&&selectedOrder&&selectedTracking&&<ShipmentTimeline tracking={selectedTracking}/>}
      {page==='orders'&&selectedOrder?.state==='DELIVERED'&&token&&<ReviewSubmission order={selectedOrder} token={token} act={act} busy={busy}/>}
      {page==='account'&&location.hash==='#support'&&<SupportPanel token={token} act={act} busy={busy}/>}
    </main>
    <footer className="shop-footer"><span>SuperSports · Play. Train. Live better.</span><a href="http://localhost:3002/admin">Local operator workspace</a><span>Simulated commerce · No real payments</span></footer>
  </div>
}

function ShipmentTimeline({tracking}:{tracking:ShipmentTracking}){
 return <section className="customer-page"><span className="store-kicker">LOCAL DELIVERY SIMULATION</span><h2>Shipment tracking</h2><p>{tracking.trackingId??'Shipment pending'} · {tracking.state.replaceAll('_',' ')}</p>{tracking.estimatedDeliveryAt&&<p>Estimated delivery · {new Date(tracking.estimatedDeliveryAt).toLocaleString('en-IN')}</p>}<ol>{(tracking.transitions??[]).map((transition,index)=><li key={`${transition.state}-${index}`}><strong>{transition.state.replaceAll('_',' ')}</strong>{transition.createdAt&&<span> · {new Date(transition.createdAt).toLocaleString('en-IN')}</span>}{transition.reason&&<p>{transition.reason}</p>}</li>)}</ol></section>
}

function ReviewSubmission({order,token,act,busy}:{order:OrderDetail;token:string;act:(work:()=>Promise<void>,success?:string)=>Promise<void>;busy:boolean}){
 return <section className="customer-page"><span className="store-kicker">VERIFIED PURCHASE</span><h2>Review your gear</h2><p>Reviews are checked by the local store team before appearing publicly.</p>{order.lines.map((line)=><form className="address-form" key={line.skuId} onSubmit={(event)=>{event.preventDefault();const f=new FormData(event.currentTarget);void act(async()=>{await request('/api/reviews/customer/reviews',token,{method:'POST',body:JSON.stringify({orderId:order.id,productId:line.productId,skuId:line.skuId,rating:Number(f.get('rating')),title:f.get('title'),body:f.get('body')})})},'Review submitted for moderation.')}}><strong>{line.productTitle}</strong><label>Rating<select name="rating" defaultValue="5"><option value="5">5 · Excellent</option><option value="4">4 · Very good</option><option value="3">3 · Good</option><option value="2">2 · Fair</option><option value="1">1 · Poor</option></select></label><label>Title<input name="title" maxLength={120} required/></label><label>Your review<textarea name="body" maxLength={2000} required/></label><button className="shop-primary" disabled={busy}>Submit review</button></form>)}</section>
}

function SupportPanel({token,act,busy}:{token?:string;act:(work:()=>Promise<void>,success?:string)=>Promise<void>;busy:boolean}){
 const [tickets,setTickets]=useState<Record<string,any>[]>([]);const [selected,setSelected]=useState<Record<string,any>|null>(null)
 const refresh=async()=>{if(!token){setTickets([]);return}const rows=await request<Record<string,any>[]>('/api/support/customer/support/tickets',token);setTickets(rows)}
 useEffect(()=>{void refresh().catch(()=>setTickets([]))},[token])
 if(!token)return <section className="customer-page"><h2>Customer support</h2><p>Sign in to contact the SuperSports team.</p></section>
 return <section className="customer-page"><span className="store-kicker">WE’RE HERE TO HELP</span><h1>Customer support</h1><form className="address-form" onSubmit={(event)=>{event.preventDefault();const f=new FormData(event.currentTarget);void act(async()=>{const created=await request<{ticketId:string}>('/api/support/customer/support/tickets',token,{method:'POST',body:JSON.stringify({subject:f.get('subject'),message:f.get('message'),orderId:String(f.get('orderId')||'').trim()||null,operationId:crypto.randomUUID()})});setSelected(await request(`/api/support/customer/support/tickets/${created.ticketId}`,token));await refresh()},'Support request created.')}}><label>Subject<input name="subject" required maxLength={160}/></label><label>Order ID (optional)<input name="orderId" placeholder="Link an order you own"/></label><label>How can we help?<textarea name="message" required maxLength={4000}/></label><button className="shop-primary" disabled={busy}>Create support request</button></form><h2>Your requests</h2><div className="saved-list">{tickets.map((ticket)=><button className="order-row" key={ticket.ticketId} onClick={()=>void request<Record<string,any>>(`/api/support/customer/support/tickets/${ticket.ticketId}`,token).then(setSelected)}><strong>{ticket.subject}</strong><span>{ticket.status}</span></button>)}</div>{selected&&<article className="order-detail"><h2>{selected.subject}</h2><p>Status: {selected.status}</p>{selected.messages?.map((item:any)=><p key={item.id}><strong>{item.audience==='OPERATOR'?'SuperSports':'You'}:</strong> {item.body}</p>)}<form onSubmit={(event)=>{event.preventDefault();const f=new FormData(event.currentTarget);void act(async()=>{await request(`/api/support/customer/support/tickets/${selected.ticketId}/messages`,token,{method:'POST',body:JSON.stringify({body:f.get('message'),operationId:crypto.randomUUID()})});setSelected(await request(`/api/support/customer/support/tickets/${selected.ticketId}`,token));await refresh()},'Reply sent.')}}><label>Reply<textarea name="message" required maxLength={4000}/></label><button className="shop-primary" disabled={busy}>Send reply</button></form></article>}</section>
}

function ProductCard({ product, currency, price, availability, summary, open, action }: {
  product: Product; currency: Currency; price?: number; availability?: number; summary?: RatingSummary; open: () => void; action?: ReactNode
}) {
  const sku = product.skus[0]
  return <article className="store-card" data-product-id={product.id}>
    <button className="store-card-image" onClick={open} aria-label={`View ${product.title}`}>
      {sku && <img src={`/${sku.assetKey}`} alt={sku.altText} loading="lazy"/>}
      <span>{(availability ?? 0) > 0 ? 'IN STOCK' : 'CHECK DETAILS'}</span>
    </button>
    <div className="store-card-body"><span className="store-brand">{product.brand}</span><button className="store-title" onClick={open}>{product.title}</button><Rating summary={summary}/><p>{product.description}</p><div className="store-card-bottom"><strong>{price !== undefined ? `${product.skus.length > 1 ? 'From ' : ''}${formattedMoney(price, currency)}` : 'Price unavailable'}</strong><span>{product.skus.length} {product.skus.length === 1 ? 'option' : 'options'}</span></div>{action}</div>
  </article>
}

function ProductDetail({ product, currency, prices, availability, summary, wishlist, busy, addCart, toggleWishlist }: {
  product: Product; currency: Currency; prices: Record<string, number>; availability: Record<string, number>; summary?: RatingSummary
  wishlist: string[]; busy: boolean; addCart: (id: string) => void; toggleWishlist: (id: string) => void
}) {
  const [selected, setSelected] = useState(product.skus[0]?.id ?? '')
  const [photoKey, setPhotoKey] = useState('')
  const sku = product.skus.find(item => item.id === selected) ?? product.skus[0]
  const photos = productPhotos(product, sku)
  const photo = photos.find(item => item.assetKey === photoKey) ?? photos[0]
  const facts = product.details
  const inStock = sku && availability[sku.id] !== undefined && availability[sku.id] > 0
  const specifications = [['Model', facts?.model], ['Brand', product.brand], ['Equipment', facts?.equipmentType], ['Material', facts?.material], ['Use', facts?.intendedUse], ['Fit', facts?.fit], ['Care', facts?.care], ['In the package', facts?.packageContents?.join(', ')]].filter(([, value]) => value)
  return <>
    <section className="detail-layout" data-product-id={product.id} data-selected-sku={sku?.id}>
      <div className="product-gallery"><div className="detail-image">{photo ? <img src={`/${photo.assetKey}`} alt={photo.altText}/> : <span>Photograph unavailable</span>}</div>{photos.length > 1 && <div className="gallery-thumbnails" aria-label="Product photographs">{photos.map((item, index) => <button key={item.assetKey} aria-label={`View photograph ${index + 1}`} aria-pressed={photo?.assetKey === item.assetKey} onClick={() => setPhotoKey(item.assetKey)}><img src={`/${item.assetKey}`} alt={item.altText}/></button>)}</div>}</div>
      <div className="detail-copy"><a href="/" onClick={event => { event.preventDefault(); history.pushState({}, '', '/'); window.dispatchEvent(new PopStateEvent('popstate')) }}>← Back to gear</a><span className="store-kicker">{product.brand}</span><h1>{product.title}</h1><a className="rating-link" href="#reviews"><Rating summary={summary}/></a><p>{product.description}</p>
        <strong className="detail-price">{sku && prices[sku.id] !== undefined ? formattedMoney(prices[sku.id], currency) : 'Price unavailable'}</strong>
        <p className={inStock ? 'stock-available' : ''}>{sku && availability[sku.id] !== undefined ? `${availability[sku.id]} available · availability snapshot` : 'Availability unavailable'}</p>
        {product.skus.length > 1 && <label>Choose your option<select value={selected} onChange={event => { setSelected(event.target.value); setPhotoKey('') }}>{product.skus.map(item => <option value={item.id} key={item.id}>{Object.entries(item.attributes).map(([key, value]) => `${key}: ${value}`).join(' · ') || item.code}</option>)}</select></label>}
        {sku && <p className="selected-sku">SKU {sku.code}</p>}
        <div className="detail-actions"><button className="shop-primary" disabled={busy || !inStock || !sku || prices[sku.id] === undefined} onClick={() => sku && addCart(sku.id)}>Add to cart</button><button className="shop-secondary" disabled={busy || !sku} onClick={() => sku && toggleWishlist(sku.id)}>{sku && wishlist.includes(sku.id) ? '♥ Saved' : '♡ Wishlist'}</button></div>
        <small>Displayed price and stock are snapshots. Checkout will revalidate both. Payments and delivery are simulated.</small>
        {!!facts?.highlights?.length && <div className="product-highlights"><h2>About this item</h2><ul>{facts.highlights.map(item => <li key={item}>{item}</li>)}</ul></div>}
      </div>
    </section>
    <section className="product-specifications"><h2>Product details</h2><dl>{specifications.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>{facts?.commerceProvenance && <p className="commerce-provenance">{facts.commerceProvenance} Photographs show the sourced model; simulated options do not imply manufacturer availability.</p>}{facts?.provenance && <details><summary>Source and image attribution</summary><p><a href={facts.provenance.sourceUrl} target="_blank" rel="noreferrer">View product source ↗</a> · Captured {facts.provenance.capturedOn}</p><p>{facts.provenance.rightsStatement}</p></details>}</section>
  </>
}
