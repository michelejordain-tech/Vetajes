from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import io
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Literal
import uuid
from datetime import datetime, timezone
from fpdf import FPDF

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="VetEjes API", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== PYDANTIC MODELS ====================

class DatosLaboratorio(BaseModel):
    """Variables de laboratorio estructuradas."""
    urea: Optional[float] = None
    creatinina: Optional[float] = None
    sdma: Optional[float] = None
    fosforo: Optional[float] = None
    potasio: Optional[float] = None
    densidad_urinaria: Optional[float] = None
    proteinuria: Optional[bool] = None

class ContribucionEje(BaseModel):
    """Detalle de qué contribuyó a activar un eje."""
    hallazgo: str
    tipo: Literal["problema", "laboratorio"]
    peso: float
    descripcion: str

class CategoriaDAMNITV(BaseModel):
    """Categoría diagnóstica con clasificación DAMNIT-V."""
    nombre: str
    tipo_damnit: str  # D, A, M, N, I, T, V, O (obstructivo)
    prioridad: int

class CategoriasDiagnosticas(BaseModel):
    categorias: List[str]
    texto_explicativo: str

class CategoriasDiagnosticasV2(BaseModel):
    """Categorías con clasificación DAMNIT-V."""
    categorias: List[CategoriaDAMNITV]
    texto_explicativo: str

class EjeResult(BaseModel):
    eje: str
    score: float
    jerarquia: Literal["primario", "secundario"]
    contribuciones: List[ContribucionEje]
    categorias_diagnosticas: CategoriasDiagnosticasV2
    resumen_activacion: str

class ReglaAplicada(BaseModel):
    problema: str
    problema_normalizado: str
    peso: float
    eje: str
    tipo: Literal["problema", "laboratorio"] = "problema"

class AnalizarRequest(BaseModel):
    problemas: str
    especie: str = Field(..., pattern="^(perro|gato)$")
    laboratorio: Optional[DatosLaboratorio] = None

class AnalizarResponse(BaseModel):
    ejes_primarios: List[EjeResult]
    ejes_secundarios: List[EjeResult]
    trazabilidad: List[ReglaAplicada]
    problemas_analizados: int
    especie: str
    laboratorio_incluido: bool
    reglas_jerarquia_aplicadas: List[str]

class ConfigVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tipo: str
    contenido: Dict[str, Any]
    version: int
    activa: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ConfigUpdateRequest(BaseModel):
    contenido: Dict[str, Any]

class CasoEjemplo(BaseModel):
    id: str
    nombre: str
    descripcion: str
    problemas: str
    especie: str
    laboratorio: DatosLaboratorio
    resultado_esperado: str

# ==================== DEFAULT DATA ====================

DEFAULT_SINONIMOS = {
    "vomito": ["vomita", "vomitos", "vomitando", "devuelve", "regurgita", "regurgitacion"],
    "diarrea": ["heces_liquidas", "deposiciones_blandas", "heces_sueltas", "caca_liquida"],
    "anorexia": ["no_come", "sin_apetito", "inapetencia", "deja_comida", "rechaza_alimento"],
    "poliuria": ["orina_mucho", "mucha_orina", "orina_frecuente", "orina_excesiva", "pu"],
    "polidipsia": ["bebe_mucho", "mucha_sed", "sed_excesiva", "toma_mucha_agua", "pd"],
    "pupd": ["pu/pd", "pu_pd", "poliuria_polidipsia"],
    "letargia": ["decaido", "sin_energia", "apatico", "cansado", "debil", "somnoliento"],
    "prurito": ["se_rasca", "picazon", "rascado", "comezón", "se_lame_mucho"],
    "tos": ["tose", "tosiendo", "tos_seca", "tos_humeda"],
    "disnea": ["dificultad_respirar", "respira_mal", "jadea", "agitado", "respira_rapido"],
    "claudicacion": ["cojea", "cojera", "renguea", "no_apoya_pata"],
    "convulsiones": ["convulsiona", "ataques", "temblores", "movimientos_involuntarios"],
    "ictericia": ["amarillo", "mucosas_amarillas", "ojos_amarillos"],
    "ascitis": ["abdomen_hinchado", "panza_grande", "barriga_inflamada"],
    "alopecia": ["perdida_pelo", "calvas", "sin_pelo", "se_le_cae_pelo"],
    "fiebre": ["temperatura_alta", "caliente", "febril"],
    "perdida_peso": ["adelgazamiento", "bajo_peso", "perdio_peso", "flaco", "delgado", "pérdida_de_peso", "perdida_de_peso", "perdida_peso", "pérdida_peso"],
    "perdida_masa_muscular": ["atrofia_muscular", "musculos_debiles", "sarcopenia", "pérdida_de_masa_muscular", "perdida_de_masa_muscular", "pérdida_masa_muscular"],
    "azotemia": ["urea_alta", "creatinina_alta", "nitrogeno_elevado"],
    "proteinuria": ["proteina_en_orina", "albumina_orina"],
    "hiporexia": ["come_poco", "poco_apetito", "apetito_disminuido"]
}

DEFAULT_SINONIMOS.update({
    "deshidratacion": ["deshidratado", "deshidratacion_moderada", "deshidratacion_severa"],
    "deshidratacion_leve": ["deshidratacion_ligera", "ligeramente_deshidratado"],
    "bcs_bajo": ["bcs_4", "bcs_4/9", "bcs_3/9", "condicion_corporal_baja", "delgado"],
    "bcs_muy_bajo": ["bcs_3", "bcs_2", "bcs_1", "bcs_2/9", "bcs_1/9", "caquectico", "emaciado", "caquexia"],
    "pupd_leve": ["pu/pd_leve", "pu_pd_leve", "poliuria_leve", "polidipsia_leve"],
    "perdida_peso_progresiva": ["adelgazamiento_progresivo", "perdida_peso_cronica", "perdida_de_peso_progresiva", "pérdida_de_peso_progresiva"],
    "perdida_peso_marcada": ["perdida_peso_severa", "adelgazamiento_marcado", "perdida_de_peso_marcada", "pérdida_de_peso_marcada", "bajo_peso_severo"],
    "debilidad": ["debil", "sin_fuerza", "astenia"],
    "mucosas_palidas": ["palido", "anemia_clinica", "membranas_palidas"],
    "linfadenopatia": ["ganglios_inflamados", "linfadenomegalia", "ganglios_grandes"],
    "esplenomegalia": ["bazo_grande", "bazo_aumentado"],
    "hepatomegalia": ["higado_grande", "higado_aumentado"],
    "masa_abdominal": ["tumor_abdominal", "masa_palpable"],
    "dolor_abdominal": ["abdomen_doloroso", "sensibilidad_abdominal"],
    "distension_abdominal": ["abdomen_distendido", "abdomen_grande"],
    # Signos hipermetabólicos
    "polifagia": ["apetito_aumentado", "come_mucho", "hambre_excesiva", "apetito_voraz", "polifagico"],
    "taquicardia": ["fc_alta", "frecuencia_cardiaca_alta", "corazon_rapido", "pulso_rapido"],
    "hiperactividad": ["hiperactivo", "inquieto", "nervioso", "agitado", "no_para"],
    "pelaje_opaco": ["pelo_opaco", "pelaje_malo", "pelo_seco", "pelaje_sin_brillo", "pelo_feo"],
    "nerviosismo": ["nervioso", "ansioso", "estresado"],
    "bocio": ["nodulo_tiroideo", "tiroides_aumentada", "masa_cervical"],
    # Signos GI crónicos
    "vomitos_intermitentes": ["vomito_intermitente", "vomitos_esporadicos", "vomito_ocasional", "vomitos_ocasionales"],
    "vomitos_cronicos": ["vomito_cronico", "vomitos_persistentes", "vomitos_recurrentes"],
    "dolor_abdominal_leve": ["dolor_abdominal_ligero", "molestia_abdominal", "sensibilidad_abdominal_leve"],
    "albumina_baja": ["hipoalbuminemia", "albumina_limite_bajo", "albumina_limite", "proteinas_bajas"],
    "perdida_peso_lenta": ["adelgazamiento_lento", "perdida_peso_gradual", "perdida_de_peso_lenta", "pérdida_de_peso_lenta"],
    "pupd_moderada": ["pu/pd_moderada", "pu_pd_moderada", "poliuria_moderada", "polidipsia_moderada"],
    "apetito_normal": ["come_bien", "buen_apetito", "apetito_conservado"]
})

