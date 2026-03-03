"""
Tests unitarios del motor de scoring de VetEjes v2.0.
Incluye tests de laboratorio y jerarquía de ejes.
Ejecutar con: pytest test_scoring.py -v
"""
import pytest
from server import (
    normalizar_problema,
    calcular_scores_con_contribuciones,
    determinar_jerarquia,
    aplicar_reglas_laboratorio,
    DEFAULT_SINONIMOS,
    DEFAULT_REGLAS,
    DatosLaboratorio
)


class TestNormalizarProblema:
    """Tests para la función de normalización de problemas."""
    
    def test_problema_ya_normalizado(self):
        """Test 1: Un problema que ya está normalizado se devuelve tal cual."""
        resultado = normalizar_problema("vomito", DEFAULT_SINONIMOS)
        assert resultado == "vomito"
    
    def test_sinonimo_simple(self):
        """Test 2: Un sinónimo simple se normaliza correctamente."""
        resultado = normalizar_problema("vomita", DEFAULT_SINONIMOS)
        assert resultado == "vomito"
    
    def test_sinonimo_pupd(self):
        """Test 3: PU/PD se normaliza correctamente."""
        resultado = normalizar_problema("pu/pd", DEFAULT_SINONIMOS)
        assert resultado == "pupd"
    
    def test_problema_desconocido(self):
        """Test 4: Un problema desconocido se devuelve limpio."""
        resultado = normalizar_problema("Problema Raro", DEFAULT_SINONIMOS)
        assert resultado == "problema_raro"
    
    def test_mayusculas_minusculas(self):
        """Test 5: La normalización es case-insensitive."""
        resultado = normalizar_problema("VOMITA", DEFAULT_SINONIMOS)
        assert resultado == "vomito"


class TestCalcularScores:
    """Tests para el cálculo de scores por eje."""
    
    def test_problema_unico(self):
        """Test 6: Score correcto para un solo problema."""
        problemas = [("vomito", "vomito")]
        scores, trazabilidad, contribuciones = calcular_scores_con_contribuciones(problemas, DEFAULT_REGLAS)
        
        assert scores["digestivo"] == 3.0
        assert len(trazabilidad) == 4  # vomito afecta 4 ejes
        assert "digestivo" in contribuciones
    
    def test_multiples_problemas_mismo_eje(self):
        """Test 7: Scores se suman cuando múltiples problemas afectan el mismo eje."""
        problemas = [("vomito", "vomito"), ("diarrea", "diarrea")]
        scores, _, _ = calcular_scores_con_contribuciones(problemas, DEFAULT_REGLAS)
        
        # digestivo: 3.0 (vomito) + 3.0 (diarrea) = 6.0
        assert scores["digestivo"] == 6.0


class TestReglasLaboratorio:
    """Tests para las reglas de laboratorio."""
    
    def test_densidad_urinaria_baja(self):
        """Test 8: Densidad urinaria ≤1.020 suma +4 a renal."""
        lab = DatosLaboratorio(densidad_urinaria=1.012)
        scores = {}
        trazabilidad = []
        contribuciones = {}
        
        scores, trazabilidad, contribuciones, tiene_azotemia, densidad_inadecuada = \
            aplicar_reglas_laboratorio(lab, scores, trazabilidad, contribuciones)
        
        assert scores["renal"] == 4.0
        assert densidad_inadecuada is True
        assert any(t.problema_normalizado == "densidad_urinaria_baja" for t in trazabilidad)
    
    def test_azotemia_con_densidad_inadecuada(self):
        """Test 9: Azotemia + densidad inadecuada suma +5 adicional (regla primaria)."""
        lab = DatosLaboratorio(creatinina=4.2, densidad_urinaria=1.012)
        scores = {}
        trazabilidad = []
        contribuciones = {}
        
        scores, trazabilidad, contribuciones, tiene_azotemia, densidad_inadecuada = \
            aplicar_reglas_laboratorio(lab, scores, trazabilidad, contribuciones)
        
        # 4.0 (densidad) + 5.0 (azotemia + densidad) = 9.0
        assert scores["renal"] == 9.0
        assert tiene_azotemia is True
        assert densidad_inadecuada is True
    
    def test_proteinuria(self):
        """Test 10: Proteinuria suma +2 a renal."""
        lab = DatosLaboratorio(proteinuria=True)
        scores = {}
        trazabilidad = []
        contribuciones = {}
        
        scores, trazabilidad, contribuciones, _, _ = \
            aplicar_reglas_laboratorio(lab, scores, trazabilidad, contribuciones)
        
        assert scores["renal"] == 2.0


