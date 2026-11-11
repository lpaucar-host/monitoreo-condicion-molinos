import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title='Monitoreo de Condición – Molinos', page_icon='⚙️', layout='wide')

st.markdown('''
<style>
.stApp{background:#f4f7fb;color:#152536}.block-container{padding-top:.7rem;padding-bottom:1rem;max-width:1600px}
.header{background:#123a63;color:white;padding:16px 18px;border-radius:14px;margin-bottom:12px}
.header h1{font-size:24px;margin:0;font-weight:800}.header p{margin:4px 0 0;color:#dbeafe;font-size:13px}
.card{background:white;border:1px solid #d9e2ec;border-radius:12px;padding:13px 15px;box-shadow:0 1px 2px rgba(15,23,42,.05);min-height:100px}
.k{font-size:12px;color:#64748b;font-weight:700;text-transform:uppercase}.v{font-size:25px;font-weight:800;color:#0f2740;margin-top:4px}.n{font-size:11px;color:#64748b;margin-top:3px}
.sec{font-size:17px;font-weight:800;color:#102a43;margin:10px 0 8px}
.footer{font-size:11px;color:#64748b;margin-top:14px}
</style>
''', unsafe_allow_html=True)

st.markdown("<div class='header'><h1>MONITOREO DE CONDICIÓN – MOLINOS</h1><p>Resumen ejecutivo · análisis vibracional · priorización · confiabilidad · diagnóstico espectral</p></div>", unsafe_allow_html=True)

page = st.radio('Navegación', ['Resumen','Análisis','Prioridad','Jack-knife','Histórico','Cobertura','Diagnóstico espectral'], horizontal=True, label_visibility='collapsed')

estado = pd.DataFrame([
    ['Molino 1A','MOL-RD08-YA','ALERTA',5.30,'4H · CONTRAEJE'],
    ['Molino 1','MOL-RD01-YA','TOLERABLE',4.60,'Punto dominante'],
    ['Molino 2','MOL-BO01-YA','TOLERABLE',4.20,'Punto dominante'],
    ['Molino 3','MOL-BO02-YA','NORMAL',2.90,'Punto dominante'],
    ['Molino 4','MOL-BO03-YA','TOLERABLE',3.90,'Punto dominante'],
], columns=['Equipo','TAG','Estado','Velocidad','Punto'])

