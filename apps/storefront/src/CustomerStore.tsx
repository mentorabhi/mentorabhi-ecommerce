import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { User, UserManager, WebStorageStateStore } from 'oidc-client-ts'
import { historyPresentation } from './orderFreshness'
import type { OrderFreshness } from './orderFreshness'
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

type Sku = { id: string; code: string; attributes: Record<string, string>; assetKey: string; altText: string }
type Product = { id: string; categoryId: string; slug: string; title: string; brand: string; description: string; skus: Sku[] }
type Category = { id: string; slug: string; name: string }
type Currency = 'INR' | 'USD'
type CartItem = { skuId: string; quantity: number; revision: number }
type Profile = { fullName: string; phone: string; line1: string; line2: string; city: string; state: string; postalCode: string; country: string; revision: number }

async function request<T>(url: string, token?: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers({ Accept: 'application/json', ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) })
  new Headers(init.headers).forEach((value, name) => headers.set(name, value))
  const response = await fetch(url, { ...init, headers })
  if (!response.ok) throw new Error(response.status === 401 ? 'Sign in to manage your saved items.' : `Could not complete that request (${response.status}).`)
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

const formattedMoney = (minor: number, currency: Currency) => new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(minor / 100)
type Order = { id: string; state: string; currency: Currency; totalMinor: number; createdAt: string }
type OrderDetail = Order & { subtotalMinor: number; discountMinor: number; taxMinor: number; shippingMinor: number; addressSnapshot: Profile; lines: { skuId: string; productTitle: string; quantity: number; unitPriceMinor: number; lineTotalMinor: number; currency: Currency }[] }
type CancellationEligibility = { eligible: boolean; reasonCode: string; shipmentRevision?: number }
type CancellationOperation = { operationId: string; status: string; currentStep?: string; errorCode?: string }
type ReturnEligibility = { eligible: boolean; reasonCode: string; windowDays: number; policyRevision: number; returnableLines: { skuId: string; productTitle: string; returnableQuantity: number }[] }
type ReturnOperation = { returnId: string; status: string; currentStep?: string; amountMinor: number; currency: Currency; errorCode?: string }
const pageFromPath = () => window.location.pathname === '/cart' ? 'cart' : window.location.pathname === '/wishlist' ? 'wishlist' : window.location.pathname === '/account' ? 'account' : window.location.pathname === '/orders' ? 'orders' : 'shop'

