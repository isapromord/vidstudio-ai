import statistics
import os
import json
import uuid
import yt_dlp

RADAR_DB_PATH = os.path.join(os.path.dirname(__file__), "radar_competitors.json")

INITIAL_RADAR_CHANNELS = {
    "@CaminoImplacable": {
        "handle": "@CaminoImplacable",
        "channel_title": "Camino Implacable",
        "channel_url": "https://www.youtube.com/@CaminoImplacable/videos",
        "niche": "Psicología Oscura & Manipulación",
        "baseline_views": 85000,
        "last_scanned": "En Vivo",
        "videos": [
            {
                "id": "FrnvSaw9qSY",
                "title": "☣⛔ DARK PSYCHOLOGY | Las 10 TÉCNICAS de Obsesión Psicológica",
                "url": "https://www.youtube.com/watch?v=FrnvSaw9qSY",
                "view_count": 2503300,
                "duration": "14:20",
                "published": "Viral",
                "thumbnail": "https://i.ytimg.com/vi/FrnvSaw9qSY/hqdefault.jpg",
                "outlier_ratio": 29.45,
                "is_outlier": True,
                "velocity_label": "🔥 29.5x Anomalía Viral"
            },
            {
                "id": "LBHirMUd6kM",
                "title": "DARK PSYCHOLOGY | Las 5 Técnicas Más Efectivas de Manipulación",
                "url": "https://www.youtube.com/watch?v=LBHirMUd6kM",
                "view_count": 465200,
                "duration": "11:15",
                "published": "Viral",
                "thumbnail": "https://i.ytimg.com/vi/LBHirMUd6kM/hqdefault.jpg",
                "outlier_ratio": 5.47,
                "is_outlier": True,
                "velocity_label": "🔥 5.5x Anomalía Viral"
            }
        ]
    },
    "@MundoEstoico": {
        "handle": "@MundoEstoico",
        "channel_title": "Mundo Estoico",
        "channel_url": "https://www.youtube.com/@MundoEstoico/videos",
        "niche": "Filosofía Estoica & Autocontrol",
        "baseline_views": 45000,
        "last_scanned": "En Vivo",
        "videos": [
            {
                "id": "5xBON9PTLEw",
                "title": "La CLAVE para que NADA ni NADIE vuelva a MOLESTARTE (Marco Aurelio)",
                "url": "https://www.youtube.com/watch?v=5xBON9PTLEw",
                "view_count": 908900,
                "duration": "16:40",
                "published": "Viral",
                "thumbnail": "https://i.ytimg.com/vi/5xBON9PTLEw/hqdefault.jpg",
                "outlier_ratio": 20.2,
                "is_outlier": True,
                "velocity_label": "🔥 20.2x Anomalía Viral"
            }
        ]
    },
    "@Inviertenti": {
        "handle": "@Inviertenti",
        "channel_title": "Invierte En Ti",
        "channel_url": "https://www.youtube.com/@Inviertenti/videos",
        "niche": "Desarrollo Personal & Mentalidad",
        "baseline_views": 42000,
        "last_scanned": "En Vivo",
        "videos": [
            {
                "id": "XDnq3BJ6ug4",
                "title": "El Arte de Pasar Desapercibido: Por Qué los Más Inteligentes Callan",
                "url": "https://www.youtube.com/watch?v=XDnq3BJ6ug4",
                "view_count": 189000,
                "duration": "12:45",
                "published": "Viral",
                "thumbnail": "https://i.ytimg.com/vi/XDnq3BJ6ug4/hqdefault.jpg",
                "outlier_ratio": 4.5,
                "is_outlier": True,
                "velocity_label": "🔥 4.5x Anomalía Viral"
            }
        ]
    }
}

HOT_NICHE_PRESETS = {
    "psicologia_oscura": {
        "name": "Psicología Oscura & Manipulación",
        "query": "psicologia oscura manipulacion lenguaje corporal",
        "niche_tag": "Psicología Oscura"
    },
    "estoicismo": {
        "name": "Estoicismo & Fortaleza Mental",
        "query": "estoicismo marco aurelio fortaleza mental disciplina",
        "niche_tag": "Estoicismo"
    },
    "leyes_poder": {
        "name": "Leyes del Poder & Seducción",
        "query": "48 leyes del poder maquiavelo psicologia seduccion",
        "niche_tag": "Poder & Estrategia"
    },
    "casos_misterio": {
        "name": "Misterio & Casos Psicológicos Reales",
        "query": "misterio psicologia criminal casos reales perturbadores",
        "niche_tag": "Misterio & Crimen"
    },
    "dinero_habitos": {
        "name": "Psicología del Dinero & Hábitos",
        "query": "psicologia del dinero habitos riqueza mentalidad",
        "niche_tag": "Dinero & Riqueza"
    }
}

