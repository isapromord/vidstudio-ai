import os
import sys
import uuid
import asyncio
import zipfile
import json
import re
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import engine
import research_engine
import brainstorm_engine
import radar_engine
import clipper_engine
import vfx_engine

app = FastAPI(title="VidStudio AI - Next-Gen Video Production & Outlier Suite")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

TASKS_DB = {}

class AnalyzeRequest(BaseModel):
    video_url: str
    custom_views: Optional[int] = None

class RenderRequest(BaseModel):
    script_text: str
    voice_name: str = "es-US-AlonsoNeural"
    title: str = "Regla de Oro"
    brand_id: str = "la_mente_observadora"
    language: str = "es"

class ThumbnailRequest(BaseModel):
    title: str = "EL PODER DEL SILENCIO"
    highlight_word: str = "SILENCIO"
    aspect_ratio: str = "9:16"
    brand_id: str = "la_mente_observadora"

class RepurposeRequest(BaseModel):
    video_url: str
    crop_mode: str = "auto"
    custom_notes: str = ""
    brand_id: str = "la_mente_observadora"

class ResearchRequest(BaseModel):
    niche_topic: str

class BrandNamesRequest(BaseModel):
    niche_topic: str
    word_limit: int = 0

class BrandSaveRequest(BaseModel):
    name: str
    handle: str
    niche: str
    archetype: str
    thesis: str
    colors: dict
    voice: dict
    flow_rules: str

class BrainstormMessageRequest(BaseModel):
    history: list = []
    message: str
    brand_id: str = "la_mente_observadora"

class ExportZipRequest(BaseModel):
    task_id: Optional[str] = None
    title: str = "Video_Viral"
    script_text: str = ""
    script_en: Optional[str] = ""
    language: str = "es"
    replica_prompts: list = []
    flow_rule: str = ""
    metadata: dict = {}
    thumb_title: str = ""
    brand_id: str = "la_mente_observadora"

class VoiceSynthesizeRequest(BaseModel):
    script_text: str
    voice_name: str = "en-US-AndrewNeural"
    language: str = "en"

class RadarScanRequest(BaseModel):
    channel_input: str

@app.get("/")
def get_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "VidStudio AI Backend Running"}

# --- RUTAS DE DECONSTRUCCIÓN Y ANÁLISIS 1 A 1 ---

@app.post("/api/analyze")
def analyze_video(req: AnalyzeRequest):
    if not req.video_url:
        raise HTTPException(status_code=400, detail="URL no válida")
    
    data = engine.extract_youtube_info_advanced(req.video_url, custom_views=req.custom_views)
    return {
        "status": "success",
        "analysis": data
    }

# --- RUTAS DE BRAINSTORMING & CO-CREACIÓN DE SERIES ---

@app.post("/api/brainstorm")
@app.post("/api/brainstorm/chat")
def brainstorm_turn(req: BrainstormMessageRequest):
    brands = research_engine.load_brands()
    active_brand = brands.get(req.brand_id, brands.get("la_mente_observadora", {}))
    res = brainstorm_engine.brainstorm_chat_turn(req.history, req.message, active_brand)
    return {"status": "success", "result": res}

# --- RUTAS DE INCUBADORA DE CANALES & RESEARCH REAL ---

@app.get("/api/brands")
def get_saved_brands():
    return research_engine.load_brands()

@app.post("/api/brands/save")
def save_new_brand(req: BrandSaveRequest):
    saved = research_engine.save_brand(req.dict())
    return {"status": "success", "brand": saved}

@app.post("/api/brand/generate-names")
def generate_more_brand_names(req: BrandNamesRequest):
    if not req.niche_topic.strip():
        raise HTTPException(status_code=400, detail="Debes especificar un nicho o temática.")
    res = research_engine.generate_ai_brand_names(req.niche_topic, word_limit=req.word_limit)
    return {
        "status": "success",
        "result": res
    }

@app.post("/api/research")
def conduct_niche_research(req: ResearchRequest):
    if not req.niche_topic.strip():
        raise HTTPException(status_code=400, detail="Debes especificar un nicho o temática.")
    
    deep_data = research_engine.research_niche_deep(req.niche_topic)
    proposal = research_engine.generate_interactive_brand_proposal(req.niche_topic)
    
    return {
        "status": "success",
        "research": deep_data,
        "proposal": proposal
    }

