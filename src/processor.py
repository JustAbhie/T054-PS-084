from __future__ import annotations
import csv, json, math
from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

D = Decimal
CENT = D('0.01')
def dec(x): return D(str(x or '0'))
def money(x): return dec(x).quantize(CENT, rounding=ROUND_HALF_UP)
def ds(x): return str(x) if x is not None else ''
def read_csv(folder, name):
    with (Path(folder)/name).open(newline='', encoding='utf-8-sig') as f: return list(csv.DictReader(f))
def write_csv(path, rows, fields):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({k: ds(r.get(k,'')) for k in fields})
def dt(s): return datetime.strptime(s,'%Y-%m-%d %H:%M:%S')
def day(s): return date.fromisoformat(s)
def fmt(x): return f'{money(x):.2f}'

OUTPUT_FIELDS = {
'requisition_log.csv':'req_id,event,own_value,combined_value,band_required,role,result'.split(','),
'award_decisions.csv':'rfq_id,quote_id,vendor_id,valid,invalid_reason,fx_rate_date,fx_rate,landed_cost_per_unit,cost_points,ontime_points,quality_points,msme_points,score,decision'.split(','),
'purchase_orders.csv':'po_id,rfq_id,vendor_id,item_id,quantity,unit_price,freight_per_unit,po_date,due_date,award_basis'.split(','),
'receipts_log.csv':'grn_id,po_id,delivered_qty,accepted_qty,excess_returned_qty,quality_rejected_qty,debit_note_id,debit_note_amount,line_status'.split(','),
'match_results.csv':'invoice_id,event_date,status,reason_codes,debit_note_applied,due_date'.split(','),
'payment_runs.csv':'run_date,invoice_id,vendor_id,msme,due_date,invoice_total,debit_note_applied,discount,interest,amount_paid,status'.split(',')}