def load_radar_db():
    if not os.path.exists(RADAR_DB_PATH):
        save_radar_db(INITIAL_RADAR_CHANNELS)
        return INITIAL_RADAR_CHANNELS
    try:
        with open(RADAR_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Sanitizar estrictamente: Solo mantener canales de verdad (no textos de búsqueda de tema)
            cleaned = {}
            for k, v in data.items():
                if k.startswith("@") and not any(k.startswith(p) for p in ["@psicologia", "@misterio", "@estoicismo", "@dinero"]):
                    cleaned[k] = v
            if not cleaned:
                cleaned = INITIAL_RADAR_CHANNELS
                save_radar_db(cleaned)
            return cleaned
    except Exception:
        return INITIAL_RADAR_CHANNELS

def save_radar_db(data):
    with open(RADAR_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def search_topic_outliers(query_text: str, niche_tag: str = "Exploración en Vivo"):
    """
    Busca videos REALES de YouTube para un tema.
    Extrae los CANALES REALES de los creadores y los registra como canales monitoreados,
    calculando anomalías virales sobre datos auténticos de YouTube.
    """
    clean_query = query_text.strip()
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch12',
        'noplaylist': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(f"ytsearch12:{clean_query}", download=False)
            entries = res.get('entries', []) or []
    except Exception as e:
        print("yt-dlp topic search error:", e)
        entries = []

    if not entries:
        return None

    db = load_radar_db()
    view_counts = [int(e.get('view_count') or 0) for e in entries if e]
    global_baseline = int(statistics.median(view_counts)) if view_counts else 35000
    if global_baseline < 1000:
        global_baseline = 35000

    # Agrupar videos por su CANAL REAL DE YOUTUBE
    channels_map = {}
    for e in entries:
        if not e: continue
        ch_name = e.get('channel') or e.get('uploader') or "Creador Destacado"
        ch_handle = f"@{ch_name.replace(' ', '')}"[:24]

        vid_id = e.get('id') or str(uuid.uuid4())[:8]
        v_url = e.get('url') or f"https://www.youtube.com/watch?v={vid_id}"
        if not v_url.startswith("http"):
            v_url = f"https://www.youtube.com/watch?v={v_url}"

        vc = int(e.get('view_count') or 0)
        dur_sec = e.get('duration') or 600
        mins = int(dur_sec // 60)
        secs = int(dur_sec % 60)
        dur_str = f"{mins}:{secs:02d}"

        thumbs = e.get('thumbnails') or []
        thumb_url = thumbs[-1].get('url') if thumbs else f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"

        ratio = round(vc / max(global_baseline, 1), 2)
        is_outlier = ratio >= 1.5

        video_obj = {
            "id": vid_id,
            "title": e.get('title') or "Video sin título",
            "url": v_url,
            "view_count": vc,
            "duration": dur_str,
            "published": "Tendencia",
            "thumbnail": thumb_url,
            "outlier_ratio": ratio,
            "is_outlier": is_outlier,
            "velocity_label": f"🔥 {ratio}x Viral" if is_outlier else f"{ratio}x Baseline"
        }

        if ch_handle not in channels_map:
            channels_map[ch_handle] = {
                "handle": ch_handle,
                "channel_title": ch_name,
                "channel_url": f"https://www.youtube.com/results?search_query={ch_name.replace(' ', '+')}",
                "niche": niche_tag,
                "baseline_views": global_baseline,
                "last_scanned": "En Vivo",
                "videos": []
            }
        channels_map[ch_handle]["videos"].append(video_obj)

    # Añadir los 3 principales canales descubiertos a la base de datos viva
    for ch_h, ch_data in list(channels_map.items())[:3]:
        ch_data["videos"].sort(key=lambda x: x["outlier_ratio"], reverse=True)
        db[ch_h] = ch_data

    save_radar_db(db)
    
    # Retornar el canal más representativo
    top_channel_handle = list(channels_map.keys())[0] if channels_map else "@CaminoImplacable"
    return db.get(top_channel_handle, list(db.values())[0])

def scan_competitor_channel(channel_input: str):
    """
    Inteligente:
    - Si es tema (más de 2 palabras y sin @ ni .com): Ejecuta búsqueda real en YouTube
      y extrae los canales auténticos de los creadores.
    - Si es @handle o URL: Escanea ese canal específico.
    """
    clean_input = channel_input.strip()
    is_phrase = len(clean_input.split()) >= 2 and not clean_input.startswith("@") and "youtube.com" not in clean_input and "youtu.be" not in clean_input

    if is_phrase:
        return search_topic_outliers(clean_input, niche_tag="Nicho en Tendencia")

    clean_url = clean_input.rstrip('/')
    if clean_url.endswith('/videos'):
        clean_url = clean_url[:-7].rstrip('/')

    if clean_url.startswith("@"):
        handle = clean_url
        channel_url = f"https://www.youtube.com/{handle}/videos"
    elif "youtube.com" in clean_url:
        part = clean_url.split("/")[-1]
        handle = part if part.startswith("@") else f"@{part}"
        channel_url = f"https://www.youtube.com/{handle}/videos"
    else:
        handle = f"@{clean_input}"
        channel_url = f"https://www.youtube.com/{handle}/videos"

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'no_warnings': True,
        'playlist_end': 12
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            res = ydl.extract_info(channel_url, download=False)
            channel_title = res.get('channel') or res.get('uploader') or res.get('title') or handle
            entries = res.get('entries', []) or []
    except Exception as e:
        print("yt-dlp channel scan warning:", e)
        return search_topic_outliers(clean_input, niche_tag="Canal sugerido")

    processed_videos = []
    view_counts = []

    for idx, e in enumerate(entries):
        if not e: continue
        title = e.get('title') or "Video sin título"
        v_url = e.get('url')
        if v_url and not v_url.startswith("http"):
            v_url = f"https://www.youtube.com/watch?v={v_url}"
        elif not v_url and e.get('id'):
            v_url = f"https://www.youtube.com/watch?v={e['id']}"
        
        vc = int(e.get('view_count') or 0)
        view_counts.append(vc)

        dur_sec = e.get('duration') or 600
        mins = int(dur_sec // 60)
        secs = int(dur_sec % 60)
        dur_str = f"{mins}:{secs:02d}"

        thumbs = e.get('thumbnails') or []
        thumb_url = thumbs[-1].get('url') if thumbs else (f"https://i.ytimg.com/vi/{e.get('id', '')}/hqdefault.jpg" if e.get('id') else "")

        processed_videos.append({
            "id": e.get('id') or str(uuid.uuid4())[:8],
            "title": title,
            "url": v_url or "https://www.youtube.com",
            "view_count": vc,
            "duration": dur_str,
            "published": "Reciente",
            "thumbnail": thumb_url,
            "outlier_ratio": 1.0,
            "is_outlier": False,
            "velocity_label": "1.0x Normal"
        })

    valid_counts = [c for c in view_counts if c > 0]
    baseline = int(statistics.median(valid_counts)) if valid_counts else 1000

    for v in processed_videos:
        ratio = round(v["view_count"] / max(baseline, 1), 2)
        v["outlier_ratio"] = ratio
        if ratio >= 2.0:
            v["is_outlier"] = True
            v["velocity_label"] = f"🔥 {ratio}x Anomalía Viral"
        else:
            v["is_outlier"] = False
            v["velocity_label"] = f"{ratio}x Baseline"

    processed_videos.sort(key=lambda x: x["outlier_ratio"], reverse=True)

    db = load_radar_db()
    if not processed_videos and handle in db:
        return db[handle]

    channel_data = {
        "handle": handle,
        "channel_title": channel_title,
        "channel_url": channel_url,
        "niche": "Análisis Competitivo",
        "baseline_views": baseline,
        "last_scanned": "En Vivo",
        "videos": processed_videos
    }

    db[handle] = channel_data
    save_radar_db(db)
    return channel_data
