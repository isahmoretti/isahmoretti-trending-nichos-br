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
        "google_kw": [
            # Lote 1 — faixa etária 0–4 anos
            "atividades para bebê", "atividades para crianças de 1 ano", "atividades para crianças de 2 anos", "atividades para crianças de 3 anos", "atividades para crianças de 4 anos",
            # Lote 2 — faixa etária 5–10 anos
            "atividades para crianças de 5 anos", "atividades para crianças de 6 anos", "atividades para crianças de 7 anos", "atividades para crianças de 8 anos", "atividades para crianças de 10 anos",
            # Lote 3 — tipos de atividades
            "atividades pedagógicas", "atividades lúdicas", "atividades manuais", "atividades recreativas", "atividades educativas",
            # Lote 4 — necessidades especiais e contextos
            "atividades para crianças autistas", "atividades para crianças com tdah", "atividades em casa", "atividades ao ar livre", "atividades de férias",
            # Lote 5 — outros públicos e formatos
            "atividades para idosos", "atividades físicas", "atividades para adolescentes", "brincadeiras para crianças", "jogos educativos",
        ],
        "reddit_subs": ["brasil", "educacao"],
        "reddit_queries": ["atividades para crianças", "atividades pedagógicas", "atividades físicas"],
        "youtube_queries": [
            "atividades para crianças em casa",
            "atividades pedagógicas educação infantil",
            "brincadeiras para crianças autistas",
            "atividades físicas para idosos",
            "jogos educativos para crianças",
        ],
    },
    "jardinagem": {
        "label": "Jardinagem",
        # Seeds baseadas em tráfego real do Google Discover (jardinagem.casaefesta.com)
        "google_kw": [
            # Lote 1 — plantas com maior tráfego Discover
            "rosa do deserto", "orquídea", "suculentas", "cactos", "jabuticaba",
            # Lote 2 — frutíferas e propagação
            "árvores frutíferas", "como fazer muda", "como plantar", "ervas e temperos", "plantas que",
            # Lote 3 — temas gerais
            "flores", "jardim", "horta", "o que plantar", "vegetais",
            # Lote 4 — cuidados e jardim
            "trepadeiras", "como regar", "como adubar", "folhagens", "paisagismo",
            # Lote 5 — plantas populares adicionais
            "costela de adão", "antúrio", "bromélias", "babosa", "monstera",
        ],
        "reddit_subs": ["jardinagem", "brasil"],
        "reddit_queries": ["jardinagem", "plantas em casa", "horta"],
        "youtube_queries": [
            "rosa do deserto cuidados",
            "como plantar orquídea",
            "suculentas para iniciantes",
            "horta em casa",
            "como fazer muda de plantas",
        ],
    },
    "decoracao": {
        "label": "Decoração",
        "google_kw": [
            # Lote 1 — datas comemorativas principais
            "páscoa", "natal", "festa junina", "dia das mães", "dia dos namorados",
            # Lote 2 — mais datas comemorativas
            "dia dos pais", "ano novo", "halloween", "dia das crianças", "carnaval",
            # Lote 3 — moldes e papelaria
            "molde", "letras", "etiquetas", "alfabeto", "máscara",
            # Lote 4 — festa e itens de papelaria
            "bolo", "painel", "convite", "lembrança", "para imprimir",
            # Lote 5 — materiais e crafts
            "feltro", "eva", "cartão", "enfeite", "tag",
        ],
        "reddit_subs": ["brasil"],
        "reddit_queries": ["decoração festa", "molde páscoa", "decoração natal"],
        "youtube_queries": [
            "molde páscoa para imprimir",
            "decoração natal faça você mesmo",
            "como fazer painel de festa",
            "molde de letras para decoração",
            "festa junina decoração",
        ],
    },
    "pet": {
        "label": "Pet",
        "google_kw": [
            # Lote 1 — suplementos diretos (intenção de compra)
            "suplemento para cachorro", "vitamina para cachorro", "ômega 3 para cachorro", "probiótico para cachorro", "colágeno para cachorro",
            # Lote 2 — problemas que levam à busca por suplemento
            "cachorro perdendo pelo", "pelo opaco cachorro", "queda de pelo cachorro", "displasia em cachorro", "cachorro sem apetite",
            # Lote 3 — nutrição e alimentação natural
            "ração natural para cachorro", "dieta barf cachorro", "nutrição canina", "cálcio para cachorro", "proteína para cachorro",
            # Lote 4 — fases da vida e perfis específicos
            "suplemento para cachorro idoso", "suplemento para filhote de cachorro", "cachorro de grande porte alimentação", "como dar suplemento para cachorro", "cachorro pode tomar vitamina humana",
            # Lote 5 — saúde, imunidade e dúvidas educativas
            "articulação cachorro", "imunidade cachorro", "pelo bonito cachorro", "suplemento para cachorro vale a pena", "cachorro com diarreia crônica",
        ],
        "reddit_subs": ["brasil"],
        "reddit_queries": ["suplemento cachorro", "ração natural cachorro", "pelo cachorro"],
        "youtube_queries": [
            "suplemento para cachorro qual o melhor",
            "ração natural para cachorro receita completa",
            "como melhorar o pelo do cachorro",
            "suplemento para cachorro idoso",
            "dieta barf para cachorro iniciante",
        ],
    },
    "educacao": {
        "label": "Educação",
        # Seeds com volume comprovado — fonte: SEMrush educador.com.br
        "google_kw": [
            # Lote 1 — alfabetização (74k–33k)
            "atividades de alfabetização", "alfabeto para imprimir", "atividades educação infantil", "tabuada para imprimir", "ditado de palavras",
            # Lote 2 — português e matemática
            "atividade de português", "letras para imprimir", "atividade de matemática 1 ano", "plano de aula educação infantil", "interpretação de texto 5 ano",
            # Lote 3 — conteúdo escolar
            "atividades de matemática 3 ano", "contas de divisão", "numeros para imprimir", "caligrafia para imprimir", "atividade de artes",
            # Lote 4 — materiais visuais e relatórios
            "relatório educação infantil", "atividade alfabeto", "bandeira do brasil para colorir", "vogais para imprimir", "história para imprimir",
            # Lote 5 — disciplinas e métodos complementares
            "jogo educativo", "brincadeiras educação infantil", "ciências para imprimir", "exercícios de matemática", "plano de aula bncc",
        ],
        "reddit_subs": ["vestibular", "brasil"],
        "reddit_queries": ["educação infantil", "atividades para imprimir", "plano de aula"],
        "youtube_queries": [
            "atividades de alfabetização para imprimir",
            "tabuada para imprimir completa",
            "plano de aula educação infantil bncc",
            "atividades de matemática 1 ano",
            "ditado de palavras para crianças",
        ],
    },
}


