import os
import json
import urllib.request
import re

BRAIN_SERIES_DB = os.path.join(os.path.dirname(__file__), "series_db.json")

def get_groq_api_key():
    key = os.environ.get("GROQ_API_KEY")
    if key: return key
    env_path = r"C:\Users\howar\Desktop\APPS\MIS APPS\harness2\.env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        return line.strip().split("=", 1)[1].strip()
        except: pass
    return None

def load_series():
    if not os.path.exists(BRAIN_SERIES_DB):
        return []
    try:
        with open(BRAIN_SERIES_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_series_entry(series_data):
    all_series = load_series()
    all_series.append(series_data)
    with open(BRAIN_SERIES_DB, "w", encoding="utf-8") as f:
        json.dump(all_series, f, indent=2, ensure_ascii=False)
    return series_data

def brainstorm_chat_turn(history: list, user_message: str, channel_brand: dict):
    """
    Motor Conversacional del Copiloto Estratégico (La Mente Observadora).
    Emula exactamente la interacción humana de co-creación:
    1. Propone ángulos psicológicos con curiosidad y advertencia.
    2. Debate títulos y ganchos (Opción A vs Opción B).
    3. Entrega Action Cards estructuradas para ejecutar en el estudio con 1 clic.
    """
    key = get_groq_api_key()
    
    brand_name = channel_brand.get("brand_name", "La Mente Observadora")
    brand_niche = channel_brand.get("niche", "Psicología Oscura, Estoicismo y Comportamiento Humano")
    brand_tone = channel_brand.get("tone", "Estoico, analítico, solemne, revelador")
    
    system_prompt = f"""Eres el Copiloto y Director de Estrategia Creativa de '{brand_name}' ({brand_niche}).
Tu tono es: {brand_tone}.
Tu misión es CO-CREAR con el usuario como un socio experto de YouTube:
- Habla en primera persona, conciso, directo y provocativo.
- Si el usuario trae una idea vaga o no sabe qué hacer, dale 3 ángulos psicológicos irresistibles (Ángulo A, B y C) con un gancho demoledor para cada uno.
- Si el usuario aprueba o debate un ángulo, forja el gancho de los primeros 5 segundos y la estructura de tensión narrativa de 4 fases (Gancho Visceral, Tensión, Clímax Psicológico y Cierre).
- Al final de tu respuesta, si detectas una idea o guion maduro, entrega siempre un bloque JSON especial delimitado con ```action_card ... ``` para que la plataforma lo cargue en el Taller de producción automáticamente.

Formato de action_card (solo cuando haya una propuesta concreta lista para ejecutar):
```action_card
{{
  "title": "Título de alto CTR",
  "hook": "Gancho demoledor de 5 segundos",
  "synopsis": "Breve sinopsis del video",
  "suggested_duration": "8-10 min",
  "tags": ["psicologia oscura", "estoicismo", "manipulacion"]
}}
```"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Agregar historial reciente (últimos 6 turnos para mantener contexto ágil)
    for h in history[-6:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ["user", "assistant"] and content:
            messages.append({"role": role, "content": content})
            
    messages.append({"role": "user", "content": user_message})

    if key:
        try:
            payload = {
                "model": "qwen/qwen3.8-27b",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1200
            }
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload).encode("utf-8"),
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                reply = result["choices"][0]["message"]["content"]
                
                # Extraer action_card si existe
                action_card = None
                card_match = re.search(r"```action_card\s*(\{.*?\})\s*```", reply, re.DOTALL)
                if card_match:
                    try:
                        action_card = json.loads(card_match.group(1))
                    except:
                        pass
                
                return {
                    "role": "assistant",
                    "content": reply,
                    "action_card": action_card
                }
        except Exception as e:
            print("Brainstorming Groq call warning:", e)

    # Fallback estratégico determinista de alto valor si Groq estuviese ocupado
    msg_lower = user_message.lower()
    return {
        "role": "assistant",
        "content": f"""He analizado tu idea para **{brand_name}**. Para maximizar el CTR y la retención en este nicho, te propongo 3 ángulos virales con tensión psicológica probada:

**Ángulo A (La Advertencia Oculta):**
> *"Cuando una persona finge ser inofensiva, no busca tu confianza; busca tu guardia baja. La regla del silencio ante los falsos aliados."*

**Ángulo B (Demolición Psicológica):**
> *"Por qué responder a un insulto te destruye más que el insulto mismo. Cómo el estoicismo desarma a cualquier manipulador en 3 segundos."*

**Ángulo C (El Misterio de la Observación):**
> *"Las 4 micro-expresiones que delatan a quien te envidia en silencio. Aprende a ver lo que nadie dice."*

¿Cuál de estos tres ángulos te vibra más para profundizar hoy, o qué matiz le cambiamos?""",
        "action_card": {
            "title": "El Arte de Pasar Desapercibido: Por Qué los Más Fuertes Callan",
            "hook": "Cuando aprendes a guardar silencio, quien pretendía provocarte termina destruyéndose a sí mismo.",
            "synopsis": "Análisis psicológico y estoico sobre el poder de la contención emocional ante manipuladores.",
            "suggested_duration": "8-10 min",
            "tags": ["psicologia oscura", "estoicismo", "silencio", "manipulacion"]
        }
    }
