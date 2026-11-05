from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Optional
D=Decimal
def money(x): return D(str(x)).quantize(D("0.01"), rounding=ROUND_HALF_UP)

@dataclass(frozen=True)
class Requisition:
    requisition_id:str; item_id:str; amount:Decimal; requested_on:date
@dataclass(frozen=True)
class Vendor:
    vendor_id:str; state:str; is_msme:bool=False
    on_time_pct:Decimal=D("100"); rejection_pct:Decimal=D("0")
@dataclass(frozen=True)
class Quote:
    vendor_id:str; base_price:Decimal; freight:Decimal=D("0"); customs:Decimal=D("0")
    other_costs:Decimal=D("0"); score:Decimal=D("0"); valid:bool=True
    received_at:Optional[datetime]=None; rfq_close:Optional[datetime]=None
    valid_until:Optional[date]=None; currency:str="INR"; exchange_rate:Optional[Decimal]=None
    is_import:bool=False; unit_weight_kg:Decimal=D("0"); distance_km:Decimal=D("0")
@dataclass(frozen=True)
class Award:
    vendor_id:str; landed_cost:Decimal; score:Decimal; reason:str; status:str="AWARDED"
@dataclass(frozen=True)
class MatchResult:
    matched:bool; hold_reasons:tuple[str,...]
@dataclass(frozen=True)
class ReceiptResult:
    accepted_quantity:Decimal; rejected_quantity:Decimal; status:str
@dataclass(frozen=True)
class PaymentInvoice:
    invoice_id:str; vendor_id:str; amount:Decimal; received_on:date; approved_on:date
    due_date:date; is_msme:bool=False; pre_gst_amount:Decimal=D("0"); status:str="APPROVED"

def approval_level(amount):
    a=D(amount)
    return "AUTO_APPROVED" if a<=D("50000") else ("MANAGER" if a<=D("500000") else "DIRECTOR")

def aggregate_split_value(reqs,item_id,on_date,window_days=7):
    start=on_date-timedelta(days=window_days)
    return sum((D(r.amount) for r in reqs if r.item_id==item_id and start<=r.requested_on<=on_date),D("0"))

def approval_for_requisition(req,all_reqs):
    total=aggregate_split_value(all_reqs,req.item_id,req.requested_on)
    return approval_level(max(D(req.amount),total)),total

def detect_split_requisitions(reqs,window_days=7):
    rows=sorted(reqs,key=lambda r:(r.item_id,r.requested_on,r.requisition_id)); out=[]
    for i,a in enumerate(rows):
        for b in rows[i+1:]:
            if b.item_id!=a.item_id:
                if b.item_id>a.item_id: break
                continue
            if 0<=(b.requested_on-a.requested_on).days<=window_days and a.amount+b.amount>D("500000"):
                out.append((a.requisition_id,b.requisition_id,a.amount+b.amount))
    return out

def valid_quote(q):
    if not q.valid: return False
    if q.received_at and q.rfq_close and q.received_at>q.rfq_close: return False
    if q.valid_until and q.rfq_close and q.valid_until<q.rfq_close.date()+timedelta(days=15): return False
    return q.currency.upper()=="INR" or q.exchange_rate is not None

def landed_cost(q):
    base=D(q.base_price)
    if q.currency.upper()!="INR":
        if q.exchange_rate is None: raise ValueError("MISSING_EXCHANGE_RATE")
        base*=D(q.exchange_rate)
    freight=D(q.freight)
    if freight==0 and D(q.unit_weight_kg)>0 and D(q.distance_km)>0:
        bands=(D(q.distance_km)/D("100")).to_integral_value(rounding="ROUND_CEILING")
        freight=D("2")*D(q.unit_weight_kg)*bands
    customs=D(q.customs)
    if q.is_import and customs==0: customs=base*D("0.10")
    return money(base+freight+customs+D(q.other_costs))

def vendor_score(q,v,lowest):
    cost=landed_cost(q)
    cp=D("50") if cost==lowest else D("50")*lowest/cost
    otp=max(D("0"),min(D("25"),D(v.on_time_pct)/D("4")))
    qp=max(D("0"),D("15")-D(v.rejection_pct))
    return (cp+otp+qp+(D("10") if v.is_msme else D("0"))).quantize(D("0.01"),rounding=ROUND_HALF_UP)

