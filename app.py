import streamlit as st
import difflib
import pandas as pd
import altair as alt
from datetime import date
import re
import math
import os
import json # Necesario para guardar el progreso exacto
import glob # Necesario para buscar archivos de sesiones guardadas

# --- INTENTO DE IMPORTAR FPDF ---
try:
    from fpdf import FPDF
    fpdf_available = True
except ImportError:
    fpdf_available = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TEPROSIF-R Pro", layout="wide", page_icon="🗣️")

# ==========================================
# PARTE 1: ESTILOS CSS (DISEÑO CLÍNICO)
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #212529; font-family: 'Segoe UI', sans-serif; }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e9ecef; }
    
    /* TARJETAS */
    div[data-testid="stVerticalBlockBorderWrapper"] { 
        background-color: white !important; 
        border-radius: 10px; 
        padding: 20px; 
        border: 1px solid #dee2e6; 
        box-shadow: 0 2px 6px rgba(0,0,0,0.02); 
        margin-bottom: 15px; 
    }
    
    /* VISUALIZADOR DE SÍLABAS */
    .syllable-container {
        font-family: 'Segoe UI Mono', 'Courier New', monospace;
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2c3e50;
        margin: 10px 0;
    }
    .syl-row { display: flex; align-items: center; margin-bottom: 8px; font-size: 1.1rem; }
    .syl-label { width: 60px; font-weight: bold; color: #6c757d; font-size: 0.8rem; text-transform: uppercase; }
    .syl-chk { margin-right: 10px; }
    
    /* SÍLABAS TÓNICAS */
    .syl-normal { color: #495057; padding: 0 2px; }
    .syl-tonic { color: #d32f2f; font-weight: 900; text-decoration: underline; padding: 0 2px; }
    
    /* DIFF VISUAL - RESALTADO DE CAMBIOS */
    .diff-deleted { 
        background-color: #ffcdd2; 
        color: #c62828; 
        padding: 2px 4px; 
        border-radius: 3px;
        font-weight: 700;
        text-decoration: line-through;
    }
    .diff-added { 
        background-color: #c8e6c9; 
        color: #2e7d32; 
        padding: 2px 4px; 
        border-radius: 3px;
        font-weight: 700;
    }
    .diff-changed { 
        background-color: #fff59d; 
        color: #f57f17; 
        padding: 2px 4px; 
        border-radius: 3px;
        font-weight: 700;
    }
    .diff-equal { 
        color: #495057; 
        padding: 0 2px; 
    }
    
    /* ALERTAS */
    .ia-box { background-color: #fffde7; border: 1px solid #fff59d; border-radius: 6px; padding: 12px; margin-top: 10px; }
    .ia-title { font-weight: bold; color: #fbc02d; font-size: 0.85rem; display: block; margin-bottom: 5px; }
    
    .ptag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 800; color: white !important; margin-right: 6px; }
    .bg-e { background-color: #8e24aa; }
    .bg-a { background-color: #0288d1; }
    .bg-s { background-color: #d32f2f; }
    
    /* CONTADORES */
    .counter-box { padding: 8px; border-radius: 6px; text-align: center; border: 1px solid #e0e0e0; background: #fff; }
    .c-purple { border-bottom: 3px solid #9c27b0; }
    .c-blue { border-bottom: 3px solid #1976d2; }
    .c-red { border-bottom: 3px solid #d32f2f; }
    .counter-label { font-weight: 800; font-size: 0.7rem; color: #555; }
    
    /* DIAGNÓSTICO */
    .diag-card { padding: 15px; border-radius: 8px; text-align: center; margin-top: 15px; border: 1px solid transparent; }
    .d-normal { background-color: #e8f5e9; color: #1b5e20; border-color: #a5d6a7; }
    .d-riesgo { background-color: #fff3e0; color: #e65100; border-color: #ffcc80; }
    .d-deficit { background-color: #ffebee; color: #b71c1c; border-color: #ef9a9a; }
    
    /* LEYENDA DIFF */
    .diff-legend {
        display: flex;
        gap: 15px;
        margin-top: 8px;
        font-size: 0.75rem;
        flex-wrap: wrap;
    }
    .diff-legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .diff-legend-box {
        width: 20px;
        height: 12px;
        border-radius: 2px;
        display: inline-block;
    }
    /* Texto de descripciones extendidas */
    .desc { font-size: 0.85rem; line-height: 1.4; display: block; margin-top: 4px; color: #333; }
    .rule-highlight { background-color: #e3f2fd; padding: 2px 5px; border-radius: 3px; font-weight: 600; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# PARTE 2: BASE DE DATOS DETALLADA
# ==========================================

METADATA_PALABRAS = {
    "1": {"word": "plancha", "syl": ["plan", "cha"], "tonic": 0},
    "2": {"word": "rueda", "syl": ["rue", "da"], "tonic": 0},
    "3": {"word": "mariposa", "syl": ["ma", "ri", "po", "sa"], "tonic": 2},
    "4": {"word": "bicicleta", "syl": ["bi", "ci", "cle", "ta"], "tonic": 2},
    "5": {"word": "helicóptero", "syl": ["he", "li", "cop", "te", "ro"], "tonic": 2},
    "6": {"word": "bufanda", "syl": ["bu", "fan", "da"], "tonic": 1},
    "7": {"word": "caperucita", "syl": ["ca", "pe", "ru", "ci", "ta"], "tonic": 3},
    "8": {"word": "alfombra", "syl": ["al", "fom", "bra"], "tonic": 1},
    "9": {"word": "refrigerador", "syl": ["re", "fri", "ge", "ra", "dor"], "tonic": 4},
    "10": {"word": "edificio", "syl": ["e", "di", "fi", "cio"], "tonic": 2},
    "11": {"word": "calcetín", "syl": ["cal", "ce", "tin"], "tonic": 2},
    "12": {"word": "dinosaurio", "syl": ["di", "no", "sau", "rio"], "tonic": 2},
    "13": {"word": "teléfono", "syl": ["te", "le", "fo", "no"], "tonic": 1},
    "14": {"word": "remedio", "syl": ["re", "me", "dio"], "tonic": 1},
    "15": {"word": "peineta", "syl": ["pei", "ne", "ta"], "tonic": 1},
    "16": {"word": "auto", "syl": ["au", "to"], "tonic": 0},
    "17": {"word": "indio", "syl": ["in", "dio"], "tonic": 0},
    "18": {"word": "pantalón", "syl": ["pan", "ta", "lon"], "tonic": 2},
    "19": {"word": "camión", "syl": ["ca", "mion"], "tonic": 1},
    "20": {"word": "cuaderno", "syl": ["cua", "der", "no"], "tonic": 1},
    "21": {"word": "micro", "syl": ["mi", "cro"], "tonic": 0},
    "22": {"word": "tren", "syl": ["tren"], "tonic": 0},
    "23": {"word": "plátano", "syl": ["pla", "ta", "no"], "tonic": 0},
    "24": {"word": "jugo", "syl": ["ju", "go"], "tonic": 0},
    "25": {"word": "enchufe", "syl": ["en", "chu", "fe"], "tonic": 1},
    "26": {"word": "jabón", "syl": ["ja", "bon"], "tonic": 1},
    "27": {"word": "tambor", "syl": ["tam", "bor"], "tonic": 1},
    "28": {"word": "volantín", "syl": ["vo", "lan", "tin"], "tonic": 2},
    "29": {"word": "jirafa", "syl": ["ji", "ra", "fa"], "tonic": 1},
    "30": {"word": "gorro", "syl": ["go", "rro"], "tonic": 0},
    "31": {"word": "árbol", "syl": ["ar", "bol"], "tonic": 0},
    "32": {"word": "dulce", "syl": ["dul", "ce"], "tonic": 0},
    "33": {"word": "guitarra", "syl": ["gui", "ta", "rra"], "tonic": 1},
    "34": {"word": "guante", "syl": ["guan", "te"], "tonic": 0},
    "35": {"word": "reloj", "syl": ["re", "loj"], "tonic": 1},
    "36": {"word": "jaula", "syl": ["jau", "la"], "tonic": 0},
    "37": {"word": "puente", "syl": ["puen", "te"], "tonic": 0},
}

# --- NORMAS DETALLADAS (Promedio y DE por categoría) ---
STATS_DETALLADO = {
    3: {"Total": (27.0, 15.1), "E": (14.7, 8.6), "A": (6.3, 4.8), "S": (5.9, 4.2)},
    4: {"Total": (13.4, 10.0), "E": (7.2, 6.4),  "A": (2.9, 2.7), "S": (3.3, 2.9)},
    5: {"Total": (7.9, 6.4),   "E": (4.1, 3.7),  "A": (1.9, 2.0), "S": (1.7, 1.9)},
    6: {"Total": (4.9, 5.1),   "E": (2.6, 3.3),  "A": (1.0, 1.2), "S": (1.2, 1.8)}
}

NORMAS_RANGOS = {
    "Completo": {3:{"N":(0,42),"R":(43,57)},4:{"N":(0,23),"R":(24,33)},5:{"N":(0,14),"R":(15,21)},6:{"N":(0,10),"R":(11,15)}},
    "Barrido": {3:{"N":(0,28),"R":(29,38)},4:{"N":(0,15),"R":(16,21)},5:{"N":(0,10),"R":(11,14)},6:{"N":(0,7),"R":(8,11)}}
}

PALABRAS_TEST = [
    "1. Plancha", "2. Rueda", "3. Mariposa", "4. Bicicleta", "5. Helicóptero",
    "6. Bufanda", "7. Caperucita", "8. Alfombra", "9. Refrigerador", "10. Edificio",
    "11. Calcetín", "12. Dinosaurio", "13. Teléfono", "14. Remedio", "15. Peineta",
    "16. Auto", "17. Indio", "18. Pantalón", "19. Camión", "20. Cuaderno",
    "21. Micro", "22. Tren", "23. Plátano", "24. Jugo", "25. Enchufe",
    "26. Jabón", "27. Tambor", "28. Volantín", "29. Jirafa", "30. Gorro",
    "31. Árbol", "32. Dulce", "33. Guitarra", "34. Guante", "35. Reloj",
    "36. Jaula", "37. Puente"
]

FONEMAS = {
    "p": {"zona": 1, "modo": "oclusiva", "voz": 0}, "b": {"zona": 1, "modo": "oclusiva", "voz": 1},
    "t": {"zona": 2, "modo": "oclusiva", "voz": 0}, "d": {"zona": 2, "modo": "oclusiva", "voz": 1},
    "k": {"zona": 4, "modo": "oclusiva", "voz": 0}, "g": {"zona": 4, "modo": "oclusiva", "voz": 1},
    "m": {"zona": 1, "modo": "nasal", "voz": 1}, "n": {"zona": 2, "modo": "nasal", "voz": 1},
    "ɲ": {"zona": 3, "modo": "nasal", "voz": 1}, "f": {"zona": 1, "modo": "fricativa", "voz": 0},
    "s": {"zona": 2, "modo": "fricativa", "voz": 0}, "x": {"zona": 4, "modo": "fricativa", "voz": 0},
    "h": {"zona": 5, "modo": "aspirada", "voz": 0}, "ĉ": {"zona": 3, "modo": "africada", "voz": 0},
    "l": {"zona": 2, "modo": "liquida", "voz": 1}, "r": {"zona": 2, "modo": "liquida", "voz": 1},
    "R": {"zona": 2, "modo": "liquida", "voz": 1}, "y": {"zona": 3, "modo": "fricativa", "voz": 1},
    "w": {"zona": 4, "modo": "semiconsonante", "voz": 1}, "a": {"zona": 0, "modo": "vocal", "voz": 1},
    "e": {"zona": 3, "modo": "vocal", "voz": 1}, "i": {"zona": 3, "modo": "vocal", "voz": 1},
    "o": {"zona": 4, "modo": "vocal", "voz": 1}, "u": {"zona": 4, "modo": "vocal", "voz": 1},
}

GRUPOS = {
    "vocales": ["a", "e", "i", "o", "u"],
    "trabantes": ["n", "l", "s", "r", "d", "z", "x", "j", "m"],
    "diptongos": ["ai", "au", "ei", "eu", "oi", "ou", "ia", "ie", "io", "iu", "ua", "ue", "ui", "uo"]
}

NOMBRES_PROCESOS = {
    "E.1": "Reducción Grupo Consonántico", "E.2": "Reducción Diptongo", "E.3": "Omisión Coda",
    "E.4": "Coalescencia", "E.5": "Omisión Elem. Átonos", "E.6": "Omisión Sílaba Tónica",
    "E.7": "Adición", "E.8": "Inversión", "A.1": "Asim. Idéntica", "A.2": "Asim. Labial",
    "A.3": "Asim. Dental", "A.4": "Asim. Palatal", "A.5": "Asim. Velar", "A.6": "Asim. a Líquidos",
    "A.7": "Asim. Nasal", "A.8": "Asim. Vocálica", "A.9": "Asim. Silábica", "S.1": "Aspiración",
    "S.2": "Posteriorización", "S.3": "Frontalización", "S.4": "Labialización", "S.5": "Oclusivización",
    "S.6": "Fricativización", "S.7": "Africación", "S.8": "Sonorización", "S.9": "Afonización",
    "S.10": "Semiconsonantización", "S.11": "Sust. Líq. por Líq.", "S.12": "Sust. Líq. por No Líq.",
    "S.13": "Sust. No Líq. por Líq.", "S.14": "Nasalización", "S.15": "Oralización", 
    "S.16": "Sust. Vocálica", "S.17": "Desafricación"
}

# === TEXTO ADICIONAL DE PROCEDIMIENTOS GENERALES PARA EL SIDEBAR ===
GUIA_PROCEDIMIENTOS = """
**1. Descartar problemas articulatorios:**
* Antes de identificar un PSF, determine si el niño tiene problemas para articular algún fonema.
* **Regla:** Si el error es siempre el mismo (ej. siempre sustituye /r/ por /d/ en todas las palabras), se considera dificultad articulatoria y **NO se contabiliza como PSF**.
* Solo es PSF si el error varía según la palabra (ej. a veces lo omite, a veces lo sustituye).
* **Excepción seseo:** La sustitución de /s/ por [θ] (z) nunca se considera PSF.

**2. Secuencia de Análisis sugerida:**
1. **Estructura (E):** Identifique primero métrica, adiciones y omisiones.
2. **Asimilación (A):** Priorice siempre la asimilación sobre la sustitución. Si un cambio hace que el fonema se parezca a otro presente, es Asimilación.
3. **Sustitución (S):** Solo cuando el cambio no se explica por asimilación.
"""

# === DEFINICIONES ACTUALIZADAS Y EXTENDIDAS (FUENTE: PDF USUARIO) ===
DEFINICIONES = {
    # --- ESTRUCTURA ---
    "E.1": """<b>Reducción de grupo consonántico:</b> Se omite uno de los fonemas del grupo (dífono consonántico).<br>
    <i>Ejemplos:</i> /tren/ → /ten/, /plátano/ → /pátano/.<br>
    <span class='rule-highlight'>Regla:</span> Si el niño nunca produce el líquido correctamente (error constante), es articulatorio y no PSF. Si varía, es PSF.""",
    
    "E.2": """<b>Reducción del diptongo:</b> Se omite uno de los fonemas del dífono vocálico (generalmente la débil).<br>
    <i>Ejemplos:</i> /auto/ → /ato/, /puente/ → /pénte/.""",
    
    "E.3": """<b>Omisión de consonante trabante (coda):</b> Se omite el fonema consonántico al final de la sílaba.<br>
    <i>Ejemplos:</i> /pantalón/ → /pa_talón/, /helicóptero/ → /elikó_tero/.<br>
    <span class='rule-highlight'>Prioridad:</span> En casos mixtos (ej: /indio/ → /i_nio/), se prioriza la Omisión de Trabante sobre la asimilación.""",
    
    "E.4": """<b>Coalescencia:</b> Se fusionan dos fonemas contiguos originando un tercer fonema diferente.<br>
    <i>Ejemplos:</i> /tren/ → /ken/ (/tr/=/k/), /remedio/ → /reméĵo/ (/di/=/y/).<br>
    <span class='rule-highlight'>Nota:</span> Se cuenta como 1 solo proceso en vez de dos (reducción + asimilación).""",
    
    "E.5": """<b>Omisión de elementos átonos:</b> Se omiten sílabas átonas o fonemas de ellas.<br>
    <i>Ejemplos:</i> /alfombra/ → /_fombra/, /mariposa/ → /ma_pósa/.<br>
    <span class='rule-highlight'>Contabilización:</span> Se cuenta 1 proceso por elementos contiguos omitidos.""",
    
    "E.6": """<b>Omisión de sílaba tónica:</b> Se elimina la sílaba acentuada o parte de sus constituyentes.<br>
    <i>Ejemplos:</i> /mariposa/ → /mari_sa/, /helicóptero/ → /eli_óptero/.""",
    
    "E.7": """<b>Adición de fonemas o sílabas:</b> Prótesis (inicio), Epéntesis (medio) o Paragoge (final).<br>
    <i>Ejemplos:</i> /indio/ → /níndio/, /auto/ → /dáuto/, /jaula/ → /xuáula/.""",
    
    "E.8": """<b>Inversión (Metátesis):</b> Se cambia de posición un fonema o sílaba conservando los originales.<br>
    <i>Ejemplos:</i> /auto/ → /uáto/, /teléfono/ → /tenéfolo/, /dulce/ → /dúsel/.""",
    
    # --- ASIMILACIÓN ---
    "A.1": """<b>Asimilación idéntica:</b> Un fonema se cambia para hacerse idéntico a otro presente.<br>
    <i>Ejemplos:</i> /bufanda/ → /bubánda/, /reloj/ → /lelóx/.""",
    
    "A.2": """<b>Asimilación labial:</b> Un fonema se hace similar a un labial (/p/, /b/, /m/, /f/) presente.<br>
    <i>Ejemplos:</i> /plátano/ → /plátamo/.""",
    
    "A.3": """<b>Asimilación dental:</b> Un fonema se hace similar a un dental (/t/, /d/, /s/) presente.<br>
    <i>Ejemplos:</i> /mariposa/ → /madipósa/.""",
    
    "A.4": """<b>Asimilación palatal:</b> Se hace similar a un palatal (/y/, /ch/, /ñ/) o vocales /e/, /i/.<br>
    <i>Ejemplo:</i> /cuaderno/ → /cuaĵérno/.""",
    
    "A.5": """<b>Asimilación velar:</b> Se hace similar a un velar (/k/, /g/, /x/) o vocales /o/, /u/.<br>
    <i>Ejemplos:</i> /bufanda/ → /gufánda/, /puente/ → /kuénte/.""",
    
    "A.6": """<b>Asimilación a líquidos:</b> Un no líquido se asemeja a un líquido (/l/, /r/, /rr/) presente.<br>
    <i>Ejemplos:</i> /guitarra/ → /litára/.""",
    
    "A.7": """<b>Asimilación nasal:</b> Un fonema oral se hace similar a un nasal (/m/, /n/, /ñ/) presente.<br>
    <i>Ejemplos:</i> /alfombra/ → /anfómbra/.""",
    
    "A.8": """<b>Asimilación vocálica:</b> Una vocal se asemeja a otra en zona o grado de abertura.<br>
    <i>Ejemplos:</i> /enchufe/ → /enchúfo/ (e se parece a u).""",
    
    "A.9": """<b>Asimilación silábica:</b> Una sílaba completa se hace idéntica a otra de la palabra.<br>
    <i>Ejemplos:</i> /helicóptero/ → /lilikóptero/, /dinosaurio/ → /didisáurio/.""",
    
    # --- SUSTITUCIÓN ---
    "S.1": """<b>Aspiración de trabante:</b> El fonema final de sílaba se aspira (/h/).<br>
    <i>Ejemplo:</i> /dulce/ → /dúhse/.<br>
    <span class='rule-highlight'>Norma:</span> La aspiración de /s/ final NO se cuenta si es norma dialectal (español de Chile).""",
    
    "S.2": """<b>Posteriorización:</b> Sustitución de fonemas anteriores (labial/dental) por posteriores (palatal/velar).<br>
    <i>Ejemplos:</i> /bufanda/ → /jufánda/, /tren/ → /kren/.""",
    
    "S.3": """<b>Frontalización:</b> Sustitución de posteriores por anteriores.<br>
    <i>Ejemplos:</i> /guante/ → /buánte/, /jugo/ → /púgo/.""",
    
    "S.4": """<b>Labialización:</b> Sustitución de consonante (no velar/líquida) por labial.<br>
    <i>Ejemplos:</i> /dinosaurio/ → /binosáurio/.""",
    
    "S.5": """<b>Oclusivización de fricativos:</b> Fricativo pasa a oclusivo/africado.<br>
    <i>Ejemplos:</i> /jirafa/ → /kiráfa/, /dulce/ → /dúlĉe/.""",
    
    "S.6": """<b>Fricativización de oclusivos:</b> Oclusivo/africado pasa a fricativo.<br>
    <i>Ejemplos:</i> /plancha/ → /plánsa/, /puente/ → /fuénte/.""",
    
    "S.7": """<b>Sustitución de fricativos entre sí:</b> Reemplazo entre fricativos de zona similar.<br>
    <i>Ejemplo:</i> /alfombra/ → /alsómbra/.""",
    
    "S.8": """<b>Sonorización:</b> Fonema áfono pasa a sonoro.<br>
    <i>Ejemplo:</i> /caperucita/ → /kaberusíta/.""",
    
    "S.9": """<b>Afonización (Pérdida de sonoridad):</b> Fonema sonoro pasa a áfono.<br>
    <i>Ejemplo:</i> /guitarra/ → /kitára/.""",
    
    "S.10": """<b>Semiconsonantización:</b> Líquido sustituido por semiconsonante (yod /j/ o wau /w/).<br>
    <i>Ejemplos:</i> /tren/ → /tjen/, /plátano/ → /pjátano/.<br>
    <span class='rule-highlight'>Regla:</span> Siempre es sustitución, NO asimilación.""",
    
    "S.11": """<b>Sustitución de líquidos entre sí:</b> Cambio entre /l/, /r/, /rr/.<br>
    <i>Ejemplos:</i> /gorro/ → /góro/, /micro/ → /míklo/.""",
    
    "S.12": """<b>Sustitución de líquido por no líquido:</b> Líquido pasa a ser otra consonante oral.<br>
    <i>Ejemplos:</i> /reloj/ → /delóx/, /gorro/ → /gódo/.""",
    
    "S.13": """<b>Sustitución de no líquido por líquido:</b><br>
    <i>Ejemplos:</i> /edificio/ → /elifísio/, /auto/ → /álto/.""",
    
    "S.14": """<b>Nasalización:</b> Fonema oral pasa a nasal (sin asimilación).<br>
    <i>Ejemplos:</i> /rueda/ → /muéda/, /auto/ → /ánto/.""",
    
    "S.15": """<b>Oralización:</b> Fonema nasal pasa a oral.<br>
    <i>Ejemplo:</i> /bufanda/ → /bufálda/.""",
    
    "S.16": """<b>Sustitución Vocálica (Disimilación):</b> Cambio de vocal para diferenciarse de otras.<br>
    <i>Ejemplo:</i> /puente/ → /puénta/."""
}

# ==========================================
# PARTE 3: LÓGICA Y FUNCIONES
# ==========================================

def calcular_edad_exacta(nacimiento, evaluacion):
    if not nacimiento or not evaluacion: return 0, 0
    years = evaluacion.year - nacimiento.year
    months = evaluacion.month - nacimiento.month
    if months < 0:
        years -= 1; months += 12
    elif months == 0 and evaluacion.day < nacimiento.day:
        years -= 1; months = 11
    return max(0, years), max(0, months)

def texto_a_fonemas(texto):
    if not texto: return ""
    t = texto.lower().strip()
    replacements = (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"))
    for a, b in replacements: t = t.replace(a, b)
    t = t.replace("ch", "ĉ").replace("ll", "y").replace("rr", "R").replace("qu", "k")
    t = t.replace("ce", "se").replace("ci", "si").replace("c", "k")
    t = t.replace("ge", "xe").replace("gi", "xi").replace("j", "x") 
    t = t.replace("v", "b").replace("z", "s").replace("ñ", "ɲ")
    if t.startswith("h") and len(t) > 1: t = t[1:]
    return t

def silabear_texto_mejorado(texto):
    """Silabeo mejorado en ALFABETO FONÉTICO"""
    t = texto_a_fonemas(texto) if not all(c in "aeioupcdfghjklmnñbtvwxyzĉɲRyw" for c in texto.lower()) else texto
    if not t:
        return []
    
    excepciones = {
        "indio": ["in", "dio"],
        "remedio": ["re", "me", "dio"],
        "edifisio": ["e", "di", "fi", "sio"],
        "dinosaurio": ["di", "no", "sau", "rio"],
        "auto": ["au", "to"],
        "xaula": ["xau", "la"],
        "rueda": ["rue", "da"],
        "peineta": ["pei", "ne", "ta"],
        "kuaderno": ["kua", "der", "no"],
        "puente": ["puen", "te"],
        "guante": ["guan", "te"],
        "planĉa": ["plan", "ĉa"],
        "mariposa": ["ma", "ri", "po", "sa"],
        "bisicleta": ["bi", "si", "cle", "ta"],
        "helikoptero": ["he", "li", "kop", "te", "ro"],
        "bufanda": ["bu", "fan", "da"],
        "kaperusita": ["ka", "pe", "ru", "si", "ta"],
        "alfombra": ["al", "fom", "bra"],
        "refrixerador": ["re", "fri", "xe", "ra", "dor"],
        "kalsetin": ["kal", "se", "tin"],
        "telefono": ["te", "le", "fo", "no"],
        "mikro": ["mi", "kro"],
        "tren": ["tren"],
        "platano": ["pla", "ta", "no"],
        "xugo": ["xu", "go"],
        "enĉufe": ["en", "ĉu", "fe"],
        "xabon": ["xa", "bon"],
        "tambor": ["tam", "bor"],
        "bolantin": ["bo", "lan", "tin"],
        "xirafa": ["xi", "ra", "fa"],
        "goRo": ["go", "Ro"],
        "arbol": ["ar", "bol"],
        "dulse": ["dul", "se"],
        "gitaRa": ["gi", "ta", "Ra"],
        "relox": ["re", "lox"],
        "pantalon": ["pan", "ta", "lon"],
        "kamion": ["ka", "mion"],
    }
    
    if t in excepciones:
        return excepciones[t]
    
    silabas = []
    i = 0
    
    vocales_fuertes = ['a', 'e', 'o']
    vocales_debiles = ['i', 'u']
    vocales = vocales_fuertes + vocales_debiles
    consonantes = [c for c in "bcdfghjklmnpqrstvwxyzĉɲRyw"]
    
    while i < len(t):
        silaba = ""
        
        while i < len(t) and t[i] in consonantes:
            silaba += t[i]
            i += 1
        
        if i < len(t) and t[i] in vocales:
            v1 = t[i]
            silaba += v1
            i += 1
            
            if i < len(t) and t[i] in vocales:
                v2 = t[i]
                es_diptongo = False
                
                if v1 in vocales_debiles and v2 in vocales_fuertes:
                    es_diptongo = True
                elif v1 in vocales_fuertes and v2 in vocales_debiles:
                    es_diptongo = True
                elif v1 in vocales_debiles and v2 in vocales_debiles:
                    es_diptongo = True
                
                if v1 == 'i' and v2 == 'o':
                    if len(silaba) == 2:
                        es_diptongo = False
                    else:
                        es_diptongo = True
                
                if v1 == 'i' and v2 == 'a':
                    if len(silaba) == 2:
                        es_diptongo = False
                    else:
                        es_diptongo = True
                
                if es_diptongo:
                    silaba += v2
                    i += 1
        
        if i < len(t) and t[i] in consonantes:
            if i + 1 < len(t):
                if t[i + 1] in consonantes:
                    grupo = t[i:i+2]
                    grupos_iniciales = ['pl', 'bl', 'pr', 'br', 'tr', 'dr', 'kr', 'gr', 'fl', 'kl', 'gl', 'fr']
                    if grupo not in grupos_iniciales:
                        silaba += t[i]
                        i += 1
                    else:
                        pass
            else:
                silaba += t[i]
                i += 1
        
        if silaba:
            silabas.append(silaba)
    
    return silabas

def generar_diff_visual(meta_fon, prod_fon, idx_tonic):
    """
    Genera HTML con diff visual carácter por carácter
    Rojo = omitido, Verde = agregado, Amarillo = cambiado
    """
    meta_syls = silabear_texto_mejorado(meta_fon)
    prod_syls = silabear_texto_mejorado(prod_fon)
    
    # Generar diff a nivel de caracteres
    matcher = difflib.SequenceMatcher(None, meta_fon, prod_fon)
    
    # META con resaltado
    meta_html = ""
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        segmento = meta_fon[i1:i2]
        if tag == 'equal':
            meta_html += f'<span class="diff-equal">{segmento}</span>'
        elif tag == 'delete':
            meta_html += f'<span class="diff-deleted">{segmento}</span>'
        elif tag == 'replace':
            meta_html += f'<span class="diff-changed">{segmento}</span>'
    
    # PRODUCCIÓN con resaltado
    prod_html = ""
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        segmento_prod = prod_fon[j1:j2]
        if tag == 'equal':
            prod_html += f'<span class="diff-equal">{segmento_prod}</span>'
        elif tag == 'insert':
            prod_html += f'<span class="diff-added">{segmento_prod}</span>'
        elif tag == 'replace':
            prod_html += f'<span class="diff-changed">{segmento_prod}</span>'
    
    # Agregar separadores silábicos
    meta_with_sep = ""
    char_count = 0
    for syl in meta_syls:
        meta_with_sep += meta_html[char_count:char_count+len(syl)]
        char_count += len(syl)
        if char_count < len(meta_fon):
            meta_with_sep += '<span style="color:#999;">-</span>'
    
    prod_with_sep = ""
    char_count = 0
    for syl in prod_syls:
        prod_with_sep += prod_html[char_count:char_count+len(syl)] if char_count < len(prod_html) else ""
        char_count += len(syl)
        if char_count < len(prod_fon):
            prod_with_sep += '<span style="color:#999;">-</span>'
    
    return meta_html, prod_html

def comparar_rasgos(m, p, context_prod=None, idx=0):
    """Compara rasgos fonológicos entre meta y producción"""
    if p == "h": return ["S.1"]

    if m not in FONEMAS or p not in FONEMAS: return []
    fm, fp = FONEMAS[m], FONEMAS[p]
    sugs = []

    if fm['modo'] == 'vocal' and fp['modo'] == 'vocal':
        if context_prod:
            vecinos = []
            if idx > 0: vecinos.append(context_prod[idx-1]) 
            if idx < len(context_prod)-1: vecinos.append(context_prod[idx+1])
            for v in vecinos:
                if v in FONEMAS and FONEMAS[v]['modo'] == 'vocal':
                    if fp['zona'] == FONEMAS[v]['zona'] and fp['zona'] != fm['zona']:
                        sugs.append("A.8"); return sugs
        sugs.append("S.16"); return sugs

    if context_prod:
        vecinos = []
        if idx > 0: vecinos.append(context_prod[idx-1]) 
        if idx < len(context_prod)-1: vecinos.append(context_prod[idx+1]) 
        if fp['zona'] == 4: 
            for v in vecinos:
                if v in FONEMAS and FONEMAS[v]['zona'] == 4 and FONEMAS[v]['modo'] == 'vocal': 
                    sugs.append("A.5"); return sugs 
        if fp['zona'] == 3: 
             for v in vecinos:
                if v in FONEMAS and FONEMAS[v]['zona'] == 3 and FONEMAS[v]['modo'] == 'vocal': 
                    sugs.append("A.4"); return sugs

    if fm['modo'] != fp['modo']:
        if fm['modo'] == 'fricativa' and fp['modo'] == 'africada': sugs.append("S.7"); return sugs
        if fm['modo'] == 'africada' and fp['modo'] == 'fricativa': sugs.append("S.17"); return sugs
        if fm['modo'] == 'fricativa' and fp['modo'] == 'oclusiva': sugs.append("S.5")
        if fm['modo'] == 'oclusiva' and fp['modo'] == 'fricativa': sugs.append("S.6")
        if fm['modo'] == 'nasal' and fp['modo'] != 'nasal': sugs.append("S.15")
        if fm['modo'] != 'nasal' and fp['modo'] == 'nasal': sugs.append("S.14")

    es_liq_m = fm['modo'] == 'liquida'
    es_liq_p = fp['modo'] == 'liquida'
    if es_liq_m and not es_liq_p:
        if p in ["y", "w", "i", "u"]: sugs.append("S.10") 
        else: sugs.append("S.12")
        return sugs 
    if not es_liq_m and es_liq_p: sugs.append("S.13"); return sugs
    if es_liq_m and es_liq_p and m != p: sugs.append("S.11"); return sugs

    if fm['voz'] != fp['voz']:
        if fm['voz'] == 1 and fp['voz'] == 0: 
            sugs.append("S.9")
        if fm['voz'] == 0 and fp['voz'] == 1: 
            sugs.append("S.8")

    if fm['zona'] != fp['zona']:
        if fp['zona'] > fm['zona']: sugs.append("S.2") 
        if fp['zona'] < fm['zona']: sugs.append("S.3") 
        if fp['zona'] == 1 and fm['zona'] > 1:
            if "S.3" in sugs: sugs.remove("S.3")
            sugs.append("S.4")
            
    return sugs

def analizar_procesos(meta, prod, num_item):
    """Análisis MEJORADO de PSF"""
    procesos_detectados = []
    meta_info = METADATA_PALABRAS.get(str(num_item))
    
    silabas_meta = meta_info['syl'] if meta_info else silabear_texto_mejorado(meta)
    silabas_prod = silabear_texto_mejorado(prod)
    idx_tonic = meta_info.get('tonic', 0) if meta_info else 0
    
    # E.1 - REDUCCIÓN GRUPO CONSONÁNTICO
    difonos = ["pl", "bl", "fl", "kl", "gl", "pr", "br", "fr", "kr", "gr", "tr", "dr"]
    for d in difonos:
        if d in meta:
            if d not in prod:
                count_meta = meta.count(d)
                count_prod = prod.count(d)
                if count_prod < count_meta:
                    for _ in range(count_meta - count_prod):
                        procesos_detectados.append("E.1")
    
    # E.3 - OMISIÓN CODA
    codas_meta = []
    codas_prod = []
    
    for sil_m in silabas_meta:
        if len(sil_m) > 1 and sil_m[-1] in GRUPOS["trabantes"]:
            codas_meta.append(sil_m[-1])
    
    for sil_p in silabas_prod:
        if len(sil_p) > 1 and sil_p[-1] in GRUPOS["trabantes"]:
            codas_prod.append(sil_p[-1])
    
    diff_codas = len(codas_meta) - len(codas_prod)
    for _ in range(max(0, diff_codas)):
        procesos_detectados.append("E.3")
    
    # E.5 - OMISIÓN ELEMENTOS ÁTONOS
    if len(silabas_prod) < len(silabas_meta):
        num_omisiones = len(silabas_meta) - len(silabas_prod)
        
        if meta_info:
            silaba_tonica = silabas_meta[idx_tonic]
            nucleo_tonico = "".join([c for c in silaba_tonica if c in GRUPOS["vocales"]])
            
            if nucleo_tonico not in prod:
                procesos_detectados.append("E.6")
                num_omisiones -= 1
        
        for _ in range(max(0, num_omisiones)):
            procesos_detectados.append("E.5")
    
    # E.4 - COALESCENCIA
    i_meta = 0
    i_prod = 0
    while i_meta < len(meta) and i_prod < len(prod):
        if meta[i_meta] == prod[i_prod]:
            i_meta += 1
            i_prod += 1
        else:
            if i_meta + 1 < len(meta):
                seg_meta = meta[i_meta:i_meta+2]
                if i_prod < len(prod):
                    if len(seg_meta) == 2 and seg_meta not in prod:
                        procesos_detectados.append("E.4")
                        i_meta += 2
                        i_prod += 1
                        continue
            i_meta += 1
            i_prod += 1
    
    # E.8 - INVERSIÓN/METÁTESIS
    if len(silabas_meta) >= 2 and len(silabas_prod) >= 2:
        for i in range(len(silabas_meta) - 1):
            if i + 1 < len(silabas_prod):
                sil_m1, sil_m2 = silabas_meta[i], silabas_meta[i+1]
                sil_p1, sil_p2 = silabas_prod[i], silabas_prod[i+1]
                
                nucleo_m1 = ''.join([c for c in sil_m1 if c in GRUPOS["vocales"]])
                nucleo_m2 = ''.join([c for c in sil_m2 if c in GRUPOS["vocales"]])
                nucleo_p1 = ''.join([c for c in sil_p1 if c in GRUPOS["vocales"]])
                nucleo_p2 = ''.join([c for c in sil_p2 if c in GRUPOS["vocales"]])
                
                if nucleo_m1 == nucleo_p2 and nucleo_m2 == nucleo_p1:
                    procesos_detectados.append("E.8")
                    break
    
    if "E.8" not in procesos_detectados:
        if sorted(meta) == sorted(prod) and meta != prod:
            if len(meta) == len(prod):
                procesos_detectados.append("E.8")
    
    # E.2 - REDUCCIÓN DIPTONGO
    for dip in GRUPOS["diptongos"]:
        if dip in meta and dip not in prod:
            v1, v2 = dip[0], dip[1]
            if (v1 in prod and v2 not in prod) or (v2 in prod and v1 not in prod):
                procesos_detectados.append("E.2")
                break
    
    # E.7 - ADICIÓN
    if len(prod) > len(meta):
        if "A.9" not in procesos_detectados:
            procesos_detectados.append("E.7")
    
    # A.9 - ASIMILACIÓN SILÁBICA
    if len(silabas_prod) >= 2:
        if silabas_prod[0] == silabas_prod[1]:
            silabas_meta_temp = meta_info['syl'] if meta_info else []
            if len(silabas_meta_temp) >= 2 and silabas_meta_temp[0] != silabas_meta_temp[1]:
                procesos_detectados.append("A.9")
    
    # ASIMILACIÓN Y SUSTITUCIÓN
    matcher = difflib.SequenceMatcher(None, meta, prod)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'delete':
            pass
        
        elif tag == 'replace':
            segmento_meta = meta[i1:i2]
            segmento_prod = prod[j1:j2]
            
            max_len = max(len(segmento_meta), len(segmento_prod))
            for idx_seg in range(max_len):
                m = segmento_meta[idx_seg] if idx_seg < len(segmento_meta) else None
                p = segmento_prod[idx_seg] if idx_seg < len(segmento_prod) else None
                
                if m is None or p is None or m == p:
                    continue
                
                es_asimilacion = False
                if p in meta:
                    es_asimilacion = True
                if prod.count(p) > 1 and meta.count(p) < prod.count(p):
                    es_asimilacion = True
                
                if es_asimilacion:
                    if p not in GRUPOS["vocales"]:
                        procesos_detectados.append("A.1")
                    
                    fm, fp = FONEMAS.get(m, {}), FONEMAS.get(p, {})
                    if fp.get('zona') == 1: procesos_detectados.append("A.2")
                    if fp.get('zona') == 2: procesos_detectados.append("A.3")
                    if fp.get('zona') == 3: procesos_detectados.append("A.4")
                    if fp.get('zona') == 4: procesos_detectados.append("A.5")
                    
                    if fp.get('modo') == 'liquida' and fm.get('modo') != 'liquida':
                        hay_otra_liq = any(FONEMAS.get(c, {}).get('modo') == 'liquida' for c in prod if c != p and c in FONEMAS)
                        if hay_otra_liq:
                            procesos_detectados.append("A.6")
                        else:
                            procesos_detectados.append("S.13")
                    
                    if fp.get('modo') == 'nasal' and fm.get('modo') != 'nasal':
                        hay_otra_nas = any(FONEMAS.get(c, {}).get('modo') == 'nasal' for c in prod if c != p and c in FONEMAS)
                        if hay_otra_nas:
                            procesos_detectados.append("A.7")
                        else:
                            procesos_detectados.append("S.14")
                else:
                    current_idx = j1 + idx_seg if idx_seg < len(segmento_prod) else j1
                    sugs_rasgos = comparar_rasgos(m, p, prod, current_idx)
                    procesos_detectados.extend(sugs_rasgos)
    
    seen = set()
    unique = []
    for x in procesos_detectados:
        if x not in seen:
            unique.append(x)
            seen.add(x)
    
    return unique

def obtener_diagnostico(total, edad_anos, modo):
    edad_uso = max(3, min(edad_anos, 6))
    norma = NORMAS_RANGOS.get(modo, {}).get(edad_uso)
    if not norma: return "Sin Datos", "gray", "", None, {}
    min_n, max_n = norma["N"]
    min_r, max_r = norma["R"]
    
    if total <= max_n: diag, color = "NORMAL", "d-normal"
    elif total <= max_r: diag, color = "RIESGO", "d-riesgo"
    else: diag, color = "DÉFICIT", "d-deficit"
    
    txt_de = ""
    z_score = None
    stats_norma = {}
    
    if modo == "Completo" and edad_uso in STATS_DETALLADO:
        stats_norma = STATS_DETALLADO[edad_uso]
        prom, de_val = stats_norma["Total"]
        z_score = (total - prom) / de_val
        signo = "+" if z_score > 0 else ""
        txt_de = f"({signo}{z_score:.2f} DE)"
        
    return diag, color, txt_de, z_score, stats_norma

# --- GENERADOR PDF CORREGIDO ---
if fpdf_available:
    class PDF(FPDF):
        def header(self):
            # Solo muestra cabecera de informe clínico en página 1
            if self.page_no() == 1:
                self.set_font('Arial', 'B', 14)
                self.cell(0, 10, 'INFORME DE EVALUACIÓN FONOLÓGICA (TEPROSIF-R)', 0, 1, 'C')
                self.set_draw_color(50, 50, 50)
                self.line(10, 20, 200, 20)
                self.ln(5)

        def footer(self):
            # Pie de página simple
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    # FUNCIÓN DE PDF ROBUSTA CON MANEJO DE FECHAS
    def crear_pdf_avanzado(nombre, fecha_nac, edad_txt, fecha_eval, total, e, a, s, diag, z_score, modo, stats, lista_items, estados_sesion, observaciones=""):
        pdf = PDF()
        pdf.set_margins(10, 10, 10) 
        
        # =======================================================
        # PÁGINA 1: INFORME ESCRITO
        # =======================================================
        pdf.add_page()
        pdf.set_margins(15, 15, 15)
        
        # 1. ANTECEDENTES
        pdf.set_fill_color(240); pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, " 1. ANTECEDENTES DEL PACIENTE", 0, 1, 'L', fill=True)
        pdf.ln(3)
        pdf.set_font('Arial', '', 10)
        # Convertimos las fechas a string antes de escribir
        pdf.cell(30, 7, "Nombre:", 1); pdf.cell(60, 7, nombre.encode('latin-1','replace').decode('latin-1'), 1)
        pdf.cell(30, 7, "Fecha Eval:", 1); pdf.cell(60, 7, str(fecha_eval), 1, 1)
        pdf.cell(30, 7, "F. Nac:", 1); pdf.cell(60, 7, str(fecha_nac), 1)
        pdf.cell(30, 7, "Edad:", 1); pdf.cell(60, 7, edad_txt.encode('latin-1','replace').decode('latin-1'), 1, 1)
        pdf.cell(30, 7, "Evaluación:", 1); pdf.cell(60, 7, modo, 1, 1)
        pdf.ln(6)

        # 2. RESULTADOS
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, " 2. RESULTADOS CUANTITATIVOS", 0, 1, 'L', fill=True)
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 9)
        pdf.set_fill_color(230)
        headers = ["TOTAL PSF", "ESTRUCTURA", "ASIMILACIÓN", "SUSTITUCIÓN"]
        w = [45, 45, 45, 45]
        for i, h in enumerate(headers): pdf.cell(w[i], 7, h, 1, 0, 'C', fill=True)
        pdf.ln()
        pdf.set_font('Arial', '', 11)
        pdf.cell(45, 10, str(total), 1, 0, 'C')
        pdf.cell(45, 10, str(e), 1, 0, 'C')
        pdf.cell(45, 10, str(a), 1, 0, 'C')
        pdf.cell(45, 10, str(s), 1, 1, 'C')
        pdf.ln(8)

        # 3. ANÁLISIS ESTADÍSTICO
        if modo == "Completo" and stats:
            pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240)
            pdf.cell(0, 8, " 3. ANÁLISIS ESTADÍSTICO", 0, 1, 'L', fill=True)
            pdf.ln(3)
            pdf.set_font('Arial', 'B', 9); pdf.set_fill_color(220, 230, 240)
            hd = ["ÍNDICE", "PROMEDIO", "D.E.", "PTJE. NIÑO", "INTERPRETACIÓN"]
            wc = [35, 30, 30, 30, 55]
            for i, h in enumerate(hd): pdf.cell(wc[i], 7, h, 1, 0, 'C', fill=True)
            pdf.ln()
            
            data_rows = [("Total PSF", stats["Total"], total), ("Estructura", stats["E"], e), ("Asimilación", stats["A"], a), ("Sustitución", stats["S"], s)]
            pdf.set_font('Arial', '', 9)
            for lbl, (prom, desv), val in data_rows:
                z = (val - prom) / desv
                estado = "Normal"
                if z > 1: estado = "Riesgo (> +1 DE)"
                if z > 2: estado = "Déficit (> +2 DE)"
                pdf.cell(wc[0], 7, lbl, 1, 0, 'L')
                pdf.cell(wc[1], 7, str(prom), 1, 0, 'C')
                pdf.cell(wc[2], 7, str(desv), 1, 0, 'C')
                pdf.cell(wc[3], 7, str(val), 1, 0, 'C')
                pdf.cell(wc[4], 7, estado, 1, 1, 'C')
            pdf.ln(5)

        # 4. OBSERVACIONES GENERALES
        pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240)
        pdf.cell(0, 8, " 4. OBSERVACIONES GENERALES", 0, 1, 'L', fill=True)
        pdf.ln(3)
        pdf.set_font('Arial', '', 10)
        obs_text = observaciones if observaciones else "Sin observaciones."
        pdf.multi_cell(0, 5, obs_text.encode('latin-1','replace').decode('latin-1'))
        pdf.ln(6)

        # 5. CONCLUSIÓN
        pdf.set_font('Arial', 'B', 11); pdf.set_fill_color(240)
        pdf.cell(0, 8, " 5. CONCLUSIÓN DIAGNÓSTICA", 0, 1, 'L', fill=True)
        pdf.ln(3)
        pdf.set_font('Arial', '', 10)
        texto = f"El desempeño fonológico corresponde a un rango de {diag}."
        if z_score is not None: 
            texto += f" Puntaje Z global: {z_score:+.2f} DE."
            
            # --- LÓGICA INTELIGENTE AÑADIDA PARA ESTRUCTURA ---
            # Si el puntaje Z de Estructura es mayor a 2 (Déficit), se añade el párrafo automático.
            z_e_val = (e - stats["E"][0]) / stats["E"][1]
            if z_e_val > 2:
                texto += "\n\nSe observa un predominio de procesos de simplificación de la estructura silábica, lo que sugiere dificultades en la metría de la palabra y grupos consonánticos."
            
        pdf.multi_cell(0, 5, texto.encode('latin-1','replace').decode('latin-1'))

        # =======================================================
        # PÁGINA 2: HOJA DE RESPUESTAS REPLICA (EN UNA SOLA PÁGINA)
        # =======================================================
        pdf.add_page()
        pdf.set_margins(10, 10, 10)
        
        # --- ENCABEZADO REORGANIZADO (TÍTULO PRIMERO) ---
        
        # TÍTULO CENTRAL
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 6, "HOJA DE RESPUESTAS TEPROSIF-R", 0, 1, 'C')
        pdf.set_font('Arial', '', 8)
        pdf.cell(0, 4, "(Ma. M. Pavez - M. Maggiolo - C. J. Coloma)", 0, 1, 'C')
        pdf.ln(4)
        
        # Fila 1: Nombre y F.N.
        pdf.set_font('Arial', '', 9)
        pdf.cell(15, 6, "Nombre:", 0, 0, 'L')
        pdf.cell(110, 6, nombre.encode('latin-1','replace').decode('latin-1'), "B", 0, 'L') 
        pdf.cell(10, 6, "F.N:", 0, 0, 'L')
        pdf.cell(55, 6, str(fecha_nac), "B", 1, 'L') 
        
        pdf.ln(2)
        
        # Fila 2: Edad, Examinador, Fecha
        pdf.cell(12, 6, "Edad:", 0, 0)
        pdf.cell(40, 6, edad_txt.encode('latin-1','replace').decode('latin-1'), "B", 0)
        pdf.cell(22, 6, "Examinador:", 0, 0)
        pdf.cell(65, 6, "", "B", 0) 
        pdf.cell(12, 6, "Fecha:", 0, 0)
        pdf.cell(39, 6, str(fecha_eval), "B", 1)
        pdf.ln(4) # Menos espacio para ahorrar hoja

        # --- TABLA DE REGISTRO COMPRIMIDA ---
        w_pal = 35; w_reg = 50; w_e = 18; w_a = 18; w_s = 18; w_tot = 15; w_obs = 35
        
        # Encabezados
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(255)
        
        # Altura reducida de cabecera (6mm)
        pdf.cell(w_pal, 6, "ITEM", 1, 0, 'C')
        pdf.cell(w_reg, 6, "REGISTRO", 1, 0, 'C')
        pdf.cell(w_e, 6, "E. SILAB.", 1, 0, 'C') 
        pdf.cell(w_a, 6, "ASIMIL.", 1, 0, 'C')
        pdf.cell(w_s, 6, "SUSTIT.", 1, 0, 'C')
        pdf.cell(w_tot, 6, "TOTAL", 1, 0, 'C')
        pdf.cell(w_obs, 6, "O.RESP (*)", 1, 1, 'C')
        
        pdf.set_font('Arial', '', 8) # Letra más pequeña para que entre
        
        for i, item_full in enumerate(lista_items):
            # Obtener datos usando la clave correcta
            k_type = f"type_{i}"; k_ok = f"ok_{i}"; k_in = f"in_{i}"
            k_e = f"e_{i}"; k_a = f"a_{i}"; k_s = f"s_{i}"
            
            parts = item_full.split(". ")
            num_str = parts[0]
            word_str = parts[1].upper()
            
            tipo_resp = estados_sesion.get(k_type, "Respuesta Válida")
            es_correcto = estados_sesion.get(k_ok, False)
            raw_input = estados_sesion.get(k_in, "")
            
            # --- CORRECCIÓN: USAR ALFABETO NORMAL Y MINÚSCULA ---
            if raw_input:
                transcripcion = raw_input.lower().strip() # Solo minúscula, sin fonética rara
            else:
                transcripcion = ""
                
            val_e = estados_sesion.get(k_e, 0)
            val_a = estados_sesion.get(k_a, 0)
            val_s = estados_sesion.get(k_s, 0)
            
            txt_reg = ""; txt_e = ""; txt_a = ""; txt_s = ""; txt_tot = ""; txt_obs = ""
            
            if tipo_resp != "Respuesta Válida":
                txt_obs = tipo_resp 
                txt_reg = "-"
            elif es_correcto:
                # --- AQUÍ ESTÁ LA SOLUCIÓN AL SIGNO DE INTERROGACIÓN ---
                # Si es correcto, escribimos la palabra original en minúscula
                txt_reg = word_str.lower()
                txt_e = "0"; txt_a = "0"; txt_s = "0"; txt_tot = "0"
            else:
                txt_reg = transcripcion 
                txt_e = str(val_e) if val_e > 0 else ""
                txt_a = str(val_a) if val_a > 0 else ""
                txt_s = str(val_s) if val_s > 0 else ""
                suma = val_e + val_a + val_s
                txt_tot = str(suma) if suma > 0 else ""
                
            # Altura reducida de fila (5mm)
            h_row = 5
            pdf.cell(w_pal, h_row, f"{num_str}. {word_str.encode('latin-1','replace').decode('latin-1')}", 1, 0, 'L')
            pdf.cell(w_reg, h_row, txt_reg.encode('latin-1','replace').decode('latin-1'), 1, 0, 'C')
            pdf.cell(w_e, h_row, txt_e, 1, 0, 'C')
            pdf.cell(w_a, h_row, txt_a, 1, 0, 'C')
            pdf.cell(w_s, h_row, txt_s, 1, 0, 'C')
            pdf.set_fill_color(240)
            pdf.cell(w_tot, h_row, txt_tot, 1, 0, 'C', fill=True)
            pdf.set_fill_color(255)
            pdf.cell(w_obs, h_row, txt_obs, 1, 1, 'C')
            
            # Corte visual si es barrido (Compacto)
            if i == 14:
                pdf.set_font('Arial', 'B', 7)
                pdf.cell(w_pal + w_reg, 5, "TOTAL BARRIDO", 1, 0, 'R')
                pdf.set_fill_color(200)
                pdf.cell(w_e+w_a+w_s+w_tot+w_obs, 5, "", 1, 1, 'C', fill=True)
                pdf.set_fill_color(255)
                pdf.set_font('Arial', '', 8)

        pdf.ln(2)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(w_pal + w_reg + w_e + w_a + w_s, 6, "TOTAL TEPROSIF COMPLETO:", 1, 0, 'R')
        pdf.cell(w_tot, 6, str(total), 1, 1, 'C')
        pdf.ln(3)
        
        pdf.set_font('Arial', '', 6) # Letra pequeña para leyenda
        pdf.multi_cell(0, 3, "(*) OTRAS RESPUESTAS: (NR) No responde, (NT) No transcribible, (OP) Otra palabra.", 0, 'L')
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(0, 5, "__________________________", 0, 1, 'R')
        pdf.cell(0, 5, "FIRMA Y TIMBRE              ", 0, 1, 'R')

        return pdf.output(dest="S").encode("latin-1")

# ==========================================
# GESTIÓN DE SESIONES (GUARDAR Y CARGAR PROGRESO)
# ==========================================

def guardar_progreso(nombre, estado_actual):
    """Guarda el estado completo de la sesión en un archivo JSON"""
    if not nombre: return
    # Filtramos solo las claves que nos interesan (widgets y configuración)
    datos_a_guardar = {
        k: v for k, v in estado_actual.items() 
        if k.startswith(("type_", "ok_", "in_", "e_", "a_", "s_")) or k == "modo"
    }
    # Añadimos metadatos extra
    datos_a_guardar["_timestamp"] = str(date.today())
    datos_a_guardar["_paciente"] = nombre
    
    # Nombre de archivo seguro
    safe_name = "".join([c for c in nombre if c.isalnum() or c in (' ', '_')]).strip().replace(" ", "_")
    filename = f"sesion_{safe_name}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(datos_a_guardar, f)
    return filename

def cargar_progreso(archivo):
    """Carga un archivo JSON y actualiza el session_state"""
    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)
    
    # Actualizar session_state
    for k, v in datos.items():
        if not k.startswith("_"): # Ignorar metadatos internos
            st.session_state[k] = v
    
    return True

def listar_sesiones():
    """Busca archivos .json de sesiones guardadas"""
    return glob.glob("sesion_*.json")

# ==========================================
# INTERFAZ GRÁFICA
# ==========================================

with st.sidebar:
    st.markdown("### 🗣️ TEPROSIF-R Pro")
    st.markdown("---")
    side_ph = st.empty()
    st.markdown("---")
    
    # --- NUEVA SECCIÓN: GUÍA CLÍNICA EXTENSA ---
    with st.expander("📘 Guía Clínica y Reglas", expanded=False):
        st.markdown(GUIA_PROCEDIMIENTOS)
    
    st.markdown("---")
    
    # --- GESTIÓN DE SESIONES (NUEVO) ---
    st.markdown("#### 💾 Gestión de Sesiones")
    
    # 1. Guardar
    st.caption("Guardar progreso actual para continuar después:")
    if st.button("Guardar Progreso", use_container_width=True):
        if "nombre_paciente_temp" in st.session_state and st.session_state.nombre_paciente_temp:
            f = guardar_progreso(st.session_state.nombre_paciente_temp, st.session_state)
            if f: st.success(f"Guardado en: {f}")
        else:
            st.warning("Ingrese el nombre del paciente primero.")

    st.markdown("---")

    # 2. Cargar
    st.caption("Cargar una evaluación anterior:")
    archivos = listar_sesiones()
    if archivos:
        archivo_sel = st.selectbox("Seleccionar archivo", archivos, format_func=lambda x: x.replace("sesion_", "").replace(".json", "").replace("_", " "))
        if st.button("Cargar Sesión", type="primary", use_container_width=True):
            if cargar_progreso(archivo_sel):
                st.success("¡Sesión cargada! La página se recargará.")
                st.rerun()
    else:
        st.info("No hay sesiones guardadas.")
        
    st.markdown("---")
    if not fpdf_available: st.error("⚠️ Falta FPDF. Instala con: pip install fpdf")

st.markdown('<div class="section-header">👤 Datos del Paciente</div>', unsafe_allow_html=True)
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    # Vinculamos el input con session_state para poder usarlo al guardar
    nombre = c1.text_input("Nombre Completo", key="nombre_paciente_temp")
    fecha_nac = c2.date_input("Fecha Nacimiento", value=date(2020,1,1))
    sexo = c3.selectbox("Sexo", ["Masculino", "Femenino"])
    fecha_eval = c4.date_input("Fecha Evaluación", value=date.today())
    anos, meses = calcular_edad_exacta(fecha_nac, fecha_eval)
    st.markdown(f'<div class="age-display">🎂 {anos} años, {meses} meses</div>', unsafe_allow_html=True)

st.write("---")
st.markdown('<div class="section-header">📋 Evaluación</div>', unsafe_allow_html=True)
c_m1, c_m2 = st.columns(2)
if c_m1.button("🚀 Barrido (15)", use_container_width=True, type="primary"): st.session_state.modo = "Barrido"
if c_m2.button("📝 Completo (37)", use_container_width=True): st.session_state.modo = "Completo"
modo = st.session_state.get("modo", "Completo")
lista = PALABRAS_TEST[:15] if modo == "Barrido" else PALABRAS_TEST
st.info(f"Modo: **{modo}**")

total_puntos = 0; s_e = 0; s_a = 0; s_s = 0; reporte = []

st.write("---")
for i, p_raw in enumerate(lista):
    parts = p_raw.split(". ")
    num, meta_w = parts[0], parts[1]
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 1.5, 1])
        c1.markdown(f'<div style="font-size:1.3rem; font-weight:700;">{num}. {meta_w.upper()}</div>', unsafe_allow_html=True)
        
        # Selector de Respuesta (Clave para "Otras Respuestas")
        resp_type = c2.selectbox(
            "Tipo", 
            ["Respuesta Válida", "NR", "NT", "OP"], 
            key=f"type_{i}", 
            label_visibility="collapsed"
        )
        is_valid = (resp_type == "Respuesta Válida")
        
        ok = c3.checkbox("✅ Correcto", key=f"ok_{i}", disabled=not is_valid)
        
        user_in = st.text_input("Transcripción:", key=f"in_{i}", disabled=(ok or not is_valid))
        
        ia_str = ""
        if user_in and not ok and is_valid:
            mf = texto_a_fonemas(meta_w)
            pf = texto_a_fonemas(user_in)
            
            # DIFF VISUAL
            meta_info = METADATA_PALABRAS.get(num, {})
            idx_tonic = meta_info.get('tonic', -1) if meta_info else -1
            meta_html, prod_html = generar_diff_visual(mf, pf, idx_tonic)
            
            st.markdown(f"""
            <div class="syllable-container">
                <div class="syl-row">
                    <div class="syl-label">META:</div>
                    <div>{meta_html}</div>
                </div>
                <div class="syl-row">
                    <div class="syl-label">NIÑO:</div>
                    <div>{prod_html}</div>
                </div>
                <div class="diff-legend">
                    <div class="diff-legend-item"><span class="diff-legend-box" style="background-color:#ffcdd2;"></span><span>Omitido</span></div>
                    <div class="diff-legend-item"><span class="diff-legend-box" style="background-color:#c8e6c9;"></span><span>Agregado</span></div>
                    <div class="diff-legend-item"><span class="diff-legend-box" style="background-color:#fff59d;"></span><span>Cambiado</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if len(pf) > len(mf) * 2 or len(pf) < len(mf) * 0.5:
                st.warning("⚠️ La transcripción parece muy diferente. Verifica si es correcta.")
            
            if mf != pf:
                sugs = analizar_procesos(mf, pf, num)
                if sugs:
                    ia_str = ", ".join(sugs)
                    html = '<div class="ia-box"><span class="ia-title">🔍 Análisis Sugerido:</span>'
                    for cod in sugs:
                        n = NOMBRES_PROCESOS.get(cod, "?")
                        d = DEFINICIONES.get(cod, "")
                        bg = "bg-s"
                        if "E." in cod: bg = "bg-e"
                        if "A." in cod: bg = "bg-a"
                        if "A." in cod: bg = "bg-a" # Duplicado intencional para asegurar lógica
                        if "S." in cod: bg = "bg-s"
                        
                        html += f'<div class="ia-item"><span class="ptag {bg}">{cod}</span><strong>{n}</strong><span class="desc">{d}</span></div>'
                    html += '</div>'
                    st.markdown(html, unsafe_allow_html=True)

        st.write("")
        c_e, c_a, c_s = st.columns(3)
        with c_e:
            st.markdown('<div class="counter-box c-purple"><span class="counter-label">ESTRUCTURA</span>', unsafe_allow_html=True)
            v_e = st.number_input("E", 0, 10, key=f"e_{i}", label_visibility="collapsed", disabled=(ok or not is_valid))
            st.markdown('</div>', unsafe_allow_html=True)
        with c_a:
            st.markdown('<div class="counter-box c-blue"><span class="counter-label">ASIMILACIÓN</span>', unsafe_allow_html=True)
            v_a = st.number_input("A", 0, 10, key=f"a_{i}", label_visibility="collapsed", disabled=(ok or not is_valid))
            st.markdown('</div>', unsafe_allow_html=True)
        with c_s:
            st.markdown('<div class="counter-box c-red"><span class="counter-label">SUSTITUCIÓN</span>', unsafe_allow_html=True)
            v_s = st.number_input("S", 0, 10, key=f"s_{i}", label_visibility="collapsed", disabled=(ok or not is_valid))
            st.markdown('</div>', unsafe_allow_html=True)

        # Lógica de Reporte
        if not is_valid:
             reporte.append({"Palabra": meta_w, "Prod": resp_type, "Pts": "N/A", "IA": "-"})
        elif not ok:
            s_e += v_e; s_a += v_a; s_s += v_s
            pts = v_e + v_a + v_s
            total_puntos += pts
            if pts > 0 or user_in:
                reporte.append({"Palabra": meta_w, "Prod": user_in, "Pts": f"E:{v_e} A:{v_a} S:{v_s}", "IA": ia_str})

diag_txt, diag_color, de_txt, z_score_val, stats_norma = obtener_diagnostico(total_puntos, anos, modo)
with side_ph.container():
    st.markdown(f"""
    <div style="background:white; padding:15px; border-radius:10px; border:1px solid #ddd; text-align:center;">
        <h5 style="margin:0; color:#888;">TOTAL</h5>
        <h1 style="margin:0; font-size:3rem; color:#333;">{total_puntos}</h1>
        <div style="font-size:0.8rem; margin-top:10px;">
            <span style="color:#9c27b0;">E: {s_e}</span> | <span style="color:#1976d2;">A: {s_a}</span> | <span style="color:#d32f2f;">S: {s_s}</span>
        </div>
    </div>
    <div class="diag-card {diag_color}">
        <strong>{diag_txt}</strong><br><small>{de_txt}</small>
    </div>
    """, unsafe_allow_html=True)

if total_puntos >= 0:
    st.markdown("---")
    st.header("📊 Interpretación")
    
    if modo == "Completo" and z_score_val is not None:
        x_val = [x/10.0 for x in range(-35, 45)]
        y_val = [(1/(math.sqrt(2*math.pi)))*math.exp(-0.5*x**2) for x in x_val]
        reg = []
        for x in x_val:
            if x < 1: reg.append("Normal")
            elif x < 2: reg.append("Riesgo")
            else: reg.append("Déficit")
        
        df_g = pd.DataFrame({'z': x_val, 'y': y_val, 'r': reg})
        
        base = alt.Chart(df_g).encode(x=alt.X('z', title='Puntaje Z'), y=alt.Y('y', axis=None))
        area = base.mark_area(opacity=0.5).encode(color=alt.Color('r', scale=alt.Scale(domain=['Normal','Riesgo','Déficit'], range=['#c8e6c9','#ffe0b2','#ffcdd2']), legend=alt.Legend(title="Estado", orient="bottom")))
        line = base.mark_line(color='black', strokeWidth=1)
        rule = alt.Chart(pd.DataFrame({'z': [z_score_val]})).mark_rule(color='black', size=2, strokeDash=[5,5]).encode(x='z')
        text = alt.Chart(pd.DataFrame({'z': [z_score_val], 't': ['PACIENTE']})).mark_text(align='left', dx=5, dy=-100, color='black', fontWeight='bold').encode(x='z', text='t')
        
        st.altair_chart((area+line+rule+text).properties(height=350).configure(background='white').configure_axis(labelColor='black', titleColor='black').configure_legend(labelColor='black', titleColor='black').configure_view(strokeWidth=0), use_container_width=True)

    # --- CAMPO DE OBSERVACIONES AGREGADO ---
    observaciones = st.text_area("Observaciones Generales / Comportamiento", height=100, placeholder="Escriba aquí observaciones cualitativas (ej: fatiga, cooperación, atención)...")

    if nombre and fpdf_available:
        try:
            edad_str = f"{anos} años, {meses} meses"
            # PASAMOS 'observaciones' a la función
            pdf_data = crear_pdf_avanzado(nombre, fecha_nac, edad_str, fecha_eval, total_puntos, s_e, s_a, s_s, diag_txt, z_score_val, modo, stats_norma, lista, st.session_state, observaciones)
            st.download_button("📄 DESCARGAR INFORME CLÍNICO (PDF)", pdf_data, f"Informe_{nombre}.pdf", "application/pdf", type="primary", use_container_width=True)
        except Exception as e:
            st.error(f"Error PDF: {e}")