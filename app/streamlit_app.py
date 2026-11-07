import pandas as pd, streamlit as st
st.set_page_config(page_title="SIP Discovery Engine", layout="wide")
@st.cache_data
def load():
    d = pd.read_csv("data/export/tagged.csv")
    try: g = pd.read_csv("data/export/golden.csv")
    except FileNotFoundError: g = None
    return d, g
df, golden = load()
syn = bool(df["synthetic"].any()) if "synthetic" in df else False
st.sidebar.title("SIP Discovery Engine")
page = st.sidebar.radio("Page", ["Overview","Opportunity ranking","Voluntary vs involuntary","Segments & sources","Evidence explorer","Validation & limitations"])
if syn: st.warning("SYNTHETIC DEMO DATA: placeholder rows to preview the layout. Not real findings.")
st.caption(f"{len(df)} posts tagged · {int(df.relevant.sum())} relevant · sources: {', '.join(sorted(df.source.unique()))}")
rel = df[df.relevant]
lapses = rel[rel.lapse_type.isin(["voluntary","involuntary"])]

if page=="Overview":
    st.header("What was collected, and how it was processed")
    st.markdown("**Pipeline:** collect → clean → filter (SIP-related?) → tag with fixed codebook → verify quotes → dashboard")
    st.bar_chart(rel.source.value_counts())
    st.subheader("Posts by journey stage"); st.bar_chart(rel.stage.value_counts())

elif page=="Opportunity ranking":
    st.header("Which causes of lapse appear most, and how severe are they?")
    t = lapses.groupby("trigger").agg(posts=("id","count"), avg_severity=("severity","mean"), need=("unmet_need","first")).reset_index()
    t["share_%"] = (t.posts/t.posts.sum()*100).round(1)
    t["score"] = (t["share_%"]*t.avg_severity).round(1)
    t = t.sort_values("score", ascending=False)
    st.caption("Score = share of lapse posts × average severity. A starting rank, not a verdict.")
    st.dataframe(t, use_container_width=True, hide_index=True)
    for _, r in t.head(3).iterrows():
        q = lapses[lapses.trigger==r.trigger].head(2).evidence_quote.tolist()
        st.markdown(f"**{r.trigger.replace('_',' ')}**: " + " · ".join(f"“{x}”" for x in q))

elif page=="Voluntary vs involuntary":
    st.header("Lapses split by whether the investor chose to stop")
    ct = pd.crosstab(lapses.source, lapses.lapse_type, normalize="index").mul(100).round(0)
    st.bar_chart(ct); st.dataframe(ct)
    st.info("The split depends heavily on where we listened. Always read it by source, not as one overall number.")

elif page=="Segments & sources":
    st.header("Proxy comparisons by source and first-time status")
    st.write("Age, income and money source are rarely stated in public posts, so segments use proxies and need interview validation.")
    st.dataframe(pd.crosstab(rel.first_time, rel.trigger))
    n = lapses.groupby("source").size()
    st.write("Lapse stories per source:", n.to_dict())
    if (n<15).any(): st.warning("Groups with fewer than 15 lapse stories are low confidence.")

elif page=="Evidence explorer":
    st.header("Verified quotes")
    c1,c2 = st.columns(2)
    src = c1.multiselect("Source", sorted(df.source.unique()), default=sorted(df.source.unique()))
    trg = c2.multiselect("Trigger", sorted(df.trigger.unique()), default=sorted(df.trigger.unique()))
    v = rel[rel.source.isin(src) & rel.trigger.isin(trg) & rel.quote_verified].sort_values("severity", ascending=False)
    st.dataframe(v[["source","year","trigger","lapse_type","severity","evidence_quote"]], use_container_width=True, hide_index=True)

else:
    st.header("How far to trust this")
    st.metric("Quotes verified as exact text", f"{rel.quote_verified.mean()*100:.0f}%")
    st.write("Tagged by:", rel.tagged_by.value_counts().to_dict())
    if golden is not None:
        st.subheader("Golden-set agreement (AI vs human)"); st.dataframe(golden, hide_index=True)
    st.markdown("**Known limits:** reviews skew negative; curated Reddit threads inflate stop stories; silent dropouts are not in public text; segment fields are mostly unstated.")
