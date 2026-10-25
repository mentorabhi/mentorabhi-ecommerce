"""Public lifecycle envelope validation for local analytical projections (v1/v2)."""
from datetime import datetime
import json
import re
from uuid import UUID

ENVELOPE = {'eventId','eventType','eventVersion','aggregateType','aggregateId','aggregateSequence','occurredAt','customerKey','data'}
V1 = {'OrderAccepted':'PENDING_PAYMENT','OrderConfirmed':'CONFIRMED','FulfillmentScheduled':'FULFILLMENT_SCHEDULED','OrderPaymentDeclined':'FAILED','OrderCheckoutExpired':'FAILED'}
V2 = {'OrderCancelled','OrderReturnRequested','OrderRefundCompleted','ShipmentMilestoneRecorded'}

def integer(value, minimum=0):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or int(value) != value or not minimum <= value <= 9223372036854775807:
        raise ValueError('invalid-integer')
    return int(value)

def fields(value, expected):
    if not isinstance(value,dict) or set(value) != set(expected): raise ValueError('unexpected-contract-fields')

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',value): raise ValueError('invalid-identifier')
    UUID(value)

def currency(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Z]{3}',value): raise ValueError('invalid-currency')

def parse_event(raw):
    try:
        event = json.loads(raw)
        fields(event,ENVELOPE)
        identifier(event['eventId']); identifier(event['aggregateId'])
        version = integer(event['eventVersion'],1)
        integer(event['aggregateSequence'],1)
        if event['aggregateType'] != 'Order' or not re.fullmatch('[0-9a-f]{64}',event['customerKey']): raise ValueError('invalid-envelope')
        occurred_at = event['occurredAt']
        # Java Instant emits nanosecond fractions while Python's datetime
        # parser accepts at most microseconds. Validate the same RFC3339
        # instant across host/container Python versions by truncating only the
        # fraction used for validation; the original event remains untouched.
        timestamp = re.fullmatch(r'(.+?)(?:\.(\d+))?(Z|[+-]\d{2}:\d{2})', occurred_at)
        if not timestamp: raise ValueError('invalid-timestamp')
        base, fraction, zone = timestamp.groups()
        normalized = base + ('.' + fraction[:6] if fraction else '') + zone.replace('Z', '+00:00')
        if datetime.fromisoformat(normalized).tzinfo is None: raise ValueError('missing-timezone')
        data = event['data']; kind = event['eventType']
        if not isinstance(data,dict) or data.get('orderId') != event['aggregateId']: raise ValueError('aggregate-mismatch')
        base = {'orderId','state'}
        if version == 1 and kind in V1:
            if data.get('state') != V1[kind]: raise ValueError('invalid-state')
            if kind == 'OrderAccepted':
                fields(data,base|{'checkoutRequestId','currency','subtotalMinor','discountMinor','taxMinor','shippingMinor','totalMinor','lines'})
                identifier(data['checkoutRequestId']); currency(data['currency'])
                if not isinstance(data['lines'],list) or not 1 <= len(data['lines']) <= 100: raise ValueError('invalid-lines')
                subtotal = discounts = 0
                for line in data['lines']:
                    fields(line,{'skuId','productId','productTitle','quantity','unitPriceMinor','discountMinor','lineTotalMinor','currency'})
                    identifier(line['skuId']); identifier(line['productId'])
                    if not isinstance(line['productTitle'],str) or not 1 <= len(line['productTitle']) <= 240 or line['currency'] != data['currency']: raise ValueError('invalid-line')
                    quantity = integer(line['quantity'],1); price = integer(line['unitPriceMinor']); discount = integer(line['discountMinor'])
                    if integer(line['lineTotalMinor']) != quantity*price-discount: raise ValueError('line-money-mismatch')
                    subtotal += quantity*price; discounts += discount
                if integer(data['subtotalMinor']) != subtotal or integer(data['discountMinor']) != discounts: raise ValueError('subtotal-mismatch')
                if integer(data['totalMinor']) != subtotal-discounts+integer(data['taxMinor'])+integer(data['shippingMinor']): raise ValueError('total-mismatch')
            elif V1[kind] == 'FAILED':
                fields(data,base|{'reason'})
                if data['reason'] not in {'PAYMENT_DECLINED','QUOTE_EXPIRED'}: raise ValueError('invalid-reason')
            else: fields(data,base)
        elif version == 2 and kind in V2:
            if kind == 'OrderCancelled':
                fields(data,base|{'operationId','refundMinor','currency','reasonCode'})
                identifier(data['operationId']); integer(data['refundMinor']); currency(data['currency'])
                if data['state'] != 'CANCELLED' or data['reasonCode'] not in {'CUSTOMER_REQUEST','SIMULATED_POLICY'}: raise ValueError('invalid-cancellation')
            elif kind == 'OrderRefundCompleted':
                fields(data,base|{'refundId','amountMinor','currency','reasonCode'})
                identifier(data['refundId']); integer(data['amountMinor']); currency(data['currency'])
                if data['state'] not in {'CANCELLED','DELIVERED'} or data['reasonCode'] not in {'CANCELLATION','RETURN'}: raise ValueError('invalid-refund')
            elif kind == 'OrderReturnRequested':
                fields(data,base|{'returnId','lines','policyRevision'})
                identifier(data['returnId']); integer(data['policyRevision'],1)
                if data['state'] != 'DELIVERED' or not isinstance(data['lines'],list) or not data['lines']: raise ValueError('invalid-return')
                for line in data['lines']:
                    fields(line,{'skuId','quantity'}); identifier(line['skuId']); integer(line['quantity'],1)
            else:
                fields(data,base|{'shipmentState','shipmentRevision','operationId'})
                identifier(data['operationId']); integer(data['shipmentRevision'],1)
                if data['shipmentState'] not in {'HANDED_OFF','IN_TRANSIT','DELIVERED'} or data['state'] != ('DELIVERED' if data['shipmentState']=='DELIVERED' else 'FULFILLMENT_SCHEDULED'): raise ValueError('invalid-shipment')
        else: raise ValueError('unsupported-event')
        return event
    except (TypeError,KeyError,ValueError,OverflowError,AttributeError) as error:
        raise ValueError('invalid-lifecycle-contract') from error

def valid_event(raw):
    try: parse_event(raw); return True
    except ValueError: return False
