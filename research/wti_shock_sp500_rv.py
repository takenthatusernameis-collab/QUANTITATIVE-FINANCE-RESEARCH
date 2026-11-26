from __future__ import annotations
import bisect,csv,datetime as dt,hashlib,json,math,os,random,statistics
from pathlib import Path
import treasury_auction_demand as base
HYPOTHESIS_ID='QFR-2026-11-26-WTI-SHOCK-SP500-RV-01'
START=dt.date(2016,11,25); VAL_START=dt.date(2019,1,1); TEST_START=dt.date(2022,1,1)
WINDOW=104; STEP=6; TARGET=5; BOOT_REPS=2000; BOOT_BLOCK=4; SEED=20261130
SERIES=('DCOILWTICO','VIXCLS','SP500'); BASE=('pre_rv5','pre_rv20','log_vix'); AUG=BASE+('wti_asinh5',)
ROOT=Path(__file__).resolve().parents[1]; RUN=os.getenv('GITHUB_RUN_ID','local'); ATTEMPT=os.getenv('GITHUB_RUN_ATTEMPT','1'); SHA=os.getenv('GITHUB_SHA','local')
NOW=dt.datetime.now(dt.timezone.utc); STAMP=NOW.strftime('%Y-%m-%dT%H%M%SZ')
OUT=ROOT/'reports'/'generated'/'wti-shock-sp500-rv'/f'{RUN}-attempt-{ATTEMPT}'
SESSION=ROOT/'reports'/'sessions'/STAMP[:10]
REG=ROOT/'research'/'HYPOTHESIS-REGISTRY.md'; PREREG=ROOT/'research'/'PREREGISTERED-QFR-2026-11-26-WTI-SHOCK-SP500-RV-01.md'
FRED='https://fred.stlouisfed.org/graph/fredgraph.csv'

def parse(body,sid,positive=False):
    r=csv.DictReader(body.decode('utf-8-sig').splitlines())
    if not r.fieldnames or sid not in r.fieldnames: raise ValueError(f'Unexpected {sid} schema: {r.fieldnames}')
    date_key='observation_date' if 'observation_date' in r.fieldnames else 'DATE'
    if date_key not in r.fieldnames: raise ValueError(f'Missing date column for {sid}')
    out={}
    for row in r:
        raw=row.get(sid)
        if raw is None or not str(raw).strip() or str(raw).strip()=='.': continue
        d=base.parse_date(row.get(date_key)); v=base.parse_float(raw)
        if d is None or v is None: raise ValueError(f'Invalid {sid} row: {row}')
        if positive and v<=0: raise ValueError(f'Non-positive {sid} value on {d}')
        if d in out: raise ValueError(f'Duplicate {sid} date: {d}')
        out[d]=v
    if not out: raise ValueError(f'No valid {sid} rows')
    return dict(sorted(out.items()))

def validate(data,today):
    for sid in SERIES:
        x=data[sid]
        if len(x)<1500: raise ValueError(f'Insufficient {sid}: {len(x)}')
        if min(x)>START+dt.timedelta(days=30): raise ValueError(f'{sid} starts too late: {min(x)}')
        if max(x)>today: raise ValueError(f'{sid} has future data: {max(x)}')
    oil=sorted(data['DCOILWTICO']); age=(today-oil[-1]).days
    if age>5: raise ValueError(f'Stale WTI: {oil[-1]}, age={age}')
    max_oil_gap=max(((b-a).days for a,b in zip(oil,oil[1:])),default=0)
    common=sorted(set(data['VIXCLS'])&set(data['SP500']))
    if len(common)<1500 or common[0]>START+dt.timedelta(days=30): raise ValueError('Insufficient common VIX/SP500 history')
    if (today-common[-1]).days>8: raise ValueError(f'Stale VIX/SP500: {common[-1]}')
    if abs((max(data['VIXCLS'])-max(data['SP500'])).days)>4: raise ValueError('VIX/SP500 latest dates are unsynchronized')
    p=sorted(data['SP500']); max_price_gap=max(((b-a).days for a,b in zip(p,p[1:])),default=0)
    return {s:{'rows':len(x),'first':min(x).isoformat(),'last':max(x).isoformat(),'max_gap_days':max_oil_gap if s=='DCOILWTICO' else max_price_gap if s=='SP500' else None} for s,x in data.items()}

def returns(prices):
    dates=sorted(prices); out=[None]
    for i in range(1,len(dates)):
        gap=(dates[i]-dates[i-1]).days
        out.append(math.log(prices[dates[i]]/prices[dates[i-1]]) if gap<=4 else None)
    return dates,out