DEFAULT_REGLAS = {
    "vomito": {"digestivo": 3.0, "metabolico": 1.5, "infeccioso": 1.0, "renal": 1.0},
    "diarrea": {"digestivo": 3.0, "infeccioso": 2.0, "metabolico": 1.0, "parasitario": 2.0},
    "anorexia": {"digestivo": 2.0, "metabolico": 2.0, "infeccioso": 1.5, "oncologico": 1.5, "balance_energetico": 3.0},
    "poliuria": {"renal": 3.0, "metabolico": 2.5, "endocrino": 2.0},
    "polidipsia": {"renal": 2.5, "metabolico": 2.0, "endocrino": 3.0},
    "pupd": {"renal": 3.0, "endocrino": 2.5, "metabolico": 2.0, "hidrico": 2.0},
    "pupd_leve": {"endocrino": 2.0, "renal": 1.5, "metabolico": 1.5, "hidrico": 2.5},
    "letargia": {"metabolico": 2.0, "infeccioso": 1.0, "cardiovascular": 1.5, "oncologico": 1.5, "balance_energetico": 1.5},
    "prurito": {"dermatologico": 3.0, "parasitario": 2.5, "alergico": 2.5},
    "tos": {"respiratorio": 3.0, "cardiovascular": 2.0, "infeccioso": 1.5},
    "disnea": {"respiratorio": 3.0, "cardiovascular": 2.5, "metabolico": 1.0},
    "claudicacion": {"musculoesqueletico": 3.0, "neurologico": 2.0, "metabolico": 1.0},
    "convulsiones": {"neurologico": 3.0, "metabolico": 2.0, "toxico": 2.0},
    "ictericia": {"hepatico": 3.0, "hemolitico": 2.5, "infeccioso": 1.5},
    "ascitis": {"hepatico": 2.5, "cardiovascular": 2.5, "oncologico": 2.0, "renal": 1.5},
    "alopecia": {"dermatologico": 2.5, "endocrino": 2.0, "parasitario": 1.5},
    "fiebre": {"infeccioso": 3.0, "inmunomediado": 2.0, "oncologico": 1.5},
    "perdida_peso": {"balance_energetico": 3.0, "digestivo": 2.0, "oncologico": 2.0, "metabolico": 1.5, "renal": 1.5, "endocrino": 1.5},
    "perdida_peso_progresiva": {"balance_energetico": 4.0, "digestivo": 2.5, "oncologico": 2.5, "renal": 2.0, "endocrino": 2.0},
    "perdida_peso_lenta": {"digestivo": 3.0, "hepatico": 2.5, "renal": 2.0, "oncologico": 2.0, "endocrino": 1.5},
    "perdida_peso_marcada": {"hipermetabolico": 4.0, "endocrino": 3.5, "oncologico": 3.0, "digestivo": 2.0},
    "perdida_masa_muscular": {"balance_energetico": 3.0, "renal": 2.0, "oncologico": 2.0},
    "azotemia": {"renal": 5.0, "metabolico": 1.0},
    "proteinuria": {"renal": 2.0},
    "hiporexia": {"balance_energetico": 2.5, "digestivo": 2.0, "renal": 1.5, "endocrino": 1.0, "infeccioso": 0.5},
    "deshidratacion": {"hidrico": 2.5, "renal": 2.0, "digestivo": 1.5, "metabolico": 1.0},
    "deshidratacion_leve": {"hidrico": 1.5, "digestivo": 1.0, "renal": 1.0},
    "bcs_bajo": {"balance_energetico": 3.5, "digestivo": 2.0, "oncologico": 2.0, "renal": 1.5},
    "bcs_muy_bajo": {"hipermetabolico": 4.0, "balance_energetico": 4.0, "oncologico": 3.0, "endocrino": 2.5},
    "debilidad": {"metabolico": 2.0, "cardiovascular": 2.0, "neurologico": 1.5, "balance_energetico": 1.5},
    "mucosas_palidas": {"hemolitico": 3.0, "oncologico": 2.0, "cardiovascular": 1.5},
    "linfadenopatia": {"oncologico": 3.0, "infeccioso": 2.5, "inmunomediado": 2.0},
    "esplenomegalia": {"oncologico": 2.5, "infeccioso": 2.0, "hemolitico": 2.0},
    "hepatomegalia": {"hepatico": 3.0, "oncologico": 2.0, "cardiovascular": 1.5},
    "masa_abdominal": {"oncologico": 4.0, "digestivo": 2.0},
    "dolor_abdominal": {"digestivo": 3.0, "urinario": 2.0, "oncologico": 1.5},
    "dolor_abdominal_leve": {"digestivo": 2.5, "hepatico": 2.0, "urinario": 1.5},
    "distension_abdominal": {"digestivo": 2.5, "hepatico": 2.0, "cardiovascular": 2.0, "oncologico": 1.5},
    # Signos GI crónicos
    "vomitos_intermitentes": {"digestivo": 3.5, "hepatico": 2.5, "renal": 2.0, "metabolico": 1.5},
    "vomitos_cronicos": {"digestivo": 4.0, "hepatico": 2.5, "renal": 2.0, "oncologico": 2.0},
    "albumina_baja": {"digestivo": 3.0, "hepatico": 3.0, "renal": 2.0, "oncologico": 1.5},
    "hipoalbuminemia": {"digestivo": 3.0, "hepatico": 3.0, "renal": 2.0, "oncologico": 1.5},
    "pupd_moderada": {"renal": 2.5, "endocrino": 2.5, "hidrico": 2.0, "metabolico": 1.5},
    "apetito_normal": {},
    # Signos hipermetabólicos
    "polifagia": {"hipermetabolico": 4.0, "endocrino": 3.5, "digestivo": 1.0},
    "taquicardia": {"hipermetabolico": 3.0, "cardiovascular": 2.5, "endocrino": 2.0, "metabolico": 1.5},
    "hiperactividad": {"hipermetabolico": 3.5, "endocrino": 3.0, "neurologico": 1.5},
    "pelaje_opaco": {"endocrino": 2.5, "dermatologico": 2.0, "balance_energetico": 1.5, "hipermetabolico": 1.5},
    "pelaje_malo": {"endocrino": 2.5, "dermatologico": 2.0, "balance_energetico": 1.5},
    "nerviosismo": {"hipermetabolico": 2.5, "endocrino": 2.0, "neurologico": 1.5},
    "inquietud": {"hipermetabolico": 2.0, "endocrino": 1.5, "neurologico": 1.0},
    "bocio": {"endocrino": 4.0, "hipermetabolico": 3.0}
}