@app.post("/api/repurpose")
def repurpose_long_video(req: RepurposeRequest):
    if not req.video_url:
        raise HTTPException(status_code=400, detail="URL no válida")
    
    brands = research_engine.load_brands()
    active_brand = brands.get(req.brand_id, brands.get("la_mente_observadora", {}))
    brand_name = active_brand.get("name", "La Mente Observadora")

    res = clipper_engine.extract_and_cut_shorts(req.video_url, brand_name=brand_name, crop_mode=req.crop_mode)
    return res

async def process_video_pipeline(task_id: str, script_text: str, voice_name: str, title: str, language: str = "es"):
    try:
        TASKS_DB[task_id]["status"] = "generating_audio"
        TASKS_DB[task_id]["progress"] = 25
        
        wav_file = os.path.join(OUTPUT_DIR, f"{task_id}_voice.wav")
        ass_file = os.path.join(OUTPUT_DIR, f"{task_id}_subtitles.ass")
        srt_file = os.path.join(OUTPUT_DIR, f"{task_id}_subtitles.srt")
        mp4_file = os.path.join(OUTPUT_DIR, f"{task_id}_final.mp4")
        cover_file = os.path.join(OUTPUT_DIR, f"{task_id}_cover.jpg")
        
        # 1. Audio
        await engine.synthesize_voice(script_text, wav_file, voice=voice_name)
        
        # 2. Whisper
        TASKS_DB[task_id]["status"] = "syncing_subtitles"
        TASKS_DB[task_id]["progress"] = 55
        await asyncio.to_thread(engine.generate_subtitles_whisper, wav_file, ass_file, srt_path=srt_file, language=language)
        
        # 3. FFmpeg
        TASKS_DB[task_id]["status"] = "rendering_video"
        TASKS_DB[task_id]["progress"] = 75
        
        video_loop = os.path.join(ASSETS_DIR, "bg_loop.mp4")
        bg_music = os.path.join(ASSETS_DIR, "bg_music.mp3")
        sfx_boom = os.path.join(ASSETS_DIR, "sfx_boom.mp3")
        
        await asyncio.to_thread(engine.assemble_final_video, video_loop, wav_file, bg_music, sfx_boom, ass_file, mp4_file)
        
        # 4. Portada
        await asyncio.to_thread(engine.generate_cover_thumbnail, title, cover_file)
        
        TASKS_DB[task_id]["status"] = "completed"
        TASKS_DB[task_id]["progress"] = 100
        TASKS_DB[task_id]["video_url"] = f"/output/{task_id}_final.mp4"
        TASKS_DB[task_id]["audio_url"] = f"/output/{task_id}_voice.wav"
        TASKS_DB[task_id]["srt_url"] = f"/output/{task_id}_subtitles.srt"
        TASKS_DB[task_id]["cover_url"] = f"/output/{task_id}_cover.jpg"
        
    except Exception as e:
        TASKS_DB[task_id]["status"] = "failed"
        TASKS_DB[task_id]["error"] = str(e)

@app.post("/api/voice/synthesize")
async def synthesize_voice_track(req: VoiceSynthesizeRequest):
    uid = str(uuid.uuid4())[:8]
    out_wav = os.path.join(OUTPUT_DIR, f"voice_{uid}.wav")
    await engine.synthesize_voice(req.script_text, out_wav, voice=req.voice_name)
    dur = clipper_engine.get_video_duration(out_wav)
    return {
        "status": "success",
        "audio_url": f"/output/voice_{uid}.wav",
        "duration": round(dur, 1),
        "voice_name": req.voice_name,
        "language": req.language
    }