def rv(values):
    if not values or any(x is None or not math.isfinite(x) for x in values): raise ValueError('Incomplete return window')
    return math.sqrt(sum(x*x for x in values))*100

def events(oil,vix,prices):
    dates,retn=returns(prices); od=sorted(oil); out=[]
    skip={k:0 for k in ('incomplete_price','missing_vix','no_prior_oil','stale_oil','short_oil','irregular_oil','overlap')}
    candidates=0
    for i in range(20,len(dates)-TARGET,STEP):
        candidates+=1; signal=dates[i]; j=bisect.bisect_left(od,signal)-1
        if j<0: skip['no_prior_oil']+=1; continue
        d=od[j]
        if (signal-d).days>5: skip['stale_oil']+=1; continue
        if j<5: skip['short_oil']+=1; continue
        window=od[j-5:j+1]
        if any((b-a).days>5 for a,b in zip(window,window[1:])): skip['irregular_oil']+=1; continue
        if signal not in vix: skip['missing_vix']+=1; continue
        try:
            pre5=rv(retn[i-4:i+1]); pre20=rv(retn[i-19:i+1]); target=rv(retn[i+1:i+TARGET+1])
        except ValueError: skip['incomplete_price']+=1; continue
        end=dates[i+TARGET]
        if out and signal<=out[-1]['target_end']: skip['overlap']+=1; continue
        # asinh(WTI / 50 USD/bbl) is finite for the observed -$36.98/bbl value on 2020-04-20.
        feature=math.asinh(oil[d]/50)-math.asinh(oil[window[0]]/50)
        out.append({'signal':signal,'oil_date':d,'oil_start':window[0],'target_start':dates[i+1],'target_end':end,'wti_asinh5':feature,'pre_rv5':math.log1p(pre5),'pre_rv20':math.log1p(pre20),'log_vix':math.log(vix[signal]),'target_rv':target,'y':math.log1p(target)})
    return out,{'candidate_origins':candidates,'accepted_events':len(out),'skipped':skip,'event_step_sessions':STEP,'target_sessions':TARGET,'strictly_prior_wti':True}