if page == 'Resumen':
    st.markdown("<div class='sec'>Resumen ejecutivo</div>", unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    vals=[('Equipos monitoreados','5','Planta concentradora'),('Última ronda','06/11/2026','Molino 1A'),('Equipo prioritario','Molino 1A','4H · Contraeje'),('Máx. actual','5.30 mm/s','Estado ALERTA'),('Diagnóstico espectral','Engrane','Confianza alta')]
    for c,(k,v,n) in zip([c1,c2,c3,c4,c5],vals):
        c.markdown(f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div><div class='n'>{n}</div></div>",unsafe_allow_html=True)
    l,r=st.columns([1.2,1])
    with l:
        fig=go.Figure()
        colors={'NORMAL':'#2e7d32','TOLERABLE':'#f9a825','ALERTA':'#ef6c00','PELIGRO':'#c62828'}
        fig.add_trace(go.Bar(x=estado.Equipo,y=estado.Velocidad,marker_color=[colors[x] for x in estado.Estado],text=estado.Velocidad,textposition='outside'))
        for y,col in [(3,'#2e7d32'),(5,'#f9a825'),(7,'#c62828')]: fig.add_hline(y=y,line_dash='dot',line_color=col)
        fig.update_layout(height=330,margin=dict(l=20,r=10,t=15,b=20),yaxis_title='mm/s',plot_bgcolor='white',paper_bgcolor='white')
        st.plotly_chart(fig,use_container_width=True)
    with r:
        st.markdown("<div class='sec'>Estado actual</div>",unsafe_allow_html=True)
        st.dataframe(estado[['Equipo','Estado','Velocidad','Punto']],hide_index=True,use_container_width=True)
        st.info('Molino 1A concentra la prioridad actual. El punto 4H del contraeje alcanzó 5.30 mm/s y mantiene tendencia ascendente.')

elif page == 'Análisis':
    st.markdown("<div class='sec'>Análisis por equipo – Molino 1A</div>",unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    vals=[('Estado actual','ALERTA','4H dominante'),('Última medición','06/11/2026','MOL-RD08-YA'),('Velocidad máx.','5.30 mm/s','4H · Contraeje'),('Aceleración RMS','0.64 g','4g'),('Envolvente','1.15 gE','4gE · ALERTA')]
    for c,(k,v,n) in zip([c1,c2,c3,c4,c5],vals): c.markdown(f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div><div class='n'>{n}</div></div>",unsafe_allow_html=True)
    dates=pd.to_datetime(['2026-07-25','2026-08-16','2026-08-22','2026-09-06','2026-09-20','2026-10-04','2026-10-18','2026-10-31','2026-11-06'])
    df=pd.DataFrame({'Fecha':dates,'4H':[2.5,4.2,4.6,4.7,4.8,4.7,5.2,5.2,5.3],'4V':[3.1,3.0,3.1,3.4,3.6,3.7,3.6,3.8,3.9],'4A':[2.2,2.4,2.9,3.3,3.6,3.5,3.7,4.0,4.2]})
    fig=go.Figure()
    for s in ['4H','4V','4A']: fig.add_trace(go.Scatter(x=df.Fecha,y=df[s],mode='lines+markers',name=s))
    for y,col in [(3,'#2e7d32'),(5,'#f9a825'),(7,'#c62828')]: fig.add_hline(y=y,line_dash='dot',line_color=col)
    fig.update_layout(height=350,margin=dict(l=20,r=10,t=10,b=20),yaxis_title='Velocidad RMS (mm/s)',plot_bgcolor='white',paper_bgcolor='white')
    st.plotly_chart(fig,use_container_width=True)
    st.success('Lectura técnica: 4H es el punto dominante y muestra crecimiento persistente. 4V y 4A permanecen en zona tolerable, también con crecimiento reciente.')

elif page == 'Prioridad':
    st.markdown("<div class='sec'>Prioridad de intervención</div>",unsafe_allow_html=True)
    pr=pd.DataFrame([
        ['P1','Molino 1A','4H · Contraeje','5.30 mm/s','ALERTA + crecimiento','Inspección dirigida del engrane y apoyo lado libre'],
        ['P2','Molino 1A','4A · Contraeje','4.20 mm/s','TOLERABLE + crecimiento','Seguimiento próximo monitoreo'],
        ['P2','Molino 1A','5A · Trunnion carga','4.20 mm/s','TOLERABLE','Verificar condición y tendencia'],
        ['P3','Molino 1A','4V · Contraeje','3.90 mm/s','TOLERABLE + crecimiento','Seguimiento de ruta'],
    ],columns=['Prioridad','Equipo','Punto','Valor','Criterio','Acción sugerida'])
    st.dataframe(pr,hide_index=True,use_container_width=True)
    st.caption('P1–P4 es una priorización interna de mantenimiento; no sustituye el diagnóstico de causa raíz.')

elif page == 'Jack-knife':
    st.markdown("<div class='sec'>Jack-knife – severidad vs cambio reciente</div>",unsafe_allow_html=True)
    jk=pd.DataFrame({'Punto':['4H','4V','4A','6A','1V'],'Actual':[4.60,3.40,3.20,2.20,1.20],'Cambio':[1.02,.57,.84,.37,.20]})
    fig=go.Figure(go.Scatter(x=jk.Cambio,y=jk.Actual,mode='markers+text',text=jk.Punto,textposition='top center',marker=dict(size=13)))
    for y,col in [(3,'#2e7d32'),(5,'#f9a825'),(7,'#c62828')]: fig.add_hline(y=y,line_dash='dot',line_color=col)
    fig.update_layout(height=420,xaxis_title='Cambio reciente (mm/s/mes)',yaxis_title='Valor actual (mm/s)',plot_bgcolor='white',paper_bgcolor='white')
    st.plotly_chart(fig,use_container_width=True)
    c1,c2,c3=st.columns(3)
    for c,k,v,n in [(c1,'Modelo 4H','+1.02 mm/s/mes','Ventana adaptativa · 12 mediciones'),(c2,'Calidad','Media','R² ≈ 0.75'),(c3,'Proyección','Condicionada','Solo si la tendencia persiste')]: c.markdown(f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div><div class='n'>{n}</div></div>",unsafe_allow_html=True)

elif page == 'Histórico':
    st.markdown("<div class='sec'>Histórico y confiabilidad – Molino 1A</div>",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    vals=[('Último mantenimiento','05/06/2026','4V · Contraeje'),('Vida ciclo actual','≈154 días','al 06/11/2026'),('Mediana histórica','201 días','intervalos de mantenimiento'),('Máximo sano histórico','257 días','referencia histórica')]
    for c,(k,v,n) in zip([c1,c2,c3,c4],vals): c.markdown(f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div><div class='n'>{n}</div></div>",unsafe_allow_html=True)
    hist=pd.DataFrame([
        ['05/06/2026','4V CONTRAEJE','Reemplazo de rodamiento y alineamiento en PDP'],
        ['17/08/2025','4V CONTRAEJE','Reemplazo de rodamiento y alineamiento'],
        ['01/07/2025','4A CONTRAEJE','Reemplazo de rodamiento'],
        ['26/08/2024','4H CONTRAEJE','Reemplazo de rodamiento'],
        ['08/05/2024','4V CONTRAEJE','Después de OVH'],
    ],columns=['Fecha','Punto','Intervención'])
    st.dataframe(hist,hide_index=True,use_container_width=True)
    st.caption('La estimación de vida se basa en eventos explícitos de mantenimiento; no se infiere un reemplazo únicamente por cambio de estado vibracional.')

elif page == 'Cobertura':
    st.markdown("<div class='sec'>Cobertura de monitoreo</div>",unsafe_allow_html=True)
    st.info('Cobertura = cumplimiento de ruta de medición; no representa severidad mecánica.')
    cov=pd.DataFrame({'Equipo':['Molino 1A','Molino 1','Molino 2','Molino 3','Molino 4'],'Cobertura %':[100,94,92,86,90]})
    fig=go.Figure(go.Bar(x=cov.Equipo,y=cov['Cobertura %'],text=cov['Cobertura %'].astype(str)+'%',textposition='outside'))
    fig.update_layout(height=330,yaxis_range=[0,110],plot_bgcolor='white',paper_bgcolor='white',margin=dict(l=20,r=10,t=15,b=20))
    st.plotly_chart(fig,use_container_width=True)

else:
    st.markdown("<div class='sec'>Diagnóstico espectral – Molino 1A · Contraeje</div>",unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6=st.columns(6)
    vals=[('Potencia','800 HP','Allis Chalmers'),('Contraeje','240 RPM','1X = 4.00 Hz'),('Piñón','19 dientes','GMF = 76 Hz'),('Catalina','293 dientes','≈15.56 RPM'),('Rodamiento L.A.','22244CC','Punto físico 3'),('Rodamiento L.L.','22244CC','Punto físico 4')]
    for c,(k,v,n) in zip([c1,c2,c3,c4,c5,c6],vals): c.markdown(f"<div class='card'><div class='k'>{k}</div><div class='v' style='font-size:20px'>{v}</div><div class='n'>{n}</div></div>",unsafe_allow_html=True)
    st.markdown("<div class='sec'>Evidencia diagnóstica</div>",unsafe_allow_html=True)
    d=pd.DataFrame([
        ['Engranaje piñón–catalina','ALTA','Armónicos GMF +145%; sidebands ±1X +372%'],
        ['Rodamiento lado libre 22244CC','MEDIA','Familia ≈30.8 Hz = 7.70X; crecimiento en envolvente ≈127%'],
        ['Soltura / holgura mecánica','BAJA','Hipótesis secundaria / posible amplificación'],
    ],columns=['Hipótesis','Confianza','Evidencia'])
    st.dataframe(d,hide_index=True,use_container_width=True)
    st.warning('Conclusión: revisar conjuntamente engrane piñón–catalina y apoyo lado libre. La familia de 30.8 Hz es candidata de rodamiento, pero no se etiqueta BPFO/BPFI sin factores geométricos verificados del 22244CC.')
    fam=pd.DataFrame({'Frecuencia Hz':[30.8,61.6,76,92.4,123.2,152,184.8,228,304],'Tipo':['Familia 30.8']*2+['GMF']+['Familia 30.8']*2+['2×GMF']+['Familia 30.8']+['3×GMF','4×GMF']})
    fig=go.Figure(go.Bar(x=fam['Frecuencia Hz'],y=[1,0.8,1.4,.72,.65,1.2,.6,1,.8],text=fam.Tipo,textposition='outside'))
    fig.update_layout(height=320,xaxis_title='Frecuencia (Hz)',yaxis_title='Evidencia relativa',showlegend=False,plot_bgcolor='white',paper_bgcolor='white')
    st.plotly_chart(fig,use_container_width=True)

st.markdown("<div class='footer'>Datos de presentación consolidados al 06/11/2026. Las proyecciones son herramientas de apoyo y deben combinarse con condición, causa raíz, criticidad e historial de intervención.</div>",unsafe_allow_html=True)