def choose_award(quotes,vendors=(),window_percent=D("0.05"),requisition_value=D("0")):
    qs=[q for q in quotes if valid_quote(q)]
    if not qs:return None
    if D(requisition_value)>D("100000") and len(qs)<3:
        return Award("",D("0"),D("0"),"Fewer than three valid quotations","MANUAL_AWARD")
    vm={v.vendor_id:v for v in vendors}; costs={id(q):landed_cost(q) for q in qs}
    low=min(costs.values()); eligible=[]
    for q in qs:
        v=vm.get(q.vendor_id,Vendor(q.vendor_id,""))
        score=vendor_score(q,v,low) if q.vendor_id in vm else D(q.score)
        if costs[id(q)]<=low*(D("1")+D(window_percent)):
            eligible.append((q,v,costs[id(q)],score))
    q,v,c,s=sorted(eligible,key=lambda x:(-x[3],0 if x[1].is_msme else 1,x[0].received_at or datetime.max,x[2],x[0].vendor_id))[0]
    return Award(q.vendor_id,c,s,"Highest score within 5% of lowest landed cost")

def process_receipt(po_quantity,received_quantity):
    poq,rq=D(po_quantity),D(received_quantity)
    if poq<0 or rq<0: raise ValueError("QUANTITY_CANNOT_BE_NEGATIVE")
    accepted=min(rq,poq*D("1.05")); rejected=max(D("0"),rq-accepted)
    return ReceiptResult(accepted,rejected,"REJECTED_OVERAGE" if rejected else ("PARTIAL" if accepted<poq else "ACCEPTED"))

def check_three_way_match(po_quantity,received_quantity,invoice_quantity,po_unit_price,invoice_unit_price,po_total=None,invoice_total=None):
    reasons=[]; poq,rq,iq=map(D,(po_quantity,received_quantity,invoice_quantity)); pop,ip=map(D,(po_unit_price,invoice_unit_price))
    if iq>rq: reasons.append("INVOICE_QUANTITY_EXCEEDS_ACCEPTED_RECEIPT")
    if iq>poq: reasons.append("INVOICE_QUANTITY_EXCEEDS_PURCHASE_ORDER")
    if abs(ip-pop)>min(pop*D("0.02"),D("100")): reasons.append("UNIT_PRICE_OUTSIDE_TOLERANCE")
    if po_total is not None and invoice_total is not None and abs(D(invoice_total)-D(po_total))>D("500"):
        reasons.append("INVOICE_TOTAL_VARIANCE_EXCEEDS_500")
    return MatchResult(not reasons,tuple(reasons))

def early_payment_discount(inv,payment_date):
    days=(payment_date-inv.approved_on).days
    rate=D("0.02") if days<=10 else (D("0.01") if days<=20 else D("0"))
    return money(D(inv.pre_gst_amount)*rate)

def msme_late_interest(principal,received_on,payment_date,bank_rate=D("0.065")):
    late=(payment_date-(received_on+timedelta(days=45))).days
    months=max(0,late//30)
    if months==0:return D("0.00")
    return money(D(principal)*((D("1")+D("3")*D(bank_rate)/D("12"))**months-D("1")))

def payment_run_day(day):
    while day.weekday() not in (0,3): day+=timedelta(days=1)
    return day

def build_payment_run(invoices,run_date,cash_limit=D("2500000")):
    eligible=[i for i in invoices if i.status=="APPROVED" and run_date<=i.due_date<=run_date+timedelta(days=7)]
    eligible.sort(key=lambda i:(0 if i.is_msme else 1,i.due_date,i.invoice_id))
    paid=[]; deferred=[]; spent=D("0")
    for inv in eligible:
        if spent+D(inv.amount)<=D(cash_limit): paid.append(inv); spent+=D(inv.amount)
        else: deferred.append(inv)
    return {"paid":paid,"deferred":deferred,"total":money(spent),"remaining":money(D(cash_limit)-spent)}
