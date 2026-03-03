# VetEjes - PRD (Product Requirements Document)

## Fecha de creación: Diciembre 2025
## Última actualización: Diciembre 2025

---

## Problema Original
App web 'VetEjes' para análisis de ejes diagnósticos veterinarios. Frontend React, Backend FastAPI, Persistencia MongoDB. Incluye formulario con textarea de problemas y selector de especie (perro/gato), motor de scoring con sinónimos y reglas, panel admin para edición de JSONs, y tests unitarios.

---

## Arquitectura

### Stack Tecnológico
- **Frontend**: React 19 + React Router + Tailwind CSS + Shadcn/UI
- **Backend**: FastAPI + Motor (async MongoDB)
- **Base de Datos**: MongoDB
- **Testing**: Pytest (19+ tests API, 16+ tests frontend)

### Estructura de Archivos
```
/app/
├── backend/
│   ├── server.py              # API FastAPI completa (v2.0)
│   ├── test_scoring.py        # Tests unitarios originales
│   └── tests/
│       └── test_vetajes_api.py # Tests API completos (19 casos)
└── frontend/src/
    ├── pages/
    │   ├── HomePage.jsx       # Formulario + datos laboratorio
    │   ├── ResultsPage.jsx    # Resultados con jerarquía
    │   └── AdminPage.jsx      # Panel de administración
    └── App.js                 # Router principal
```

---

## User Personas
1. **Veterinario Clínico**: Usa el formulario para ingresar problemas del paciente y obtener orientación diagnóstica.
2. **Administrador del Sistema**: Edita sinónimos, reglas y categorías desde el panel admin.

---

## Requerimientos Core (Estáticos)
- [x] Formulario con textarea para lista de problemas (uno por línea)
- [x] Selector de especie (perro/gato)
- [x] Endpoint POST /api/analizar con normalización de sinónimos
- [x] Cálculo de scores por eje con reglas problema→pesos
- [x] Retorno de ejes con categorías diagnósticas (DAMNIT-V)
- [x] Trazabilidad completa de reglas aplicadas
- [x] Panel admin para editar JSONs (sinónimos, reglas, categorías)
- [x] Historial de versiones en MongoDB
- [x] Tests unitarios del motor de scoring (19+ casos)
- [x] Respuestas JSON tipadas con Pydantic

---

## Lo Implementado (Diciembre 2025)

### MVP (Iteración 1) ✅
- Motor de scoring completo con normalización de sinónimos
- 15 problemas veterinarios comunes con reglas de peso
- 17 ejes diagnósticos con categorías y textos explicativos
- Endpoints: `/api/analizar`, `/api/config/{tipo}`, `/api/config/historial`
- HomePage: Split-screen con formulario profesional
- ResultsPage: Bento grid con top 4 ejes y tabs de detalles
- AdminPage: Tabs para edición de JSONs con validación

### Lógica Clínica Avanzada (Iteración 2) ✅
- **Datos de Laboratorio**: Campos para Urea, Creatinina, SDMA, Fósforo, Potasio, Densidad urinaria, Proteinuria
- **Jerarquía de Ejes**: Clasificación primario/secundario basada en reglas clínicas
- **Reglas Clínicas**: Azotemia + densidad inadecuada → Renal PRIMARIO
- **Trazabilidad Mejorada**: Contribuciones por hallazgo con tipo (problema/laboratorio)
- **Caso Ejemplo Precargado**: Gato geriátrico con ERC (demuestra jerarquía)
- **Modo Estudio/Clínico**: Toggle para mostrar/ocultar scores y detalles técnicos
- **Categorías DAMNIT-V**: Clasificación diagnóstica con códigos de mecanismo

### Exportación a PDF (Iteración 3) ✅
- **Endpoint `/api/exportar-pdf`**: Genera PDF con resultados del análisis
- **Contenido del PDF**: Header, reglas clínicas, ejes primarios/secundarios, trazabilidad, disclaimer
- **Botón en UI**: "Exportar PDF" en ResultsPage para descargar el informe

### Bug Fixes ✅
- Normalización de problemas con tildes y espacios (`pérdida de peso` → `perdida_peso`)
- Limpieza de configuración cacheada en MongoDB
- Sanitización de caracteres Unicode para PDF (→, tildes)

---

## Backlog Priorizado

### P0 (Crítico)
- ✅ Todo completado

### P1 (Importante)
- [ ] Autenticación básica para panel admin

### P2 (Deseable)
- [ ] Historial de análisis realizados
- [ ] Favoritos/templates de problemas frecuentes
- [ ] Modo oscuro
- [ ] Refactorización del backend en módulos (`core/`, `models/`, `routers/`)

---

## Tests Pasados
- **Backend**: 19/19 (100%)
- **Frontend**: 16/16 (100%)

Archivos de test:
- `/app/backend/tests/test_vetajes_api.py`
- `/app/test_reports/iteration_2.json`

---

## Próximos Pasos
1. Agregar autenticación (JWT o Google OAuth) al panel admin
2. Implementar exportación de resultados a PDF
3. Agregar más sinónimos y reglas según feedback de veterinarios
