"""Writes SYNTHETIC demo data so the dashboard can be previewed. Replace with real pipeline output."""
import random, pandas as pd
random.seed(7)
T = [  # trigger, lapse, stage, action, post, quote, need, emotion, severity
 ("failed_debit","involuntary","early_2_6m","stopped","My SIP bounced twice because salary came late and nobody told me it lapsed.","nobody told me it lapsed","Alert before and after a failed debit, with an easy retry","frustrated",3),
 ("low_early_returns","voluntary","early_2_6m","paused","Three months in and the balance looks tiny, returns flat, so I paused.","the balance looks tiny","Context on what early numbers normally look like","disappointed",2),
 ("market_fall","voluntary","mid_6_12m","paused","Market fell and my SIP showed red, so I paused until it recovers.","my SIP showed red","Reassurance grounded in facts about volatility","anxious",3),
 ("app_confusion","unclear","just_started","none_stated","I do not understand why XIRR differs from the percentage on the home screen.","why XIRR differs","Plain-language explanation of return numbers","confused",2),
 ("cash_crunch","voluntary","mid_6_12m","reduced","Irregular freelance income, so I cut my SIP and wish I could skip one month.","wish I could skip one month","Skip or pause a month without cancelling","anxious",2),
 ("outside_advice","voluntary","early_2_6m","stopped","A friend said SIPs are a waste so I stopped.","A friend said SIPs are a waste","Trusted, neutral explanations inside the app","confused",2),
 ("none_stated","not_applicable","later_12m_plus","continued","Still going after 14 months, it just happens from my salary account.","it just happens","Nothing, autopay works","calm",1),
 ("lost_interest","voluntary","mid_6_12m","stopped","Honestly forgot about it and let it lapse.","forgot about it","A light periodic check-in that is not pushy","calm",1),
]
W = {"Play Store":[5,2,1,2,1,0,1,1],"App Store":[4,2,1,2,1,0,1,1],"Reddit":[1,3,3,1,3,3,1,1],"YouTube":[0,2,2,1,2,4,1,2],"Forum":[1,2,2,2,2,2,1,1]}
rows=[];i=0
for src,w in W.items():
    for _ in range(14):
        t=random.choices(T,w)[0];i+=1
        ok=random.random()>0.1
        rows.append(dict(id=i,source=src,year=random.choice([2022,2023,2024,2025]),stage=t[2],action=t[3],lapse_type=t[1],trigger=t[0],
          unmet_need=t[6],emotion=t[7],severity=t[8],first_time=random.choice(["yes","yes","unclear"]),post_text=t[4],
          evidence_quote=t[5],quote_verified=ok,tagged_by=random.choice(["model_a","model_b"]),relevant=True,synthetic=True))
pd.DataFrame(rows).to_csv("data/export/tagged.csv",index=False)
pd.DataFrame([dict(field="lapse_type",agreement=0.78,n=20),dict(field="trigger",agreement=0.70,n=20),dict(field="stage",agreement=0.65,n=20)]).to_csv("data/export/golden.csv",index=False)
print("wrote",len(rows),"synthetic rows")
