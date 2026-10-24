package com.supersports.inventory;
import java.util.*;import java.sql.Timestamp;import java.time.Instant;import org.springframework.jdbc.core.JdbcTemplate;import org.springframework.stereotype.Repository;import org.springframework.transaction.annotation.Transactional;
@Repository class InventoryRepository{
 static final UUID WAREHOUSE=UUID.fromString("00000000-0000-4000-8000-000000000001");private final JdbcTemplate jdbc;InventoryRepository(JdbcTemplate j){jdbc=j;}
 @Transactional void acceptCheckoutFence(UUID orderId,long fence){if(fence<1)throw new IllegalArgumentException("Checkout fence must be positive");jdbc.update("INSERT INTO checkout_order_fence(order_id,fence) VALUES (?,?) ON CONFLICT(order_id) DO UPDATE SET fence=EXCLUDED.fence,updated_at=now() WHERE checkout_order_fence.fence<=EXCLUDED.fence",orderId,fence);Long current=jdbc.queryForObject("SELECT fence FROM checkout_order_fence WHERE order_id=? FOR UPDATE",Long.class,orderId);if(current==null||current!=fence)throw new StaleCheckoutFenceException();}
 static final class StaleCheckoutFenceException extends RuntimeException{}
 List<Map<String,Object>> balances(){return jdbc.queryForList("SELECT w.id AS \"warehouseId\",w.name AS \"warehouseName\",b.sku_id AS \"skuId\",COALESCE(b.on_hand,0) AS \"onHand\",COALESCE(b.revision,0) AS revision FROM warehouse w LEFT JOIN inventory_balance b ON b.warehouse_id=w.id WHERE w.active ORDER BY w.name,b.sku_id");}
 long availability(UUID sku){return jdbc.queryForObject("SELECT GREATEST(0,COALESCE(sum(b.on_hand),0)-COALESCE((SELECT sum(l.quantity) FROM inventory_reservation_line l JOIN inventory_reservation r ON r.id=l.reservation_id WHERE l.sku_id=? AND r.state IN ('HELD','PROTECTED') AND (r.state='PROTECTED' OR r.expires_at>now())),0)) FROM inventory_balance b JOIN warehouse w ON w.id=b.warehouse_id AND w.active WHERE b.sku_id=?",Long.class,sku,sku);}
 List<Map<String,Object>> movements(UUID sku){return jdbc.queryForList("SELECT id,warehouse_id AS \"warehouseId\",sku_id AS \"skuId\",delta,actor,reason,idempotency_key AS \"idempotencyKey\",source,occurred_at AS \"occurredAt\" FROM stock_movement WHERE (? IS NULL OR sku_id=?) ORDER BY occurred_at DESC LIMIT 500",sku,sku);}
 @Transactional Map<String,Object> adjust(UUID sku,long delta,String actor,String reason,String key){InventoryRules.validateAdjustment(delta,reason,key);jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,key),rs->{rs.next();return null;});var prior=jdbc.queryForList("SELECT id,sku_id AS \"skuId\",delta,actor,reason FROM stock_movement WHERE idempotency_key=?",key);if(!prior.isEmpty()){var old=prior.getFirst();if(!sku.toString().equals(old.get("skuId").toString())||delta!=((Number)old.get("delta")).longValue()||!actor.equals(old.get("actor"))||!reason.trim().equals(old.get("reason")))return Map.of("conflict",true);return Map.of("movementId",old.get("id"),"skuId",sku,"delta",delta,"replayed",true);}
 jdbc.update("INSERT INTO inventory_balance(warehouse_id,sku_id,on_hand) VALUES (?,?,0) ON CONFLICT DO NOTHING",WAREHOUSE,sku);long current=jdbc.queryForObject("SELECT on_hand FROM inventory_balance WHERE warehouse_id=? AND sku_id=? FOR UPDATE",Long.class,WAREHOUSE,sku);long next=InventoryRules.resultingStock(current,delta);UUID movement=UUID.randomUUID();jdbc.update("INSERT INTO stock_movement(id,warehouse_id,sku_id,delta,actor,reason,idempotency_key) VALUES (?,?,?,?,?,?,?)",movement,WAREHOUSE,sku,delta,actor,reason.trim(),key);jdbc.update("UPDATE inventory_balance SET on_hand=?,revision=revision+1 WHERE warehouse_id=? AND sku_id=?",next,WAREHOUSE,sku);return Map.of("movementId",movement,"skuId",sku,"delta",delta,"onHand",next,"replayed",false);}
 @Transactional Map<String,Object> reserve(UUID orderId,Map<UUID,Long> requested,Instant expiresAt){
  Instant now=Instant.now();if(requested==null||requested.isEmpty()||expiresAt==null||!expiresAt.isAfter(now)||expiresAt.isAfter(now.plusSeconds(1800))||requested.values().stream().anyMatch(q->q==null||q<=0))throw new IllegalArgumentException("Reservation expiry must be within 30 minutes and quantities positive");
  jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,"checkout-reservation:"+orderId),rs->{rs.next();return null;});
  var prior=jdbc.queryForList("SELECT id,state,expires_at FROM inventory_reservation WHERE order_id=? FOR UPDATE",orderId);
  if(!prior.isEmpty()){
   UUID id=(UUID)prior.getFirst().get("id");var old=jdbc.queryForList("SELECT sku_id,quantity FROM inventory_reservation_line WHERE reservation_id=?",id);
   var oldLines=new HashMap<UUID,Long>();old.forEach(line->oldLines.put((UUID)line.get("sku_id"),((Number)line.get("quantity")).longValue()));
   if(!oldLines.equals(requested))return Map.of("conflict",true);
   String state=prior.getFirst().get("state").toString();
   if(state.equals("HELD")&&((Timestamp)prior.getFirst().get("expires_at")).toInstant().isBefore(now)){
    for(UUID sku:requested.keySet().stream().sorted().toList()){
     long onHand=jdbc.queryForObject("SELECT on_hand FROM inventory_balance WHERE warehouse_id=? AND sku_id=? FOR UPDATE",Long.class,WAREHOUSE,sku);
     long held=jdbc.queryForObject("SELECT COALESCE(sum(l.quantity),0) FROM inventory_reservation_line l JOIN inventory_reservation r ON r.id=l.reservation_id WHERE l.warehouse_id=? AND l.sku_id=? AND r.state IN ('HELD','PROTECTED') AND (r.state='PROTECTED' OR r.expires_at>now())",Long.class,WAREHOUSE,sku);
     if(!InventoryReservationRules.canReserve(onHand,requested.get(sku),held))throw new InsufficientStockException();
    }
    jdbc.update("UPDATE inventory_reservation SET expires_at=?,updated_at=now() WHERE id=?",Timestamp.from(expiresAt),id);
    return Map.of("reservationId",id,"state","HELD","replayed",false,"renewed",true);
   }
   return Map.of("reservationId",id,"state",state,"replayed",true);
  }
  for(UUID sku:requested.keySet().stream().sorted().toList()){
   jdbc.update("INSERT INTO inventory_balance(warehouse_id,sku_id,on_hand) VALUES (?,?,0) ON CONFLICT DO NOTHING",WAREHOUSE,sku);
   long onHand=jdbc.queryForObject("SELECT on_hand FROM inventory_balance WHERE warehouse_id=? AND sku_id=? FOR UPDATE",Long.class,WAREHOUSE,sku);
   long held=jdbc.queryForObject("SELECT COALESCE(sum(l.quantity),0) FROM inventory_reservation_line l JOIN inventory_reservation r ON r.id=l.reservation_id WHERE l.warehouse_id=? AND l.sku_id=? AND r.state IN ('HELD','PROTECTED') AND (r.state='PROTECTED' OR r.expires_at>now())",Long.class,WAREHOUSE,sku);
   if(!InventoryReservationRules.canReserve(onHand,requested.get(sku),held))throw new InsufficientStockException();
  }
  UUID id=UUID.randomUUID();jdbc.update("INSERT INTO inventory_reservation(id,order_id,state,expires_at) VALUES (?,?,'HELD',?)",id,orderId,Timestamp.from(expiresAt));
  requested.entrySet().stream().sorted(Map.Entry.comparingByKey()).forEach(e->jdbc.update("INSERT INTO inventory_reservation_line(reservation_id,warehouse_id,sku_id,quantity) VALUES (?,?,?,?)",id,WAREHOUSE,e.getKey(),e.getValue()));
  return Map.of("reservationId",id,"state","HELD","replayed",false);
 }
 @Transactional Map<String,Object> transitionReservation(UUID orderId,String target){
  if(!Set.of("PROTECTED","COMMITTED","RELEASED").contains(target))throw new IllegalArgumentException("Unsupported reservation transition");
  var rows=jdbc.queryForList("SELECT id,state FROM inventory_reservation WHERE order_id=? FOR UPDATE",orderId);if(rows.isEmpty())throw new ReservationNotFoundException();
  UUID id=(UUID)rows.getFirst().get("id");String state=rows.getFirst().get("state").toString();if(state.equals(target))return Map.of("orderId",orderId,"state",state,"replayed",true);
  if(target.equals("PROTECTED")&&!state.equals("HELD"))throw new IllegalStateException("Only held reservations can be protected");
  if((target.equals("COMMITTED")||target.equals("RELEASED"))&&!Set.of("HELD","PROTECTED").contains(state))throw new IllegalStateException("Reservation is already terminal");
  if(state.equals("HELD")&&jdbc.queryForObject("SELECT expires_at>now() FROM inventory_reservation WHERE id=?",Boolean.class,id)==false)throw new IllegalStateException("Reservation expired");
  if(target.equals("COMMITTED"))for(var line:jdbc.queryForList("SELECT sku_id,warehouse_id,quantity FROM inventory_reservation_line WHERE reservation_id=? ORDER BY sku_id",id)){
   UUID sku=(UUID)line.get("sku_id");long qty=((Number)line.get("quantity")).longValue();long current=jdbc.queryForObject("SELECT on_hand FROM inventory_balance WHERE warehouse_id=? AND sku_id=? FOR UPDATE",Long.class,line.get("warehouse_id"),sku);long next=InventoryReservationRules.committedOnHand(current,qty);String key="checkout:"+orderId+":commit:"+sku;
   jdbc.update("INSERT INTO stock_movement(id,warehouse_id,sku_id,delta,actor,reason,idempotency_key,source) VALUES (?,?,?,?,?,?,?,'checkout')",UUID.randomUUID(),line.get("warehouse_id"),sku,-qty,orderId.toString(),"Checkout reservation committed",key);
   jdbc.update("UPDATE inventory_balance SET on_hand=?,revision=revision+1 WHERE warehouse_id=? AND sku_id=?",next,line.get("warehouse_id"),sku);
  }
  jdbc.update("UPDATE inventory_reservation SET state=?,updated_at=now() WHERE id=?",target,id);return Map.of("orderId",orderId,"state",target,"replayed",false);
 }
 @Transactional Map<String,Object> cancelCommittedReservation(UUID orderId,UUID operationId){
  jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,"reservation-cancel:"+orderId),rs->{rs.next();return null;});
  var rows=jdbc.queryForList("SELECT id,state,cancellation_operation_id FROM inventory_reservation WHERE order_id=? FOR UPDATE",orderId);
  if(rows.isEmpty())throw new ReservationNotFoundException();var reservation=rows.getFirst();
  if(operationId.equals(reservation.get("cancellation_operation_id")))return Map.of("orderId",orderId,"state","CANCELLED","replayed",true);
  if(reservation.get("cancellation_operation_id")!=null||!"COMMITTED".equals(reservation.get("state")))throw new IllegalStateException("Only a committed reservation can be cancelled");
  UUID reservationId=(UUID)reservation.get("id");
  for(var line:jdbc.queryForList("SELECT warehouse_id,sku_id,quantity FROM inventory_reservation_line WHERE reservation_id=? ORDER BY sku_id",reservationId)){
   UUID sku=(UUID)line.get("sku_id");long qty=((Number)line.get("quantity")).longValue();UUID warehouse=(UUID)line.get("warehouse_id");
   Long current=jdbc.queryForObject("SELECT on_hand FROM inventory_balance WHERE warehouse_id=? AND sku_id=? FOR UPDATE",Long.class,warehouse,sku);
   long next=Math.addExact(current,qty);String key="cancel:"+operationId+":"+sku;
   jdbc.update("INSERT INTO stock_movement(id,warehouse_id,sku_id,delta,actor,reason,idempotency_key,source) VALUES (?,?,?,?,?,?,?,'cancellation')",UUID.randomUUID(),warehouse,sku,qty,"supersports-orders","Committed order cancellation restock",key);
   jdbc.update("UPDATE inventory_balance SET on_hand=?,revision=revision+1 WHERE warehouse_id=? AND sku_id=?",next,warehouse,sku);
  }
  jdbc.update("UPDATE inventory_reservation SET state='CANCELLED',cancellation_operation_id=?,updated_at=now() WHERE id=?",operationId,reservationId);
  return Map.of("orderId",orderId,"state","CANCELLED","replayed",false);
 }
 @Transactional Map<String,Object> registerReturn(UUID returnId,UUID orderId,List<ReturnInspectionRules.UnitKey> units){
  if(returnId==null||orderId==null||units==null||units.isEmpty()||units.size()>5000||units.stream().anyMatch(unit->unit==null||unit.skuId()==null||unit.ordinal()<0))throw new IllegalArgumentException("Invalid return manifest");
  var ordered=units.stream().sorted(Comparator.comparing((ReturnInspectionRules.UnitKey unit)->unit.skuId().toString()).thenComparingInt(ReturnInspectionRules.UnitKey::ordinal)).toList();
  if(ordered.stream().map(unit->unit.skuId()+":"+unit.ordinal()).distinct().count()!=ordered.size())throw new IllegalArgumentException("Duplicate return manifest unit");
  String hash=ReturnInspectionRules.hashUnits(ordered);
  var prior=jdbc.queryForList("SELECT order_id,manifest_hash,state,revision FROM inventory_return WHERE return_id=? FOR UPDATE",returnId);
  if(!prior.isEmpty()){var row=prior.getFirst();if(!orderId.equals(row.get("order_id"))||!hash.equals(row.get("manifest_hash").toString().trim()))throw new ReturnOperationConflictException();return Map.of("returnId",returnId,"orderId",orderId,"state",row.get("state"),"revision",row.get("revision"),"replayed",true);}
  jdbc.update("INSERT INTO inventory_return(return_id,order_id,manifest_hash,state) VALUES (?,?,?,'RECEIVED')",returnId,orderId,hash);
  for(var unit:ordered)jdbc.update("INSERT INTO inventory_return_unit(return_id,order_id,sku_id,unit_ordinal) VALUES (?,?,?,?)",returnId,orderId,unit.skuId(),unit.ordinal());
  return Map.of("returnId",returnId,"orderId",orderId,"state","RECEIVED","revision",0,"replayed",false);
 }
 @Transactional Map<String,Object> inspectReturn(UUID returnId,long expectedRevision,UUID operationId,String actor,List<ReturnInspectionRules.Decision> decisions){
  if(returnId==null||operationId==null||expectedRevision<0)throw new IllegalArgumentException("Invalid inspection identity or revision");
  jdbc.query("SELECT pg_advisory_xact_lock(hashtextextended(?,0))",ps->ps.setString(1,"return-inspection-operation:"+operationId),rs->{rs.next();return null;});
  var rows=jdbc.queryForList("SELECT order_id,state,revision FROM inventory_return WHERE return_id=? FOR UPDATE",returnId);if(rows.isEmpty())throw new ReturnNotFoundException();var parent=rows.getFirst();
  var receivedRows=jdbc.queryForList("SELECT sku_id,unit_ordinal FROM inventory_return_unit WHERE return_id=? ORDER BY sku_id,unit_ordinal",returnId);
  var received=receivedRows.stream().map(row->new ReturnInspectionRules.UnitKey((UUID)row.get("sku_id"),((Number)row.get("unit_ordinal")).intValue())).toList();
  List<ReturnInspectionRules.Decision> validated=ReturnInspectionRules.validate(decisions,received);String hash=ReturnInspectionRules.hash(validated);
  var prior=jdbc.queryForList("SELECT return_id,request_hash,previous_revision,next_revision,actor_subject,inspected_units,created_at FROM inventory_return_inspection_audit WHERE operation_id=?",operationId);
  if(!prior.isEmpty()){var audit=prior.getFirst();if(!returnId.equals(audit.get("return_id"))||!hash.equals(audit.get("request_hash").toString().trim()))throw new ReturnOperationConflictException();return Map.of("returnId",returnId,"state","INSPECTED","revision",audit.get("next_revision"),"operationId",operationId,"actorSubject",audit.get("actor_subject"),"inspectedUnits",audit.get("inspected_units"),"replayed",true);}
  long revision=((Number)parent.get("revision")).longValue();if(revision!=expectedRevision)throw new StaleReturnRevisionException();if(!"RECEIVED".equals(parent.get("state")))throw new IllegalStateException("Return has already been inspected");
  if(actor==null||actor.isBlank()||actor.length()>160)throw new IllegalArgumentException("Invalid inspection actor");long next=revision+1;
  for(var decision:validated){UUID sku=decision.skuId();int changed=jdbc.update("UPDATE inventory_return_unit SET condition=?,reason=?,inspected_by=?,inspected_at=now() WHERE return_id=? AND sku_id=? AND unit_ordinal=? AND condition='PENDING'",decision.condition(),decision.reason().trim(),actor,returnId,sku,decision.ordinal());if(changed!=1)throw new IllegalStateException("Return unit is already inspected");
   if("SELLABLE".equals(decision.condition())){jdbc.update("INSERT INTO inventory_balance(warehouse_id,sku_id,on_hand) VALUES (?,?,0) ON CONFLICT DO NOTHING",WAREHOUSE,sku);long current=jdbc.queryForObject("SELECT on_hand FROM inventory_balance WHERE warehouse_id=? AND sku_id=? FOR UPDATE",Long.class,WAREHOUSE,sku);long updated=Math.addExact(current,1);String movementKey="return:"+returnId+":"+sku+":"+decision.ordinal();jdbc.update("INSERT INTO stock_movement(id,warehouse_id,sku_id,delta,actor,reason,idempotency_key,source) VALUES (?,?,?,?,?,?,?,'return-inspection')",UUID.randomUUID(),WAREHOUSE,sku,1,actor,"Sellable returned unit restocked",movementKey);jdbc.update("UPDATE inventory_balance SET on_hand=?,revision=revision+1 WHERE warehouse_id=? AND sku_id=?",updated,WAREHOUSE,sku);}
  }
  jdbc.update("INSERT INTO inventory_return_inspection_audit(operation_id,return_id,request_hash,previous_revision,next_revision,actor_subject,inspected_units) VALUES (?,?,?,?,?,?,?)",operationId,returnId,hash,revision,next,actor,validated.size());
  jdbc.update("UPDATE inventory_return SET state='INSPECTED',revision=?,updated_at=now() WHERE return_id=? AND revision=?",next,returnId,revision);
  return Map.of("returnId",returnId,"orderId",parent.get("order_id"),"state","INSPECTED","revision",next,"operationId",operationId,"actorSubject",actor,"inspectedUnits",validated.size(),"replayed",false);
 }
 List<Map<String,Object>> pendingReturns(){var parents=jdbc.queryForList("SELECT return_id AS \"returnId\",order_id AS \"orderId\",revision,created_at AS \"receivedAt\" FROM inventory_return WHERE state='RECEIVED' ORDER BY created_at,return_id");var result=new ArrayList<Map<String,Object>>();for(var parent:parents){var row=new LinkedHashMap<String,Object>(parent);row.put("units",jdbc.queryForList("SELECT sku_id AS \"skuId\",unit_ordinal AS ordinal,condition FROM inventory_return_unit WHERE return_id=? ORDER BY sku_id,unit_ordinal",parent.get("returnId")));result.add(row);}return result;}
 static final class ReturnNotFoundException extends RuntimeException{}
 static final class ReturnOperationConflictException extends RuntimeException{}
 static final class StaleReturnRevisionException extends RuntimeException{}
 static final class InsufficientStockException extends RuntimeException{}
 static final class ReservationNotFoundException extends RuntimeException{}
}