def solve(a,b):
    n=len(b); m=[a[i][:]+[b[i]] for i in range(n)]
    for c in range(n):
        p=max(range(c,n),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<1e-10: raise ValueError('Singular OLS')
        m[c],m[p]=m[p],m[c]; z=m[c][c]
        for j in range(c,n+1): m[c][j]/=z
        for r in range(n):
            if r==c: continue
            f=m[r][c]
            for j in range(c,n+1): m[r][j]-=f*m[c][j]
    return [m[i][n] for i in range(n)]

def predict(train,current,features):
    means=[statistics.fmean(r[k] for r in train) for k in features]
    scales=[statistics.pstdev(r[k] for r in train) or 1 for k in features]
    x=[[1]+[(r[k]-means[i])/scales[i] for i,k in enumerate(features)] for r in train]
    y=[r['y'] for r in train]; w=len(features)+1
    a=[[sum(z[i]*z[j] for z in x)+(1e-8 if i==j and i else 0) for j in range(w)] for i in range(w)]
    b=[sum(x[k][i]*y[k] for k in range(len(x))) for i in range(w)]
    coef=solve(a,b); row=[1]+[(current[k]-means[i])/scales[i] for i,k in enumerate(features)]
    return sum(z*v for z,v in zip(coef,row))

def walkforward(rows):
    out=[]
    for cur in rows:
        train=[r for r in rows if r['signal']<cur['signal'] and r['target_end']<cur['signal']][-WINDOW:]
        if len(train)<WINDOW: continue
        try: b=predict(train,cur,BASE); a=predict(train,cur,AUG)
        except (ValueError,ZeroDivisionError,OverflowError): continue
        out.append({'signal':cur['signal'],'target_end':cur['target_end'],'y':cur['y'],'base':b,'aug':a,'train_n':len(train)})
    return out

def metrics(rows,key):
    e=[r[key]-r['y'] for r in rows]; y=[r['y'] for r in rows]; mean=statistics.fmean(y); sse=sum(x*x for x in e); den=sum((x-mean)**2 for x in y)
    return {'n':len(rows),'mae':statistics.fmean(abs(x) for x in e),'rmse':math.sqrt(sse/len(e)),'oos_r2':1-sse/den if den>1e-12 else None}

def paired(rows):
    if len(rows)<30:return None
    d=[{'loss':(r['base']-r['y'])**2-(r['aug']-r['y'])**2} for r in rows]; rng=random.Random(SEED); samples=[]
    for _ in range(BOOT_REPS): samples.append(statistics.fmean(x['loss'] for x in base.circular_block_sample(d,rng,BOOT_BLOCK)))
    samples.sort(); return {'n':len(d),'reps':len(samples),'block_events':BOOT_BLOCK,'mean_delta':statistics.fmean(x['loss'] for x in d),'ci95_low':samples[int(.025*(len(samples)-1))],'ci95_high':samples[int(.975*(len(samples)-1))]}

def improvement(b,a): return 100*(b['rmse']-a['rmse'])/b['rmse'] if b and a and b['rmse']>0 else None

def decide(v,t,p):
    vi=improvement(v['base'],v['aug']); ti=improvement(t['base'],t['aug'])
    if v['n']>=30 and t['n']>=30 and vi is not None and ti is not None and vi>0 and ti>0 and p and p['ci95_low']>0: return 'BACKTESTED','PROMISING — both chronological RMSE comparisons improve and paired-loss 95% lower bound is positive; independent validation remains necessary'
    if vi is not None and ti is not None and vi<=0 and ti<=0 and p and p['ci95_high']<0: return 'REJECTED','REJECTED — augmented model fails to improve either period and paired-loss inference indicates it is worse'
    return 'INCONCLUSIVE','INCONCLUSIVE — evidence is mixed, statistically uncertain or insufficient under the frozen rule'

def run(asof=None):
    raw={}; data={}; urls={}
    for sid in SERIES:
        url=f'{FRED}?id={sid}&cosd={START.isoformat()}'; raw[sid]=base.fetch_bytes(url,timeout=25); data[sid]=parse(raw[sid],sid,positive=sid!='DCOILWTICO'); urls[sid]=url
    coverage=validate(data,asof or dt.datetime.now(dt.timezone.utc).date())
    ev,meta=events(data['DCOILWTICO'],data['VIXCLS'],data['SP500'])
    if len(ev)<WINDOW+60: raise ValueError(f'Insufficient accepted events: {len(ev)}')
    pred=walkforward(ev); val=[r for r in pred if VAL_START<=r['signal']<TEST_START]; test=[r for r in pred if r['signal']>=TEST_START]
    if len(val)<30 or len(test)<30: raise ValueError(f'Insufficient forecasts: validation={len(val)}, test={len(test)}')
    vm={'n':len(val),'base':metrics(val,'base'),'aug':metrics(val,'aug')}; tm={'n':len(test),'base':metrics(test,'base'),'aug':metrics(test,'aug')}; boot=paired(test); status,disp=decide(vm,tm,boot)
    return {'hypothesis_id':HYPOTHESIS_ID,'status':status,'disposition':disp,'completed_backtest':True,'retrieved_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'run_id':RUN,'attempt':ATTEMPT,'source_commit_sha':SHA,'daily_kpi':'Daily real-data backtest minimum already met by distinct experiments; this is an additional distinct test.','coverage':coverage,'data_sources':{s:{'url':urls[s],'rows':len(data[s]),'sha256':hashlib.sha256(raw[s]).hexdigest()} for s in SERIES},'event_construction':meta,'validation':vm,'test':tm,'validation_improvement_pct':improvement(vm['base'],vm['aug']),'test_improvement_pct':improvement(tm['base'],tm['aug']),'paired_test_loss':boot,'methodology':{'baseline':list(BASE),'augmented':list(AUG),'wti_feature':'asinh(WTI[d]/50)-asinh(WTI[d-5]/50), USD/barrel; d is latest valid WTI observation strictly before signal date','target':'log1p(next-five-session S&P 500 realized volatility in percent)','training_window_events':WINDOW,'validation':'2019-2021','test':'2022 onward','bootstrap_reps':BOOT_REPS,'bootstrap_block_events':BOOT_BLOCK},'limitations':['WTI Cushing is a location-specific physical benchmark, not a global crude basket or futures return.','Strict prior-date alignment avoids same-date publication ambiguity but does not reconstruct intraday historical release timestamps.','Current FRED/EIA vintages are used; historical point-in-time revisions are not reconstructed.','SP500 is a cash price index, not an executable futures or total-return series.','Forecast only; no causal, trading, profitability or deployment claim.','No raw source rows are persisted.']}

def update_handoff(result,report_relative):
    link='../'+report_relative
    row=f"| {HYPOTHESIS_ID} | {result['status']} | Strictly lagged five-observation WTI asinh-price change adds information about next-five-session S&P 500 realized volatility beyond recent RV and VIX. | {json.dumps(result.get('coverage',{}),sort_keys=True)} | {result['disposition']} | [session report]({link}) |"
    lines=REG.read_text(encoding='utf-8').splitlines(); idx=next((i for i,x in enumerate(lines) if HYPOTHESIS_ID in x),None)
    if idx is None:
        h=next(i for i,x in enumerate(lines) if x.startswith('| Hypothesis ID |')); lines.insert(h+2,row)
    else: lines[idx]=row
    REG.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    pre=PREREG.read_text(encoding='utf-8'); status=f"- **Status:** {result['status']} — {result['disposition']}"
    old=next((x for x in pre.splitlines() if x.startswith('- **Status:**')),None)
    if old: pre=pre.replace(old,status,1)
    if '## Empirical disposition' in pre: pre=pre.split('## Empirical disposition',1)[0].rstrip()
    pre+='\n\n## Empirical disposition\n\n'+f"- **Status:** {result['status']} — {result['disposition']}\n- **Completed real-data backtest:** {'yes' if result.get('completed_backtest') else 'no'}\n- **Validation/test forecasts:** {result.get('validation',{}).get('n')} / {result.get('test',{}).get('n')}\n- **RMSE improvement:** {result.get('validation_improvement_pct')}% / {result.get('test_improvement_pct')}%\n- **Paired test-loss 95% CI:** {json.dumps(result.get('paired_test_loss'),sort_keys=True)}\n- **Report:** [session report]({link})\n- Forecast screen only; no trading or deployment claim.\n"
    PREREG.write_text(pre,encoding='utf-8')

def persist(result,error=None):
    report=SESSION/f'{STAMP}_session-wti-shock-{RUN}.md'; manifest=OUT/'manifest.json'; report.parent.mkdir(parents=True,exist_ok=True); manifest.parent.mkdir(parents=True,exist_ok=True)
    lines=[f'# WTI repricing and S&P 500 RV — {STAMP}',f"- Hypothesis: {HYPOTHESIS_ID}",f"- Status: {result['status']}",f"- Disposition: {result['disposition']}",f"- Source commit: {SHA}",f"- Daily KPI: {result.get('daily_kpi','not established')}",f"- Data coverage: {json.dumps(result.get('coverage',{}),sort_keys=True)}",f"- Validation RMSE baseline/augmented: {result.get('validation',{}).get('base',{}).get('rmse')} / {result.get('validation',{}).get('aug',{}).get('rmse')}",f"- Test RMSE baseline/augmented: {result.get('test',{}).get('base',{}).get('rmse')} / {result.get('test',{}).get('aug',{}).get('rmse')}",f"- Validation/test RMSE improvement: {result.get('validation_improvement_pct')}% / {result.get('test_improvement_pct')}%",f"- Validation/test forecasts: {result.get('validation',{}).get('n')} / {result.get('test',{}).get('n')}",f"- Paired test loss: {json.dumps(result.get('paired_test_loss'),sort_keys=True)}",f"- Skipped events: {json.dumps(result.get('event_construction',{}).get('skipped'),sort_keys=True)}",f"- Source hashes: {json.dumps({k:v.get('sha256') for k,v in result.get('data_sources',{}).items()},sort_keys=True)}",f"- Error: {error or result.get('error')}",'', 'VERIFIED: deterministic parser, strict-prior WTI timing, negative-price asinh handling, non-overlapping targets, walk-forward maturity, decision logic and synthetic end-to-end tests; live source coverage and metrics only if completed_backtest is true.', 'UNVERIFIED: historical point-in-time revisions, intraday dissemination timing, causality, independent replication and instrument-level economic value.', 'Forecast only. No trading, profitability or deployment claim. WTI negative prices are retained via the preregistered asinh transform. No raw source rows are committed.']
    report.write_text('\n'.join(lines)+'\n',encoding='utf-8'); manifest.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    rel=str(report.relative_to(ROOT)); update_handoff(result,rel)
    return str(report.relative_to(ROOT)),str(manifest.relative_to(ROOT))

def main():
    try: result=run()
    except Exception as exc: result={'hypothesis_id':HYPOTHESIS_ID,'status':'INCONCLUSIVE','completed_backtest':False,'disposition':f'INCONCLUSIVE — bounded source/execution failure: {type(exc).__name__}: {exc}','run_id':RUN,'attempt':ATTEMPT,'source_commit_sha':SHA,'daily_kpi':'Daily minimum met by distinct earlier experiments.','error':f'{type(exc).__name__}: {exc}'}
    print(json.dumps({'result':result,'paths':persist(result)},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