export default function CustomerStore() {
  const [user, setUser] = useState<User | null>(null)
  const [authReady, setAuthReady] = useState(false)
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [availability, setAvailability] = useState<Record<string, number>>({})
  const [currency, setCurrency] = useState<Currency>('INR')
  const [cart, setCart] = useState<CartItem[]>([])
  const [wishlist, setWishlist] = useState<string[]>([])
  const [profile, setProfile] = useState<Profile | null>(null)
  const [couponCode, setCouponCode] = useState('')
  const [orders, setOrders] = useState<Order[]>([])
  const [orderFreshness, setOrderFreshness] = useState<OrderFreshness>()
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null)
  const [cancellationEligibility, setCancellationEligibility] = useState<CancellationEligibility | null>(null)
  const [cancellationOperation, setCancellationOperation] = useState<CancellationOperation | null>(null)
  const [returnEligibility, setReturnEligibility] = useState<ReturnEligibility | null>(null)
  const [returnOperation, setReturnOperation] = useState<ReturnOperation | null>(null)
  const [page, setPage] = useState(pageFromPath)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState(new URLSearchParams(location.search).get('q') ?? '')
  const [categoryFilter, setCategoryFilter] = useState(new URLSearchParams(location.search).get('category') ?? '')
  const [sort, setSort] = useState('featured')
  const token = user?.access_token
  const selectedCategory = categories.find((category) => category.id === categoryFilter || category.slug === categoryFilter)

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

  const refreshCatalog = async (query = search) => {
    const queryString = new URLSearchParams()
    if (query.trim()) queryString.set('q', query.trim())
    if (categoryFilter) queryString.set('category', categoryFilter)
    const [items, cats, active] = await Promise.all([
      request<Product[]>(`/api/catalog/products${queryString.size ? `?${queryString}` : ''}`),
      request<Category[]>('/api/catalog/categories'),
      request<{ code: Currency }>('/api/pricing/currency'),
    ])
    setProducts(items); setCategories(cats); setCurrency(active.code)
    const skuIds = items.flatMap((product) => product.skus.map((sku) => sku.id))
    const snapshots = await Promise.all(skuIds.map(async (skuId) => {
      const [price, stock] = await Promise.all([
        request<{ amountMinor: number; currency: Currency }>(`/api/pricing/public/skus/${skuId}`),
        request<{ available: number }>(`/api/inventory/availability/${skuId}`),
      ])
      return [skuId, price.amountMinor, stock.available] as const
    }))
    setPrices(Object.fromEntries(snapshots.map(([id, amount]) => [id, amount])))
    setAvailability(Object.fromEntries(snapshots.map(([id, , available]) => [id, available])))
  }

  const refreshCustomer = async (accessToken = token) => {
    if (!accessToken) { setCart([]); setWishlist([]); setProfile(null); return }
    const [items, saved, address] = await Promise.all([
      request<CartItem[]>('/api/customer/cart', accessToken),
      request<{ skuId: string }[]>('/api/customer/wishlist', accessToken),
      request<Profile>('/api/customer/profile', accessToken),
    ])
    setCart(items); setWishlist(saved.map((item) => item.skuId)); setProfile(address)
  }

  useEffect(() => { void refreshCatalog().catch((e: Error) => setError(e.message)) }, [categoryFilter])
  useEffect(() => { if (authReady) void refreshCustomer().catch((e: Error) => setError(e.message)) }, [token, authReady])

  const visibleProducts = useMemo(() => {
    const selected = products.filter((product) => !selectedCategory || product.categoryId === selectedCategory.id)
    if (sort === 'price-low') return [...selected].sort((a, b) => (prices[a.skus[0]?.id] ?? 0) - (prices[b.skus[0]?.id] ?? 0))
    if (sort === 'price-high') return [...selected].sort((a, b) => (prices[b.skus[0]?.id] ?? 0) - (prices[a.skus[0]?.id] ?? 0))
    if (sort === 'name') return [...selected].sort((a, b) => a.title.localeCompare(b.title))
    return selected
  }, [products, categoryFilter, selectedCategory, sort, prices])

  const act = async (work: () => Promise<void>, success?: string) => {
    setBusy(true); setError(''); setMessage('')
    try { await work(); if (success) setMessage(success); await refreshCustomer() }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not save your changes.') }
    finally { setBusy(false) }
  }

  const navigate = (next: string, href: string) => { history.pushState({}, '', href); setPage(next); setMessage(''); setError(''); window.scrollTo(0, 0) }
  useEffect(() => { const pop = () => setPage(pageFromPath()); addEventListener('popstate', pop); return () => removeEventListener('popstate', pop) }, [])
  const detailSlug = location.pathname.startsWith('/products/') ? decodeURIComponent(location.pathname.slice('/products/'.length)) : ''
  const detail = products.find((product) => product.slug === detailSlug)
  const allSkus = products.flatMap((product) => product.skus.map((sku) => ({ product, sku })))
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
  const openOrder = async (orderId: string) => { if (!token) return; const detail = await request<OrderDetail>(`/api/orders/${orderId}`, token); const tracking = await request<{tracking:{state:string}}>(`/api/orders/${orderId}/tracking`, token); const visibleDetail = tracking.tracking?.state === 'DELIVERED' ? { ...detail, state: 'DELIVERED' } : detail; setSelectedOrder(visibleDetail); setOrders((current) => current.map((order) => order.id === orderId ? { ...order, state: visibleDetail.state } : order)); setCancellationOperation(null); setReturnOperation(null); setCancellationEligibility(detail.state === 'FULFILLMENT_SCHEDULED' ? await request<CancellationEligibility>(`/api/orders/${orderId}/cancellation-eligibility`, token) : null); setReturnEligibility(tracking.tracking?.state === 'DELIVERED' ? await request<ReturnEligibility>(`/api/orders/${orderId}/returns/eligibility`, token) : null) }
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
    if (!selectedOrder || !token || ['FULFILLMENT_SCHEDULED', 'FAILED', 'MANUAL_REVIEW'].includes(selectedOrder.state)) return
    const orderId = selectedOrder.id
    const timer = window.setInterval(() => {
      void request<OrderDetail>(`/api/orders/${orderId}`, token).then((updated) => {
        setSelectedOrder((current) => current?.id === orderId ? updated : current)
        setOrders((current) => current.map((order) => order.id === orderId ? { ...order, state: updated.state } : order))
      }).catch(() => undefined)
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
      <form className="shop-search" onSubmit={(e) => { e.preventDefault(); const params = new URLSearchParams(); if (search) params.set('q', search); if (categoryFilter) params.set('category', categoryFilter); history.pushState({}, '', `/?${params}`); setPage('shop'); void refreshCatalog(search).catch((err: Error) => setError(err.message)) }}><label className="sr-only" htmlFor="store-search">Search sports gear</label><input id="store-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search cricket, football and more"/><button aria-label="Search products">⌕</button></form>
      <nav aria-label="Shopping" className="shop-actions"><a href="/wishlist" onClick={(e) => { e.preventDefault(); navigate('wishlist', '/wishlist') }}>Wishlist <span>{wishlist.length}</span></a><a href="/cart" onClick={(e) => { e.preventDefault(); navigate('cart', '/cart') }}>Cart <span>{cart.length}</span></a>{user && <a href="/orders" onClick={(e) => { e.preventDefault(); navigate('orders', '/orders') }}>Orders</a>}<a href="/account" onClick={(e) => { e.preventDefault(); navigate('account', '/account') }}>{user ? 'Account' : 'Sign in'}</a></nav>
    </header>
    <nav className="category-nav" aria-label="Sports categories"><a href="/" onClick={(e) => { e.preventDefault(); setCategoryFilter(''); navigate('shop', '/') }} className={!categoryFilter ? 'active' : ''}>All gear</a>{categories.map((category) => <a key={category.id} href={`/?category=${category.slug}`} className={categoryFilter === category.id || categoryFilter === category.slug ? 'active' : ''} onClick={(e) => { e.preventDefault(); setCategoryFilter(category.id); navigate('shop', `/?category=${category.slug}`) }}>{category.name}</a>)}<span className="store-currency">Prices in {currency}</span></nav>
    <main className="shop-content">
      {error && <div className="store-alert error" role="alert">{error}<button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
      {message && <div className="store-alert success" role="status">{message}<button onClick={() => setMessage('')} aria-label="Dismiss message">×</button></div>}
      {page === 'orders' && token && <div className={`order-update-status status-${historyView.state.toLowerCase()}`} role="status" aria-live="polite" data-freshness-state={historyView.state}><strong>{historyView.message}</strong>{orderFreshness?.checkedAt && <small>Checked {new Date(orderFreshness.checkedAt).toLocaleTimeString('en-IN')}</small>}</div>}
      {detailSlug ? detail ? <ProductDetail product={detail} currency={currency} prices={prices} availability={availability} wishlist={wishlist} busy={busy} addCart={(skuId) => act(async () => { if (!user) { await customerIdentity.signinRedirect(); return } const currentQuantity = cart.find((item) => item.skuId === skuId)?.quantity ?? 0; if (currentQuantity >= 99) throw new Error('A maximum of 99 units can be added per item.'); await request(`/api/customer/cart/items/${skuId}`, token, { method: 'PUT', body: JSON.stringify({ quantity: currentQuantity + 1 }) }) }, 'Added to your cart.')} toggleWishlist={(skuId) => act(async () => { if (!user) { await customerIdentity.signinRedirect(); return } await request(`/api/customer/wishlist/items/${skuId}`, token, { method: wishlist.includes(skuId) ? 'DELETE' : 'POST' }) }, wishlist.includes(skuId) ? 'Removed from wishlist.' : 'Saved to your wishlist.')} /> : <p className="store-empty">That product is not available.</p>
      : page === 'shop' ? <>
        <section className="store-hero"><img src="/brand/supersports-banner.jpg" alt="SuperSports sports and fitness — play, train, live better"/></section>
        <div className="collection-heading" id="products"><div><span>THE SUPERSPORTS EDIT</span><h1>{search ? `Results for “${search}”` : selectedCategory?.name ?? 'Ready when you are.'}</h1><p>{visibleProducts.length} products · Free local delivery simulation</p></div><label>Sort by <select value={sort} onChange={(e) => setSort(e.target.value)}><option value="featured">Featured</option><option value="name">Name</option><option value="price-low">Price: low to high</option><option value="price-high">Price: high to low</option></select></label></div>
        {visibleProducts.length ? <div className="store-product-grid">{visibleProducts.map((product) => <ProductCard key={product.id} product={product} currency={currency} price={prices[product.skus[0]?.id]} availability={availability[product.skus[0]?.id]} open={() => { history.pushState({}, '', `/products/${product.slug}`); setPage('detail'); window.scrollTo(0, 0) }} />)}</div> : <div className="store-empty"><h2>No matching gear yet</h2><p>Try another search or category.</p></div>}
      </> : page === 'cart' ? <section className="customer-page"><span className="store-kicker">YOUR PICKS</span><h1>Your cart</h1><p className="store-lede">Prices and availability are snapshots; checkout revalidates them before creating an order.</p>{cart.length ? <><div className="cart-summary"><span>Estimated subtotal · display only</span><strong>{formattedMoney(cartItems.reduce((sum, item) => sum + (prices[item.skuId] ?? 0) * item.quantity, 0), currency)}</strong></div><div className="saved-list">{cartItems.map((item) => <article key={item.skuId} className="saved-row"><img src={`/${item.sku.assetKey}`} alt={item.sku.altText}/><div><a href={`/products/${item.product.slug}`} onClick={(e) => { e.preventDefault(); history.pushState({}, '', `/products/${item.product.slug}`); setPage('detail') }}>{item.product.title}</a><span>{item.sku.code} · {formattedMoney(prices[item.skuId] ?? 0, currency)}</span><label>Quantity <input type="number" min="1" max="99" value={item.quantity} onChange={(e) => { const quantity = Number(e.target.value); if (quantity >= 1 && quantity <= 99) void act(async () => { await request(`/api/customer/cart/items/${item.skuId}`, token, { method: 'PUT', body: JSON.stringify({ quantity }) }) }) }}/></label></div><button className="link-button" onClick={() => void act(async () => { await request(`/api/customer/cart/items/${item.skuId}`, token, { method: 'DELETE' }) }, 'Removed from cart.')}>Remove</button></article>)}</div>{unavailableCartItems.map((item) => <div className="stale-cart" key={item.skuId}><span>This product is no longer available · {item.skuId}</span><button className="link-button" onClick={() => void act(async () => { await request(`/api/customer/cart/items/${item.skuId}`, token, { method: 'DELETE' }) }, 'Removed unavailable item.')}>Remove</button></div>)}</> : <div className="store-empty"><h2>Your cart is ready for a first pick.</h2><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}>Explore sports gear</a></div>}</section>
      : page === 'wishlist' ? <section className="customer-page"><span className="store-kicker">SAVED FOR LATER</span><h1>Your wishlist</h1>{savedItems.length ? <div className="store-product-grid">{savedItems.map(({ product, sku }) => <ProductCard key={sku.id} product={{ ...product, skus: [sku] }} currency={currency} price={prices[sku.id]} availability={availability[sku.id]} open={() => { history.pushState({}, '', `/products/${product.slug}`); setPage('detail') }} action={<button className="link-button" onClick={() => void act(async () => { await request(`/api/customer/wishlist/items/${sku.id}`, token, { method: 'DELETE' }) }, 'Removed from wishlist.')}>Remove</button>} />)}</div> : <div className="store-empty"><h2>Keep your favourites close.</h2><p>Save gear from a product page and it will be here next time.</p><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}>Browse gear</a></div>}</section>
      : <section className="customer-page"><span className="store-kicker">YOUR DETAILS</span><h1>Your profile</h1>{!user ? <div className="profile-prompt"><p>Sign in or create a customer account to save your cart, wishlist and Indian delivery address.</p><button className="shop-primary" onClick={() => void customerIdentity.signinRedirect()}>Sign in or create account</button><small>Local self-registration · No payment information needed</small></div> : profile && <form className="address-form" onSubmit={(e) => { e.preventDefault(); const f = new FormData(e.currentTarget); void act(async () => { const saved = await request<{ revision: number }>('/api/customer/profile', token, { method: 'PUT', body: JSON.stringify({ fullName: f.get('fullName'), phone: f.get('phone'), line1: f.get('line1'), line2: f.get('line2'), city: f.get('city'), state: f.get('state'), postalCode: f.get('postalCode'), country: 'IN', expectedRevision: profile.revision }) }); setProfile({ ...profile, fullName: String(f.get('fullName')), phone: String(f.get('phone')), line1: String(f.get('line1')), line2: String(f.get('line2')), city: String(f.get('city')), state: String(f.get('state')), postalCode: String(f.get('postalCode')), revision: saved.revision }) }, 'Your profile was saved.') }}><label>Full name<input name="fullName" required defaultValue={profile.fullName}/></label><label>Phone<input name="phone" type="tel" defaultValue={profile.phone}/></label><label>Address line 1<input name="line1" required defaultValue={profile.line1}/></label><label>Address line 2<input name="line2" defaultValue={profile.line2}/></label><label>City<input name="city" required defaultValue={profile.city}/></label><label>State<input name="state" required defaultValue={profile.state}/></label><label>PIN code<input name="postalCode" inputMode="numeric" pattern="[1-9][0-9]{5}" required defaultValue={profile.postalCode}/></label><label>Country<select value="IN" disabled><option value="IN">India</option></select></label><button className="shop-primary" disabled={busy}>Save profile and address</button><button type="button" className="link-button" onClick={() => void customerIdentity.signoutRedirect()}>Sign out</button></form>}</section>}
      {page === 'cart' && cart.length > 0 && <section className="checkout-actions"><label>Coupon code (optional)<input value={couponCode} onChange={(e) => setCouponCode(e.target.value)} placeholder="WELCOME10"/></label><button className="shop-primary" disabled={busy || !token || !profile?.fullName || !profile.line1 || !profile.city || !profile.state || !profile.postalCode || unavailableCartItems.length > 0} onClick={() => void act(checkout)}>{!token ? 'Sign in to checkout' : !profile?.line1 ? 'Add delivery address first' : busy ? 'Submitting…' : 'Place simulated order'}</button><small>No payment details are collected. Payment and delivery are local simulations.</small></section>}
      {page === 'orders' && <section className="customer-page"><span className="store-kicker">YOUR ACTIVITY</span><h1>Your orders</h1>{!token ? <div className="profile-prompt"><p>Sign in to view your orders.</p><button className="shop-primary" onClick={() => void customerIdentity.signinRedirect()}>Sign in</button></div> : selectedOrder ? <><button className="link-button" onClick={() => { setSelectedOrder(null); setCancellationEligibility(null); setCancellationOperation(null); setReturnEligibility(null); setReturnOperation(null) }}>← Back to orders</button><div className="order-detail"><span>Order {selectedOrder.id}</span><h2>{selectedOrder.state.replaceAll('_', ' ')}</h2>{selectedOrder.lines.map((line) => <div className="order-line" key={line.skuId}><span>{line.productTitle} × {line.quantity}</span><strong>{formattedMoney(line.lineTotalMinor, line.currency)}</strong></div>)}<div className="order-totals"><span>Subtotal <b>{formattedMoney(selectedOrder.subtotalMinor, selectedOrder.currency)}</b></span><span>Discount <b>−{formattedMoney(selectedOrder.discountMinor, selectedOrder.currency)}</b></span><span>Simulated tax <b>{formattedMoney(selectedOrder.taxMinor, selectedOrder.currency)}</b></span><span>Simulated shipping <b>{formattedMoney(selectedOrder.shippingMinor, selectedOrder.currency)}</b></span><strong>Total <b>{formattedMoney(selectedOrder.totalMinor, selectedOrder.currency)}</b></strong></div><address>{selectedOrder.addressSnapshot.fullName}<br/>{selectedOrder.addressSnapshot.line1}<br/>{selectedOrder.addressSnapshot.city}, {selectedOrder.addressSnapshot.state} {selectedOrder.addressSnapshot.postalCode}<br/>India</address>{cancellationEligibility?.eligible && !cancellationOperation && <button className="shop-primary" onClick={() => void act(requestCancellation)}>Cancel order</button>}{cancellationOperation && <p className="history-freshness" role="status">Cancellation {cancellationOperation.status.toLowerCase().replaceAll('_', ' ')}{cancellationOperation.currentStep ? ` · ${cancellationOperation.currentStep.toLowerCase().replaceAll('_', ' ')}` : ''}{cancellationOperation.errorCode ? ` · ${cancellationOperation.errorCode}` : ''}</p>}{returnEligibility?.eligible && <div className="returnable-lines"><h3>Return items · within {returnEligibility.windowDays} days</h3>{returnEligibility.returnableLines.filter((line) => line.returnableQuantity > 0).map((line) => <div className="order-line" key={line.skuId}><span>{line.productTitle} · {line.returnableQuantity} returnable</span><button className="link-button" onClick={() => void act(() => requestReturn(line.skuId))}>Return 1 unit</button></div>)}</div>}{returnOperation && <p className="return-status" role="status">Return {returnOperation.status.toLowerCase().replaceAll('_', ' ')} · simulated refund {formattedMoney(returnOperation.amountMinor, returnOperation.currency)}{returnOperation.errorCode ? ` · ${returnOperation.errorCode}` : ''}</p>}</div></> : orders.length ? <><p className="history-freshness">Order status updates arrive asynchronously.</p><div className="saved-list">{orders.map((order) => <button className="order-row" key={order.id} onClick={() => void openOrder(order.id)}><div><strong>Order {order.id.slice(0, 8).toUpperCase()}</strong><span>{new Date(order.createdAt).toLocaleString('en-IN')}</span></div><span className="order-state">{order.state.replaceAll('_', ' ')}</span><strong>{formattedMoney(order.totalMinor, order.currency)}</strong></button>)}</div></> : <div className="store-empty"><h2>No orders yet.</h2><a href="/" onClick={(e) => { e.preventDefault(); navigate('shop', '/') }}>Browse sports gear</a></div>}</section>}
    </main>
    <footer className="shop-footer"><span>SuperSports · Play. Train. Live better.</span><a href="/admin">Local operator workspace</a><span>Simulated commerce · No real payments</span></footer>
  </div>
}