class TestJerarquia:
    """Tests para la determinación de jerarquía primario/secundario."""
    
    def test_renal_primario_con_azotemia_y_densidad(self):
        """Test 11: Renal es primario cuando hay azotemia + densidad inadecuada."""
        scores = {"renal": 15.0, "balance_energetico": 10.0, "digestivo": 5.0}
        
        primarios, secundarios, reglas = determinar_jerarquia(
            scores, tiene_azotemia=True, densidad_inadecuada=True
        )
        
        assert "renal" in primarios
        assert "balance_energetico" in secundarios
        assert any("PRIMARIO" in r for r in reglas)
    
    def test_balance_energetico_secundario(self):
        """Test 12: Balance energético pasa a secundario si renal es primario."""
        scores = {"renal": 15.0, "balance_energetico": 12.0, "digestivo": 5.0}
        
        primarios, secundarios, reglas = determinar_jerarquia(
            scores, tiene_azotemia=True, densidad_inadecuada=True
        )
        
        assert "balance_energetico" in secundarios
        assert any("SECUNDARIO" in r for r in reglas)
    
    def test_sin_regla_especial_top2_primarios(self):
        """Test 13: Sin regla especial, top 2 son primarios."""
        scores = {"digestivo": 10.0, "infeccioso": 8.0, "metabolico": 5.0}
        
        primarios, secundarios, reglas = determinar_jerarquia(
            scores, tiene_azotemia=False, densidad_inadecuada=False
        )
        
        assert len(primarios) == 2
        assert "digestivo" in primarios
        assert "infeccioso" in primarios
        assert "metabolico" in secundarios


class TestCasoCompleto:
    """Test de integración del caso ejemplo."""
    
    def test_caso_gato_renal(self):
        """Test 14: Caso ejemplo de gato con enfermedad renal crónica."""
        # Simular entrada del caso ejemplo
        problemas_raw = ["PU/PD", "pérdida de peso", "pérdida de masa muscular", "hiporexia", "vomito"]
        
        # Normalizar
        problemas_norm = [
            (normalizar_problema(p, DEFAULT_SINONIMOS), p) 
            for p in problemas_raw
        ]
        
        # Calcular scores base
        scores, trazabilidad, contribuciones = calcular_scores_con_contribuciones(
            problemas_norm, DEFAULT_REGLAS
        )
        
        # Aplicar laboratorio
        lab = DatosLaboratorio(
            urea=120.0,
            creatinina=4.2,
            sdma=28.0,
            fosforo=7.5,
            potasio=3.2,
            densidad_urinaria=1.012,
            proteinuria=True
        )
        
        scores, trazabilidad, contribuciones, tiene_azotemia, densidad_inadecuada = \
            aplicar_reglas_laboratorio(lab, scores, trazabilidad, contribuciones)
        
        # Determinar jerarquía
        primarios, secundarios, reglas = determinar_jerarquia(
            scores, tiene_azotemia, densidad_inadecuada
        )
        
        # Verificaciones
        assert "renal" in primarios, "Renal debe ser primario"
        assert tiene_azotemia, "Debe detectar azotemia"
        assert densidad_inadecuada, "Debe detectar densidad inadecuada"
        assert scores["renal"] > scores.get("balance_energetico", 0), "Renal debe tener mayor score"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