# Categorías con clasificación DAMNIT-V y filtro por especie
# especie puede ser: "perro", "gato", "ambos"
DEFAULT_CATEGORIAS_V2 = {
    "renal": {
        "categorias": [
            {"nombre": "Enfermedad renal crónica", "tipo_damnit": "D", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Insuficiencia renal aguda", "tipo_damnit": "A", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Pielonefritis", "tipo_damnit": "I", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Urolitiasis", "tipo_damnit": "O", "prioridad": 4, "especie": "ambos"},
            {"nombre": "Glomerulonefritis", "tipo_damnit": "A", "prioridad": 5, "especie": "ambos"},
            {"nombre": "Nefrotoxicidad", "tipo_damnit": "T", "prioridad": 6, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje renal/urinario: evalúa función de filtración, concentración urinaria y excreción."
    },
    "balance_energetico": {
        "categorias": [
            {"nombre": "Caquexia por enfermedad crónica", "tipo_damnit": "M", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Malabsorción intestinal", "tipo_damnit": "D", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Hipertiroidismo", "tipo_damnit": "M", "prioridad": 3, "especie": "gato"},
            {"nombre": "Diabetes mellitus", "tipo_damnit": "M", "prioridad": 4, "especie": "ambos"},
            {"nombre": "Neoplasia oculta", "tipo_damnit": "N", "prioridad": 5, "especie": "ambos"},
            {"nombre": "Insuficiencia pancreática exocrina", "tipo_damnit": "D", "prioridad": 6, "especie": "ambos"},
            {"nombre": "Hipoadrenocorticismo", "tipo_damnit": "M", "prioridad": 7, "especie": "perro"}
        ],
        "texto_explicativo": "Eje de balance energético: evalúa pérdida de peso, masa muscular y estado nutricional."
    },
    "hidrico": {
        "categorias": [
            {"nombre": "Deshidratación por pérdidas GI", "tipo_damnit": "M", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Deshidratación por falla renal", "tipo_damnit": "D", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Deshidratación por diabetes", "tipo_damnit": "M", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Hipoadrenocorticismo", "tipo_damnit": "M", "prioridad": 4, "especie": "perro"},
            {"nombre": "Pérdidas renales (diabetes insípida)", "tipo_damnit": "M", "prioridad": 5, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje del estado hídrico: evalúa alteraciones en el balance de agua y electrolitos."
    },
    "digestivo": {
        "categorias": [
            {"nombre": "Gastritis crónica", "tipo_damnit": "I", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Enteritis/IBD", "tipo_damnit": "A", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Pancreatitis", "tipo_damnit": "I", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Obstrucción intestinal", "tipo_damnit": "O", "prioridad": 4, "especie": "ambos"},
            {"nombre": "Neoplasia GI (linfoma)", "tipo_damnit": "N", "prioridad": 5, "especie": "ambos"},
            {"nombre": "Megaesófago", "tipo_damnit": "D", "prioridad": 6, "especie": "perro"},
            {"nombre": "Tricobezoar", "tipo_damnit": "O", "prioridad": 7, "especie": "gato"}
        ],
        "texto_explicativo": "Eje digestivo: afecciones del tracto gastrointestinal que afectan digestión y absorción."
    },
    "metabolico": {
        "categorias": [
            {"nombre": "Diabetes mellitus", "tipo_damnit": "M", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Cetoacidosis diabética", "tipo_damnit": "M", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Desequilibrio electrolítico", "tipo_damnit": "M", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Hipoglucemia", "tipo_damnit": "M", "prioridad": 4, "especie": "ambos"},
            {"nombre": "Lipidosis hepática", "tipo_damnit": "M", "prioridad": 5, "especie": "gato"}
        ],
        "texto_explicativo": "Eje metabólico: alteraciones en el equilibrio energético, hormonal y electrolítico."
    },
    "hipermetabolico": {
        "categorias": [
            {"nombre": "Hipertiroidismo", "tipo_damnit": "M", "prioridad": 1, "especie": "gato"},
            {"nombre": "Feocromocitoma", "tipo_damnit": "N", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Neoplasia oculta", "tipo_damnit": "N", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Inflamación crónica sistémica", "tipo_damnit": "I", "prioridad": 4, "especie": "ambos"},
            {"nombre": "Diabetes mellitus descompensada", "tipo_damnit": "M", "prioridad": 5, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje hipermetabólico: estados de aumento del gasto energético con pérdida de peso a pesar de apetito normal o aumentado."
    },
    "infeccioso": {
        "categorias": [
            {"nombre": "Parvovirus", "tipo_damnit": "I", "prioridad": 1, "especie": "perro"},
            {"nombre": "Moquillo", "tipo_damnit": "I", "prioridad": 2, "especie": "perro"},
            {"nombre": "Leptospirosis", "tipo_damnit": "I", "prioridad": 3, "especie": "perro"},
            {"nombre": "PIF", "tipo_damnit": "I", "prioridad": 4, "especie": "gato"},
            {"nombre": "Panleucopenia", "tipo_damnit": "I", "prioridad": 5, "especie": "gato"},
            {"nombre": "FeLV/FIV", "tipo_damnit": "I", "prioridad": 6, "especie": "gato"},
            {"nombre": "Ehrlichiosis", "tipo_damnit": "I", "prioridad": 7, "especie": "perro"},
            {"nombre": "Anaplasmosis", "tipo_damnit": "I", "prioridad": 8, "especie": "perro"},
            {"nombre": "Leishmaniasis", "tipo_damnit": "I", "prioridad": 9, "especie": "perro"}
        ],
        "texto_explicativo": "Eje infeccioso: enfermedades causadas por virus, bacterias, hongos o rickettsias."
    },
    "endocrino": {
        "categorias": [
            {"nombre": "Hipotiroidismo", "tipo_damnit": "M", "prioridad": 1, "especie": "perro"},
            {"nombre": "Hipertiroidismo", "tipo_damnit": "M", "prioridad": 2, "especie": "gato"},
            {"nombre": "Hiperadrenocorticismo (Cushing)", "tipo_damnit": "M", "prioridad": 3, "especie": "perro"},
            {"nombre": "Hipoadrenocorticismo (Addison)", "tipo_damnit": "M", "prioridad": 4, "especie": "perro"},
            {"nombre": "Diabetes insípida", "tipo_damnit": "M", "prioridad": 5, "especie": "ambos"},
            {"nombre": "Acromegalia", "tipo_damnit": "M", "prioridad": 6, "especie": "gato"}
        ],
        "texto_explicativo": "Eje endocrino: desórdenes de las glándulas que regulan el metabolismo hormonal."
    },
    "dermatologico": {
        "categorias": [
            {"nombre": "Dermatitis atópica", "tipo_damnit": "A", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Pioderma", "tipo_damnit": "I", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Dermatofitosis", "tipo_damnit": "I", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Seborrea", "tipo_damnit": "D", "prioridad": 4, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje dermatológico: condiciones que afectan piel, pelo y estructuras anexas."
    },
    "parasitario": {
        "categorias": [
            {"nombre": "Giardiasis", "tipo_damnit": "I", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Coccidiosis", "tipo_damnit": "I", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Helmintos", "tipo_damnit": "I", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Pulgas/Ácaros", "tipo_damnit": "I", "prioridad": 4, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje parasitario: infestaciones por parásitos internos o externos."
    },
    "respiratorio": {
        "categorias": [
            {"nombre": "Traqueobronquitis", "tipo_damnit": "I", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Neumonía", "tipo_damnit": "I", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Colapso traqueal", "tipo_damnit": "D", "prioridad": 3, "especie": "perro"},
            {"nombre": "Asma felino", "tipo_damnit": "A", "prioridad": 4, "especie": "gato"}
        ],
        "texto_explicativo": "Eje respiratorio: enfermedades del sistema respiratorio superior e inferior."
    },
    "cardiovascular": {
        "categorias": [
            {"nombre": "Cardiomiopatía dilatada", "tipo_damnit": "D", "prioridad": 1, "especie": "perro"},
            {"nombre": "Cardiomiopatía hipertrófica", "tipo_damnit": "D", "prioridad": 2, "especie": "gato"},
            {"nombre": "Endocardiosis valvular", "tipo_damnit": "D", "prioridad": 3, "especie": "perro"},
            {"nombre": "ICC", "tipo_damnit": "D", "prioridad": 4, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje cardiovascular: patologías del corazón y sistema circulatorio."
    },
    "neurologico": {
        "categorias": [
            {"nombre": "Epilepsia idiopática", "tipo_damnit": "A", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Enfermedad discal", "tipo_damnit": "D", "prioridad": 2, "especie": "perro"},
            {"nombre": "Meningoencefalitis", "tipo_damnit": "I", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Síndrome vestibular", "tipo_damnit": "D", "prioridad": 4, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje neurológico: alteraciones del sistema nervioso central y periférico."
    },
    "musculoesqueletico": {
        "categorias": [
            {"nombre": "Displasia de cadera", "tipo_damnit": "D", "prioridad": 1, "especie": "perro"},
            {"nombre": "Luxación patelar", "tipo_damnit": "D", "prioridad": 2, "especie": "perro"},
            {"nombre": "Artritis", "tipo_damnit": "D", "prioridad": 3, "especie": "ambos"},
            {"nombre": "Rotura LCC", "tipo_damnit": "T", "prioridad": 4, "especie": "perro"}
        ],
        "texto_explicativo": "Eje musculoesquelético: afecciones de huesos, articulaciones, músculos y ligamentos."
    },
    "hepatico": {
        "categorias": [
            {"nombre": "Hepatitis", "tipo_damnit": "I", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Lipidosis hepática", "tipo_damnit": "M", "prioridad": 2, "especie": "gato"},
            {"nombre": "Colangitis", "tipo_damnit": "I", "prioridad": 3, "especie": "gato"},
            {"nombre": "Shunt portosistémico", "tipo_damnit": "D", "prioridad": 4, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje hepático: enfermedades del hígado y vías biliares."
    },
    "hemolitico": {
        "categorias": [
            {"nombre": "AHIM", "tipo_damnit": "A", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Hemoparásitos (Babesia)", "tipo_damnit": "I", "prioridad": 2, "especie": "perro"},
            {"nombre": "Hemoparásitos (Mycoplasma)", "tipo_damnit": "I", "prioridad": 3, "especie": "gato"},
            {"nombre": "Intoxicación", "tipo_damnit": "T", "prioridad": 4, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje hemolítico: destrucción acelerada de glóbulos rojos."
    },
    "oncologico": {
        "categorias": [
            {"nombre": "Linfoma", "tipo_damnit": "N", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Mastocitoma", "tipo_damnit": "N", "prioridad": 2, "especie": "perro"},
            {"nombre": "Osteosarcoma", "tipo_damnit": "N", "prioridad": 3, "especie": "perro"},
            {"nombre": "Hemangiosarcoma", "tipo_damnit": "N", "prioridad": 4, "especie": "perro"},
            {"nombre": "Fibrosarcoma", "tipo_damnit": "N", "prioridad": 5, "especie": "gato"},
            {"nombre": "Carcinoma mamario", "tipo_damnit": "N", "prioridad": 6, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje oncológico: neoplasias malignas y benignas."
    },
    "alergico": {
        "categorias": [
            {"nombre": "DAPP", "tipo_damnit": "A", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Alergia alimentaria", "tipo_damnit": "A", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Atopia", "tipo_damnit": "A", "prioridad": 3, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje alérgico: reacciones de hipersensibilidad."
    },
    "toxico": {
        "categorias": [
            {"nombre": "Rodenticidas", "tipo_damnit": "T", "prioridad": 1, "especie": "ambos"},
            {"nombre": "AINES", "tipo_damnit": "T", "prioridad": 2, "especie": "ambos"},
            {"nombre": "Chocolate/Xilitol", "tipo_damnit": "T", "prioridad": 3, "especie": "perro"},
            {"nombre": "Lirios", "tipo_damnit": "T", "prioridad": 4, "especie": "gato"},
            {"nombre": "Permetrina", "tipo_damnit": "T", "prioridad": 5, "especie": "gato"}
        ],
        "texto_explicativo": "Eje tóxico: exposición a sustancias tóxicas."
    },
    "inmunomediado": {
        "categorias": [
            {"nombre": "Lupus", "tipo_damnit": "A", "prioridad": 1, "especie": "ambos"},
            {"nombre": "Poliartritis inmunomediada", "tipo_damnit": "A", "prioridad": 2, "especie": "ambos"},
            {"nombre": "TIM", "tipo_damnit": "A", "prioridad": 3, "especie": "ambos"}
        ],
        "texto_explicativo": "Eje inmunomediado: sistema inmune ataca tejidos propios."
    }
}

# Caso ejemplo precargado
CASO_EJEMPLO = CasoEjemplo(
    id="caso_renal_ejemplo",
    nombre="Caso Renal Clásico - Gato Geriátrico",
    descripcion="Gato de 14 años con signos clásicos de enfermedad renal crónica. Este caso demuestra cómo los datos de laboratorio modifican la jerarquía de ejes diagnósticos.",
    problemas="""PU/PD
pérdida de peso
pérdida de masa muscular
hiporexia
vomito ocasional
letargia""",
    especie="gato",
    laboratorio=DatosLaboratorio(
        urea=120.0,
        creatinina=4.2,
        sdma=28.0,
        fosforo=7.5,
        potasio=3.2,
        densidad_urinaria=1.012,
        proteinuria=True
    ),
    resultado_esperado="Eje RENAL como PRIMARIO (azotemia + densidad urinaria inadecuada). Eje BALANCE ENERGÉTICO como SECUNDARIO explicativo."
)

# ==================== REGLAS DE LABORATORIO ====================

def aplicar_reglas_laboratorio(
    laboratorio: DatosLaboratorio,
    scores: Dict[str, float],
    trazabilidad: List[ReglaAplicada],
    contribuciones_por_eje: Dict[str, List[ContribucionEje]]
) -> tuple[Dict[str, float], List[ReglaAplicada], Dict[str, List[ContribucionEje]], bool, bool]:
    """
    Aplica reglas clínicas basadas en datos de laboratorio.
    Retorna: scores actualizados, trazabilidad, contribuciones, tiene_azotemia, densidad_inadecuada
    """
    tiene_azotemia = False
    densidad_inadecuada = False
    
    if laboratorio is None:
        return scores, trazabilidad, contribuciones_por_eje, tiene_azotemia, densidad_inadecuada
    
    # Regla: Densidad urinaria ≤ 1.020 → renal +4
    if laboratorio.densidad_urinaria is not None and laboratorio.densidad_urinaria <= 1.020:
        peso = 4.0
        scores["renal"] = scores.get("renal", 0.0) + peso
        densidad_inadecuada = True
        
        trazabilidad.append(ReglaAplicada(
            problema=f"Densidad urinaria {laboratorio.densidad_urinaria}",
            problema_normalizado="densidad_urinaria_baja",
            peso=peso,
            eje="renal",
            tipo="laboratorio"
        ))
        
        if "renal" not in contribuciones_por_eje:
            contribuciones_por_eje["renal"] = []
        contribuciones_por_eje["renal"].append(ContribucionEje(
            hallazgo=f"Densidad urinaria {laboratorio.densidad_urinaria}",
            tipo="laboratorio",
            peso=peso,
            descripcion="Densidad ≤1.020 indica falla en concentración urinaria"
        ))
    
    # Detectar azotemia (urea o creatinina elevadas)
    if laboratorio.urea is not None and laboratorio.urea > 60:
        tiene_azotemia = True
    if laboratorio.creatinina is not None and laboratorio.creatinina > 1.6:
        tiene_azotemia = True
    if laboratorio.sdma is not None and laboratorio.sdma > 18:
        tiene_azotemia = True
    
    # Regla: Azotemia + densidad urinaria baja → renal +5 (eje primario)
    if tiene_azotemia and densidad_inadecuada:
        peso = 5.0
        scores["renal"] = scores.get("renal", 0.0) + peso
        
        desc_azotemia = []
        if laboratorio.urea and laboratorio.urea > 60:
            desc_azotemia.append(f"Urea {laboratorio.urea}")
        if laboratorio.creatinina and laboratorio.creatinina > 1.6:
            desc_azotemia.append(f"Creatinina {laboratorio.creatinina}")
        if laboratorio.sdma and laboratorio.sdma > 18:
            desc_azotemia.append(f"SDMA {laboratorio.sdma}")
        
        hallazgo = " + ".join(desc_azotemia) + f" + Densidad {laboratorio.densidad_urinaria}"
        
        trazabilidad.append(ReglaAplicada(
            problema=hallazgo,
            problema_normalizado="azotemia_con_densidad_inadecuada",
            peso=peso,
            eje="renal",
            tipo="laboratorio"
        ))
        
        contribuciones_por_eje["renal"].append(ContribucionEje(
            hallazgo=hallazgo,
            tipo="laboratorio",
            peso=peso,
            descripcion="Combinación patognomónica: azotemia con incapacidad de concentrar orina"
        ))
    elif tiene_azotemia:
        # Solo azotemia sin evaluar densidad
        peso = 3.0
        scores["renal"] = scores.get("renal", 0.0) + peso
        
        desc_azotemia = []
        if laboratorio.urea and laboratorio.urea > 60:
            desc_azotemia.append(f"Urea {laboratorio.urea}")
        if laboratorio.creatinina and laboratorio.creatinina > 1.6:
            desc_azotemia.append(f"Creatinina {laboratorio.creatinina}")
        if laboratorio.sdma and laboratorio.sdma > 18:
            desc_azotemia.append(f"SDMA {laboratorio.sdma}")
        
        hallazgo = " + ".join(desc_azotemia)
        
        trazabilidad.append(ReglaAplicada(
            problema=hallazgo,
            problema_normalizado="azotemia",
            peso=peso,
            eje="renal",
            tipo="laboratorio"
        ))
        
        if "renal" not in contribuciones_por_eje:
            contribuciones_por_eje["renal"] = []
        contribuciones_por_eje["renal"].append(ContribucionEje(
            hallazgo=hallazgo,
            tipo="laboratorio",
            peso=peso,
            descripcion="Azotemia indica compromiso de función renal"
        ))
    
    # Regla: Proteinuria → renal +2
    if laboratorio.proteinuria:
        peso = 2.0
        scores["renal"] = scores.get("renal", 0.0) + peso
        
        trazabilidad.append(ReglaAplicada(
            problema="Proteinuria presente",
            problema_normalizado="proteinuria",
            peso=peso,
            eje="renal",
            tipo="laboratorio"
        ))
        
        if "renal" not in contribuciones_por_eje:
            contribuciones_por_eje["renal"] = []
        contribuciones_por_eje["renal"].append(ContribucionEje(
            hallazgo="Proteinuria",
            tipo="laboratorio",
            peso=peso,
            descripcion="Pérdida de proteína en orina indica daño glomerular"
        ))
    
    # Regla: Fósforo elevado con azotemia → renal +1
    if laboratorio.fosforo is not None and laboratorio.fosforo > 6.0 and tiene_azotemia:
        peso = 1.0
        scores["renal"] = scores.get("renal", 0.0) + peso
        
        trazabilidad.append(ReglaAplicada(
            problema=f"Fósforo {laboratorio.fosforo}",
            problema_normalizado="hiperfosfatemia",
            peso=peso,
            eje="renal",
            tipo="laboratorio"
        ))
        
        contribuciones_por_eje["renal"].append(ContribucionEje(
            hallazgo=f"Fósforo {laboratorio.fosforo}",
            tipo="laboratorio",
            peso=peso,
            descripcion="Hiperfosfatemia secundaria a falla renal"
        ))
    
    # Regla: Potasio bajo → balance energético/renal
    if laboratorio.potasio is not None and laboratorio.potasio < 3.5:
        peso = 1.5
        scores["balance_energetico"] = scores.get("balance_energetico", 0.0) + peso
        
        trazabilidad.append(ReglaAplicada(
            problema=f"Potasio {laboratorio.potasio}",
            problema_normalizado="hipopotasemia",
            peso=peso,
            eje="balance_energetico",
            tipo="laboratorio"
        ))
        
        if "balance_energetico" not in contribuciones_por_eje:
            contribuciones_por_eje["balance_energetico"] = []
        contribuciones_por_eje["balance_energetico"].append(ContribucionEje(
            hallazgo=f"Potasio {laboratorio.potasio}",
            tipo="laboratorio",
            peso=peso,
            descripcion="Hipopotasemia puede indicar pérdidas o ingesta inadecuada"
        ))
    
    return scores, trazabilidad, contribuciones_por_eje, tiene_azotemia, densidad_inadecuada

# ==================== SCORING ENGINE ====================

def normalizar_problema(problema: str, sinonimos: Dict[str, List[str]]) -> str:
    """Normaliza un problema usando el diccionario de sinónimos."""
    import unicodedata
    
    def quitar_tildes(texto: str) -> str:
        return ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )
    
    problema_limpio = problema.strip().lower().replace(" ", "_")
    problema_sin_tildes = quitar_tildes(problema_limpio)
    
    # Buscar primero por coincidencia exacta
    if problema_limpio in sinonimos:
        return problema_limpio
    
    # Buscar sin tildes
    if problema_sin_tildes in sinonimos:
        return problema_sin_tildes
    
    # Buscar en sinónimos (con y sin tildes)
    for termino_normalizado, lista_sinonimos in sinonimos.items():
        sinonimos_lower = [s.lower() for s in lista_sinonimos]
        sinonimos_sin_tildes = [quitar_tildes(s.lower()) for s in lista_sinonimos]
        
        if problema_limpio in sinonimos_lower or problema_sin_tildes in sinonimos_sin_tildes:
            return termino_normalizado
    
    # Buscar coincidencias parciales (problema contiene término o viceversa)
    for termino_normalizado in sinonimos.keys():
        termino_sin_tildes = quitar_tildes(termino_normalizado)
        # Si el problema contiene el término base (ej: "deshidratación_leve" contiene "deshidratacion")
        if termino_sin_tildes in problema_sin_tildes or problema_sin_tildes in termino_sin_tildes:
            return termino_normalizado
    
    # Buscar en las reglas directamente también
    # para capturar términos que no tienen sinónimos definidos
    return problema_sin_tildes

def calcular_scores_con_contribuciones(
    problemas_normalizados: List[tuple],
    reglas: Dict[str, Dict[str, float]]
) -> tuple[Dict[str, float], List[ReglaAplicada], Dict[str, List[ContribucionEje]]]:
    """Calcula scores con contribuciones detalladas por eje."""
    scores: Dict[str, float] = {}
    trazabilidad: List[ReglaAplicada] = []
    contribuciones_por_eje: Dict[str, List[ContribucionEje]] = {}
    
    for problema_norm, problema_orig in problemas_normalizados:
        if problema_norm in reglas:
            for eje, peso in reglas[problema_norm].items():
                scores[eje] = scores.get(eje, 0.0) + peso
                
                trazabilidad.append(ReglaAplicada(
                    problema=problema_orig,
                    problema_normalizado=problema_norm,
                    peso=peso,
                    eje=eje,
                    tipo="problema"
                ))
                
                if eje not in contribuciones_por_eje:
                    contribuciones_por_eje[eje] = []
                contribuciones_por_eje[eje].append(ContribucionEje(
                    hallazgo=problema_orig,
                    tipo="problema",
                    peso=peso,
                    descripcion=f"Problema clínico: {problema_norm}"
                ))
    
    return scores, trazabilidad, contribuciones_por_eje

def determinar_jerarquia(
    scores: Dict[str, float],
    tiene_azotemia: bool,
    densidad_inadecuada: bool
) -> tuple[List[str], List[str], List[str]]:
    """
    Determina qué ejes son primarios y cuáles secundarios.
    Retorna: (ejes_primarios, ejes_secundarios, reglas_aplicadas)
    """
    reglas_aplicadas = []
    ejes_primarios = []
    ejes_secundarios = []
    
    sorted_ejes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Regla clave: Si hay azotemia + densidad inadecuada, renal es primario
    renal_es_primario = tiene_azotemia and densidad_inadecuada
    
    if renal_es_primario:
        reglas_aplicadas.append(
            "REGLA APLICADA: Azotemia + densidad urinaria inadecuada → Eje RENAL clasificado como PRIMARIO"
        )
        
        # Renal es primario, balance_energetico pasa a secundario
        if "balance_energetico" in scores:
            reglas_aplicadas.append(
                "REGLA APLICADA: Con eje renal primario → Eje BALANCE ENERGÉTICO pasa a SECUNDARIO (explicativo)"
            )
    
    for eje, score in sorted_ejes:
        if renal_es_primario:
            if eje == "renal":
                ejes_primarios.append(eje)
            elif eje == "balance_energetico":
                ejes_secundarios.append(eje)
            elif len(ejes_primarios) < 2:
                ejes_primarios.append(eje)
            else:
                ejes_secundarios.append(eje)
        else:
            # Sin regla especial, top 2 son primarios
            if len(ejes_primarios) < 2:
                ejes_primarios.append(eje)
            else:
                ejes_secundarios.append(eje)
    
    return ejes_primarios, ejes_secundarios, reglas_aplicadas

def generar_resumen_activacion(eje: str, contribuciones: List[ContribucionEje]) -> str:
    """Genera un resumen legible de qué activó el eje."""
    if not contribuciones:
        return f"Eje {eje} sin contribuciones directas detectadas."
    
    partes = []
    for c in contribuciones:
        partes.append(f"{c.hallazgo} (+{c.peso})")
    
    return f"Eje {eje} activado por: {', '.join(partes)}"

def obtener_ejes_resultado(
    scores: Dict[str, float],
    categorias: Dict[str, Any],
    contribuciones_por_eje: Dict[str, List[ContribucionEje]],
    ejes_primarios: List[str],
    ejes_secundarios: List[str],
    especie: str = "perro"
) -> tuple[List[EjeResult], List[EjeResult]]:
    """Construye los resultados de ejes con toda la información, filtrando por especie."""
    
    def filtrar_categorias_por_especie(cats: List[dict], especie: str) -> List[dict]:
        """Filtra las categorías diagnósticas según la especie del paciente."""
        return [
            c for c in cats 
            if c.get("especie", "ambos") in ["ambos", especie]
        ]
    
    def construir_eje(eje: str, jerarquia: str) -> Optional[EjeResult]:
        if eje not in scores:
            return None
        
        cat_data = categorias.get(eje, {
            "categorias": [{"nombre": "Sin categorías", "tipo_damnit": "?", "prioridad": 1, "especie": "ambos"}],
            "texto_explicativo": "Sin información disponible."
        })
        
        if isinstance(cat_data, dict):
            # Obtener y filtrar categorías por especie
            cats = cat_data.get("categorias", [])
            if cats and isinstance(cats[0], str):
                cats = [{"nombre": c, "tipo_damnit": "?", "prioridad": i+1, "especie": "ambos"} for i, c in enumerate(cats)]
            
            # Filtrar por especie
            cats_filtradas = filtrar_categorias_por_especie(cats, especie)
            
            # Crear objetos CategoriaDAMNITV (sin el campo especie que no está en el modelo)
            categorias_modelo = []
            for c in cats_filtradas:
                cat_dict = {k: v for k, v in c.items() if k != "especie"}
                if isinstance(c, dict):
                    categorias_modelo.append(CategoriaDAMNITV(**cat_dict))
                else:
                    categorias_modelo.append(c)
            
            cat_data = CategoriasDiagnosticasV2(
                categorias=categorias_modelo,
                texto_explicativo=cat_data.get("texto_explicativo", "")
            )
        
        contribuciones = contribuciones_por_eje.get(eje, [])
        resumen = generar_resumen_activacion(eje, contribuciones)
        
        return EjeResult(
            eje=eje,
            score=round(scores[eje], 2),
            jerarquia=jerarquia,
            contribuciones=contribuciones,
            categorias_diagnosticas=cat_data,
            resumen_activacion=resumen
        )
    
    primarios = [e for eje in ejes_primarios if (e := construir_eje(eje, "primario"))]
    secundarios = [e for eje in ejes_secundarios[:2] if (e := construir_eje(eje, "secundario"))]
    
    return primarios, secundarios

# ==================== DATABASE HELPERS ====================

async def get_active_config(tipo: str) -> Optional[Dict]:
    config = await db.config_versions.find_one(
        {"tipo": tipo, "activa": True},
        {"_id": 0}
    )
    return config

async def save_config(tipo: str, contenido: Dict[str, Any]) -> ConfigVersion:
    await db.config_versions.update_many(
        {"tipo": tipo, "activa": True},
        {"$set": {"activa": False}}
    )
    
    last_version = await db.config_versions.find_one(
        {"tipo": tipo},
        sort=[("version", -1)]
    )
    next_version = (last_version["version"] + 1) if last_version else 1
    
    new_config = ConfigVersion(
        tipo=tipo,
        contenido=contenido,
        version=next_version,
        activa=True
    )
    
    await db.config_versions.insert_one(new_config.model_dump())
    return new_config

async def init_default_configs():
    for tipo, contenido in [
        ("sinonimos", DEFAULT_SINONIMOS),
        ("reglas", DEFAULT_REGLAS),
        ("categorias", DEFAULT_CATEGORIAS_V2)
    ]:
        existing = await db.config_versions.find_one({"tipo": tipo})
        if not existing:
            await save_config(tipo, contenido)

# ==================== API ENDPOINTS ====================

@api_router.get("/")
async def root():
    return {"message": "VetEjes API v2.0", "status": "running"}

@api_router.post("/analizar", response_model=AnalizarResponse)
async def analizar_problemas(request: AnalizarRequest):
    """Analiza problemas clínicos y datos de laboratorio."""
    sinonimos_config = await get_active_config("sinonimos")
    reglas_config = await get_active_config("reglas")
    categorias_config = await get_active_config("categorias")
    
    sinonimos = sinonimos_config["contenido"] if sinonimos_config else DEFAULT_SINONIMOS
    reglas = reglas_config["contenido"] if reglas_config else DEFAULT_REGLAS
    categorias = categorias_config["contenido"] if categorias_config else DEFAULT_CATEGORIAS_V2
    
    problemas_raw = [p.strip() for p in request.problemas.split("\n") if p.strip()]
    
    if not problemas_raw:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un problema")
    
    problemas_normalizados = [
        (normalizar_problema(p, sinonimos), p) for p in problemas_raw
    ]
    
    # Calcular scores base con contribuciones
    scores, trazabilidad, contribuciones_por_eje = calcular_scores_con_contribuciones(
        problemas_normalizados, reglas
    )
    
    # Aplicar reglas de laboratorio
    tiene_azotemia = False
    densidad_inadecuada = False
    
    if request.laboratorio:
        scores, trazabilidad, contribuciones_por_eje, tiene_azotemia, densidad_inadecuada = \
            aplicar_reglas_laboratorio(
                request.laboratorio,
                scores,
                trazabilidad,
                contribuciones_por_eje
            )
    
    if not scores:
        raise HTTPException(
            status_code=400,
            detail="No se encontraron reglas aplicables"
        )
    
    # Determinar jerarquía
    ejes_primarios, ejes_secundarios, reglas_jerarquia = determinar_jerarquia(
        scores, tiene_azotemia, densidad_inadecuada
    )
    
    # Construir resultados (filtrados por especie)
    primarios, secundarios = obtener_ejes_resultado(
        scores, categorias, contribuciones_por_eje,
        ejes_primarios, ejes_secundarios, request.especie
    )
    
    return AnalizarResponse(
        ejes_primarios=primarios,
        ejes_secundarios=secundarios,
        trazabilidad=trazabilidad,
        problemas_analizados=len(problemas_raw),
        especie=request.especie,
        laboratorio_incluido=request.laboratorio is not None,
        reglas_jerarquia_aplicadas=reglas_jerarquia
    )

@api_router.get("/caso-ejemplo")
async def get_caso_ejemplo():
    """Retorna el caso ejemplo precargado."""
    return CASO_EJEMPLO

@api_router.post("/exportar-pdf")
async def exportar_pdf(request: AnalizarRequest):
    """Genera un PDF con los resultados del análisis."""
    
    def sanitize_text(text: str) -> str:
        """Reemplaza caracteres Unicode no soportados por Helvetica."""
        replacements = {
            '→': '->',
            '←': '<-',
            '↑': '^',
            '↓': 'v',
            '•': '-',
            '–': '-',
            '—': '-',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '…': '...',
            '≤': '<=',
            '≥': '>=',
            'á': 'a',
            'é': 'e',
            'í': 'i',
            'ó': 'o',
            'ú': 'u',
            'ñ': 'n',
            'Á': 'A',
            'É': 'E',
            'Í': 'I',
            'Ó': 'O',
            'Ú': 'U',
            'Ñ': 'N',
            'ü': 'u',
            'Ü': 'U',
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text
    
    # Primero ejecutar el análisis
    sinonimos_config = await get_active_config("sinonimos")
    reglas_config = await get_active_config("reglas")
    categorias_config = await get_active_config("categorias")
    
    sinonimos = sinonimos_config["contenido"] if sinonimos_config else DEFAULT_SINONIMOS
    reglas = reglas_config["contenido"] if reglas_config else DEFAULT_REGLAS
    categorias = categorias_config["contenido"] if categorias_config else DEFAULT_CATEGORIAS_V2
    
    problemas_raw = [p.strip() for p in request.problemas.split("\n") if p.strip()]
    
    if not problemas_raw:
        raise HTTPException(status_code=400, detail="Debe proporcionar al menos un problema")
    
    problemas_normalizados = [
        (normalizar_problema(p, sinonimos), p) for p in problemas_raw
    ]
    
    scores, trazabilidad, contribuciones_por_eje = calcular_scores_con_contribuciones(
        problemas_normalizados, reglas
    )
    
    tiene_azotemia = False
    densidad_inadecuada = False
    
    if request.laboratorio:
        scores, trazabilidad, contribuciones_por_eje, tiene_azotemia, densidad_inadecuada = \
            aplicar_reglas_laboratorio(
                request.laboratorio, scores, trazabilidad, contribuciones_por_eje
            )
    
    if not scores:
        raise HTTPException(status_code=400, detail="No se encontraron reglas aplicables")
    
    ejes_primarios, ejes_secundarios, reglas_jerarquia = determinar_jerarquia(
        scores, tiene_azotemia, densidad_inadecuada
    )
    
    primarios, secundarios = obtener_ejes_resultado(
        scores, categorias, contribuciones_por_eje, ejes_primarios, ejes_secundarios, request.especie
    )
    
    # Generar PDF
    pdf = FPDF()
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 15, "VetEjes - Analisis de Ejes Diagnosticos", ln=True, align="C")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Especie: {request.especie.capitalize()}", ln=True, align="C")
    pdf.ln(5)
    
    # Reglas de jerarquía
    if reglas_jerarquia:
        pdf.set_fill_color(254, 243, 199)
        pdf.set_text_color(146, 64, 14)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, "Reglas Clinicas Aplicadas:", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 9)
        for regla in reglas_jerarquia:
            regla_clean = sanitize_text(regla)
            pdf.cell(0, 6, f"  - {regla_clean[:80]}", ln=True, fill=True)
        pdf.ln(3)
    
    # Ejes Primarios
    if primarios:
        pdf.set_text_color(30, 64, 175)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "EJES PRIMARIOS", ln=True)
        
        for eje in primarios:
            pdf.set_fill_color(239, 246, 255)
            pdf.set_text_color(30, 64, 175)
            pdf.set_font("Helvetica", "B", 12)
            eje_nombre = eje.eje.replace("_", " ").upper()
            pdf.cell(0, 8, f"{eje_nombre} - {eje.score} pts", ln=True, fill=True)
            
            pdf.set_text_color(60, 60, 60)
            pdf.set_font("Helvetica", "", 9)
            activacion_text = sanitize_text(eje.resumen_activacion)[:100]
            pdf.cell(0, 5, f"Activacion: {activacion_text}", ln=True)
            
            if eje.contribuciones:
                pdf.set_font("Helvetica", "I", 8)
                contrib_text = ", ".join([f"{sanitize_text(c.hallazgo)} (+{c.peso})" for c in eje.contribuciones[:5]])
                pdf.cell(0, 5, f"Contribuciones: {contrib_text[:90]}", ln=True)
            
            if eje.categorias_diagnosticas and eje.categorias_diagnosticas.categorias:
                cats = [sanitize_text(c.nombre) for c in eje.categorias_diagnosticas.categorias[:4]]
                pdf.set_font("Helvetica", "", 8)
                pdf.cell(0, 5, f"Categorias DAMNIT-V: {', '.join(cats)[:80]}", ln=True)
            pdf.ln(2)
    
    # Ejes Secundarios
    if secundarios:
        pdf.set_text_color(100, 116, 139)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "EJES SECUNDARIOS", ln=True)
        
        for eje in secundarios:
            pdf.set_fill_color(248, 250, 252)
            pdf.set_text_color(71, 85, 105)
            pdf.set_font("Helvetica", "B", 11)
            eje_nombre = eje.eje.replace("_", " ").upper()
            pdf.cell(0, 7, f"{eje_nombre} - {eje.score} pts", ln=True, fill=True)
            
            pdf.set_text_color(60, 60, 60)
            pdf.set_font("Helvetica", "", 9)
            activacion_text = sanitize_text(eje.resumen_activacion)[:100]
            pdf.cell(0, 5, f"Activacion: {activacion_text}", ln=True)
            pdf.ln(2)
    
    # Trazabilidad
    pdf.ln(5)
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "TRAZABILIDAD DE HALLAZGOS", ln=True)
    
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(226, 232, 240)
    pdf.cell(60, 6, "Hallazgo", border=1, fill=True)
    pdf.cell(50, 6, "Normalizado", border=1, fill=True)
    pdf.cell(50, 6, "Eje", border=1, fill=True)
    pdf.cell(20, 6, "Peso", border=1, fill=True, ln=True)
    
    pdf.set_font("Helvetica", "", 8)
    for t in trazabilidad[:15]:
        pdf.cell(60, 5, sanitize_text(t.problema[:30]), border=1)
        pdf.cell(50, 5, sanitize_text(t.problema_normalizado[:25]), border=1)
        pdf.cell(50, 5, t.eje.replace("_", " "), border=1)
        pdf.cell(20, 5, f"+{t.peso}", border=1, ln=True)
    
    # Footer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 4, "NOTA: Este documento es una herramienta de apoyo al razonamiento clinico. No genera diagnosticos definitivos. Las decisiones clinicas deben basarse en la evaluacion completa del paciente por un profesional veterinario.")
    
    # Generar bytes
    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    
    filename = f"vetajes_analisis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/config/sinonimos")
async def get_sinonimos():
    config = await get_active_config("sinonimos")
    if not config:
        return {"contenido": DEFAULT_SINONIMOS, "version": 0, "activa": True}
    return config

@api_router.put("/config/sinonimos")
async def update_sinonimos(request: ConfigUpdateRequest):
    new_config = await save_config("sinonimos", request.contenido)
    return {"message": "Sinónimos actualizados", "version": new_config.version}

@api_router.get("/config/reglas")
async def get_reglas():
    config = await get_active_config("reglas")
    if not config:
        return {"contenido": DEFAULT_REGLAS, "version": 0, "activa": True}
    return config

@api_router.put("/config/reglas")
async def update_reglas(request: ConfigUpdateRequest):
    new_config = await save_config("reglas", request.contenido)
    return {"message": "Reglas actualizadas", "version": new_config.version}

@api_router.get("/config/categorias")
async def get_categorias():
    config = await get_active_config("categorias")
    if not config:
        return {"contenido": DEFAULT_CATEGORIAS_V2, "version": 0, "activa": True}
    return config

@api_router.put("/config/categorias")
async def update_categorias(request: ConfigUpdateRequest):
    new_config = await save_config("categorias", request.contenido)
    return {"message": "Categorías actualizadas", "version": new_config.version}

@api_router.get("/config/historial")
async def get_historial(tipo: Optional[str] = None):
    query = {"tipo": tipo} if tipo else {}
    historial = await db.config_versions.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"historial": historial}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await init_default_configs()
    logger.info("VetEjes API v2.0 iniciada correctamente")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
