from pathlib import Path
import sys
import pandas as pd  # type: ignore[import-not-found]
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.processor import process

def test_sample_command_stream_end_to_end(tmp_path):
    p=process(ROOT/'data',tmp_path)
    assert not p.errors, p.errors
    assert len(p.rows['award_decisions.csv'])==60
    assert len(p.rows['purchase_orders.csv'])==20
    assert len(p.rows['receipts_log.csv'])==37
    assert len(p.rows['match_results.csv'])==37
    assert (tmp_path/'payment_runs.csv').exists()

def test_planted_edge_cases(tmp_path):
    p=process(ROOT/'data',tmp_path)
    a=pd.read_csv(tmp_path/'award_decisions.csv')
    # Strict close boundary and 15-day validity acceptance.
    q24=a[a.quote_id=='QT-0024'].iloc[0]; q25=a[a.quote_id=='QT-0025'].iloc[0]
    assert bool(q24.valid) is True and bool(q25.valid) is False
    # Import FX holiday falls back to the latest earlier business-day rate.
    q60=a[a.quote_id=='QT-0060'].iloc[0]
    assert q60.fx_rate_date=='2026-10-01'
    r=pd.read_csv(tmp_path/'receipts_log.csv')
    assert int(r[r.grn_id=='GRN-0018'].iloc[0].accepted_qty)==210
    assert int(r[r.grn_id=='GRN-0006'].iloc[0].excess_returned_qty)==1
    m=pd.read_csv(tmp_path/'match_results.csv')
    assert m[m.invoice_id=='INV-0028'].iloc[0].reason_codes=='PRICE_VARIANCE'
    assert m[m.invoice_id=='INV-0011'].iloc[0].reason_codes=='TOTAL_MISMATCH'
    assert m[m.invoice_id=='INV-0019'].iloc[-1].status=='APPROVED'
    # Debit note carries its balance across successive invoices.
    m15=m[m.invoice_id=='INV-0015'].iloc[0]
    m17=m[m.invoice_id=='INV-0017'].iloc[0]
    assert float(m15.debit_note_applied)==61360.00
    assert float(m17.debit_note_applied)==95420.00
    pay=pd.read_csv(tmp_path/'payment_runs.csv')
    p26=pay[pay.invoice_id=='INV-0026']
    assert list(p26.status)==['DEFERRED_CASH_LIMIT','PAID']
    p19=pay[pay.invoice_id=='INV-0019'].iloc[0]
    assert p19.run_date=='2026-10-26' and p19.interest>0

def test_no_duplicate_quote_rows_after_manual_award(tmp_path):
    process(ROOT/'data',tmp_path)
    a=pd.read_csv(tmp_path/'award_decisions.csv')
    assert a.quote_id.nunique()==len(a)==60
    assert (a[a.rfq_id=='RFQ-0003'].decision=='MANUAL_AWARD').sum()==1


def test_split_requisition_band_changes_when_second_request_is_raised(tmp_path):
    process(ROOT/'data',tmp_path)
    log=pd.read_csv(tmp_path/'requisition_log.csv')
    req2=log[log.req_id=='REQ-0002'].iloc[0]
    req6=log[(log.req_id=='REQ-0006') & (log.event=='RAISE_REQ')].iloc[0]
    assert req2.band_required=='MANAGER' and req2.combined_value==260000
    assert req6.band_required=='DIRECTOR' and req6.combined_value==520000
    approvals=log[(log.req_id=='REQ-0006') & (log.event=='APPROVE_REQ')]
    assert list(approvals.result)==['REFUSED_INSUFFICIENT_ROLE','APPROVED']