class ProcurementProcessor:
  def __init__(self, data_dir):
    self.data_dir=Path(data_dir)
    self.vendors={x['vendor_id']:x for x in read_csv(data_dir,'vendors.csv')}
    self.items={x['item_id']:x for x in read_csv(data_dir,'items.csv')}
    self.reqs={x['req_id']:x for x in read_csv(data_dir,'requisitions.csv')}
    self.rfqs={x['rfq_id']:x for x in read_csv(data_dir,'rfqs.csv')}
    self.quotes=read_csv(data_dir,'quotations.csv')
    self.grns={x['grn_id']:x for x in read_csv(data_dir,'goods_receipts.csv')}
    self.invoices={x['invoice_id']:x for x in read_csv(data_dir,'invoices.csv')}
    self.dist={x['state']:dec(x['distance_km']) for x in read_csv(data_dir,'state_distances.csv')}
    self.fx=defaultdict(dict)
    for x in read_csv(data_dir,'fx_rates.csv'): self.fx[x['currency']][x['rate_date']]=dec(x['inr_per_unit'])
    self.approval={}; self.raised_reqs=set(); self.rfq_status={}; self.po={}; self.received=defaultdict(int); self.debit=defaultdict(lambda:D('0.00'))
    self.approved_qty=defaultdict(int); self.invoice_status={}; self.invoice_approval={}; self.paid=set(); self.last_grn_date={}
    self.rows={k:[] for k in OUTPUT_FIELDS}; self.errors=[]; self.events=[]
    self.quote_by_rfq=defaultdict(list)
    for q in self.quotes:self.quote_by_rfq[q['rfq_id']].append(q)

  def approval_info(self, req_id):
    r=self.reqs[req_id]; t=dt(r['req_ts']); item=r['item_id']; total=D('0')
    for x in self.reqs.values():
      xt=dt(x['req_ts'])
      if x['req_id'] in self.raised_reqs and x['item_id']==item and t-timedelta(days=7)<=xt<=t: total+=dec(x['est_value'])
    own=dec(r['est_value']); band='AUTO_APPROVED' if total<=50000 else ('MANAGER' if total<=500000 else 'DIRECTOR')
    return own,total,band

  def do_raise(self,rid):
    self.raised_reqs.add(rid)
    own,total,band=self.approval_info(rid)
    result='AUTO_APPROVED' if band=='AUTO_APPROVED' else 'PENDING_APPROVAL'
    if band=='AUTO_APPROVED': self.approval[rid]=True
    self.rows['requisition_log.csv'].append(dict(req_id=rid,event='RAISE_REQ',own_value=fmt(own),combined_value=fmt(total),band_required=band,role='',result=result))
  def do_approve(self,rid,role,name):
    own,total,band=self.approval_info(rid); ranks={'MANAGER':1,'DIRECTOR':2}; ok=(band=='AUTO_APPROVED') or ranks.get(role,0)>=ranks.get(band,99)
    if ok:self.approval[rid]=True
    self.rows['requisition_log.csv'].append(dict(req_id=rid,event='APPROVE_REQ',own_value=fmt(own),combined_value=fmt(total),band_required=band,role=role,result='APPROVED' if ok else 'REFUSED_INSUFFICIENT_ROLE'))
  def fx_for(self,currency, quote_date):
    if currency=='INR': return quote_date,D('1.0')
    rates=self.fx.get(currency,{})
    prior=[d for d in rates if d<=quote_date]
    if not prior: return '',None
    d=max(prior); return d,rates[d]
  def quote_eval(self,q,rfq):
    reason=[]; close=dt(rfq['close_ts']); received=dt(q['received_ts']); v=self.vendors[q['vendor_id']]
    if q['vendor_id'] not in rfq['invited_vendors'].split(';'):reason.append('VENDOR_NOT_INVITED')
    if received>=close:reason.append('RECEIVED_AT_OR_AFTER_CLOSE')
    if day(q['valid_until']) < close.date()+timedelta(days=15):reason.append('VALIDITY_LESS_THAN_15_DAYS')
    fxdate,rate=self.fx_for(q['currency'],received.date().isoformat())
    if rate is None:reason.append('MISSING_EXCHANGE_RATE')
    item=self.items[self.reqs[rfq['req_id']]['item_id']]
    freight=dec(q['freight_per_unit']) if q['freight_per_unit'] else D('2')*dec(item['unit_weight_kg'])*self.dist.get(v['state'],D('0'))/D('100')
    unit=(dec(q['unit_price'])+freight)*(rate or D('0'))
    if v['vendor_type']=='IMPORT': unit*=D('1.10')
    unit=money(unit)
    valid=not reason
    return dict(valid=valid,reason=';'.join(reason),fxdate=fxdate,rate=rate,freight=freight,landed=unit,unit_price=dec(q['unit_price']),quote=q,vendor=v)
  def do_close(self,rfqid, award_override=None):
    rfq=self.rfqs[rfqid]; req=self.reqs[rfq['req_id']]; close=dt(rfq['close_ts']); evaluations=[self.quote_eval(q,rfq) for q in self.quote_by_rfq[rfqid]]
    valid=[e for e in evaluations if e['valid']]
    if award_override:
      winner=next((e for e in valid if e['quote']['vendor_id']==award_override),None)
      if winner is None: self.errors.append(f'{rfqid}: manual award vendor has no valid quote'); return
      basis='MANUAL_AWARD'
    elif dec(req['est_value'])>100000 and len(valid)<3:
      winner=None; basis='MANUAL_AWARD'
    elif not valid: winner=None; basis='NO_VALID_QUOTATIONS'
    else:
      low=min(e['landed'] for e in valid)
      for e in valid:
        v=e['vendor']; e['cost_points']=D('50')*low/e['landed'] if e['landed'] else D('0')
        e['ontime_points']=dec(v['ontime_pct'])/D('4')
        e['quality_points']=max(D('0'),D('15')-dec(v['rejection_pct']))
        e['msme_points']=D('10') if v['msme']=='true' else D('0')
        e['score']=money(e['cost_points']+e['ontime_points']+e['quality_points']+e['msme_points'])
      ranked=sorted(valid,key=lambda e:(-e['score'],e['vendor']['msme']!='true',e['quote']['received_ts']))
      top=ranked[0]
      if top['landed']<=low*D('1.05'):
        winner=top; basis='AWARDED_TOP_SCORE'
      else:
        lows=[e for e in valid if e['landed']==low]
        winner=sorted(lows,key=lambda e:(e['vendor']['msme']!='true',e['quote']['received_ts']))[0]; basis='AWARDED_LOWEST_LANDED'
    for e in evaluations:
      v=e['vendor']; q=e['quote']; low=min([x['landed'] for x in valid],default=D('0'))
      cp=money(D('50')*low/e['landed']) if e['valid'] and e['landed'] else D('0')
      op=dec(v['ontime_pct'])/D('4'); qp=max(D('0'),D('15')-dec(v['rejection_pct'])); mp=D('10') if v['msme']=='true' else D('0')
      score=money(cp+op+qp+mp) if e['valid'] else ''
      decision=(basis if winner is e else '')
      if not award_override:
        self.rows['award_decisions.csv'].append(dict(rfq_id=rfqid,quote_id=q['quote_id'],vendor_id=q['vendor_id'],valid=str(e['valid']).lower(),invalid_reason=e['reason'],fx_rate_date=e['fxdate'],fx_rate=fmt(e['rate']) if e['rate'] is not None else '',landed_cost_per_unit=fmt(e['landed']) if e['valid'] else '',cost_points=fmt(cp) if e['valid'] else '',ontime_points=fmt(op) if e['valid'] else '',quality_points=fmt(qp) if e['valid'] else '',msme_points=fmt(mp) if e['valid'] else '',score=fmt(score) if score!='' else '',decision=decision))
    if award_override and winner:
      for row in self.rows['award_decisions.csv']:
        if row['rfq_id']==rfqid and row['quote_id']==winner['quote']['quote_id']:
          row['decision']='MANUAL_AWARD'
    if winner:
      q=winner['quote']; item=req['item_id']; poid='PO-'+rfqid.split('-')[1]; award_date=close.date(); due=award_date+timedelta(days=int(q['delivery_days']))
      self.po[poid]=dict(po_id=poid,rfq_id=rfqid,vendor_id=q['vendor_id'],item_id=item,quantity=int(req['quantity']),unit_price=fmt(dec(q['unit_price'])*(winner['rate'] or D('1'))),freight_per_unit=fmt(winner['freight']*(winner['rate'] or D('1'))),po_date=award_date.isoformat(),due_date=due.isoformat(),award_basis=basis, gst_pct=dec(self.items[item]['gst_pct']))
      self.rows['purchase_orders.csv'].append({k:v for k,v in self.po[poid].items() if k in OUTPUT_FIELDS['purchase_orders.csv']})
      self.rfq_status[rfqid]='AWARDED'
    else:self.rfq_status[rfqid]=basis

  def do_grn(self,gid):
    g=self.grns[gid]; po=self.po.get(g['po_id'])
    if not po:self.errors.append(f'{gid}: PO does not exist yet');return
    poq=int(po['quantity']); prev=self.received[g['po_id']]; delivered=int(g['delivered_qty']); quality=int(g['quality_rejected_qty'])
    maxaccepted=math.floor(poq*1.05); good=max(0,delivered-quality); accepted=min(good,max(0,maxaccepted-prev)); excess=max(0,good-accepted)
    self.received[g['po_id']]+=accepted
    self.last_grn_date[g['po_id']]=g['grn_ts'][:10]
    debit=money(D(quality)*(dec(po['unit_price'])+dec(po['freight_per_unit'])))
    dnid=f'DN-{gid.split("-")[1]}' if debit>0 else ''
    if debit>0:self.debit[g['vendor_id']]+=debit
    status='CLOSED' if self.received[g['po_id']]>=D(poq)*D('0.95') and day(g['grn_ts'][:10])>day(po['due_date']) else ('REJECTED' if excess else ('PARTIAL' if self.received[g['po_id']]<poq else 'ACCEPTED'))
    self.rows['receipts_log.csv'].append(dict(grn_id=gid,po_id=g['po_id'],delivered_qty=delivered,accepted_qty=accepted,excess_returned_qty=excess,quality_rejected_qty=quality,debit_note_id=dnid,debit_note_amount=fmt(debit),line_status=status))

  def do_invoice(self,iid,event_date,rematch=False):
    inv=self.invoices[iid]; po=self.po.get(inv['po_id'])
    if not po:self.errors.append(f'{iid}: PO does not exist yet');return
    vendor=inv['vendor_id']; qty=int(inv['quantity']); accepted=self.received[inv['po_id']]-self.approved_qty[inv['po_id']]
    reasons=[]
    if qty>accepted: reasons.append('QTY_EXCEEDS_RECEIPT')
    tol=min(dec(po['unit_price'])*D('0.02'),D('100'))
    if abs(dec(inv['unit_price'])-dec(po['unit_price']))>tol: reasons.append('PRICE_VARIANCE')
    gst=dec(po['gst_pct'])/100; computed=money(D(qty)*dec(inv['unit_price'])*(D('1')+gst))
    if abs(dec(inv['invoice_total'])-computed)>D('500'): reasons.append('TOTAL_MISMATCH')
    due=day(inv['received_date'])+timedelta(days=45 if self.vendors[vendor]['msme']=='true' else 30)
    applied=D('0')
    status='HOLD' if reasons else 'APPROVED'
    if status=='APPROVED':
      applied=min(self.debit[vendor],dec(inv['invoice_total'])); self.debit[vendor]-=applied
      self.approved_qty[inv['po_id']]+=qty; self.invoice_approval[iid]=day(event_date); self.invoice_status[iid]='APPROVED'
    else:self.invoice_status[iid]='HOLD'
    self.rows['match_results.csv'].append(dict(invoice_id=iid,event_date=event_date,status=status,reason_codes=';'.join(reasons),debit_note_applied=fmt(applied),due_date=due.isoformat()))

  def do_payment(self,run_date):
    rd=day(run_date)
    if rd.weekday() not in (0,3): self.errors.append(f'{run_date}: PAYMENT_RUN_NOT_SCHEDULED');return
    eligible=[]
    for iid,inv in self.invoices.items():
      if self.invoice_status.get(iid)!='APPROVED' or iid in self.paid:continue
      po=self.po.get(inv['po_id'])
      if not po:continue
      due=day(inv['received_date'])+timedelta(days=45 if self.vendors[inv['vendor_id']]['msme']=='true' else 30)
      if due<=rd+timedelta(days=7): eligible.append((iid,inv,due))
    eligible.sort(key=lambda x:(self.vendors[x[1]['vendor_id']]['msme']!='true',x[2],x[0]))
    spent=D('0'); limit=D('2500000'); defer_rest=False
    for iid,inv,due in eligible:
      vendor=inv['vendor_id']; applied=D('0') # applied debit note was already deducted at approval
      # locate the amount already netted from match result
      for m in reversed(self.rows['match_results.csv']):
        if m['invoice_id']==iid and m['status']=='APPROVED': applied=dec(m['debit_note_applied']);break
      discount=money(dec(inv['taxable_value'])*D('0.02')) if 0<=(rd-self.invoice_approval[iid]).days<=10 else (money(dec(inv['taxable_value'])*D('0.01')) if 11<=(rd-self.invoice_approval[iid]).days<=20 else D('0'))
      principal=max(D('0'),dec(inv['invoice_total'])-applied)
      late=(rd-due).days
      interest=D('0')
      if self.vendors[vendor]['msme']=='true' and late>0:
        interest=money(principal*((D('1')+D('0.195')/12)**(D(late)/30)-1))
      payable=money(principal-discount+interest)
      status='PAID'
      if defer_rest or spent+payable>limit:
        defer_rest=True; status='DEFERRED_CASH_LIMIT'; amount='0.00'
      else:
        spent+=payable; self.paid.add(iid); amount=fmt(payable)
      self.rows['payment_runs.csv'].append(dict(run_date=run_date,invoice_id=iid,vendor_id=vendor,msme=self.vendors[vendor]['msme'],due_date=due.isoformat(),invoice_total=fmt(inv['invoice_total']),debit_note_applied=fmt(applied),discount=fmt(discount),interest=fmt(interest),amount_paid=amount,status=status))

  def run(self, commands_path=None):
    commands_path=Path(commands_path or self.data_dir/'commands.txt')
    for line_no,line in enumerate(commands_path.read_text(encoding='utf-8').splitlines(),1):
      line=line.strip()
      if not line or line.startswith('#'):continue
      p=line.split('|'); op=p[0]
      try:
        if op=='RAISE_REQ':self.do_raise(p[1])
        elif op=='APPROVE_REQ':self.do_approve(p[1],p[2],p[3])
        elif op=='FLOAT_RFQ':
          rfq=self.rfqs[p[1]]; self.rfq_status[p[1]]='FLOAT' if self.approval.get(rfq['req_id']) else 'BLOCKED_NOT_APPROVED'
        elif op=='CLOSE_RFQ':
          rfq=self.rfqs[p[1]]
          if self.rfq_status.get(p[1])=='FLOAT':self.do_close(p[1])
          else:self.errors.append(f'line {line_no}: {p[1]} not floated/approved')
        elif op=='MANUAL_AWARD':
          if self.rfq_status.get(p[1])=='MANUAL_AWARD': self.do_close(p[1],p[2])
          else:self.errors.append(f'line {line_no}: {p[1]} is not awaiting manual award')
        elif op=='RECEIVE_GRN':self.do_grn(p[1])
        elif op=='RECEIVE_INVOICE':self.do_invoice(p[1],self.invoices[p[1]]['received_date'])
        elif op=='REMATCH':
          inv=self.invoices[p[1]]; event_date=self.last_grn_date.get(inv['po_id'],inv['received_date']); self.do_invoice(p[1],event_date,True)
        elif op=='PAYMENT_RUN':self.do_payment(p[1])
        else:self.errors.append(f'line {line_no}: unknown command {op}')
      except Exception as e:self.errors.append(f'line {line_no} {line}: {type(e).__name__}: {e}')
    return self.rows
  def export(self, out_dir):
    for name,fields in OUTPUT_FIELDS.items():
      rows=self.rows[name]
      if name=='award_decisions.csv': rows=sorted(rows,key=lambda r:r['quote_id'])
      if name=='purchase_orders.csv': rows=sorted(rows,key=lambda r:r['po_id'])
      write_csv(Path(out_dir)/name,rows,fields)
    (Path(out_dir)/'processing_report.json').write_text(json.dumps({'counts':{k:len(v) for k,v in self.rows.items()},'errors':self.errors},indent=2))

def process(data_dir, out_dir):
  p=ProcurementProcessor(data_dir); p.run(); p.export(out_dir); return p
