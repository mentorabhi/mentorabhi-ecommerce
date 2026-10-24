import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { User, UserManager, WebStorageStateStore } from 'oidc-client-ts'
import './style.css'

const manager = new UserManager({
  authority: 'http://localhost:8180/realms/supersports',
  client_id: 'supersports-web',
  redirect_uri: `${window.location.origin}/signin-callback`,
  post_logout_redirect_uri: window.location.origin,
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
})

type Product = { id: string; categoryId: string; slug: string; title: string; brand: string; description: string; status: string; revision: number; skus: Sku[] }
type Sku = { id: string; code: string; assetKey: string; altText: string; attributes: Record<string, unknown> }
type Category = { id: string; slug: string; name: string; sportId: string }
type Balance = { skuId: string; warehouseName: string; onHand: number; revision: number }
type Currency = 'INR' | 'USD'

async function api<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), Authorization: `Bearer ${token}`, ...options.headers },
  })
  if (!response.ok) {
    if (response.status === 401) throw new ApiError('Your session expired. Sign in again to continue.', 401)
    if (response.status === 403) throw new ApiError('Your account does not have access to this section.', 403)
    const detail = await response.json().catch(() => ({})) as { detail?: string; message?: string }
    throw new ApiError(detail.detail || detail.message || `Request failed (${response.status}).`, response.status)
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

class ApiError extends Error { constructor(message: string, readonly status: number) { super(message) } }
const money = (amount: number, currency: Currency) => new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount / 100)

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [screen, setScreen] = useState<'catalog' | 'pricing' | 'inventory'>('catalog')
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [currency, setCurrency] = useState<Currency>('INR')
  const [currencyRevision, setCurrencyRevision] = useState(1)
  const [coupons, setCoupons] = useState<Record<string, unknown>[]>([])
  const [balances, setBalances] = useState<Balance[]>([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState<ApiError | Error | null>(null)
  const [saving, setSaving] = useState(false)
  const token = user?.access_token ?? ''
  const accessibleScreens = [
    { id: 'catalog' as const, label: 'Catalog', icon: '◈' },
    { id: 'pricing' as const, label: 'Prices & coupons', icon: '↗' },
    { id: 'inventory' as const, label: 'Inventory', icon: '▤' },
  ]

  useEffect(() => {
    const callback = async () => {
      try {
        if (window.location.pathname === '/signin-callback') {
          const signedIn = await manager.signinRedirectCallback()
          setUser(signedIn)
          window.history.replaceState({}, document.title, '/')
        } else setUser(await manager.getUser())
      } catch { setError(new Error('Sign in could not be completed. Return to the login page and try again.')) }
      finally { setLoading(false) }
    }
    void callback()
    const loaded = (signedIn: User) => setUser(signedIn)
    const unloaded = () => setUser(null)
    manager.events.addUserLoaded(loaded)
    manager.events.addUserUnloaded(unloaded)
    return () => { manager.events.removeUserLoaded(loaded); manager.events.removeUserUnloaded(unloaded) }
  }, [])

  const run = async (work: () => Promise<void>) => {
    setError(null); setMessage(''); setSaving(true)
    try { await work() } catch (caught) { setError(caught instanceof Error ? caught : new Error('Something went wrong.')) }
    finally { setSaving(false) }
  }

  const refresh = async () => {
    if (!token) return
    {
      const [p, c] = await Promise.all([
        api<Product[]>('/api/catalog/admin/products', token),
        api<Category[]>('/api/catalog/categories', token),
      ])
      setProducts(p); setCategories(c)
    }
    {
      const [active, allPrices, couponRows] = await Promise.all([
        api<{ code: Currency; revision: number }>('/api/pricing/currency', token),
        api<{ skuId: string; currency: Currency; amountMinor: number }[]>('/api/pricing/prices', token),
        api<Record<string, unknown>[]>('/api/pricing/coupons', token),
      ])
      setCurrency(active.code)
      setCurrencyRevision(active.revision)
      setPrices(Object.fromEntries(allPrices.map((item) => [`${item.skuId}:${item.currency}`, item.amountMinor])))
      setCoupons(couponRows)
    }
    setBalances(await api<Balance[]>('/api/inventory/balances', token))
  }

  useEffect(() => { void refresh().catch((caught) => setError(caught)) }, [token])

  if (loading) return <main className="center-state" aria-live="polite">Loading your workspace…</main>
  if (!user) return <main className="login-shell"><a className="login-brand" href="/"><img src="/brand/supersports-icon.jpg" alt=""/><strong>Super<span>Sports</span></strong></a><div className="login-card"><p className="eyebrow">MERCHANDISING WORKSPACE</p><h1>Make every<br/>match count.</h1><p>Manage the gear, prices and stock that keep players ready.</p><button className="button primary wide" onClick={() => void manager.signinRedirect()}>Sign in with local account <span aria-hidden="true">↗</span></button><p className="quiet">Local admin · English · INR default</p></div><div className="login-art"><img className="brand-banner" src="/brand/supersports-banner.jpg" alt="SuperSports sports and fitness banner"/></div></main>

  const title = accessibleScreens.find((item) => item.id === screen)?.label ?? 'Catalog'

  return <div className="app-shell">
    <aside className="sidebar"><a className="brand-link brand-lockup" href="#home"><img src="/brand/supersports-icon.jpg" alt=""/><strong>Super<span>Sports</span></strong></a><div className="workspace-label">LOCAL COMMERCE <span>DEV</span></div><nav aria-label="Workspace sections">{accessibleScreens.map((item) => <button key={item.id} className={`nav-item ${screen===item.id?'selected':''}`} onClick={() => { setScreen(item.id); setError(null); setMessage('') }}><span className="nav-icon" aria-hidden="true">{item.icon}</span>{item.label}{screen===item.id && <span className="nav-active"/>}</button>)}</nav><div className="sidebar-bottom"><div className="health-dot"><i/>All services connected</div><div className="profile"><div className="avatar">{user.profile.preferred_username?.toString().slice(0,1).toUpperCase() ?? 'S'}</div><div><strong>{user.profile.preferred_username?.toString() ?? 'Local user'}</strong><span>Local account</span></div></div></div></aside>
    <main id="home" className="main-area"><header className="topbar"><div className="breadcrumb"><span>Workspace</span><b>/</b><strong>{title}</strong></div><div className="top-actions"><span className="live-badge"><i/>LOCAL ENVIRONMENT</span><button className="icon-button refresh-button" aria-label="Refresh data" onClick={() => void run(async()=>{await refresh();setMessage('Workspace data refreshed.')})}>⟳</button><button className="icon-button" aria-label="Sign out" onClick={() => void manager.signoutRedirect()}>↪</button></div></header><div className="content"><div className="page-heading"><div><p className="eyebrow">SUPERSPORTS STUDIO <span className="heading-dot">●</span> {screen==='catalog'?'MERCHANDISING':screen==='pricing'?'REVENUE TOOLS':'FULFILMENT'}</p><h1>{title}<span className="heading-period">.</span></h1><p className="subtitle">{screen==='catalog'?'Build a catalog players can trust.':screen==='pricing'?'Keep every price and offer in play.':'Know what is ready for the next order.'}</p></div>{screen==='catalog'&&<div className="summary-chip"><span className="summary-number">{products.length.toString().padStart(2,'0')}</span><span>ACTIVE<br/>PRODUCTS</span></div>}</div>
      {error && <div className={`notice ${error instanceof ApiError&&error.status===403?'warning':'error'}`} role="alert"><span aria-hidden="true">{error instanceof ApiError&&error.status===403?'◉':'!'}</span><div><strong>{error instanceof ApiError&&error.status===403?'Access limited':'We couldn’t load that'}</strong><p>{error.message}</p>{error instanceof ApiError&&error.status===401&&<button className="text-button" onClick={() => void manager.signinRedirect()}>Sign in again</button>}</div><button className="notice-close" aria-label="Dismiss message" onClick={()=>setError(null)}>×</button></div>}
      {message&&<div className="notice success" role="status"><span aria-hidden="true">✓</span><div><strong>Done</strong><p>{message}</p></div><button className="notice-close" aria-label="Dismiss message" onClick={()=>setMessage('')}>×</button></div>}
      {screen==='catalog'&&<Catalog products={products} categories={categories} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      {screen==='pricing'&&<Pricing prices={prices} products={products} currency={currency} currencyRevision={currencyRevision} coupons={coupons} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      {screen==='inventory'&&<Inventory balances={balances} products={products} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      <footer className="footer"><span>Built for the love of the game.</span><span>SUPERSPORTS <b>·</b> LOCAL FIRST</span></footer>
    </div></main>
  </div>
}

function Catalog({products,categories,token,saving,run,refresh,setMessage}:{products:Product[];categories:Category[];token:string;saving:boolean;run:(f:()=>Promise<void>)=>Promise<void>;refresh:()=>Promise<void>;setMessage:(s:string)=>void}){
 const [open,setOpen]=useState(false)
 const [categoryFilter,setCategoryFilter]=useState<string|null>(null)
 const visibleProducts=products.filter((product)=>categoryFilter===null||product.categoryId===categoryFilter)
 return <><section className="toolbar"><div className="filter-pills" aria-label="Filter products by category"><button type="button" className={`filter-pill ${categoryFilter===null?'active':''}`} aria-pressed={categoryFilter===null} onClick={()=>setCategoryFilter(null)}>All sports</button>{categories.map((category)=><button type="button" key={category.id} className={`filter-pill ${categoryFilter===category.id?'active':''}`} aria-pressed={categoryFilter===category.id} onClick={()=>setCategoryFilter(category.id)}>{category.name}</button>)}</div><button className="button primary" onClick={()=>setOpen(!open)}><b>＋</b> Add product</button></section>
 {open&&<form className="panel form-panel" onSubmit={(event)=>{event.preventDefault();const form=new FormData(event.currentTarget);void run(async()=>{const product=await api<{id:string}>('/api/catalog/products',token,{method:'POST',body:JSON.stringify({categoryId:form.get('category'),slug:form.get('slug'),brand:form.get('brand'),title:form.get('title'),description:form.get('description')})});const sku=await api<{id:string}>(`/api/catalog/products/${product.id}/skus`,token,{method:'POST',body:JSON.stringify({code:form.get('code'),attributes:{},assetKey:form.get('asset'),altText:form.get('alt')})});const currentPrices=await api<{skuId:string;currency:Currency;revision:number}[]>('/api/pricing/prices',token);await Promise.all((['INR','USD'] as Currency[]).map(async(currency)=>{const current=currentPrices.find((price)=>price.skuId===sku.id&&price.currency===currency);await api(`/api/pricing/prices/${sku.id}/${currency}`,token,{method:'PUT',body:JSON.stringify({amountMinor:Number(form.get(currency==='INR'?'inr':'usd')),expectedRevision:current?.revision??0})})}));const currentProduct=products.find((item)=>item.id===product.id);await api(`/api/catalog/products/${product.id}/activate`,token,{method:'POST',body:JSON.stringify({expectedRevision:currentProduct?.revision??1})});setMessage('Product, SKU and INR/USD price books saved; product is active.');setOpen(false);await refresh()})}}>
   <div className="panel-title"><div><span className="eyebrow">NEW CATALOG ITEM</span><h2>Product details</h2></div><button type="button" className="icon-button" aria-label="Close form" onClick={()=>setOpen(false)}>×</button></div><div className="form-grid"><label>Product name<input name="title" required placeholder="e.g. Match-day training ball"/></label><label>Brand<input name="brand" required defaultValue="SuperSports"/></label><label>Product slug<input name="slug" required pattern="[a-z0-9-]+" placeholder="match-day-training-ball"/></label><label>Category<select name="category" required defaultValue=""><option value="" disabled>Select category</option>{categories.map((c)=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><label>SKU code<input name="code" required placeholder="SS-CR-BALL-002"/></label><label>Local image key<input name="asset" required pattern="[A-Za-z0-9/_-]+\.svg" placeholder="products/match-ball.svg"/></label><label>Image description<input name="alt" required placeholder="Illustrated red match ball"/></label><label>INR price (paise)<input name="inr" type="number" min="1" required placeholder="129900"/></label><label>USD price (cents)<input name="usd" type="number" min="1" required placeholder="1599"/></label><label className="span-two">Description<textarea name="description" required rows={3} placeholder="What makes this gear ready for play?"/></label></div><div className="form-actions"><span>Both INR and USD prices are required before activation.</span><button className="button primary" disabled={saving}>{saving?'Saving…':'Save and activate'}</button></div>
  </form>}
 {products.length===0?<div className="empty-state"><div className="empty-icon">◈</div><h2>Your catalog is warming up</h2><p>Add your first product or load the reproducible Cricket and Football fixtures from the repository.</p></div>:visibleProducts.length===0?<div className="empty-state compact"><div className="empty-icon">◈</div><h2>No products in this category</h2><p>Add a product to this category or choose another category.</p></div>:<div className="product-grid">{visibleProducts.map((product)=><article className="product-card" key={product.id}><div className="product-image"><img src={`/${product.skus[0]?.assetKey??'products/football.svg'}`} alt={product.skus[0]?.altText??''}/><span className="stock-tag">{product.status==='active'?'LIVE':'DRAFT'}</span></div><div className="product-info"><div className="product-meta"><span>{product.brand}</span><span>{product.skus.length} SKU</span></div><h2>{product.title}</h2><p>{product.description}</p><div className="product-bottom"><strong>{product.skus[0]?.code??product.slug}</strong><span className="arrow-chip" aria-hidden="true">↗</span></div></div></article>)}</div>}
 </>
}

function Pricing({prices,products,currency,currencyRevision,coupons,token,saving,run,refresh,setMessage}:{prices:Record<string,number>;products:Product[];currency:Currency;currencyRevision:number;coupons:Record<string,unknown>[];token:string;saving:boolean;run:(f:()=>Promise<void>)=>Promise<void>;refresh:()=>Promise<void>;setMessage:(s:string)=>void}){
 const [couponOpen,setCouponOpen]=useState(false)
 return <><section className="panel currency-panel"><div><span className="eyebrow">ACTIVE STORE CURRENCY</span><h2>One storefront. Clear pricing.</h2><p>Switch between complete price books. Every active SKU keeps both amounts.</p></div><div className="currency-switch" aria-label="Store currency">{(['INR','USD'] as Currency[]).map((code)=><button key={code} className={currency===code?'selected':''} aria-pressed={currency===code} disabled={saving} onClick={()=>void run(async()=>{await api('/api/pricing/currency',token,{method:'PUT',body:JSON.stringify({currency:code,expectedRevision:currencyRevision})});setMessage(`Store currency changed to ${code}.`);await refresh()})}><span>{code==='INR'?'₹':'$'}</span>{code}</button>)}</div></section>
 <section className="section-block"><div className="section-heading"><div><span className="eyebrow">PRICE BOOKS</span><h2>Products & pricing</h2></div><span className="result-count">{products.reduce((n,p)=>n+p.skus.length,0)} ACTIVE SKUS</span></div><div className="table-wrap"><table><thead><tr><th>ITEM</th><th>SKU</th><th>INR</th><th>USD</th><th>STATUS</th></tr></thead><tbody>{products.flatMap((p)=>p.skus.map((sku)=><tr key={sku.id}><td data-label="Product"><strong>{p.title}</strong><span>{p.brand}</span></td><td data-label="SKU"><code>{sku.code}</code></td><td data-label="INR">{prices[`${sku.id}:INR`]?money(prices[`${sku.id}:INR`],'INR'):<span className="missing">Missing</span>}</td><td data-label="USD">{prices[`${sku.id}:USD`]?money(prices[`${sku.id}:USD`],'USD'):<span className="missing">Missing</span>}</td><td data-label="Status"><span className="status-tag">Complete</span></td></tr>))}</tbody></table></div></section>
 <section className="section-block"><div className="section-heading"><div><span className="eyebrow">OFFER MANAGEMENT</span><h2>Coupons <span className="count-bubble">{coupons.length}</span></h2></div><button className="button secondary" onClick={()=>setCouponOpen(!couponOpen)}>＋ Create coupon</button></div>
 {couponOpen&&<form className="panel coupon-form" onSubmit={(event)=>{event.preventDefault();const f=new FormData(event.currentTarget);void run(async()=>{await api('/api/pricing/coupons',token,{method:'POST',body:JSON.stringify({code:f.get('code'),active:true,startsAt:new Date(String(f.get('startsAt'))).toISOString(),endsAt:new Date(String(f.get('endsAt'))).toISOString(),currency:f.get('currency'),kind:f.get('kind'),value:Number(f.get('value')),minimumSubtotalMinor:Number(f.get('minimum')||0),maximumDiscountMinor:f.get('maximum')?Number(f.get('maximum')):null,globalLimit:null,perCustomerLimit:null,rules:{}})});setCouponOpen(false);setMessage('Coupon definition saved. Redemption limits are enforced at checkout in a later milestone.');await refresh()})}}><label>Coupon code<input name="code" pattern="[A-Za-z0-9_-]{3,40}" required placeholder="MATCHDAY10"/></label><label>Discount<select name="kind"><option value="PERCENT">Percent (basis points)</option><option value="FIXED">Fixed amount</option></select></label><label>Value<input name="value" type="number" min="1" required/></label><label>Currency<select name="currency"><option>INR</option><option>USD</option></select></label><label>Starts<input name="startsAt" type="datetime-local" required/></label><label>Ends<input name="endsAt" type="datetime-local" required/></label><label>Minimum subtotal (minor units)<input name="minimum" type="number" min="0" defaultValue="0"/></label><label>Maximum discount (minor units)<input name="maximum" type="number" min="1"/></label><button className="button primary" disabled={saving}>Save coupon</button></form>}
 <div className="coupon-grid">{coupons.length===0?<p className="quiet">No coupon definitions yet.</p>:coupons.map((coupon)=><article className="coupon-card" key={String(coupon.id)}><div className="coupon-stamp">%</div><div><code>{String(coupon.code)}</code><strong>{coupon.kind==='PERCENT'?`${(Number(coupon.value)/100).toFixed(0)}% off`:money(Number(coupon.value),coupon.currency as Currency)}</strong><span>{String(coupon.currency)} · {coupon.active?'Active':'Paused'}</span></div></article>)}</div>
 </section></>
}

function Inventory({balances,products,token,saving,run,refresh,setMessage}:{balances:Balance[];products:Product[];token:string;saving:boolean;run:(f:()=>Promise<void>)=>Promise<void>;refresh:()=>Promise<void>;setMessage:(s:string)=>void}){
 const skuName=new Map(products.flatMap((p)=>p.skus.map((s)=>[s.id,`${p.title} · ${s.code}`] as const)))
 return <><section className="inventory-summary"><div className="inventory-intro"><span className="eyebrow">MAIN WAREHOUSE</span><h2>Stock that’s ready to play.</h2><p>Adjustments are recorded as signed movements with a reason and replay-safe key.</p><div className="inventory-stats"><div><strong>{balances.reduce((n,b)=>n+Number(b.onHand),0)}</strong><span>UNITS ON HAND</span></div><div><strong>{balances.filter((b)=>Number(b.onHand)>0).length}</strong><span>STOCKED SKUS</span></div></div></div><form className="adjust-form" onSubmit={(event)=>{event.preventDefault();const form=event.currentTarget;const f=new FormData(form);void run(async()=>{await api('/api/inventory/adjustments',token,{method:'POST',body:JSON.stringify({skuId:f.get('skuId'),delta:Number(f.get('delta')),reason:f.get('reason'),idempotencyKey:f.get('key')})});setMessage('Stock movement recorded.');form.reset();await refresh()})}}><div className="form-title"><div className="mini-icon">＋</div><div><strong>Record adjustment</strong><span>Movement ledger entry</span></div></div><label>Product / SKU<select name="skuId" required defaultValue=""><option value="" disabled>Choose an active SKU</option>{products.length?products.flatMap((p)=>p.skus.map((s)=><option key={s.id} value={s.id}>{p.title} · {s.code}</option>)):balances.map((b)=><option key={b.skuId} value={b.skuId}>{skuName.get(b.skuId)??b.skuId}</option>)}</select></label><label>Quantity change<input name="delta" type="number" required placeholder="e.g. 12 or -2"/></label><label>Reason<input name="reason" required minLength={3} maxLength={500} placeholder="Cycle count correction"/></label><label>Idempotency key<input name="key" required minLength={8} maxLength={120} pattern="[A-Za-z0-9._:-]{8,120}" placeholder="cycle-count-2026-10-23"/></label><button className="button primary wide" disabled={saving}>Save stock movement <span aria-hidden="true">↗</span></button></form></section>
 <section className="section-block"><div className="section-heading"><div><span className="eyebrow">ON-HAND SUMMARY</span><h2>Warehouse stock</h2></div><span className="result-count">{balances.length} SKU BALANCES</span></div>{balances.length===0?<div className="empty-state compact"><div className="empty-icon">▤</div><h2>No inventory movements yet</h2><p>Load the fixture dataset or record the first stock adjustment.</p></div>:<div className="table-wrap"><table><thead><tr><th>PRODUCT</th><th>WAREHOUSE</th><th>ON HAND</th><th>REVISION</th><th>HEALTH</th></tr></thead><tbody>{balances.map((b)=><tr key={b.skuId}><td data-label="Product"><strong>{skuName.get(b.skuId)??b.skuId}</strong></td><td data-label="Warehouse">{b.warehouseName}</td><td data-label="On hand" className="quantity-cell">{b.onHand}</td><td data-label="Revision">{b.revision}</td><td data-label="Health"><span className={`status-tag ${Number(b.onHand)===0?'low-stock':''}`}>{Number(b.onHand)===0?'Out of stock':'In stock'}</span></td></tr>)}</tbody></table></div>}</section></>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
