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
        "google_kw": ["jardinagem", "plantas em casa", "horta doméstica", "suculentas", "jardim vertical"],
        "reddit_subs": ["jardinagem", "brasil"],
        "reddit_queries": ["jardinagem", "plantas em casa", "horta"],
        "youtube_queries": ["jardinagem 2025", "plantas em casa", "horta doméstica"],
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

        # Interesse relativo entre as palavras-chave (mais estável que related_queries)
        kws = nicho_data["google_kw"][:5]
        pt.build_payload(kws, geo="BR", timeframe="today 3-m")
        time.sleep(4)

        iot = pt.interest_over_time()
        if not iot.empty:
            media = iot[kws].mean().sort_values(ascending=False)
            for kw, valor in media.items():
                result["related_top"].append({
                    "termo": kw,
                    "valor": round(float(valor), 1),
                    "base": "interesse médio 3 meses",
                })

        time.sleep(5)

        # Related queries para o termo principal do nicho
        pt.build_payload([kws[0]], geo="BR", timeframe="today 3-m")
        time.sleep(4)
        related = pt.related_queries()

        data_kw = related.get(kws[0], {})
        top_df = data_kw.get("top")
        rising_df = data_kw.get("rising")

        if top_df is not None and not top_df.empty:
            for _, row in top_df.head(15).iterrows():
                result["trending"].append({
                    "termo": row["query"],
                    "valor": int(row["value"]),
                })

        if rising_df is not None and not rising_df.empty:
            for _, row in rising_df.head(10).iterrows():
                result["related_rising"].append({
                    "termo": row["query"],
                    "valor": str(row["value"]),
                    "base": kws[0],
                })

        time.sleep(3)
        log.info(f"Google Trends [{nicho_key}]: {len(result['related_top'])} kws, {len(result['trending'])} queries, {len(result['related_rising'])} rising")

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

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info(f"Salvo em {output_file}")


if __name__ == "__main__":
    main()
