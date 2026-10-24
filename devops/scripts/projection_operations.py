"""Reconcile retained Orders facts with Kafka and an Order History candidate."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from uuid import uuid4

STATES={"OrderAccepted":"PENDING_PAYMENT","OrderConfirmed":"CONFIRMED",
        "FulfillmentScheduled":"FULFILLMENT_SCHEDULED","OrderPaymentDeclined":"FAILED","OrderCheckoutExpired":"FAILED"}


def canonical_hash(value):
    def normalized(item):
        if isinstance(item,dict):return {key:normalized(child) for key,child in item.items()}
        if isinstance(item,list):return [normalized(child) for child in item]
        if isinstance(item,float) and item.is_integer():return int(item)
        return item
    return hashlib.sha256(json.dumps(normalized(value),sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def compare_snapshot(source, inspection, expected_audit=None):
    errors=[]
    scan=inspection["scan"]; snapshot=inspection["snapshot"]
    def indexed(rows,key,label):
        result={row[key]:row for row in rows}
        if len(result)!=len(rows):errors.append(label+"_DUPLICATE_ID")
        return result
    expected=indexed(source["events"],"eventId","OUTBOX")
    kafka=indexed(scan["events"],"eventId","KAFKA")
    inbox=indexed(snapshot["events"],"eventId","INBOX")
    timeline=indexed(snapshot["timeline"],"eventId","TIMELINE")
    for name,rows in (("KAFKA",kafka),("INBOX",inbox),("TIMELINE",timeline)):
        if set(rows)!=set(expected):errors.append(name+"_EVENT_SET_MISMATCH")
    for event_id,event in expected.items():
        fingerprint=canonical_hash(event)
        retained=kafka.get(event_id)
        if retained and retained["canonicalHash"]!=fingerprint:errors.append("KAFKA_EVENT_HASH_MISMATCH:"+event_id)
        applied=inbox.get(event_id)
        if applied:
            if applied.get("canonicalHash") is not None:
                matches=applied["canonicalHash"]==fingerprint
            else:matches=retained is not None and applied["rawHash"] in retained["rawHashes"]
            if not matches:errors.append("INBOX_EVENT_HASH_MISMATCH:"+event_id)
        step=timeline.get(event_id)
        if step:
            fields=(step["orderId"]==event["aggregateId"] and step["sequence"]==event["aggregateSequence"]
                    and step["eventType"]==event["eventType"] and step["state"]==STATES.get(event["eventType"]))
            try:
                time_matches=abs((datetime.fromisoformat(step["occurredAt"])-datetime.fromisoformat(event["occurredAt"])).total_seconds())<=0.000001
            except (ValueError,TypeError):time_matches=False
            if not fields or not time_matches:errors.append("TIMELINE_CONTENT_MISMATCH:"+event_id)
    orders=indexed(source["orders"],"orderId","ORDERS")
    projected=indexed(snapshot["orders"],"orderId","PROJECTION")
    if set(orders)!=set(projected):errors.append("ORDER_SET_MISMATCH")
    totals={}
    for order_id,order in orders.items():
        totals[order["currency"]]=totals.get(order["currency"],0)+order["totalMinor"]
        candidate=projected.get(order_id)
        if candidate:
            if any(candidate[key]!=order[key] for key in ("state","currency","totalMinor","customerKey","lastSequence")):
                errors.append("ORDER_STATE_OWNER_MONEY_MISMATCH:"+order_id)
            ordered=lambda rows:sorted(rows,key=lambda row:row["skuId"])
            if canonical_hash(ordered(candidate["lines"]))!=canonical_hash(ordered(order["lines"])):
                errors.append("ORDER_LINES_MISMATCH:"+order_id)
    if snapshot["pendingEvents"]:errors.append("PENDING_SEQUENCE_GAPS")
    if scan["conflicts"]:errors.append("KAFKA_EVENT_ID_CONTENT_CONFLICT")
    audits={row["operation_id"]:row for row in snapshot["audit"]}
    deliveries={row["operation_id"]:row for row in snapshot["deliveries"]}
    for poison in scan["poison"]:
        resolved=False
        for operation_id,audit in audits.items():
            delivery=deliveries.get(operation_id,{})
            event=expected.get(audit["event_id"])
            if (audit["source_coordinate"]==poison["coordinate"] and delivery.get("published_offset") is not None
                    and event is not None and audit["replay_payload_hash"]==canonical_hash(event)
                    and audit.get("original_payload_hash")==poison.get("rawHash")):
                resolved=True;break
        if not resolved:errors.append("UNRESOLVED_POISON:"+poison["coordinate"])
    if any(row.get("published_offset") is None for row in deliveries.values()):errors.append("UNPUBLISHED_REPLAY_INTENT")
    if expected_audit is not None:
        for name in ("audit","deliveries"):
            if canonical_hash(sorted(snapshot[name],key=lambda row:row["operation_id"]))!=canonical_hash(sorted(expected_audit[name],key=lambda row:row["operation_id"])):
                errors.append("REPLAY_"+name.upper()+"_COPY_MISMATCH")
    return {"ok":not errors,"events":len(expected),"orders":len(orders),"totalsMinor":totals,
            "totalsScope":"all current order states; not recognized sales","poisonRecords":len(scan["poison"]),
            "replayAudits":len(audits),"highWater":scan["highWater"],"errorCount":len(errors),"errors":errors[:50],
            "limitation":"Historical reconciliation covers retained outbox and Kafka records; current order rows alone do not prove historical transitions."}


def source_snapshot(manage, *, project="supersports", version="s1-m06"):
    # Explicit local owner/admin diagnostic, never a service's cross-database query.
    query="""SELECT json_build_object(
      'events',(SELECT coalesce(json_agg(payload ORDER BY id),'[]') FROM order_outbox),
      'orders',(SELECT coalesce(json_agg(row_to_json(facts) ORDER BY facts.\"orderId\"),'[]') FROM (
        SELECT o.id AS \"orderId\",o.state,o.currency,o.total_minor AS \"totalMinor\",
          (SELECT customer_key FROM order_outbox WHERE aggregate_id=o.id ORDER BY aggregate_sequence DESC LIMIT 1) AS \"customerKey\",
          (SELECT max(aggregate_sequence) FROM order_outbox WHERE aggregate_id=o.id) AS \"lastSequence\",
          (SELECT coalesce(json_agg(json_build_object('skuId',sku_id,'productId',product_id,'productTitle',product_title,
             'quantity',quantity,'unitPriceMinor',unit_price_minor,'discountMinor',discount_minor,
             'lineTotalMinor',line_total_minor,'currency',currency) ORDER BY sku_id),'[]')
           FROM customer_order_line WHERE order_id=o.id) AS lines FROM customer_order o) facts))::text"""
    result=manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","orders","-tA","-v","ON_ERROR_STOP=1","-c",query],
                          project=project,version=version,capture=True)
    return json.loads(result.stdout.strip())


def reconcile(manage, *, project="supersports", version="s1-m06"):
    import stream_operations
    for attempt in range(3):
        before=source_snapshot(manage,project=project,version=version)
        inspection=stream_operations.operator(manage,{"action":"inspect"},project=project,version=version)
        after=source_snapshot(manage,project=project,version=version)
        if canonical_hash(before)==canonical_hash(after):
            result=compare_snapshot(after,inspection)
            if result["ok"] or attempt==2:return {**result,"target":manage.history_target(project=project)}
        time.sleep(1)
    return {"ok":False,"errors":["SOURCE_CHANGED_DURING_RECONCILIATION"],"target":manage.history_target(project=project)}


def _copy_replay_audit(manage, old, candidate, project, version):
    dump=manage.compose(["exec","-T","postgres","pg_dump","-U","postgres","-d",old["database"],
        "--data-only","--no-owner","--no-acl","--table=public.order_history_replay_audit","--table=public.order_history_replay_delivery"],
        project=project,version=version,capture=True)
    manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d",candidate["database"],"-v","ON_ERROR_STOP=1"],
                   project=project,version=version,capture=True,input_text=dump.stdout)


def activate(manage, candidate, *, project="supersports", version="s1-m06"):
    old=manage.history_target(project=project)
    command=["--profile","streaming","up","-d","--no-deps","--force-recreate","--wait","--wait-timeout","120","order-history"]
    try:
        manage.compose(command,project=project,version=version,history_override=candidate)
        manage.set_history_target(candidate,project=project)
    except (RuntimeError,OSError) as error:
        try:manage.compose(command,project=project,version=version,history_override=old)
        except RuntimeError as rollback:raise RuntimeError("CUTOVER_FAILED_ROLLBACK_FAILED") from rollback
        raise RuntimeError("CUTOVER_FAILED_OLD_TARGET_RESTORED") from error


def rebuild(manage, *, project="supersports", version="s1-m06", dry_run=False, inject_mismatch=False):
    import stream_operations
    if dry_run and inject_mismatch:raise ValueError("Choose either --dry-run or --inject-reconciliation-mismatch.")
    operation=uuid4().hex
    suffix=operation[:12]
    candidate={"database":"order_history_r_"+suffix,"group":"order-history-r-"+suffix}
    old=manage.history_target(project=project)
    directory=manage.ROOT/"devops/.local/stream-rebuilds"/manage.validated_project_name(project)
    if directory.is_symlink() or directory.parent.is_symlink():raise ValueError("Refusing a symlinked rebuild receipt directory.")
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=directory/(operation+".json")
    record={"operationId":operation,"candidate":candidate,"previousTarget":old,"ok":False,"status":"CREATED"}
    def persist():
        descriptor,temporary=tempfile.mkstemp(prefix=".receipt-",dir=directory)
        try:
            with os.fdopen(descriptor,"w") as handle:json.dump(record,handle,indent=2);handle.write("\n");handle.flush();os.fsync(handle.fileno())
            os.replace(temporary,path)
        finally:Path(temporary).unlink(missing_ok=True)
    persist()
    try:
        active=stream_operations.operator(manage,{"action":"snapshot"},project=project,version=version)
        database=manage.validated_history_target(candidate)["database"]
        manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","postgres","-v","ON_ERROR_STOP=1",
                        "-c",f'CREATE DATABASE "{database}" OWNER supersports_order_history ALLOW_CONNECTIONS false'],project=project,version=version,capture=True)
        manage.compose(["exec","-T","postgres","psql","-X","-U","postgres","-d","postgres","-v","ON_ERROR_STOP=1",
                        "-c",f'REVOKE ALL ON DATABASE "{database}" FROM PUBLIC; ALTER DATABASE "{database}" ALLOW_CONNECTIONS true'],project=project,version=version,capture=True)
        stream_operations.operator(manage,{"action":"snapshot"},project=project,version=version,target=candidate)
        _copy_replay_audit(manage,old,candidate,project,version)
        record["status"]="REPLAYING";persist()
        for attempt in range(3):
            before=source_snapshot(manage,project=project,version=version)
            inspection=stream_operations.operator(manage,{"action":"rebuild","injectMismatch":inject_mismatch},
                                                   project=project,version=version,target=candidate)
            after=source_snapshot(manage,project=project,version=version)
            if canonical_hash(before)==canonical_hash(after):break
        else:raise RuntimeError("SOURCE_CHANGED_DURING_REBUILD")
        result=compare_snapshot(after,inspection,expected_audit=active)
        record["reconciliation"]=result;record["watermarks"]=inspection["watermarks"]
        if not result["ok"]:
            record["status"]="RECONCILIATION_FAILED";return {**record,"receiptFile":str(path)}
        record["status"]="RECONCILED";persist()
        if not dry_run:
            activate(manage,candidate,project=project,version=version)
        record["ok"]=True;record["status"]="DRY_RUN_VERIFIED" if dry_run else "ACTIVE"
        return {**record,"receiptFile":str(path)}
    except RuntimeError as error:
        record["status"]="FAILED";record["errors"]=[str(error)]
        return {**record,"receiptFile":str(path)}
    finally:persist()
