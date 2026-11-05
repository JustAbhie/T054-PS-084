from pathlib import Path
import sys, json
import pandas as pd  # type: ignore[reportMissingModuleSource]
import streamlit as st  # type: ignore[reportMissingImports]
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.processor import process

st.set_page_config(page_title='ProcureFlow | T054 PS-084',page_icon='📦',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
:root{--ink:#17243a;--muted:#718096;--line:#e7edf5;--brand:#3559e0;--bg:#f6f8fc}
.stApp{background:var(--bg)} .block-container{padding-top:1.35rem;max-width:1500px}
[data-testid="stSidebar"]{background:#111c32} [data-testid="stSidebar"] *{color:#eaf0ff!important}
.hero{background:linear-gradient(115deg,#15233f,#304e9b);padding:26px 30px;border-radius:18px;color:white;margin-bottom:18px}
.hero h1{font-size:30px;margin:0 0 4px 0;color:white}.hero p{margin:0;color:#dbe5ff}
.kpi{background:white;border:1px solid var(--line);border-radius:14px;padding:17px 18px;min-height:105px}
.kpi .label{font-size:12px;color:#718096;text-transform:uppercase;letter-spacing:.07em}.kpi .value{font-size:27px;font-weight:750;color:#17243a;margin-top:5px}
.kpi .hint{font-size:12px;color:#8492a6}
.section{font-size:18px;font-weight:700;color:#17243a;margin:14px 0 8px}
div[data-testid="stDataFrame"]{border:1px solid #e7edf5;border-radius:12px;overflow:hidden}
.stButton>button{border-radius:9px;font-weight:650}
</style>''',unsafe_allow_html=True)

DATA=ROOT/'data'; OUT=ROOT/'outputs'
@st.cache_data(show_spinner=False)
def load_csv(path): return pd.read_csv(path) if path.exists() else pd.DataFrame()

def ensure_run():
    if 'ran' not in st.session_state: st.session_state.ran=False
    if not st.session_state.ran:
        p=process(DATA,OUT); st.session_state.ran=True; st.session_state.errors=p.errors
    return

with st.sidebar:
    st.markdown('## PROCUREFLOW')
    st.caption('T054 · PS-084')
    page=st.radio('WORKSPACE',['Overview','Vendors & Items','Requisitions','Sourcing & Awards','Purchase Orders','Goods Receipts','Invoice Matching','Payment Runs','Run & Export'],label_visibility='collapsed')
    st.divider()
    st.caption('Procure-to-pay control center')
    if st.button('↻ Reprocess command stream',use_container_width=True):
        st.cache_data.clear(); st.session_state.ran=False; st.rerun()
ensure_run()

files={n:load_csv(OUT/n) for n in ['requisition_log.csv','award_decisions.csv','purchase_orders.csv','receipts_log.csv','match_results.csv','payment_runs.csv']}
vendors=load_csv(DATA/'vendors.csv'); items=load_csv(DATA/'items.csv'); reqs=load_csv(DATA/'requisitions.csv'); quotes=load_csv(DATA/'quotations.csv'); invoices=load_csv(DATA/'invoices.csv')
awards=files['award_decisions.csv']; pos=files['purchase_orders.csv']; receipts=files['receipts_log.csv']; matches=files['match_results.csv']; payments=files['payment_runs.csv']; reqlog=files['requisition_log.csv']

st.markdown('<div class="hero"><h1>ProcureFlow</h1><p>Procurement intelligence · Vendor scoring · Three-way matching · Payment control</p></div>',unsafe_allow_html=True)
if page=='Overview':
    paid=payments[payments.status=='PAID'] if not payments.empty else payments
    hold=matches[matches.status=='HOLD'] if not matches.empty else matches
    c1,c2,c3,c4=st.columns(4)
    metrics=[('Vendors',len(vendors),'Registered suppliers'),('Requisitions',len(reqs),'Purchase requests'),('Purchase orders',len(pos),'Awarded orders'),('Invoices on hold',len(hold),'Require review')]
    for c,(lab,val,hint) in zip([c1,c2,c3,c4],metrics):
        c.markdown(f'<div class="kpi"><div class="label">{lab}</div><div class="value">{val:,}</div><div class="hint">{hint}</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="section">Workflow snapshot</div>',unsafe_allow_html=True)
    a,b=st.columns([1.15,1])
    with a:
        if not matches.empty:
            d=matches.status.value_counts().rename_axis('Status').reset_index(name='Invoices')
            st.subheader('Invoice match outcomes')
            st.bar_chart(d.set_index('Status')['Invoices'])
        else: st.info('No invoice match records yet.')
    with b:
        if not awards.empty:
            d=awards.decision.replace('', 'Not selected').value_counts().rename_axis('Decision').reset_index(name='Quotes')
            st.subheader('Quotation decisions')
            st.bar_chart(d.set_index('Decision')['Quotes'])
        else: st.info('No quotation decisions yet.')
    st.markdown('<div class="section">Exceptions needing attention</div>',unsafe_allow_html=True)
    if not hold.empty: st.dataframe(hold,use_container_width=True,hide_index=True)
    else: st.success('No held invoices in the processed command stream.')
    if st.session_state.get('errors'): st.warning(f"{len(st.session_state.errors)} processing warning(s). Open Run & Export for details.")
elif page=='Vendors & Items':
    st.subheader('Supplier directory')
    q=st.text_input('Search vendors by name, ID, state or category')
    vf=vendors.copy();
    if q: vf=vf[vf.astype(str).apply(lambda r:r.str.contains(q,case=False).any(),axis=1)]
    st.dataframe(vf,use_container_width=True,hide_index=True)
    st.subheader('Item catalogue'); st.dataframe(items,use_container_width=True,hide_index=True)
elif page=='Requisitions':
    st.subheader('Requisition register')
    st.dataframe(reqs.merge(reqlog.groupby('req_id',as_index=False).agg({'band_required':'last','result':'last'}),on='req_id',how='left'),use_container_width=True,hide_index=True)
    st.subheader('Approval event history'); st.dataframe(reqlog,use_container_width=True,hide_index=True)
elif page=='Sourcing & Awards':
    st.subheader('Quotation evaluation')
    if not awards.empty:
        rfq = st.selectbox('RFQ', sorted(awards.rfq_id.unique()))
        st.dataframe(awards[awards.rfq_id == rfq], use_container_width=True, hide_index=True)

        win = awards[
            (awards.rfq_id == rfq)
            & awards.decision.notna()
            & (awards.decision.astype(str).str.strip() != '')
        ]

        decisions = (
            win.decision
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        if decisions:
            st.success('Decision: ' + ', '.join(decisions))
        else:
            st.info('No award decision recorded for this RFQ.')
    else:
        st.info('No RFQs processed.')
elif page=='Purchase Orders':
    st.subheader('Purchase order register'); st.dataframe(pos,use_container_width=True,hide_index=True)
elif page=='Goods Receipts':
    st.subheader('Goods receipt register'); st.dataframe(receipts,use_container_width=True,hide_index=True)
elif page=='Invoice Matching':
    st.subheader('Three-way match control')
    if not matches.empty:
        status=st.multiselect('Filter status',matches.status.unique().tolist(),default=matches.status.unique().tolist())
        st.dataframe(matches[matches.status.isin(status)],use_container_width=True,hide_index=True)
    else: st.info('No invoices processed.')
elif page=='Payment Runs':
    st.subheader('Payment run ledger')
    if not payments.empty:
        k1,k2=st.columns(2); k1.metric('Total paid',f"₹{pd.to_numeric(payments.loc[payments.status=='PAID','amount_paid']).sum():,.2f}"); k2.metric('Deferred invoices',int((payments.status=='DEFERRED_CASH_LIMIT').sum()))
        st.dataframe(payments,use_container_width=True,hide_index=True)
    else: st.info('No payment runs processed.')
elif page=='Run & Export':
    st.subheader('Process command stream')
    st.write('The engine reads the supplied CSV master data and processes `commands.txt` strictly in file order.')
    st.code('python main.py --data data/T054-PS-084-sample-data --out outputs',language='bash')
    if st.button('Run engine now',type='primary'):
        st.session_state.ran=False; st.cache_data.clear(); st.rerun()
    st.subheader('Generated evaluation files')
    for name in files:
        p=OUT/name
        if p.exists():
            st.download_button('Download '+name,data=p.read_bytes(),file_name=name,mime='text/csv',key=name)
    report=OUT/'processing_report.json'
    if report.exists():
        info=json.loads(report.read_text()); st.metric('Processing warnings',len(info['errors']))
        if info['errors']: st.dataframe(pd.DataFrame({'Warning':info['errors']}),use_container_width=True,hide_index=True)
        st.json(info['counts'])
st.caption('ProcureFlow · Internal academic prototype · Financial decisions require authorized review.')