function ProductCard({product,currency,price,availability,open,action}:{product:Product;currency:Currency;price?:number;availability?:number;open:()=>void;action?:ReactNode}) {
  const sku = product.skus[0]
  return <article className="store-card"><button className="store-card-image" onClick={open} aria-label={`View ${product.title}`}><img src={`/${sku?.assetKey ?? 'products/football.svg'}`} alt={sku?.altText ?? product.title}/><span>{(availability ?? 0) > 0 ? 'IN STOCK' : 'CHECK DETAILS'}</span></button><div className="store-card-body"><span className="store-brand">{product.brand}</span><button className="store-title" onClick={open}>{product.title}</button><p>{product.description}</p><div className="store-card-bottom"><strong>{price ? formattedMoney(price, currency) : 'Price unavailable'}</strong><span>{availability ?? 0} available · snapshot</span></div>{action}</div></article>
}

function ProductDetail({product,currency,prices,availability,wishlist,busy,addCart,toggleWishlist}:{product:Product;currency:Currency;prices:Record<string,number>;availability:Record<string,number>;wishlist:string[];busy:boolean;addCart:(id:string)=>void;toggleWishlist:(id:string)=>void}) {
  const [selected, setSelected] = useState(product.skus[0]?.id ?? '')
  const sku = product.skus.find((item) => item.id === selected) ?? product.skus[0]
  return <section className="detail-layout"><div className="detail-image"><img src={`/${sku?.assetKey ?? 'products/football.svg'}`} alt={sku?.altText ?? product.title}/></div><div className="detail-copy"><a href="/" onClick={(e) => { e.preventDefault(); history.pushState({}, '', '/'); window.dispatchEvent(new PopStateEvent('popstate')) }}>← Back to gear</a><span className="store-kicker">{product.brand}</span><h1>{product.title}</h1><p>{product.description}</p><strong className="detail-price">{sku && prices[sku.id] ? formattedMoney(prices[sku.id], currency) : 'Price unavailable'}</strong><p>{sku ? `${availability[sku.id] ?? 0} available · availability snapshot` : 'No active variants'}</p>{product.skus.length > 1 && <label>Choose your option<select value={selected} onChange={(e) => setSelected(e.target.value)}>{product.skus.map((item) => <option value={item.id} key={item.id}>{Object.values(item.attributes).join(' · ') || item.code}</option>)}</select></label>}<div className="detail-actions"><button className="shop-primary" disabled={busy || !sku} onClick={() => sku && addCart(sku.id)}>Add to cart</button><button className="shop-secondary" disabled={busy || !sku} onClick={() => sku && toggleWishlist(sku.id)}>{sku && wishlist.includes(sku.id) ? '♥ Saved' : '♡ Wishlist'}</button></div><small>Displayed price and stock are snapshots. Checkout will revalidate both.</small></div></section>
}