@app.post("/api/render")
async def start_render(req: RenderRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    TASKS_DB[task_id] = {
        "status": "queued",
        "progress": 5,
        "title": req.title
    }
    background_tasks.add_task(process_video_pipeline, task_id, req.script_text, req.voice_name, req.title, req.language)
    return {"status": "started", "task_id": task_id}

@app.post("/api/thumbnail/generate")
def create_custom_thumbnail(req: ThumbnailRequest):
    brands = research_engine.load_brands()
    active_brand = brands.get(req.brand_id, brands.get("la_mente_observadora", {}))
    brand_name = active_brand.get("name", "LA MENTE OBSERVADORA")
    
    thumb_id = str(uuid.uuid4())[:8]
    filename = f"thumb_{thumb_id}.jpg"
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    res = engine.generate_advanced_thumbnail(
        title=req.title,
        highlight_word=req.highlight_word,
        aspect_ratio=req.aspect_ratio,
        brand_name=brand_name,
        output_path=output_path
    )
    return {
        "status": "success",
        "thumbnail_url": f"/output/{filename}",
        "flow_prompt": res.get("flow_prompt", ""),
        "aspect_ratio": req.aspect_ratio
    }

@app.post("/api/thumbnail/ab-variants")
def create_ab_thumbnail_variants(req: ThumbnailRequest):
    brands = research_engine.load_brands()
    active_brand = brands.get(req.brand_id, brands.get("la_mente_observadora", {}))
    brand_name = active_brand.get("name", "LA MENTE OBSERVADORA")
    
    variants = engine.generate_ab_thumbnails(
        title=req.title,
        highlight_word=req.highlight_word,
        brand_name=brand_name,
        aspect_ratio=req.aspect_ratio
    )
    return {
        "status": "success",
        "aspect_ratio": req.aspect_ratio,
        "variants": variants
    }

@app.get("/api/radar/channels")
def get_radar_channels():
    return radar_engine.load_radar_db()

@app.get("/api/radar/presets")
def get_radar_presets():
    return radar_engine.HOT_NICHE_PRESETS

@app.post("/api/radar/scan")
def scan_radar_channel(req: RadarScanRequest):
    if not req.channel_input.strip():
        raise HTTPException(status_code=400, detail="Debes especificar un canal o URL de YouTube.")
    res = radar_engine.scan_competitor_channel(req.channel_input)
    return {
        "status": "success",
        "channel": res
    }

@app.post("/api/export/zip")
def export_production_kit(req: ExportZipRequest):
    safe_title = re.sub(r'[^\w\s-]', '', req.title).strip().replace(' ', '_')[:28] or "Proyecto_Viral"
    zip_filename = f"Kit_{safe_title}_{str(uuid.uuid4())[:6]}.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_filename)

    task_wav = os.path.join(OUTPUT_DIR, f"{req.task_id}_voice.wav") if req.task_id else None
    task_srt = os.path.join(OUTPUT_DIR, f"{req.task_id}_subtitles.srt") if req.task_id else None
    task_ass = os.path.join(OUTPUT_DIR, f"{req.task_id}_subtitles.ass") if req.task_id else None
    task_mp4 = os.path.join(OUTPUT_DIR, f"{req.task_id}_final.mp4") if req.task_id else None

    thumb_169_path = os.path.join(OUTPUT_DIR, f"temp_169_{safe_title}.jpg")
    thumb_916_path = os.path.join(OUTPUT_DIR, f"temp_916_{safe_title}.jpg")

    try:
        engine.generate_advanced_thumbnail(title=req.thumb_title or req.title, aspect_ratio="16:9", output_path=thumb_169_path)
    except: pass
    try:
        engine.generate_advanced_thumbnail(title=req.thumb_title or req.title, aspect_ratio="9:16", output_path=thumb_916_path)
    except: pass

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        if task_wav and os.path.exists(task_wav):
            z.write(task_wav, "01_AUDIO/voz_master_16k.wav")
        
        if task_srt and os.path.exists(task_srt):
            z.write(task_srt, "02_SUBTITULOS/subtitulos_universal.srt")
        if task_ass and os.path.exists(task_ass):
            z.write(task_ass, "02_SUBTITULOS/subtitulos_estilizados.ass")
            
        prompts_json = json.dumps({
            "proyecto": req.title,
            "idioma": req.language,
            "regla_mimic": req.flow_rule,
            "escenas": req.replica_prompts
        }, indent=2, ensure_ascii=False)
        z.writestr("03_GOOGLE_FLOW/storyboard_10_escenas.json", prompts_json)
        
        prompts_txt = f"=== REGLA DE MIMETISMO PARA GOOGLE FLOW ===\n{req.flow_rule}\n\n=== 10 ESCENAS SECUENCIALES PARA GOOGLE FLOW (9:16) ===\n\n"
        for p in req.replica_prompts:
            prompts_txt += f"ESCENA {p.get('escena')} ({p.get('segundos')}) - {p.get('tipo')}\n"
            prompts_txt += f"Descripción: {p.get('descripcion')}\n"
            prompts_txt += f"Prompt EN: {p.get('prompt_en')}\n\n"
        z.writestr("03_GOOGLE_FLOW/storyboard_prompts.txt", prompts_txt)
        z.writestr("03_GOOGLE_FLOW/regla_mimic_estilo.txt", req.flow_rule or "Cinematic vertical 9:16")

        if os.path.exists(thumb_169_path):
            z.write(thumb_169_path, "04_PORTADAS/miniatura_16x9_split.jpg")
        if os.path.exists(thumb_916_path):
            z.write(thumb_916_path, "04_PORTADAS/portada_vertical_9x16.jpg")

        meta = req.metadata or {}
        seo_txt = f"=== METADATOS OPTIMIZADOS PARA YOUTUBE ===\n\nTÍTULO:\n{meta.get('title', req.title)}\n\nDESCRIPCIÓN:\n{meta.get('description', '')}\n\nTAGS:\n{' '.join(['#' + t for t in meta.get('tags', [])])}\n"
        z.writestr("05_METADATOS/youtube_seo_package.txt", seo_txt)

        tt_txt = (
            f"=== COPIES PARA TIKTOK E INSTAGRAM REELS (EMBUDO A YOUTUBE) ===\n\n"
            f"COPY TIKTOK (Hook de curiosidad extrema):\n{meta.get('title', req.title)}\n\n"
            f"¿Comprendes este principio o sigues cometiendo el mismo error? Comenta abajo y mira el documental completo en YouTube.\n\n"
            f"{' '.join(['#' + t for t in meta.get('tags', [])])} #fyp #viral #parati #psicologiaoscura\n\n"
            f"COPY INSTAGRAM REELS (Reflexión y guardado):\n"
            f"Guarda este post para recordarlo cuando la situación lo exija. 👇\n"
            f"{meta.get('title', req.title)}\n\n"
            f"🔴 Suscríbete en el enlace de la bio para ver la lección completa en YouTube."
        )
        z.writestr("05_METADATOS/tiktok_reels_copies.txt", tt_txt)

        if task_mp4 and os.path.exists(task_mp4):
            z.write(task_mp4, "06_VIDEO/video_render_muestra.mp4")

        # Pista Secundaria en Inglés (YouTube Multi-Language Audio Track)
        if req.script_en and len(req.script_en.strip()) > 10:
            try:
                en_wav = os.path.join(OUTPUT_DIR, f"temp_en_{safe_title}.wav")
                en_srt = os.path.join(OUTPUT_DIR, f"temp_en_{safe_title}.srt")
                en_ass = os.path.join(OUTPUT_DIR, f"temp_en_{safe_title}.ass")
                asyncio.run(engine.synthesize_voice(req.script_en, en_wav, voice="en-US-AndrewNeural"))
                if os.path.exists(en_wav):
                    engine.generate_subtitles_whisper(en_wav, en_ass, srt_path=en_srt, language="en")
                    z.write(en_wav, "01_AUDIO/02_pista_secundaria_ENGLISH_US_48k.wav")
                    if os.path.exists(en_srt):
                        z.write(en_srt, "02_SUBTITULOS/subtitulos_ENGLISH.srt")
                for f_tmp in [en_wav, en_srt, en_ass]:
                    if os.path.exists(f_tmp):
                        try: os.remove(f_tmp)
                        except: pass
            except Exception as err_en:
                print("Warning generating English audio track in zip:", err_en)

    for tp in [thumb_169_path, thumb_916_path]:
        if os.path.exists(tp):
            try: os.remove(tp)
            except: pass

    return {
        "status": "success",
        "zip_url": f"/output/{zip_filename}",
        "filename": zip_filename
    }

# --- RUTAS DE GESTIÓN DE EMBUDO & WORKFLOW KANBAN ---

FUNNEL_DB_FILE = os.path.join(BASE_DIR, "funnel_projects.json")

def load_funnel_db():
    if not os.path.exists(FUNNEL_DB_FILE):
        return [
            {
                "id": "p1",
                "title": "El Arte de No Reaccionar (Estoicismo Puro)",
                "status": "published",
                "notes": "2 videos largos + 6 shorts de embudo activos",
                "brand_id": "la_mente_observadora",
                "created_at": "Hoy"
            },
            {
                "id": "p2",
                "title": "Por Qué Debes Ocultar Tus Planes",
                "status": "production",
                "notes": "Generando escenas 3D en Google Flow",
                "brand_id": "la_mente_observadora",
                "created_at": "Hoy"
            },
            {
                "id": "p3",
                "title": "Las 48 Leyes: Ley #1 Nunca Eclipses al Maestro",
                "status": "script",
                "notes": "Guion AVD estructurado en 4 fases",
                "brand_id": "la_mente_observadora",
                "created_at": "Hoy"
            }
        ]
    try:
        with open(FUNNEL_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_funnel_db(data):
    with open(FUNNEL_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

@app.get("/api/funnel/projects")
def get_funnel_projects():
    return {"status": "success", "projects": load_funnel_db()}

class FunnelSaveRequest(BaseModel):
    title: str
    status: str = "idea"
    notes: Optional[str] = ""
    brand_id: str = "la_mente_observadora"

@app.post("/api/funnel/projects")
def save_funnel_project(req: FunnelSaveRequest):
    db = load_funnel_db()
    proj_id = str(uuid.uuid4())[:8]
    item = {
        "id": proj_id,
        "title": req.title,
        "status": req.status,
        "notes": req.notes,
        "brand_id": req.brand_id,
        "created_at": "Hoy"
    }
    db.append(item)
    save_funnel_db(db)
    return {"status": "success", "project": item}

@app.post("/api/funnel/projects/move")
def move_funnel_project(req: dict):
    proj_id = req.get("id")
    new_status = req.get("status")
    db = load_funnel_db()
    for p in db:
        if p["id"] == proj_id:
            p["status"] = new_status
            break
    save_funnel_db(db)
    return {"status": "success", "projects": db}

class VfxRequest(BaseModel):
    video_source: Optional[str] = None
    prompt: str
    aspect_ratio: Optional[str] = "keep"

@app.post("/api/vfx/render")
def render_vfx_by_prompt(req: VfxRequest):
    try:
        source_path = req.video_source
        if not source_path or not os.path.exists(source_path):
            sample_candidates = [
                os.path.join(OUTPUT_DIR, "repurposed_sample.mp4"),
                r"C:\Users\howar\Desktop\APPS\MIS APPS\VIDEDIT\clip_5s.mp4",
                r"C:\Users\howar\Desktop\APPS\MIS APPS\VIDEDIT\sample_podcast_mic.mp4",
                os.path.join(ASSETS_DIR, "bg_loop.mp4")
            ]
            for cand in sample_candidates:
                if os.path.exists(cand):
                    source_path = cand
                    break
        
        if not source_path or not os.path.exists(source_path):
            raise HTTPException(status_code=400, detail="No se encontró un video fuente válido para editar")
            
        result = vfx_engine.generate_vfx_video(source_path, req.prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vfx/presets")
def get_vfx_presets():
    return {
        "presets": [
            {
                "id": "film_noir_punch",
                "title": "Film Noir + Dynamic Zoom",
                "prompt": "Color grading Film Noir blanco y negro dramático, zoom punch dinámico en momentos clave y lower-third elegante."
            },
            {
                "id": "cyberpunk_neon",
                "title": "Cyberpunk Neon & Progress",
                "prompt": "Estilo Cyberpunk con sombras azules y neón magenta, barra de progreso inferior y subtítulos dinámicos."
            },
            {
                "id": "podcast_pro",
                "title": "Podcast Pro + Superposición",
                "prompt": "Superponer micrófono de podcast al frente con escala y posición natural sin tapar elementos clave, color cálido y lower third."
            },
            {
                "id": "change_clothes",
                "title": "Cambio de Ropa / Traje Ejecutivo",
                "prompt": "Cambiar la ropa por un traje ejecutivo negro elegante, iluminación de estudio profesional y 9:16 vertical."
            },
            {
                "id": "kinetic_viral",
                "title": "Subtítulos Hormozi + VHS Retro",
                "prompt": "Subtítulos estilo Hormozi amarillos con palabras clave en oro, grano vintage VHS y punch zoom."
            }
        ]
    }

@app.get("/api/task/{task_id}")
def get_task_status(task_id: str):
    if task_id not in TASKS_DB:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return TASKS_DB[task_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8585, reload=False)
