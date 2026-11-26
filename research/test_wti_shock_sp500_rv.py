import datetime as dt,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import wti_shock_sp500_rv as m

class WtiShockTests(unittest.TestCase):
    def dates(self,start,n):
        out=[]; d=start
        while len(out)<n:
            if d.weekday()<5: out.append(d)
            d+=dt.timedelta(days=1)
        return out
    def market(self,n=900):
        ds=self.dates(dt.date(2016,11,25),n)
        p={d:2200+i*.31+10*math.sin(i/13)+2*math.cos(i/5) for i,d in enumerate(ds)}
        v={d:18+2.3*math.sin(i/17)+.25*math.cos(i/7) for i,d in enumerate(ds)}
        o={d:48+.015*i+2*math.sin(i/23)+.5*math.cos(i/9) for i,d in enumerate(ds)}
        return ds,o,v,p
    def test_parser_preserves_negative_wti_and_skips_dot(self):
        raw=b'observation_date,DCOILWTICO\n2020-04-17,18.31\n2020-04-20,-36.98\n2020-04-21,8.91\n2020-04-22,.\n'
        x=m.parse(raw,'DCOILWTICO')
        self.assertEqual(x[dt.date(2020,4,20)],-36.98); self.assertEqual(len(x),3)
    def test_parser_rejects_duplicate_and_nonpositive_vix(self):
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            m.parse(b'observation_date,VIXCLS\n2026-11-20,18\n2026-11-20,19\n','VIXCLS',True)
        with self.assertRaisesRegex(ValueError,'Non-positive'):
            m.parse(b'observation_date,VIXCLS\n2026-11-20,0\n','VIXCLS',True)
    def test_parser_rejects_wrong_schema(self):
        with self.assertRaisesRegex(ValueError,'Unexpected'):
            m.parse(b'date,value\n2026-11-20,1\n','DCOILWTICO')
    def test_coverage_accepts_fresh_and_negative_wti(self):
        ds=self.dates(dt.date(2016,11,25),1900)
        data={'DCOILWTICO':{d:(-36.98 if i==850 else 40+i*.001) for i,d in enumerate(ds)},'VIXCLS':{d:18+i*.0001 for i,d in enumerate(ds)},'SP500':{d:2000+i*.1 for i,d in enumerate(ds)}}
        cov=m.validate(data,ds[-1]+dt.timedelta(days=1)); self.assertEqual(cov['DCOILWTICO']['rows'],1900)
    def test_source_level_gaps_are_reported_not_imputed_or_globally_rejected(self):
        ds=self.dates(dt.date(2016,11,25),1900); oil={d:40+i*.001 for i,d in enumerate(ds)}
        for d in ds[400:410]: oil.pop(d)
        data={'DCOILWTICO':oil,'VIXCLS':{d:18 for d in ds},'SP500':{d:2000 for d in ds}}
        cov=m.validate(data,ds[-1]+dt.timedelta(days=1))
        self.assertGreater(cov['DCOILWTICO']['max_gap_days'],5)
    def test_coverage_rejects_stale_and_future_sources(self):
        ds=self.dates(dt.date(2016,11,25),1900)
        def data(oil): return {'DCOILWTICO':oil,'VIXCLS':{d:18 for d in ds},'SP500':{d:2000 for d in ds}}
        with self.assertRaisesRegex(ValueError,'Stale WTI'):
            m.validate(data({d:40 for d in ds[:-20]}),ds[-1]+dt.timedelta(days=1))
        with self.assertRaisesRegex(ValueError,'future data'):
            m.validate(data({d:40 for d in ds}),ds[-1]-dt.timedelta(days=1))
    def test_strict_prior_wti_and_asinh_feature(self):
        ds,o,v,p=self.market(); ev,meta=m.events(o,v,p); self.assertGreater(len(ev),100)
        row=ev[0]; i=ds.index(row['signal']); self.assertEqual(row['oil_date'],ds[i-1]); self.assertLess(row['oil_date'],row['signal'])
        expected=math.asinh(o[ds[i-1]]/50)-math.asinh(o[ds[i-6]]/50)
        self.assertAlmostEqual(row['wti_asinh5'],expected); self.assertTrue(meta['strictly_prior_wti'])
    def test_negative_wti_price_produces_finite_feature(self):
        ds,o,v,p=self.market(); i=248; o[ds[i-1]]=-36.98
        ev,_=m.events(o,v,p); row=next(x for x in ev if x['signal']==ds[i])
        self.assertTrue(math.isfinite(row['wti_asinh5']))
    def test_same_date_wti_value_cannot_change_feature(self):
        ds,o,v,p=self.market(); ev1,_=m.events(o,v,p); o[ds[248]]*=4; ev2,_=m.events(o,v,p)
        a=next(x for x in ev1 if x['signal']==ds[248]); b=next(x for x in ev2 if x['signal']==ds[248])
        self.assertEqual(a['wti_asinh5'],b['wti_asinh5'])
    def test_missing_wti_not_forward_filled_and_stale_signal_skipped(self):
        ds,o,v,p=self.market(); i=248; o.pop(ds[i-1]); ev,_=m.events(o,v,p)
        row=next(x for x in ev if x['signal']==ds[i]); self.assertNotEqual(row['oil_date'],ds[i-1])
        o2=dict(o)
        for d in ds[i-5:i]: o2.pop(d,None)
        ev2,meta=m.events(o2,v,p); self.assertNotIn(ds[i],[x['signal'] for x in ev2]); self.assertGreater(meta['skipped']['stale_oil'],0)
    def test_events_are_six_sessions_apart_and_targets_do_not_overlap(self):
        ds,o,v,p=self.market(); ev,_=m.events(o,v,p)
        for a,b in zip(ev,ev[1:]):
            self.assertLess(a['target_end'],b['signal']); self.assertEqual(ds.index(b['signal'])-ds.index(a['signal']),6)
    def test_walkforward_requires_104_matured_training_events(self):
        start=dt.date(2020,1,3); rows=[]
        for i in range(105):
            d=start+dt.timedelta(days=7*i); rows.append({'signal':d,'target_end':d+dt.timedelta(days=6),'target_start':d+dt.timedelta(days=1),'y':.2+.01*math.sin(i/3)+i*.0001,'pre_rv5':.1+i%11*.01,'pre_rv20':.2+i%13*.01,'log_vix':2.5+i%7*.03,'wti_asinh5':.02*math.sin(i/5)+i%3*.002})
        pred=m.walkforward(rows); self.assertEqual(len(pred),1); self.assertEqual(pred[0]['train_n'],104)
    def test_decision_stays_inconclusive_without_positive_bootstrap_bound(self):
        v={'n':50,'base':{'rmse':1.0},'aug':{'rmse':.9}}; t={'n':50,'base':{'rmse':1.0},'aug':{'rmse':.9}}
        self.assertEqual(m.decide(v,t,{'ci95_low':-.01,'ci95_high':.1})[0],'INCONCLUSIVE')
        self.assertEqual(m.decide(v,t,{'ci95_low':.01,'ci95_high':.1})[0],'BACKTESTED')
    def test_full_synthetic_walkforward_pipeline(self):
        ds=self.dates(dt.date(2016,11,25),2400)
        vals={'DCOILWTICO':{d:(-36.98 if i==850 else 52+.006*i+4*math.sin(i/19)) for i,d in enumerate(ds)},'VIXCLS':{d:18+3*math.sin(i/21)+.5*math.cos(i/8) for i,d in enumerate(ds)},'SP500':{d:2200*math.exp(.00022*i+.008*math.sin(i/8)+.003*math.cos(i/3)) for i,d in enumerate(ds)}}
        bodies={s:('observation_date,'+s+'\n'+'\n'.join(f'{d},{x}' for d,x in v.items())+'\n').encode() for s,v in vals.items()}
        def fetch(url,timeout=25):
            for s,b in bodies.items():
                if f'id={s}&' in url:return b
            raise AssertionError(url)
        with patch.object(m.base,'fetch_bytes',side_effect=fetch): result=m.run(ds[-1]+dt.timedelta(days=1))
        self.assertTrue(result['completed_backtest']); self.assertGreaterEqual(result['validation']['n'],30); self.assertGreaterEqual(result['test']['n'],30)
        self.assertEqual(result['data_sources']['DCOILWTICO']['rows'],2400)
    def test_handoff_upsert_preserves_concurrent_registry_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); reg=root/'registry.md'; pre=root/'prereg.md'
            reg.write_text('# Registry\n\n| Hypothesis ID | Status |\n|---|---|\n| OTHER | BACKTESTED | concurrent update |\n',encoding='utf-8')
            pre.write_text('# Prereg\n\n- **Status:** FEASIBILITY_CHECKED\n',encoding='utf-8')
            result={'status':'INCONCLUSIVE','disposition':'INCONCLUSIVE — concurrent test','completed_backtest':True,'coverage':{},'validation':{'n':107},'test':{'n':204},'validation_improvement_pct':1.6,'test_improvement_pct':-1.1,'paired_test_loss':{'ci95_low':-.003,'ci95_high':-.0001}}
            with patch.object(m,'REG',reg),patch.object(m,'PREREG',pre): m.update_handoff(result,'reports/test.md')
            content=reg.read_text(); self.assertIn('| OTHER | BACKTESTED |',content); self.assertIn(m.HYPOTHESIS_ID,content)
            self.assertIn('INCONCLUSIVE',pre.read_text()); self.assertIn('ci95_low',pre.read_text())

    def test_persistence_is_idempotent_and_updates_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); reg=root/'registry.md'; pre=root/'prereg.md'
            reg.write_text('# Registry\n\n| Hypothesis ID | Status |\n|---|---|\n',encoding='utf-8')
            pre.write_text('# Prereg\n\n- **Status:** FEASIBILITY_CHECKED\n\n## Empirical disposition\nold\n',encoding='utf-8')
            result={'status':'INCONCLUSIVE','disposition':'INCONCLUSIVE — test','completed_backtest':False,'coverage':{},'run_id':'x'}
            with patch.object(m,'ROOT',root),patch.object(m,'SESSION',root/'sessions'),patch.object(m,'OUT',root/'out'),patch.object(m,'REG',reg),patch.object(m,'PREREG',pre):
                m.persist(result); m.persist(result)
            self.assertEqual(reg.read_text().count(m.HYPOTHESIS_ID),1)
            self.assertIn('INCONCLUSIVE',pre.read_text()); self.assertTrue((root/'out'/'manifest.json').exists())

if __name__=='__main__': unittest.main()
