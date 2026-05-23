import json
import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

NICHOS = {
    "atividades":    {"label": "🔤 Alfabetização e Ed. Infantil", "cor": "#e76f51"},
    "jardinagem":    {"label": "🌱 Jardinagem",                   "cor": "#2d6a4f"},
    "decoracao":     {"label": "🏡 Decoração",                    "cor": "#b5838d"},
    "educacao":      {"label": "🔢 Matemática e Gestão Escolar",  "cor": "#457b9d"},
    "pet":           {"label": "🐾 Pet",                          "cor": "#f4a261"},
    "desenvolvimento": {"label": "👶 Desenvolvimento Infantil",   "cor": "#6a994e"},
    "concursos":     {"label": "🎓 Concursos e Formação Docente",  "cor": "#7b2d8b"},
}

st.set_page_config(
    page_title="Tendências BR — Nichos",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Tendências Diárias — Nichos BR")
st.caption("Alfabetização · Matemática e Gestão · Jardinagem · Decoração · Pet · Desenvolvimento Infantil · Concursos para Professores")


@st.cache_data(ttl=3600)
def load_data(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_dates() -> list[str]:
    return sorted([f.stem for f in DATA_DIR.glob("*.json")], reverse=True)


dates = list_dates()

if not dates:
    st.warning("Nenhum dado coletado ainda. Execute `python collect.py` para gerar o primeiro arquivo.")
    st.code("python collect.py", language="bash")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    selected_date = st.selectbox("📅 Data", dates)
    st.divider()
    st.caption("Fontes: Google Trends · Reddit · YouTube")
    st.caption("Atualizado diariamente às 7h BRT")

data = load_data(str(DATA_DIR / f"{selected_date}.json"))
st.caption(f"Coleta realizada em: {data.get('collected_at', '—')} UTC")

# ── Métricas rápidas ──────────────────────────────────────────────────────────

total_pautas = len(data.get("pautas", []))
cols = st.columns(7)
for col, (key, cfg) in zip(cols, NICHOS.items()):
    nicho = data["nichos"].get(key, {})
    gt = nicho.get("google_trends", {})
    total_termos = len(gt.get("related_top", [])) + len(gt.get("trending", []))
    total_yt = len(nicho.get("youtube", []))
    col.metric(cfg["label"], f"{total_termos} termos", f"{total_yt} vídeos")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_labels = ["📝 Pautas para Discover"] + [cfg["label"] for cfg in NICHOS.values()]
tabs = st.tabs(tab_labels)

# ── Aba Pautas ────────────────────────────────────────────────────────────────

URGENCIA_COR = {"🔥 Alta": "#e63946", "⬆️ Média": "#f4a261", "📈 Normal": "#2a9d8f"}

with tabs[0]:
    pautas = data.get("pautas", [])
    if not pautas:
        st.info("Pautas serão geradas automaticamente na próxima coleta.")
    else:
        st.markdown(f"**{len(pautas)} sugestões de pauta** otimizadas para o Google Discover — ordenadas por potencial.")
        st.divider()

        filtro_nicho = st.multiselect(
            "Filtrar por nicho",
            options=list({p["nicho"] for p in pautas}),
            default=list({p["nicho"] for p in pautas}),
        )
        pautas_filtradas = [p for p in pautas if p["nicho"] in filtro_nicho]

        for p in pautas_filtradas:
            cor = URGENCIA_COR.get(p["urgencia"], "#888")
            with st.expander(
                f"{p['urgencia']}  ·  **{p['nicho']}**  ·  Score {p['score']}  —  _{p['termo_base']}_"
            ):
                c1, c2 = st.columns([3, 2])

                with c1:
                    st.markdown("**Títulos sugeridos — Lista**")
                    for titulo in p["titulos"].get("lista", []):
                        st.markdown(f"- {titulo}")

                    st.markdown("**Títulos sugeridos — Como Fazer**")
                    for titulo in p["titulos"].get("como_fazer", []):
                        st.markdown(f"- {titulo}")

                    st.markdown("**Títulos — Tendência**")
                    for titulo in p["titulos"].get("tendencia", []):
                        st.markdown(f"- {titulo}")

                with c2:
                    st.markdown("**Detalhes da pauta**")
                    st.markdown(f"- **Formato:** {p.get('formato_recomendado', '—')}")
                    st.markdown(f"- **Tamanho:** {p.get('tamanho', '—')}")
                    st.markdown(f"- **Imagem:** {p.get('imagem', '—')}")

                    st.markdown("**Dicas Google Discover**")
                    for dica in p.get("dicas_discover", []):
                        st.markdown(f"- {dica}")

        # Botão para exportar como CSV
        if pautas_filtradas:
            import pandas as pd
            rows = []
            for p in pautas_filtradas:
                for fmt, titulos in p["titulos"].items():
                    for titulo in titulos:
                        rows.append({
                            "Nicho": p["nicho"],
                            "Termo base": p["termo_base"],
                            "Score": p["score"],
                            "Urgência": p["urgencia"],
                            "Formato": fmt,
                            "Título sugerido": titulo,
                        })
            df_export = pd.DataFrame(rows)
            st.divider()
            st.download_button(
                "⬇️ Baixar todas as pautas (.csv)",
                df_export.to_csv(index=False).encode("utf-8"),
                file_name=f"pautas-discover-{selected_date}.csv",
                mime="text/csv",
            )

# ── Tabs por nicho ────────────────────────────────────────────────────────────

nicho_tabs = tabs[1:]

for tab, (key, cfg) in zip(nicho_tabs, NICHOS.items()):
    with tab:
        nicho = data["nichos"].get(key, {})
        if not nicho:
            st.warning("Dados indisponíveis para este nicho.")
            continue

        # Google Trends
        st.subheader("🔍 Google Trends")
        gt = nicho.get("google_trends", {})

        c1, c2 = st.columns([3, 2])

        with c1:
            st.markdown("**📈 Variações mais buscadas**")
            top = gt.get("related_top", [])
            if top:
                df = pd.DataFrame(top).rename(
                    columns={"termo": "Variação", "valor": "Score", "base": "Seed"}
                )
                cols_show = [c for c in ["Variação", "Score", "Seed"] if c in df.columns]
                st.dataframe(df[cols_show], hide_index=True, use_container_width=True)
            else:
                st.caption("Nenhuma variação capturada")

        with c2:
            st.markdown("**🚀 Subindo agora**")
            rising = gt.get("related_rising", [])
            if rising:
                df = pd.DataFrame(rising).rename(
                    columns={"termo": "Termo", "valor": "Crescimento", "base": "Seed"}
                )
                cols_show = [c for c in ["Termo", "Crescimento", "Seed"] if c in df.columns]
                st.dataframe(df[cols_show], hide_index=True, use_container_width=True)
            else:
                st.caption("Sem dados")

            seeds = gt.get("seeds", [])
            if seeds:
                st.markdown("**🌱 Seeds (interesse médio 3 meses)**")
                df_s = pd.DataFrame(seeds).rename(columns={"termo": "Seed", "valor": "Score"})
                st.dataframe(df_s.head(10), hide_index=True, use_container_width=True)

        st.divider()

        # YouTube
        st.subheader("▶️ YouTube — Vídeos em Alta")
        videos = nicho.get("youtube", [])
        if videos:
            grid = st.columns(3)
            for i, v in enumerate(videos[:9]):
                with grid[i % 3]:
                    titulo = v["titulo"]
                    titulo_curto = titulo[:55] + "..." if len(titulo) > 55 else titulo
                    st.markdown(f"**{titulo_curto}**")
                    st.caption(f"📺 {v['canal']}  ·  {v['publicado']}")
                    st.markdown(f"[Assistir ↗]({v['url']})")
                    st.markdown("---")
        else:
            st.info("Nenhum vídeo coletado para esta data. Os vídeos aparecem após a coleta automática diária.")
