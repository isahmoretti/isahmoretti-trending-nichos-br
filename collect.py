#!/usr/bin/env python3
"""
Coleta diária de tendências: jardinagem, decoração e educação.
Fontes: Google Trends, Reddit, YouTube Data API v3
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta, date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

NICHOS = {
    "atividades": {
        "label": "Atividades",
        "google_kw": ["atividades para crianças", "atividades pedagógicas", "atividades físicas", "atividades lúdicas", "atividades para idosos"],
        "reddit_subs": ["brasil", "educacao"],
        "reddit_queries": ["atividades para crianças", "atividades pedagógicas", "atividades físicas"],
        "youtube_queries": ["atividades para crianças 2025", "atividades pedagógicas educação infantil", "atividades físicas em casa"],
    },
    "jardinagem": {
        "label": "Jardinagem",
        "google_kw": [
            # Plantas específicas (lote 1)
            "rosa do deserto", "orquídea", "suculentas", "cactos", "trepadeiras",
            # Intenções de busca (lote 2)
            "como plantar", "como fazer muda", "como adubar", "podar", "replantar",
            # Temas gerais (lote 3)
            "flores", "jardim", "horta", "adubo", "o que plantar",
            # Outros (lote 4)
            "árvores", "plantas que",
        ],
        "reddit_subs": ["jardinagem", "brasil"],
        "reddit_queries": ["jardinagem", "plantas em casa", "horta"],
        "youtube_queries": [
            "rosa do deserto cuidados", "como plantar orquídea",
            "suculentas para iniciantes", "horta em casa 2025",
            "como fazer muda de plantas",
        ],
    },
    "decoracao": {
        "label": "Decoração",
        "google_kw": ["decoração sala", "decoração quarto", "home decor brasil", "minimalismo", "decoração apartamento"],
        "reddit_subs": ["brasil"],
        "reddit_queries": ["decoração", "decor apartamento", "sala decorada"],
        "youtube_queries": ["decoração sala 2025", "decorar apartamento pequeno", "tendências decoração"],
    },
    "educacao": {
        "label": "Educação",
        "google_kw": ["concurso público 2025", "curso online gratuito", "vestibular 2025", "educação infantil", "homeschooling brasil"],
        "reddit_subs": ["vestibular", "concursospublicos", "brasil"],
        "reddit_queries": ["concurso público", "vestibular", "educação"],
        "youtube_queries": ["estudar em casa", "técnicas de estudo", "curso gratuito 2025"],
    },
}


def collect_google_trends(nicho_key: str, nicho_data: dict) -> dict:
    result = {"trending": [], "related_top": [], "related_rising": []}
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="pt-BR", tz=180)

        all_kws = nicho_data["google_kw"]
        interest_scores: dict[str, float] = {}

        # ── Passo 1: interest_over_time em lotes de 5 ────────────────────────
        for i in range(0, len(all_kws), 5):
            lote = all_kws[i:i + 5]
            try:
                pt.build_payload(lote, geo="BR", timeframe="today 3-m")
                time.sleep(5)
                iot = pt.interest_over_time()
                if not iot.empty:
                    for kw in lote:
                        if kw in iot.columns:
                            interest_scores[kw] = round(float(iot[kw].mean()), 1)
                time.sleep(6)
            except Exception as e:
                log.warning(f"Google Trends lote {lote} [{nicho_key}]: {e}")
                time.sleep(10)

        # Salva ranking de interesse de todas as keywords
        for kw, score in sorted(interest_scores.items(), key=lambda x: x[1], reverse=True):
            result["related_top"].append({
                "termo": kw,
                "valor": score,
                "base": "interesse médio 3 meses",
            })

        # ── Passo 2: related_queries para as top 3 keywords com mais volume ──
        top_kws = [item["termo"] for item in result["related_top"][:3]]
        seen_queries: set[str] = set()

        for kw in top_kws:
            try:
                pt.build_payload([kw], geo="BR", timeframe="today 3-m")
                time.sleep(5)
                related = pt.related_queries()
                data_kw = related.get(kw, {})

                top_df = data_kw.get("top")
                rising_df = data_kw.get("rising")

                if top_df is not None and not top_df.empty:
                    for _, row in top_df.head(15).iterrows():
                        q = row["query"]
                        if q not in seen_queries:
                            seen_queries.add(q)
                            result["trending"].append({
                                "termo": q,
                                "valor": int(row["value"]),
                                "base": kw,
                            })

                if rising_df is not None and not rising_df.empty:
                    for _, row in rising_df.head(8).iterrows():
                        q = row["query"]
                        if q not in seen_queries:
                            seen_queries.add(q)
                            result["related_rising"].append({
                                "termo": q,
                                "valor": str(row["value"]),
                                "base": kw,
                            })

                time.sleep(7)
            except Exception as e:
                log.warning(f"Google Trends related_queries '{kw}' [{nicho_key}]: {e}")
                time.sleep(12)

        log.info(
            f"Google Trends [{nicho_key}]: {len(result['related_top'])} keywords, "
            f"{len(result['trending'])} variações, {len(result['related_rising'])} rising"
        )

    except Exception as e:
        log.error(f"Google Trends [{nicho_key}] falhou: {e}")

    return result


def collect_reddit(nicho_key: str, nicho_data: dict) -> list:
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        log.warning(f"Reddit [{nicho_key}]: variáveis REDDIT_CLIENT_ID/SECRET não definidas")
        return []

    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent="trending-nichos-br/1.0",
        )

        posts = []
        seen = set()

        for query in nicho_data["reddit_queries"]:
            for sub_name in nicho_data["reddit_subs"]:
                try:
                    for post in reddit.subreddit(sub_name).search(
                        query, sort="hot", time_filter="week", limit=5
                    ):
                        if post.id not in seen:
                            seen.add(post.id)
                            posts.append({
                                "titulo": post.title,
                                "upvotes": post.score,
                                "comentarios": post.num_comments,
                                "subreddit": sub_name,
                                "url": f"https://reddit.com{post.permalink}",
                            })
                    time.sleep(1)
                except Exception as e:
                    log.warning(f"Reddit r/{sub_name} [{nicho_key}]: {e}")

        posts.sort(key=lambda x: x["upvotes"], reverse=True)
        log.info(f"Reddit [{nicho_key}]: {len(posts[:10])} posts")
        return posts[:10]

    except Exception as e:
        log.error(f"Reddit [{nicho_key}] falhou: {e}")
        return []


def collect_youtube(nicho_key: str, nicho_data: dict) -> list:
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        log.warning(f"YouTube [{nicho_key}]: YOUTUBE_API_KEY não definida")
        return []

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)

        published_after = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        videos = []
        seen = set()

        for query in nicho_data["youtube_queries"]:
            try:
                response = youtube.search().list(
                    q=query,
                    part="snippet",
                    type="video",
                    regionCode="BR",
                    relevanceLanguage="pt",
                    order="viewCount",
                    publishedAfter=published_after,
                    maxResults=5,
                ).execute()

                for item in response.get("items", []):
                    vid_id = item["id"]["videoId"]
                    if vid_id not in seen:
                        seen.add(vid_id)
                        videos.append({
                            "titulo": item["snippet"]["title"],
                            "canal": item["snippet"]["channelTitle"],
                            "publicado": item["snippet"]["publishedAt"][:10],
                            "query_base": query,
                            "url": f"https://youtube.com/watch?v={vid_id}",
                        })
                time.sleep(0.5)
            except Exception as e:
                log.warning(f"YouTube query '{query}' [{nicho_key}]: {e}")

        log.info(f"YouTube [{nicho_key}]: {len(videos[:15])} vídeos")
        return videos[:15]

    except Exception as e:
        log.error(f"YouTube [{nicho_key}] falhou: {e}")
        return []


TEMPLATES_NICHO = {
    "atividades": {
        "lista":      ["{n} {t} para experimentar em casa (sem gastar nada)",
                       "{n} {t} que ensinam e divertem ao mesmo tempo",
                       "As {n} melhores {t} para fazer hoje, segundo especialistas"],
        "como_fazer": ["Como fazer {t}: guia completo passo a passo",
                       "{T}: como estimular o desenvolvimento de forma divertida",
                       "{T}: tudo que você precisa saber em {ano}"],
        "tendencia":  ["Por que {t} está em alta no Brasil agora",
                       "{T}: a busca que explodiu no Google esta semana",
                       "{T} em {ano}: o que mudou e o que esperar"],
    },
    "jardinagem": {
        "lista":      ["{n} dicas de {t} para quem está começando do zero",
                       "{n} erros em {t} que matam suas plantas (evite estes)",
                       "{n} ideias de {t} baratas para fazer neste fim de semana"],
        "como_fazer": ["Como fazer {t} em casa: passo a passo para iniciantes",
                       "{T}: o guia definitivo para {ano}",
                       "Tudo sobre {t}: dicas, cuidados e erros comuns"],
        "tendencia":  ["Por que {t} virou febre nas redes sociais",
                       "{T}: a tendência que domina os jardins em {ano}",
                       "{T} em alta: como aproveitar essa onda agora"],
    },
    "decoracao": {
        "lista":      ["{n} ideias de {t} para transformar qualquer ambiente",
                       "{n} truques de {t} que fazem toda a diferença",
                       "{n} inspirações de {t} para copiar agora"],
        "como_fazer": ["Como usar {t}: passo a passo completo para iniciantes",
                       "{T}: como aplicar essa tendência na sua casa",
                       "Guia de {t}: do básico ao incrível em {ano}"],
        "tendencia":  ["Por que {t} está dominando a decoração em {ano}",
                       "{T}: a tendência que vai transformar sua casa",
                       "{T} em {ano}: o que está em alta nos interiores brasileiros"],
    },
    "educacao": {
        "lista":      ["{n} dicas de {t} que vão mudar sua forma de estudar",
                       "{n} estratégias de {t} usadas por quem passa em concursos",
                       "{n} recursos gratuitos de {t} para usar hoje mesmo"],
        "como_fazer": ["Como se preparar para {t}: rotina completa para {ano}",
                       "{T}: o guia definitivo para quem quer resultados",
                       "Tudo sobre {t}: estratégia, materiais e cronograma"],
        "tendencia":  ["Por que {t} está em alta entre os brasileiros",
                       "{T}: a aposta certa para {ano}",
                       "{T} em {ano}: o que mudou e como se posicionar"],
    },
}

DICAS_DISCOVER_BASE = [
    "Publique de manhã (7h–9h BRT) — pico de abertura do Discover",
    "Imagem mínima 1200×628 px, sem texto sobreposto",
    "Título entre 50–70 caracteres — ideal para o cartão do Discover",
    "Primeiros 2 parágrafos devem responder diretamente à busca",
    "Inclua a data ou ano no título para sinalizar atualidade",
]

DICAS_POR_NICHO = {
    "atividades": ["Foto real de criança em atividade converte mais que ilustração",
                   "Mencione faixa etária no título — aumenta clique qualificado"],
    "jardinagem": ["Foto do resultado final (planta/jardim bonito) gera mais cliques",
                   "Inclua custo estimado (ex: 'por menos de R$30') — alto CTR"],
    "decoracao":  ["Imagem antes/depois tem CTR 40% maior no Discover",
                   "Mostre ambiente real, não renderização — mais engajamento"],
    "educacao":   ["Mencione concurso ou vestibular específico para tráfego qualificado",
                   "Inclua prazo ou data ('em 3 meses', '2026') — aumenta urgência"],
}


def _gera_titulos(termo: str, nicho_key: str, ano: int, n: int) -> dict:
    t = termo.strip()
    T = t[0].upper() + t[1:]
    templates = TEMPLATES_NICHO.get(nicho_key, TEMPLATES_NICHO["educacao"])

    def fill(tpl):
        return tpl.format(t=t, T=T, n=n, ano=ano)

    return {
        "lista":      [fill(tpl) for tpl in templates["lista"]],
        "como_fazer": [fill(tpl) for tpl in templates["como_fazer"]],
        "tendencia":  [fill(tpl) for tpl in templates["tendencia"]],
    }


def generate_pautas(result: dict) -> list:
    ano = datetime.utcnow().year
    pautas = []

    for nicho_key, nicho_data in result.get("nichos", {}).items():
        gt = nicho_data.get("google_trends", {})

        # Monta pool de termos com score
        pool = []
        for item in gt.get("trending", []):
            if isinstance(item, dict):
                pool.append({"termo": item["termo"], "score": float(item.get("valor", 50))})
        for item in gt.get("related_top", []):
            pool.append({"termo": item["termo"], "score": float(item.get("valor", 10))})
        for item in gt.get("related_rising", []):
            pool.append({"termo": item["termo"], "score": 60.0})  # rising = oportunidade

        # Deduplica e ordena
        seen = set()
        pool_uniq = []
        for it in sorted(pool, key=lambda x: x["score"], reverse=True):
            if it["termo"] not in seen:
                seen.add(it["termo"])
                pool_uniq.append(it)

        for item in pool_uniq[:5]:
            score = item["score"]
            n_itens = 20 if score >= 70 else 15 if score >= 30 else 10
            urgencia = "🔥 Alta" if score >= 70 else "⬆️ Média" if score >= 30 else "📈 Normal"

            titulos = _gera_titulos(item["termo"], nicho_key, ano, n_itens)
            dicas = DICAS_DISCOVER_BASE[:3] + DICAS_POR_NICHO.get(nicho_key, [])

            pautas.append({
                "nicho": nicho_data.get("label", nicho_key),
                "nicho_key": nicho_key,
                "termo_base": item["termo"],
                "score": score,
                "urgencia": urgencia,
                "titulos": titulos,
                "formato_recomendado": "Lista" if score >= 50 else "Como fazer",
                "tamanho": "1.800 a 2.500 palavras",
                "imagem": f"Foto real relacionada a '{item['termo']}' — sem texto, alta resolução",
                "dicas_discover": dicas,
            })

    pautas.sort(key=lambda x: x["score"], reverse=True)
    log.info(f"Pautas geradas: {len(pautas)}")
    return pautas


def main():
    today = date.today().isoformat()
    output_file = DATA_DIR / f"{today}.json"

    if output_file.exists():
        log.info(f"Dados de {today} já existem. Use --force para sobrescrever.")
        return

    log.info(f"Iniciando coleta para {today}")

    result = {
        "date": today,
        "collected_at": datetime.utcnow().isoformat(),
        "nichos": {},
    }

    for key, nicho in NICHOS.items():
        log.info(f"── {nicho['label']} ──")
        result["nichos"][key] = {
            "label": nicho["label"],
            "google_trends": collect_google_trends(key, nicho),
            "reddit": collect_reddit(key, nicho),
            "youtube": collect_youtube(key, nicho),
        }
        time.sleep(5)

    result["pautas"] = generate_pautas(result)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info(f"Salvo em {output_file}")


if __name__ == "__main__":
    main()
