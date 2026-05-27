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
        # Cluster #1 em receita — RPM $1,82, 41% do tráfego do site
        # Prioridade: profundidade por ano escolar + bridge com necessidades especiais (RPM 3–5×)
        "label": "Alfabetização e Ed. Infantil",
        "google_kw": [
            # Lote 1 — alfabetização por ano escolar (variações da página #1 em ganho)
            "atividades de alfabetização 1 ano", "atividades de alfabetização 2 ano", "atividades de alfabetização 3 ano", "fichas de alfabetização para imprimir", "sílabas para imprimir",
            # Lote 2 — educação infantil por faixa etária (berçário → pré)
            "atividades para berçário para imprimir", "atividades para maternal 1 para imprimir", "atividades para maternal 2 para imprimir", "atividades para jardim para imprimir", "atividades para pré-escola para imprimir",
            # Lote 3 — bridge alfabetização + necessidades especiais (CPC alto: anunciantes de terapia)
            "atividades de alfabetização para crianças com dislexia", "atividades para criança com dificuldade de aprendizagem", "método fônico atividades para imprimir", "como ensinar a ler criança com dificuldade", "atividades de alfabetização para crianças com tdah",
            # Lote 4 — leitura e escrita complementares
            "atividades de leitura para imprimir", "atividades de escrita para imprimir", "vogais para imprimir", "alfabeto para imprimir", "caligrafia para imprimir",
            # Lote 5 — estimulação em casa (público pais — liga com nicho desenvolvimento)
            "como estimular a leitura em casa", "atividades de alfabetização em casa", "como ensinar a criança a ler em casa", "brincadeiras para alfabetização", "jogos de alfabetização para imprimir",
        ],
        "reddit_subs": ["brasil", "educacao"],
        "reddit_queries": ["alfabetização crianças", "atividades para imprimir", "educação infantil em casa"],
        "youtube_queries": [
            "atividades de alfabetização 1 ano para imprimir",
            "método fônico para crianças em casa",
            "atividades para maternal para imprimir",
            "como ensinar criança com dislexia a ler",
            "atividades de alfabetização para crianças com tdah",
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
        # Dois clusters: gestão escolar (RPM $6,92 — mais alto do nicho) + matemática por ano
        "label": "Matemática e Gestão Escolar",
        "google_kw": [
            # Lote 1 — gestão escolar (RPM alto: coordenadores compram software/serviços)
            "boletim escolar para imprimir", "ficha de avaliação educação infantil", "plano de aula pronto para imprimir", "diário de classe para imprimir", "relatório descritivo do aluno",
            # Lote 2 — documentos pedagógicos (mesmo público de gestão)
            "ata de reunião de pais e mestres", "plano de aula bncc educação infantil", "ficha de observação do aluno", "portfólio educação infantil", "relatório individual de aluno educação infantil",
            # Lote 3 — matemática anos iniciais (1°, 2°, 3° — RPM $0,87, alto volume)
            "atividades de matemática 1 ano para imprimir", "atividades de matemática 2 ano para imprimir", "atividades de matemática 3 ano para imprimir", "tabuada para imprimir", "contas de adição para imprimir",
            # Lote 4 — matemática anos finais + operações
            "atividades de matemática 4 ano para imprimir", "atividades de matemática 5 ano para imprimir", "contas de subtração para imprimir", "contas de multiplicação para imprimir", "contas de divisão para imprimir",
            # Lote 5 — outras disciplinas + projetos escolares
            "atividades de ciências para imprimir", "atividades de história para imprimir", "maquete do sistema solar como fazer", "projetos escolares ensino fundamental", "atividades de artes para imprimir",
        ],
        "reddit_subs": ["brasil", "educacao"],
        "reddit_queries": ["plano de aula", "atividades de matemática para imprimir", "gestão escolar"],
        "youtube_queries": [
            "como fazer boletim escolar online",
            "tabuada para imprimir completa",
            "atividades de matemática 1 ano para imprimir",
            "plano de aula bncc educação infantil pronto",
            "maquete do sistema solar passo a passo",
        ],
    },
    "desenvolvimento": {
        "label": "Desenvolvimento Infantil",
        "google_kw": [
            # Lote 1 — neurodiversidade (alto CPC: anunciantes de terapia, neuropsicologia)
            "tdah em crianças", "atividades para criança com tdah", "sinais de autismo em crianças", "como ajudar criança autista em casa", "dislexia em crianças",
            # Lote 2 — fala e linguagem (fonoaudiologia, apps de fala, terapia)
            "atraso na fala", "criança não fala 2 anos", "como estimular a fala da criança", "desenvolvimento da linguagem infantil", "fonoaudiologia infantil",
            # Lote 3 — marcos e estimulação precoce (pediatria, cursos de mãe)
            "estimulação precoce", "marcos do desenvolvimento infantil", "como estimular bebê em casa", "desenvolvimento motor infantil", "desenvolvimento cognitivo infantil",
            # Lote 4 — comportamento e criação (terapia comportamental, cursos para pais)
            "birra infantil como lidar", "ansiedade em crianças", "como colocar limites nos filhos", "criança hiperativa o que fazer", "choro excessivo bebê",
            # Lote 5 — atividades e recursos para pais (brinquedos, apps, cursos)
            "brinquedos educativos para crianças", "atividades montessori em casa", "como brincar com bebê", "atividades para estimular criança em casa", "método montessori",
        ],
        "reddit_subs": ["brasil", "maternidade"],
        "reddit_queries": ["desenvolvimento infantil", "tdah crianças", "estimulação bebê"],
        "youtube_queries": [
            "atividades para criança com tdah em casa",
            "estimulação precoce para bebês",
            "como lidar com birra infantil",
            "desenvolvimento da fala em crianças",
            "método montessori em casa para iniciantes",
        ],
    },
    "concursos": {
        "label": "Concursos e Formação Docente",
        # ~50 mil vagas abertas em 2026 — anunciantes: Gran Cursos, Estratégia, TEC, QConcursos (CPC R$5–15)
        # + cursos EAD gratuitos (Univesp, IFs) — anunciante: EdTech pago que compete com o gratuito
        "google_kw": [
            # Lote 1 — editais abertos 2026 (buscas de quem está se inscrevendo agora)
            "concurso público professor 2026", "edital concurso professor 2026", "concurso professor municipal 2026", "processo seletivo professor 2026", "concurso prefeitura professor",
            # Lote 2 — preparação e prova didática (liga com conteúdo já existente no site)
            "plano de aula para concurso professor", "prova didática concurso professor", "como fazer plano de aula para concurso", "BNCC para concurso de professor", "legislação educacional concurso professor",
            # Lote 3 — estudo e aprovação
            "como passar em concurso de professor", "questões de concurso professor pedagogia", "apostila concurso professor", "simulado concurso professor pedagogia", "concurso professor educação infantil",
            # Lote 4 — cursos EAD gratuitos para professores (infoeducacao.com.br — alto volume)
            "curso EAD gratuito para professores", "especialização gratuita para professores", "curso gratuito com certificado para professores", "pós-graduação gratuita para professores", "especialização EAD gratuita pedagogia",
            # Lote 5 — formação continuada e desenvolvimento profissional
            "curso de psicopedagogia gratuito", "formação continuada professores", "curso de especialização em educação infantil", "curso livre para professores online", "como obter certificado horas complementares",
        ],
        "reddit_subs": ["brasil", "concursospublicos"],
        "reddit_queries": ["concurso professor 2026", "curso gratuito professor", "especialização EAD pedagogia"],
        "youtube_queries": [
            "como fazer plano de aula para concurso público professor",
            "prova didática concurso professor passo a passo",
            "curso EAD gratuito para professores 2026",
            "BNCC para concurso de professor",
            "especialização gratuita educação infantil",
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
                pt.build_payload(lote, geo="BR", timeframe="today 1-m")
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

        seeds_set = set(all_kws)

        for kw in seeds_order:
            try:
                pt.build_payload([kw], geo="BR", timeframe="now 7-d")
                time.sleep(6)
                related = pt.related_queries()
                data_kw = related.get(kw, {})

                top_df = data_kw.get("top")
                rising_df = data_kw.get("rising")

                if top_df is not None and not top_df.empty:
                    for _, row in top_df.head(5).iterrows():
                        q = row["query"]
                        if q not in seen_queries and q not in seeds_set:
                            seen_queries.add(q)
                            result["related_top"].append({
                                "termo": q,
                                "valor": int(row["value"]),
                                "base": kw,
                            })

                if rising_df is not None and not rising_df.empty:
                    for _, row in rising_df.head(3).iterrows():
                        q = row["query"]
                        if q not in seen_queries and q not in seeds_set:
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
        "lista":      ["{T} para imprimir: {n} fichas prontas para usar hoje",
                       "{n} atividades de {t} por nível — do mais fácil ao mais avançado",
                       "{n} fichas de {t} alinhadas à BNCC (baixe grátis em PDF)"],
        "como_fazer": ["Como trabalhar {t} em casa: guia passo a passo para pais e professores",
                       "{T}: atividades práticas para cada fase do aprendizado",
                       "Como ajudar a criança com dificuldade em {t}: dicas comprovadas em {ano}"],
        "tendencia":  ["Por que {t} está entre as buscas mais quentes de pais e professores",
                       "{T} em {ano}: novos recursos, fichas e o que os especialistas recomendam",
                       "{T}: o que mudou na abordagem pedagógica e como aplicar hoje"],
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
        "lista":      ["{T} para imprimir: {n} modelos prontos para usar hoje",
                       "{n} atividades de {t} por ano escolar — do 1° ao 5° ano",
                       "{n} recursos de {t} que todo professor precisa ter em {ano}"],
        "como_fazer": ["Como criar {t} do zero: modelo completo e editável",
                       "{T}: passo a passo para professores e coordenadores",
                       "Tudo sobre {t} em {ano}: modelos, exemplos e como aplicar na prática"],
        "tendencia":  ["Por que {t} está entre os materiais mais baixados por educadores",
                       "{T}: o recurso que escolas inteiras adotaram em {ano}",
                       "{T} em {ano}: o que mudou e os melhores modelos atualizados"],
    },
    "desenvolvimento": {
        "lista":      ["{n} sinais de {t} que todo pai precisa conhecer",
                       "{n} atividades para estimular {t} em casa (sem precisar de terapeuta)",
                       "{n} formas de ajudar seu filho com {t} a partir de hoje"],
        "como_fazer": ["Como ajudar seu filho com {t}: guia completo para pais",
                       "{T}: o que é, como identificar e o que fazer em {ano}",
                       "Como estimular {t} no seu filho: passo a passo para pais"],
        "tendencia":  ["Por que cada vez mais pais estão buscando sobre {t}",
                       "{T}: o que as pesquisas mais recentes dizem em {ano}",
                       "{T} em {ano}: novas descobertas e como isso afeta seu filho"],
    },
    "concursos": {
        "lista":      ["{n} concursos para professores com inscrições abertas em {ano}",
                       "{n} dicas para passar na prova didática de concurso público",
                       "{n} editais de concurso professor que você não pode perder em {ano}"],
        "como_fazer": ["Como montar plano de aula para concurso público: modelo completo {ano}",
                       "{T}: como se preparar e o que cai na prova em {ano}",
                       "Como se inscrever em concurso para professor: passo a passo completo"],
        "tendencia":  ["Por que o concurso de professor em {t} está movimentando educadores em {ano}",
                       "{T}: edital aberto e o que você precisa saber antes de se inscrever",
                       "{T} em {ano}: vagas, salário e como se preparar em tempo recorde"],
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
    "atividades": ["Mencione o ano escolar no título (ex: '1° ano') — filtra tráfego qualificado",
                   "Adicione 'para imprimir' ou 'em PDF' no título — dobra CTR neste nicho"],
    "jardinagem": ["Foto do resultado final (planta/jardim bonito) gera mais cliques",
                   "Inclua custo estimado (ex: 'por menos de R$30') — alto CTR"],
    "decoracao":  ["Imagem antes/depois tem CTR 40% maior no Discover",
                   "Mostre ambiente real, não renderização — mais engajamento"],
    "educacao":   ["Para gestão escolar: mencione 'editável' ou 'pronto para preencher' no título — RPM mais alto",
                   "Para matemática: mencione o ano escolar e 'para imprimir' — busca muito específica"],
    "pet":        ["Foto de cachorro real (não ilustração) aumenta CTR significativamente",
                   "Mencione raça ou porte no título quando possível — aumenta clique qualificado"],
    "desenvolvimento": ["Foto real de pai/mãe com filho tem CTR maior que ilustração",
                        "Mencione a faixa etária no título — pais buscam por idade específica do filho"],
    "concursos":    ["Mencione o estado ou cidade no título quando houver edital específico aberto",
                     "Inclua o ano no título — candidatos buscam informação atualizada",
                     "Artigos sobre prova didática têm RPM alto (anunciante = curso preparatório)"],
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


SITES_REFERENCIA = [
    {
        "nome": "InfoEducação",
        "feed": "https://infoeducacao.com.br/feed/",
        "url":  "https://infoeducacao.com.br",
        "foco": "Cursos EAD gratuitos e especializações para professores",
    },
    {
        "nome": "PEBSP",
        "feed": "https://www.pebsp.com/feed/",
        "url":  "https://www.pebsp.com",
        "foco": "Concursos e processos seletivos para professores de SP",
    },
    {
        "nome": "Conecta Professores",
        "feed": "https://conectaprofessores.com/feed/",
        "url":  "https://conectaprofessores.com",
        "foco": "Oportunidades, cursos gratuitos e recursos para professores",
    },
]


def collect_site_updates() -> list[dict]:
    import urllib.request
    import xml.etree.ElementTree as ET
    import re

    articles = []
    for source in SITES_REFERENCIA:
        try:
            req = urllib.request.Request(
                source["feed"],
                headers={"User-Agent": "Mozilla/5.0 (compatible; TrendBot/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
            root = ET.fromstring(content)
            channel = root.find("channel")
            if channel is None:
                continue
            for item in channel.findall("item")[:8]:
                title = (item.findtext("title") or "").strip()
                link  = (item.findtext("link")  or "").strip()
                pub   = (item.findtext("pubDate") or "").strip()
                desc  = (item.findtext("description") or "").strip()
                desc  = re.sub(r"<[^>]+>", " ", desc)
                desc  = re.sub(r"\s+", " ", desc).strip()[:200]
                if title and link:
                    articles.append({
                        "fonte": source["nome"],
                        "foco":  source["foco"],
                        "titulo": title,
                        "url":    link,
                        "data":   pub,
                        "resumo": desc,
                    })
            log.info(f"Site updates [{source['nome']}]: {len([a for a in articles if a['fonte'] == source['nome']])} artigos")
        except Exception as e:
            log.warning(f"Site updates [{source['nome']}]: {e}")

    return articles


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Sobrescreve dados do dia mesmo que já existam")
    args = parser.parse_args()

    today = date.today().isoformat()
    output_file = DATA_DIR / f"{today}.json"

    if output_file.exists() and not args.force:
        log.info(f"Dados de {today} já existem. Use --force para sobrescrever.")
        return

    log.info(f"Iniciando coleta para {today}")

    result = {
        "date": today,
        "collected_at": datetime.utcnow().isoformat(),
        "nichos": {},
        "site_updates": [],
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
    result["site_updates"] = collect_site_updates()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info(f"Salvo em {output_file}")


if __name__ == "__main__":
    main()