def collect_google_trends(nicho_key: str, nicho_data: dict) -> dict:
    result = {"trending": [], "related_top": [], "related_rising": [], "seeds": []}
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

        # Salva ranking das seeds como referência interna (não exibido como variação)
        seeds_ranked = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)
        for kw, score in seeds_ranked:
            result["seeds"].append({"termo": kw, "valor": score})

        # ── Passo 2: related_queries para TODOS os seeds ─────────────────────
        # Máx 5 resultados por seed → garante variedade entre tópicos
        # (evita que um único assunto domine, ex: rosa do deserto em jardinagem)
        seeds_order = [kw for kw, _ in seeds_ranked] if seeds_ranked else all_kws
        seen_queries: set[str] = set()

        for kw in seeds_order:
            try:
                pt.build_payload([kw], geo="BR", timeframe="today 3-m")
                time.sleep(6)
                related = pt.related_queries()
                data_kw = related.get(kw, {})

                top_df = data_kw.get("top")
                rising_df = data_kw.get("rising")

                if top_df is not None and not top_df.empty:
                    for _, row in top_df.head(5).iterrows():
                        q = row["query"]
                        if q not in seen_queries:
                            seen_queries.add(q)
                            result["related_top"].append({
                                "termo": q,
                                "valor": int(row["value"]),
                                "base": kw,
                            })

                if rising_df is not None and not rising_df.empty:
                    for _, row in rising_df.head(3).iterrows():
                        q = row["query"]
                        if q not in seen_queries:
                            seen_queries.add(q)
                            result["related_rising"].append({
                                "termo": q,
                                "valor": str(row["value"]),
                                "base": kw,
                            })

                time.sleep(8)
            except Exception as e:
                log.warning(f"Google Trends related_queries '{kw}' [{nicho_key}]: {e}")
                time.sleep(15)

        log.info(
            f"Google Trends [{nicho_key}]: {len(result['seeds'])} seeds, "
            f"{len(result['related_top'])} variações, {len(result['related_rising'])} rising"
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
        "lista":      ["{n} ideias de {t} para fazer em casa (com molde grátis)",
                       "{n} modelos de {t} para imprimir e usar agora",
                       "{n} inspirações de {t} que todo mundo está buscando"],
        "como_fazer": ["Como fazer {t}: passo a passo fácil para iniciantes",
                       "{T}: como criar em casa sem gastar muito",
                       "Tudo sobre {t} em {ano}: moldes, ideias e tutoriais"],
        "tendencia":  ["Por que {t} está entre as buscas mais quentes do Brasil",
                       "{T}: as tendências que dominam em {ano}",
                       "{T} em {ano}: o que está em alta e como aproveitar"],
    },
    "educacao": {
        "lista":      ["{n} atividades de {t} para imprimir e usar em sala de aula",
                       "{n} ideias de {t} alinhadas à BNCC para educação infantil",
                       "{n} fichas de {t} prontas para baixar e aplicar hoje"],
        "como_fazer": ["Como trabalhar {t} em sala de aula: passo a passo completo",
                       "{T}: atividades práticas para educação infantil e fundamental",
                       "Plano de aula de {t}: modelo completo para {ano}"],
        "tendencia":  ["Por que {t} está entre as buscas mais quentes de professores",
                       "{T}: os materiais mais baixados por educadores em {ano}",
                       "{T} em {ano}: novidades, recursos e atividades atualizadas"],
    },
    "pet": {
        "lista":      ["{n} sinais de que seu cachorro precisa de {t}",
                       "{n} benefícios de {t} que todo tutor deveria conhecer",
                       "{n} dúvidas sobre {t} respondidas por veterinários"],
        "como_fazer": ["Como usar {t} no seu cachorro: guia completo para tutores",
                       "{T}: o que é, para que serve e como escolher o melhor",
                       "Tudo sobre {t}: dosagem, benefícios e cuidados em {ano}"],
        "tendencia":  ["Por que {t} está entre as buscas mais quentes de tutores de pets",
                       "{T}: o que os veterinários estão recomendando em {ano}",
                       "{T} em alta: como isso pode transformar a saúde do seu cachorro"],
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
    "pet":        ["Foto de cachorro real (não ilustração) aumenta CTR significativamente",
                   "Mencione raça ou porte no título quando possível — aumenta clique qualificado"],
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
        for item in gt.get("related_top", []):
            pool.append({"termo": item["termo"], "score": float(item.get("valor", 50))})
        for item in gt.get("related_rising", []):
            pool.append({"termo": item["termo"], "score": 65.0})  # rising = oportunidade
        for item in gt.get("seeds", []):
            pool.append({"termo": item["termo"], "score": float(item.get("valor", 10))})

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
