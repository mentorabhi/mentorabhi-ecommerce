import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { User, UserManager, WebStorageStateStore } from 'oidc-client-ts'
import './style.css'
import CustomerStore from './CustomerStore'

const operatorManager = new UserManager({
  authority: 'http://localhost:8180/realms/supersports',
  client_id: 'supersports-web',
  redirect_uri: `${window.location.origin}/admin/signin-callback`,
  post_logout_redirect_uri: `${window.location.origin}/admin`,
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),
})

type Product = { id: string; categoryId: string; slug: string; title: string; brand: string; description: string; status: string; revision: number; skus: Sku[] }
type Sku = { id: string; code: string; assetKey: string; altText: string; attributes: Record<string, unknown> }
type Category = { id: string; slug: string; name: string; sportId: string }
type Balance = { skuId: string; warehouseName: string; onHand: number; revision: number }
type Currency = 'INR' | 'USD'
type Configuration = { revision: number; categories: { id: string; label: string }[]; settings: { key: string; category: string; value: string; valueType: string; activationMode: string; revision: number }[] }

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

function AdminApp() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [screen, setScreen] = useState<'catalog' | 'pricing' | 'inventory' | 'configuration' | 'reviews' | 'support' | 'shipments' | 'analytics'>('catalog')
  const [products, setProducts] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [currency, setCurrency] = useState<Currency>('INR')
  const [currencyRevision, setCurrencyRevision] = useState(1)
  const [coupons, setCoupons] = useState<Record<string, unknown>[]>([])
  const [balances, setBalances] = useState<Balance[]>([])
  const [configuration, setConfiguration] = useState<Configuration | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState<ApiError | Error | null>(null)
  const [saving, setSaving] = useState(false)
  const token = user?.access_token ?? ''
  const accessibleScreens = [
    { id: 'catalog' as const, label: 'Catalog', icon: '◈' },
    { id: 'pricing' as const, label: 'Prices & coupons', icon: '↗' },
    { id: 'inventory' as const, label: 'Inventory', icon: '▤' },
    { id: 'configuration' as const, label: 'Configuration', icon: '⚙' },
    { id: 'reviews' as const, label: 'Reviews', icon: '★' },
    { id: 'support' as const, label: 'Support', icon: '✉' },
    { id: 'shipments' as const, label: 'Shipments', icon: '➜' },
    { id: 'analytics' as const, label: 'Analytics', icon: '▥' },
  ]

  useEffect(() => {
    const callback = async () => {
      try {
        if (window.location.pathname === '/admin/signin-callback') {
          const signedIn = await operatorManager.signinRedirectCallback()
          setUser(signedIn)
          window.history.replaceState({}, document.title, '/admin')
        } else setUser(await operatorManager.getUser())
      } catch { setError(new Error('Sign in could not be completed. Return to the login page and try again.')) }
      finally { setLoading(false) }
    }
    void callback()
    const loaded = (signedIn: User) => setUser(signedIn)
    const unloaded = () => setUser(null)
    operatorManager.events.addUserLoaded(loaded)
    operatorManager.events.addUserUnloaded(unloaded)
    return () => { operatorManager.events.removeUserLoaded(loaded); operatorManager.events.removeUserUnloaded(unloaded) }
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
    setConfiguration(await api<Configuration>('/api/configuration', token))
  }

  useEffect(() => { void refresh().catch((caught) => setError(caught)) }, [token])

  if (loading) return <main className="center-state" aria-live="polite">Loading your workspace…</main>
  if (!user) return <main className="login-shell"><a className="login-brand" href="/"><img src="/brand/supersports-icon.jpg" alt=""/><strong>Super<span>Sports</span></strong></a><div className="login-card"><p className="eyebrow">MERCHANDISING WORKSPACE</p><h1>Make every<br/>match count.</h1><p>Manage the gear, prices and stock that keep players ready.</p><button className="button primary wide" onClick={() => void operatorManager.signinRedirect()}>Sign in with local account <span aria-hidden="true">↗</span></button><p className="quiet">Local admin · English · INR default</p></div><div className="login-art"><img className="brand-banner" src="/brand/supersports-banner.jpg" alt="SuperSports sports and fitness banner"/></div></main>

  const title = accessibleScreens.find((item) => item.id === screen)?.label ?? 'Catalog'

  return <div className="app-shell">
    <aside className="sidebar"><a className="brand-link brand-lockup" href="#home"><img src="/brand/supersports-icon.jpg" alt=""/><strong>Super<span>Sports</span></strong></a><div className="workspace-label">LOCAL COMMERCE <span>DEV</span></div><nav aria-label="Workspace sections">{accessibleScreens.map((item) => <button key={item.id} className={`nav-item ${screen===item.id?'selected':''}`} onClick={() => { setScreen(item.id); setError(null); setMessage('') }}><span className="nav-icon" aria-hidden="true">{item.icon}</span>{item.label}{screen===item.id && <span className="nav-active"/>}</button>)}</nav><div className="sidebar-bottom"><div className="health-dot"><i/>All services connected</div><div className="profile"><div className="avatar">{user.profile.preferred_username?.toString().slice(0,1).toUpperCase() ?? 'S'}</div><div><strong>{user.profile.preferred_username?.toString() ?? 'Local user'}</strong><span>Local account</span></div></div></div></aside>
    <main id="home" className="main-area"><header className="topbar"><div className="breadcrumb"><span>Workspace</span><b>/</b><strong>{title}</strong></div><div className="top-actions"><span className="live-badge"><i/>LOCAL ENVIRONMENT</span><button className="icon-button refresh-button" aria-label="Refresh data" onClick={() => void run(async()=>{await refresh();setMessage('Workspace data refreshed.')})}>⟳</button><button className="icon-button" aria-label="Sign out" onClick={() => void operatorManager.signoutRedirect()}>↪</button></div></header><div className="content"><div className="page-heading"><div><p className="eyebrow">SUPERSPORTS STUDIO <span className="heading-dot">●</span> {screen==='catalog'?'MERCHANDISING':screen==='pricing'?'REVENUE TOOLS':screen==='inventory'?'FULFILMENT':'PLATFORM SETTINGS'}</p><h1>{title}<span className="heading-period">.</span></h1><p className="subtitle">{screen==='catalog'?'Build a catalog players can trust.':screen==='pricing'?'Keep every price and offer in play.':screen==='inventory'?'Know what is ready for the next order.':'Manage local integrations and commerce simulations.'}</p></div>{screen==='catalog'&&<div className="summary-chip"><span className="summary-number">{products.length.toString().padStart(2,'0')}</span><span>ACTIVE<br/>PRODUCTS</span></div>}</div>
      {error && <div className={`notice ${error instanceof ApiError&&error.status===403?'warning':'error'}`} role="alert"><span aria-hidden="true">{error instanceof ApiError&&error.status===403?'◉':'!'}</span><div><strong>{error instanceof ApiError&&error.status===403?'Access limited':'We couldn’t load that'}</strong><p>{error.message}</p>{error instanceof ApiError&&error.status===401&&<button className="text-button" onClick={() => void operatorManager.signinRedirect()}>Sign in again</button>}</div><button className="notice-close" aria-label="Dismiss message" onClick={()=>setError(null)}>×</button></div>}
      {message&&<div className="notice success" role="status"><span aria-hidden="true">✓</span><div><strong>Done</strong><p>{message}</p></div><button className="notice-close" aria-label="Dismiss message" onClick={()=>setMessage('')}>×</button></div>}
      {screen==='catalog'&&<Catalog products={products} categories={categories} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      {screen==='pricing'&&<Pricing prices={prices} products={products} currency={currency} currencyRevision={currencyRevision} coupons={coupons} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      {screen==='inventory'&&<Inventory balances={balances} products={products} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      {screen==='configuration'&&configuration&&<Configurations snapshot={configuration} token={token} saving={saving} run={run} refresh={refresh} setMessage={setMessage}/>}
      {screen==='reviews'&&<ModerationQueue kind="reviews" token={token} run={run} saving={saving} setMessage={setMessage}/>}
      {screen==='support'&&<ModerationQueue kind="support" token={token} run={run} saving={saving} setMessage={setMessage}/>}
      {screen==='shipments'&&<ShipmentSimulator token={token} run={run} saving={saving} setMessage={setMessage}/>}
      {screen==='analytics'&&<AnalyticsDashboard token={token}/>}
      <footer className="footer"><span>Built for the love of the game.</span><span>SUPERSPORTS <b>·</b> LOCAL FIRST</span></footer>
    </div></main>
  </div>
}

type AnalyticsSummary = { confirmed_orders: number; gmv_minor: number; order_value_minor: number; discounts_minor: number; refunded_minor: number; refund_events: number; cancellations: number; return_orders: number; units_sold: number; latest_event_at: string|null }
type SalesDay = { day: string; orders: number; gmvMinor: number; orderValueMinor: number; discountsMinor: number }
type ProductSales = { productId: string; productTitle: string; unitsSold: number; salesMinor: number; discountsMinor: number }
type RefundRow = { day: string; reasonCode: string; events: number; amountMinor: number }

function AnalyticsDashboard({token}:{token:string}) {
  const [currency,setCurrency]=useState<Currency>('INR')
  const [days,setDays]=useState(30)
  const [summary,setSummary]=useState<AnalyticsSummary|null>(null)
  const [daily,setDaily]=useState<SalesDay[]>([])
  const [products,setProducts]=useState<ProductSales[]>([])
  const [refunds,setRefunds]=useState<RefundRow[]>([])
  const [error,setError]=useState('')
  const [loading,setLoading]=useState(false)
  const refresh=async()=>{
    setLoading(true);setError('')
    try {
      const [s,d,p,r]=await Promise.all([
        api<AnalyticsSummary>(`/api/reports/summary?currency=${currency}&days=${days}`,token),
        api<SalesDay[]>(`/api/reports/daily-sales?currency=${currency}&days=${days}`,token),
        api<ProductSales[]>(`/api/reports/top-products?currency=${currency}&days=${days}&limit=10`,token),
        api<RefundRow[]>(`/api/reports/refunds?currency=${currency}&days=${days}`,token),
      ])
      setSummary(s);setDaily(d);setProducts(p);setRefunds(r)
    } catch(e) { setError(e instanceof Error?e.message:'Analytics data is unavailable.') }
    finally { setLoading(false) }
  }
  useEffect(()=>{void refresh()},[token,currency,days])
  const confirmed=summary?.confirmed_orders??0
  const gmv=summary?.gmv_minor??0
  const orderValue=summary?.order_value_minor??0
  const refunded=summary?.refunded_minor??0
  const max=Math.max(1,...daily.map(row=>Number(row.gmvMinor)||0))
  const moneyValue=(minor:number)=>money(Number(minor)||0,currency)
  return <section className="analytics-dashboard">
    <div className="analytics-toolbar"><div className="currency-switch" aria-label="Report currency"><button className={currency==='INR'?'selected':''} onClick={()=>setCurrency('INR')}>₹ INR</button><button className={currency==='USD'?'selected':''} onClick={()=>setCurrency('USD')}>$ USD</button></div><div className="analytics-actions"><label className="analytics-period">Period<select aria-label="Report period" value={days} onChange={event=>setDays(Number(event.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={365}>Last 365 days</option></select></label><span className="result-count">{summary?.latest_event_at?`LATEST EVENT · ${new Date(summary.latest_event_at).toLocaleString('en-IN')}`:'LIFECYCLE DATA · REFRESHED ON REQUEST'}</span><button className="button secondary" disabled={loading} onClick={()=>void refresh()}>{loading?'Loading…':'Refresh reports'}</button><a className="button secondary" href="http://localhost:8095" target="_blank" rel="noreferrer">Open dashboard studio ↗</a></div></div>
    {error&&<div className="notice warning" role="status"><span>i</span><div><strong>Reports are unavailable</strong><p>{error}. Start the local analytics profile and run the batch ingestion job.</p></div></div>}
    {summary&&<>
      <div className="metric-grid">
        <MetricCard label="GROSS MERCHANDISE VALUE" value={moneyValue(gmv)} hint="Confirmed merchandise subtotal before discounts, tax and shipping"/>
        <MetricCard label="NET MERCHANDISE SALES" value={moneyValue(gmv-summary.discounts_minor)} hint="GMV less confirmed order discounts"/>
        <MetricCard label="CONFIRMED ORDERS" value={String(confirmed)} hint={`${summary.cancellations} cancellations · ${summary.return_orders} return requests`}/>
        <MetricCard label="AVERAGE ORDER VALUE" value={moneyValue(confirmed?Math.round(orderValue/confirmed):0)} hint="Confirmed order total, including tax and shipping"/>
        <MetricCard label="UNITS SOLD" value={String(summary.units_sold)} hint={`${confirmed?(summary.units_sold/confirmed).toFixed(1):'0.0'} items per confirmed order`}/>
        <MetricCard label="ORDER DISCOUNTS" value={moneyValue(summary.discounts_minor)} hint="Discount snapshots on confirmed orders"/>
        <MetricCard label="DISCOUNT RATE" value={`${gmv?((summary.discounts_minor/gmv)*100).toFixed(1):'0.0'}%`} hint="Order discounts ÷ gross merchandise value"/>
        <MetricCard label="COMPLETED REFUNDS" value={moneyValue(refunded)} hint={`${summary.refund_events} refund events in this period`}/>
        <MetricCard label="REFUND AMOUNT RATE" value={`${orderValue?((refunded/orderValue)*100).toFixed(1):'0.0'}%`} hint="Refund amount ÷ order value in selected period"/>
        <MetricCard label="NET CASH SALES" value={moneyValue(orderValue-refunded)} hint="Order value accepted less refunds issued in period"/>
      </div>
      <div className="analytics-grid"><section className="analytics-panel"><div className="section-heading"><div><span className="eyebrow">LAST {days} DAYS</span><h2>Merchandise sales by day</h2></div><span className="result-count">{currency}</span></div>{daily.length===0?<p className="analytics-empty">No confirmed orders in this period.</p>:<div className="sales-bars" role="img" aria-label="Daily gross merchandise value chart">{[...daily].reverse().map((row)=><div className="sales-bar-column" key={row.day} title={`${row.day}: ${moneyValue(Number(row.gmvMinor))} · ${row.orders} orders`}><div className="sales-bar" style={{height:`${Math.max(4,Number(row.gmvMinor)/max*100)}%`}}/><small>{row.day.slice(5)}</small></div>)}</div>}</section>
        <section className="analytics-panel"><div className="section-heading"><div><span className="eyebrow">PRODUCT PERFORMANCE</span><h2>Top products</h2></div><span className="result-count">{currency}</span></div>{products.length===0?<p className="analytics-empty">No product sales available yet.</p>:<div className="table-wrap"><table><thead><tr><th>PRODUCT</th><th>UNITS</th><th>SALES</th></tr></thead><tbody>{products.map((row)=><tr key={row.productId}><td><strong>{row.productTitle}</strong><span>{row.productId.slice(0,8)}</span></td><td>{row.unitsSold}</td><td>{moneyValue(row.salesMinor)}</td></tr>)}</tbody></table></div>}</section>
      </div>
      <section className="analytics-panel"><div className="section-heading"><div><span className="eyebrow">RETURNS & REFUNDS</span><h2>Completed refund report</h2></div><span className="result-count">{currency}</span></div>{refunds.length===0?<p className="analytics-empty">No completed refunds in the current event history.</p>:<div className="table-wrap"><table><thead><tr><th>DATE</th><th>REASON</th><th>EVENTS</th><th>AMOUNT</th></tr></thead><tbody>{refunds.map((row,i)=><tr key={`${row.day}-${row.reasonCode}-${i}`}><td>{row.day}</td><td>{row.reasonCode}</td><td>{row.events}</td><td>{moneyValue(row.amountMinor)}</td></tr>)}</tbody></table></div>}</section>
      <p className="analytics-footnote">GMV is confirmed merchandise subtotal before discounts, tax and shipping. Refunds use their issue date and may include allocated tax; net cash sales is a period activity measure. Figures never combine currencies. Sessions, conversion, cart abandonment, coupon attribution and inventory health need additional source events or owner APIs and are not estimated here.</p>
    </>}
  </section>
}

function MetricCard({label,value,hint}:{label:string;value:string;hint:string}) { return <article className="metric-card"><span className="eyebrow">{label}</span><strong>{value}</strong><small>{hint}</small></article> }

function ShipmentSimulator({token,run,saving,setMessage}:{token:string;run:(f:()=>Promise<void>)=>Promise<void>;saving:boolean;setMessage:(s:string)=>void}){
 const [orderId,setOrderId]=useState('');const [shipment,setShipment]=useState<Record<string,any>|null>(null)
 const next:Record<string,string>={SCHEDULED:'HANDED_OFF',HANDED_OFF:'IN_TRANSIT',IN_TRANSIT:'DELIVERED'}
 const load=async()=>setShipment(await api(`/api/fulfillment/operator/shipments/${orderId.trim()}`,token))
 return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">LOCAL SIMULATOR</span><h2>Shipment progression</h2></div><span className="result-count">NO CARRIER CONNECTED</span></div><p>Advance a synthetic shipment one audited step at a time.</p><form className="configuration-list" onSubmit={(event)=>{event.preventDefault();void run(load)}}><label>Order ID<input value={orderId} onChange={(event)=>setOrderId(event.target.value)} placeholder="Paste a scheduled order UUID" required/></label><button className="button secondary" disabled={saving}>Load shipment</button></form>{shipment&&<article className="configuration-row"><div><strong>{shipment.trackingId} · {shipment.state}</strong><code>Revision {shipment.revision}</code><small>Estimated delivery {shipment.estimatedDeliveryAt?new Date(shipment.estimatedDeliveryAt).toLocaleString('en-IN'):'Not scheduled'}</small></div>{next[shipment.state]&&<button className="button primary" disabled={saving} onClick={()=>void run(async()=>{await api(`/api/fulfillment/operator/shipments/${orderId.trim()}/transitions`,token,{method:'POST',body:JSON.stringify({expectedRevision:shipment.revision,operationId:crypto.randomUUID(),targetState:next[shipment.state],reason:'Operator advanced local shipment simulation'})});setMessage(`Shipment advanced to ${next[shipment.state]}.`);await load()})}>Advance to {next[shipment.state]}</button>}</article>}</section>
}

function ModerationQueue({kind,token,run,saving,setMessage}:{kind:'reviews'|'support';token:string;run:(f:()=>Promise<void>)=>Promise<void>;saving:boolean;setMessage:(s:string)=>void}){
 const [rows,setRows]=useState<Record<string,any>[]>([])
 const refresh=async()=>setRows(await api<Record<string,any>[]>(kind==='reviews'?'/api/reviews/operator/reviews/pending':'/api/support/operator/support/tickets',token))
 useEffect(()=>{void refresh().catch(()=>setRows([]))},[token,kind])
 return <section className="section-block"><div className="section-heading"><div><span className="eyebrow">CUSTOMER CARE</span><h2>{kind==='reviews'?'Reviews awaiting moderation':'Open support tickets'}</h2></div><button className="button secondary" onClick={()=>void refresh()}>Refresh</button></div>{rows.length===0?<div className="empty-state compact"><h2>Queue is clear</h2><p>New customer submissions will appear here.</p></div>:<div className="configuration-groups">{rows.map((row)=><article className="section-block" key={row.reviewId??row.ticketId}><div className="section-heading"><div><span className="eyebrow">{kind==='reviews'?'REVIEW':'TICKET'} · {String(row.reviewId??row.ticketId).slice(0,8)}</span><h3>{row.title??row.subject}</h3></div><span className="result-count">{row.state??row.status}</span></div><p>{row.body??'Customer support request'}{row.orderId?` · Order ${String(row.orderId).slice(0,8)}`:''}</p><div className="form-actions">{kind==='reviews'?<><button className="button primary" disabled={saving} onClick={()=>void run(async()=>{await api(`/api/reviews/operator/reviews/${row.reviewId}/moderation`,token,{method:'POST',body:JSON.stringify({state:'PUBLISHED',reason:'Meets review guidelines',operationId:crypto.randomUUID()})});setMessage('Review published.');await refresh()})}>Publish</button><button className="button secondary" disabled={saving} onClick={()=>void run(async()=>{await api(`/api/reviews/operator/reviews/${row.reviewId}/moderation`,token,{method:'POST',body:JSON.stringify({state:'REJECTED',reason:'Does not meet review guidelines',operationId:crypto.randomUUID()})});await refresh()})}>Reject</button></>:<form onSubmit={(event)=>{event.preventDefault();const form=new FormData(event.currentTarget);void run(async()=>{await api(`/api/support/operator/support/tickets/${row.ticketId}/messages`,token,{method:'POST',body:JSON.stringify({body:form.get('reply'),operationId:crypto.randomUUID()})});await api(`/api/support/operator/support/tickets/${row.ticketId}/status`,token,{method:'PUT',body:JSON.stringify({status:'IN_PROGRESS',reason:'Operator replied to customer'})}).catch(()=>undefined);setMessage('Support reply recorded.');await refresh()})}}><label>Reply to customer<input name="reply" required maxLength={4000}/></label><button className="button primary" disabled={saving}>Send reply</button></form>}</div></article>)}</div>}</section>
}

function Configurations({snapshot,token,saving,run,refresh,setMessage}:{snapshot:Configuration;token:string;saving:boolean;run:(f:()=>Promise<void>)=>Promise<void>;refresh:()=>Promise<void>;setMessage:(s:string)=>void}){
 const labels:Record<string,string>={'checkout.tax.rate-bps':'Simulated tax rate (basis points)','checkout.shipping.INR':'Simulated shipping (INR paise)','checkout.shipping.USD':'Simulated shipping (USD cents)','checkout.inventory.reservation-seconds':'Inventory reservation duration (seconds)','checkout.payment.authorization-mode':'Payment authorization simulation','returns.window-days':'Return window (days)'}
 return <div className="configuration-groups">{snapshot.categories.map((category)=><section className="section-block" key={category.id}><div className="section-heading"><div><span className="eyebrow">CONFIGURATION CATEGORY</span><h2>{category.label}</h2></div><span className="result-count">REVISION {snapshot.revision}</span></div><div className="configuration-list">{snapshot.settings.filter((item)=>item.category===category.id).map((setting)=><article className="configuration-row" key={setting.key}><div><strong>{labels[setting.key]??setting.key}</strong><code>{setting.key}</code><small>{setting.key==='returns.window-days'?'Applies to new return requests; accepted requests retain the policy revision.':setting.activationMode==='OPERATOR_EDITABLE'?'Changes apply to new checkouts. Existing orders retain their snapshot.':'Read only · configured through a reviewed migration.'} · setting revision {setting.revision}</small></div>{setting.activationMode==='OPERATOR_EDITABLE'?<form onSubmit={(event)=>{event.preventDefault();const form=new FormData(event.currentTarget);void run(async()=>{const path=setting.key.startsWith('returns.')?`/api/configuration/returns/${setting.key.slice('returns.'.length)}`:`/api/configuration/checkout/${setting.key.slice('checkout.'.length)}`;await api(path,token,{method:'PUT',body:JSON.stringify({value:form.get('value'),expectedRevision:setting.revision})});setMessage(`${labels[setting.key]} updated and recorded in the audit log.`);await refresh()})}}>{setting.key==='checkout.payment.authorization-mode'?<select name="value" defaultValue={setting.value}><option value="APPROVE">Approve simulated payments</option><option value="DECLINE">Decline simulated payments</option></select>:<input name="value" type="number" min={setting.key==='checkout.inventory.reservation-seconds'?60:setting.key==='returns.window-days'?1:0} max={setting.key==='checkout.inventory.reservation-seconds'?1800:setting.key==='checkout.tax.rate-bps'?10000:setting.key==='returns.window-days'?90:100000000} defaultValue={setting.value} required/>}<button className="button primary" disabled={saving}>Save</button></form>:<span className="configuration-value">{setting.value}</span>}</article>)}</div></section>)}</div>
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
 type PendingReturn={returnId:string;orderId:string;revision:number;receivedAt:string;units:{skuId:string;ordinal:number;condition:string}[]}
 const [pendingReturns,setPendingReturns]=useState<PendingReturn[]>([])
 const refreshPending=async()=>setPendingReturns(await api<PendingReturn[]>('/api/inventory/returns/pending',token))
 useEffect(()=>{void refreshPending().catch(()=>setPendingReturns([]))},[token])
 return <><section className="inventory-summary"><div className="inventory-intro"><span className="eyebrow">MAIN WAREHOUSE</span><h2>Stock that’s ready to play.</h2><p>Adjustments are recorded as signed movements with a reason and replay-safe key.</p><div className="inventory-stats"><div><strong>{balances.reduce((n,b)=>n+Number(b.onHand),0)}</strong><span>UNITS ON HAND</span></div><div><strong>{balances.filter((b)=>Number(b.onHand)>0).length}</strong><span>STOCKED SKUS</span></div></div></div><form className="adjust-form" onSubmit={(event)=>{event.preventDefault();const form=event.currentTarget;const f=new FormData(form);void run(async()=>{await api('/api/inventory/adjustments',token,{method:'POST',body:JSON.stringify({skuId:f.get('skuId'),delta:Number(f.get('delta')),reason:f.get('reason'),idempotencyKey:f.get('key')})});setMessage('Stock movement recorded.');form.reset();await refresh()})}}><div className="form-title"><div className="mini-icon">＋</div><div><strong>Record adjustment</strong><span>Movement ledger entry</span></div></div><label>Product / SKU<select name="skuId" required defaultValue=""><option value="" disabled>Choose an active SKU</option>{products.length?products.flatMap((p)=>p.skus.map((s)=><option key={s.id} value={s.id}>{p.title} · {s.code}</option>)):balances.map((b)=><option key={b.skuId} value={b.skuId}>{skuName.get(b.skuId)??b.skuId}</option>)}</select></label><label>Quantity change<input name="delta" type="number" required placeholder="e.g. 12 or -2"/></label><label>Reason<input name="reason" required minLength={3} maxLength={500} placeholder="Cycle count correction"/></label><label>Idempotency key<input name="key" required minLength={8} maxLength={120} pattern="[A-Za-z0-9._:-]{8,120}" placeholder="cycle-count-2026-10-23"/></label><button className="button primary wide" disabled={saving}>Save stock movement <span aria-hidden="true">↗</span></button></form></section>
 <section className="section-block"><div className="section-heading"><div><span className="eyebrow">RETURN QUALITY</span><h2>Items waiting for inspection</h2></div><span className="result-count">{pendingReturns.length} RETURNS</span></div>{pendingReturns.length===0?<div className="empty-state compact"><div className="empty-icon">✓</div><h2>No returned units awaiting inspection</h2><p>Refunded returns appear here after the Orders service registers their unit manifest.</p></div>:<div className="configuration-groups">{pendingReturns.map((receipt)=><article className="section-block" key={receipt.returnId}><div className="section-heading"><div><span className="eyebrow">RETURN {receipt.returnId}</span><h3>Order {receipt.orderId.slice(0,8).toUpperCase()}</h3></div><span className="result-count">REVISION {receipt.revision}</span></div><form className="configuration-list" onSubmit={(event)=>{event.preventDefault();const form=event.currentTarget;const data=new FormData(form);const decisions=receipt.units.map((unit,index)=>({skuId:unit.skuId,ordinal:unit.ordinal,condition:data.get(`condition-${index}`),reason:data.get(`reason-${index}`)}));void run(async()=>{await api(`/api/inventory/returns/${receipt.returnId}/inspection`,token,{method:'POST',body:JSON.stringify({expectedRevision:receipt.revision,operationId:crypto.randomUUID(),decisions})});setMessage('Return inspection recorded. Only sellable units were returned to stock.');await refreshPending();await refresh()})}}>{receipt.units.map((unit,index)=><div className="configuration-row" key={`${unit.skuId}-${unit.ordinal}`}><div><strong>{skuName.get(unit.skuId)??unit.skuId}</strong><small>Returned unit {unit.ordinal+1} · received {new Date(receipt.receivedAt).toLocaleString('en-IN')}</small></div><label>Condition<select name={`condition-${index}`} required defaultValue=""><option value="" disabled>Choose condition</option><option value="SELLABLE">Sellable · restock</option><option value="DAMAGED">Damaged · keep out of stock</option><option value="DISPUTED">Disputed · keep out of stock</option></select></label><label>Inspection reason<input name={`reason-${index}`} required minLength={3} maxLength={500} placeholder="Describe the observed condition"/></label></div>)}<button className="button primary" disabled={saving}>Save inspection decisions</button></form></article>)}</div>}</section>
 <section className="section-block"><div className="section-heading"><div><span className="eyebrow">ON-HAND SUMMARY</span><h2>Warehouse stock</h2></div><span className="result-count">{balances.length} SKU BALANCES</span></div>{balances.length===0?<div className="empty-state compact"><div className="empty-icon">▤</div><h2>No inventory movements yet</h2><p>Load the fixture dataset or record the first stock adjustment.</p></div>:<div className="table-wrap"><table><thead><tr><th>PRODUCT</th><th>WAREHOUSE</th><th>ON HAND</th><th>REVISION</th><th>HEALTH</th></tr></thead><tbody>{balances.map((b)=><tr key={b.skuId}><td data-label="Product"><strong>{skuName.get(b.skuId)??b.skuId}</strong></td><td data-label="Warehouse">{b.warehouseName}</td><td data-label="On hand" className="quantity-cell">{b.onHand}</td><td data-label="Revision">{b.revision}</td><td data-label="Health"><span className={`status-tag ${Number(b.onHand)===0?'low-stock':''}`}>{Number(b.onHand)===0?'Out of stock':'In stock'}</span></td></tr>)}</tbody></table></div>}</section></>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)

function App() {
  return window.location.pathname.startsWith('/admin') ? <AdminApp/> : <CustomerStore/>
}
