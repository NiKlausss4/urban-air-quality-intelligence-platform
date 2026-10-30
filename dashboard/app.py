import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Urban Air Quality Intelligence", page_icon="🌫️", layout="wide")
st.title("Urban Air Quality Intelligence")
st.caption("Observed CPCB and US Embassy measurements via xKDR, with Open-Meteo historical weather context. Correlation does not imply causation.")

@st.cache_data(ttl=120)
def query(sql):
    db = create_engine(os.getenv("DATABASE_URL", "postgresql+psycopg2://airquality:airquality@localhost:5432/airquality"))
    with db.connect() as conn:
        return pd.read_sql(text(sql), conn)

try:
    cities = query("select name from dim_city order by name")
    if cities.empty:
        st.warning("No city data is loaded yet. Configure an xKDR API key and trigger the Airflow DAG or run the ETL command.")
        st.stop()
    options = cities.name.tolist()
    selected = st.sidebar.multiselect("Cities", options, default=options)
    if not selected:
        st.info("Select at least one city.")
        st.stop()
    quoted = ",".join("'" + c.replace("'", "''") + "'" for c in selected)
    aq = query(f"select c.name city,p.code pollutant,f.value,f.unit,f.observed_at,f.anomaly,s.name station,s.latitude,s.longitude from fact_air_quality f join dim_city c using(city_id) join dim_pollutant p using(pollutant_id) join dim_station s using(station_id) join raw_api_response r on r.raw_id=f.raw_id where r.source='xkdr' and c.name in ({quoted}) order by observed_at")
    if aq.empty:
        st.warning("No pollutant measurements are currently available for the selected cities and ingestion window. The platform does not generate substitute readings.")
    else:
        missing_cities=sorted(set(selected)-set(aq.city.unique()))
        if missing_cities:
            st.warning("No xKDR measurements were returned for: " + ", ".join(missing_cities) + ". These cities are excluded from comparisons until source data is available.")
        pm = aq[aq.pollutant.isin(["PM2.5", "PM10"])]
        avg25 = pm.loc[pm.pollutant.eq("PM2.5"), "value"].mean()
        avg10 = pm.loc[pm.pollutant.eq("PM10"), "value"].mean()
        freshness = aq.observed_at.max()
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Measurements", f"{len(aq):,}")
        c2.metric("Cities monitored", str(aq.city.nunique()))
        c3.metric("Mean PM2.5", "—" if pd.isna(avg25) else f"{avg25:.1f} µg/m³")
        c4.metric("Mean PM10", "—" if pd.isna(avg10) else f"{avg10:.1f} µg/m³")
        age_hours=(pd.Timestamp.now(tz="UTC")-freshness).total_seconds()/3600
        st.caption(f"Data freshness: {'Fresh' if age_hours < 48 else 'Stale'} · latest observation {freshness:%Y-%m-%d %H:%M UTC} ({age_hours:.1f} hours ago)")
        tab1,tab2,tab3,tab4,tab5=st.tabs(["Overview & trends","City comparison","Hotspots","Weather correlation","Data quality"])
        with tab1:
            period=st.selectbox("Trend period",["Daily","Weekly","Monthly"])
            freq={"Daily":"D","Weekly":"W","Monthly":"MS"}[period]
            trend=aq.groupby([pd.Grouper(key="observed_at",freq=freq),"pollutant"],as_index=False).value.mean()
            st.plotly_chart(px.line(trend,x="observed_at",y="value",color="pollutant",title=f"{period} mean pollutant levels"),use_container_width=True)
            peaks=aq[aq.anomaly].sort_values("value",ascending=False).head(20)
            st.subheader("High readings flagged by the platform")
            if peaks.empty: st.caption("No readings crossed the platform's exploratory threshold in this selection.")
            else: st.dataframe(peaks[["city","station","pollutant","value","unit","observed_at"]],use_container_width=True)
        with tab2:
            rank=aq.groupby(["city","pollutant"],as_index=False).value.mean()
            st.plotly_chart(px.bar(rank,x="city",y="value",color="pollutant",barmode="group",title="Mean concentrations by city"),use_container_width=True)
        with tab3:
            stations=aq.dropna(subset=["latitude","longitude"])
            if stations.empty: st.info("Station coordinates are not available for the selected observations.")
            else: st.plotly_chart(px.scatter_mapbox(stations,lat="latitude",lon="longitude",color="value",size="value",hover_name="station",hover_data=["city","pollutant","observed_at"],zoom=3,mapbox_style="carto-positron",title="Observed station readings"),use_container_width=True)
        with tab4:
            wx=query(f"select c.name city,w.observed_at,w.temperature_c,w.relative_humidity,w.wind_speed_kmh,w.precipitation_mm from fact_weather w join dim_city c using(city_id) where c.name in ({quoted})")
            if wx.empty: st.info("Weather data has not been loaded for these cities yet.")
            else:
                joined=pd.merge_asof(aq.sort_values("observed_at"),wx.sort_values("observed_at"),on="observed_at",by="city",direction="nearest",tolerance=pd.Timedelta("1h"))
                cols=["value","temperature_c","relative_humidity","wind_speed_kmh"]
                corr=joined[cols].corr(numeric_only=True)
                st.plotly_chart(px.imshow(corr,text_auto=".2f",color_continuous_scale="RdBu",zmin=-1,zmax=1,title="Pearson correlation (descriptive only)"),use_container_width=True)
        with tab5:
            runs=query("select started_at,finished_at,status,extracted,transformed,rejected,duplicates,errors from pipeline_run order by started_at desc limit 20")
            st.dataframe(runs,use_container_width=True)
            st.download_button("Download selected measurements",aq.to_csv(index=False),"air_quality.csv","text/csv")
except Exception as exc:
    st.error(f"Database unavailable or warehouse not initialized: {exc}")
