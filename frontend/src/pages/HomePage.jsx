import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "./components/ui/button";
import { Textarea } from "./components/ui/textarea";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Switch } from "./components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./components/ui/collapsible";
import { 
  Dog, Cat, Stethoscope, Settings, Loader2, ArrowRight, 
  FlaskConical, ChevronDown, FileQuestion, Beaker
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function HomePage() {
  const navigate = useNavigate();
  const [problemas, setProblemas] = useState("");
  const [especie, setEspecie] = useState("perro");
  const [loading, setLoading] = useState(false);
  const [loadingCaso, setLoadingCaso] = useState(false);
  const [labOpen, setLabOpen] = useState(false);
  
  // Datos de laboratorio
  const [laboratorio, setLaboratorio] = useState({
    urea: "",
    creatinina: "",
    sdma: "",
    fosforo: "",
    potasio: "",
    densidad_urinaria: "",
    proteinuria: false
  });

  const handleLabChange = (field, value) => {
    setLaboratorio(prev => ({ ...prev, [field]: value }));
  };

  const buildLabData = () => {
    const lab = {};
    if (laboratorio.urea) lab.urea = parseFloat(laboratorio.urea);
    if (laboratorio.creatinina) lab.creatinina = parseFloat(laboratorio.creatinina);
    if (laboratorio.sdma) lab.sdma = parseFloat(laboratorio.sdma);
    if (laboratorio.fosforo) lab.fosforo = parseFloat(laboratorio.fosforo);
    if (laboratorio.potasio) lab.potasio = parseFloat(laboratorio.potasio);
    if (laboratorio.densidad_urinaria) lab.densidad_urinaria = parseFloat(laboratorio.densidad_urinaria);
    if (laboratorio.proteinuria) lab.proteinuria = laboratorio.proteinuria;
    
    return Object.keys(lab).length > 0 ? lab : null;
  };

  const handleAnalizar = async () => {
    if (!problemas.trim()) {
      toast.error("Por favor, ingresa al menos un problema");
      return;
    }

    setLoading(true);
    try {
      const labData = buildLabData();
      const requestData = {
        problemas: problemas,
        especie: especie,
        laboratorio: labData
      };
      
      const response = await axios.post(`${API}/analizar`, requestData);
      
      sessionStorage.setItem("vetEjesResults", JSON.stringify(response.data));
      sessionStorage.setItem("vetEjesRequest", JSON.stringify(requestData));
      
      // Dismiss any existing toasts before navigation
      toast.dismiss();
      
      navigate("/resultados");
    } catch (error) {
      console.error("Error al analizar:", error);
      const errorMsg = error.response?.data?.detail || "Error al procesar el análisis";
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const cargarCasoEjemplo = async () => {
    setLoadingCaso(true);
    try {
      const response = await axios.get(`${API}/caso-ejemplo`);
      const caso = response.data;
      
      setProblemas(caso.problemas);
      setEspecie(caso.especie);
      setLaboratorio({
        urea: caso.laboratorio.urea?.toString() || "",
        creatinina: caso.laboratorio.creatinina?.toString() || "",
        sdma: caso.laboratorio.sdma?.toString() || "",
        fosforo: caso.laboratorio.fosforo?.toString() || "",
        potasio: caso.laboratorio.potasio?.toString() || "",
        densidad_urinaria: caso.laboratorio.densidad_urinaria?.toString() || "",
        proteinuria: caso.laboratorio.proteinuria || false
      });
      setLabOpen(true);
      
      toast.success(`Caso cargado: ${caso.nombre}`);
    } catch (error) {
      console.error("Error al cargar caso:", error);
      toast.error("Error al cargar el caso ejemplo");
    } finally {
      setLoadingCaso(false);
    }
  };

  return (
    <div className="split-screen">
      {/* Left: Form Section */}
      <div className="form-section bg-white overflow-y-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-800 rounded-xl flex items-center justify-center">
                <Stethoscope className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                VetEjes
              </h1>
              <Badge variant="outline" className="text-xs">v2.0</Badge>
            </div>
            <Link to="/admin" data-testid="admin-link">
              <Button variant="ghost" size="sm" className="text-slate-500 hover:text-blue-800">
                <Settings className="w-4 h-4 mr-2" />
                Admin
              </Button>
            </Link>
          </div>
          
          <h2 className="text-2xl lg:text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Razonamiento Clínico por Etapas
          </h2>
          <p className="text-slate-600">
            Analiza problemas clínicos y datos de laboratorio para orientar el diagnóstico.
          </p>
        </div>

        {/* Caso Ejemplo Button */}
        <Button
          variant="outline"
          onClick={cargarCasoEjemplo}
          disabled={loadingCaso}
          className="w-full mb-6 border-dashed border-2 hover:border-blue-300 hover:bg-blue-50"
          data-testid="load-example-btn"
        >
          {loadingCaso ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <FileQuestion className="w-4 h-4 mr-2" />
          )}
          Cargar Caso Ejemplo (Gato Renal)
        </Button>

        {/* Species Selector */}
        <div className="mb-4">
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Especie del paciente
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setEspecie("perro")}
              data-testid="species-dog"
              className={`species-option ${especie === "perro" ? "selected" : ""}`}
            >
              <div className="species-icon">
                <Dog className="w-5 h-5" />
              </div>
              <span className="font-medium text-slate-700">Perro</span>
            </button>
            <button
              type="button"
              onClick={() => setEspecie("gato")}
              data-testid="species-cat"
              className={`species-option ${especie === "gato" ? "selected" : ""}`}
            >
              <div className="species-icon">
                <Cat className="w-5 h-5" />
              </div>
              <span className="font-medium text-slate-700">Gato</span>
            </button>
          </div>
        </div>

        {/* Problems Input */}
        <div className="mb-4">
          <label className="block text-sm font-semibold text-slate-700 mb-2">
            Lista de problemas
            <Badge variant="secondary" className="ml-2 font-normal text-xs">
              Un problema por línea
            </Badge>
          </label>
          <Textarea
            data-testid="problems-input"
            placeholder="Ejemplo:
PU/PD
pérdida de peso
hiporexia
vomito ocasional"
            value={problemas}
            onChange={(e) => setProblemas(e.target.value)}
            className="min-h-[140px] text-sm resize-none bg-slate-50 border-slate-200 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-800"
          />
        </div>

        {/* Laboratory Data Collapsible */}
        <Collapsible open={labOpen} onOpenChange={setLabOpen} className="mb-4">
          <CollapsibleTrigger asChild>
            <Button 
              variant="ghost" 
              className="w-full justify-between p-3 h-auto bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg"
              data-testid="lab-toggle"
            >
              <div className="flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-blue-800" />
                <span className="font-semibold text-slate-700">Datos de Laboratorio</span>
                <Badge variant="secondary" className="text-xs">Opcional</Badge>
              </div>
              <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${labOpen ? 'rotate-180' : ''}`} />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3">
            <Card className="border-slate-200">
              <CardContent className="pt-4">
                <div className="grid grid-cols-2 gap-3">
                  {/* Urea */}
                  <div>
                    <Label className="text-xs text-slate-600">Urea (mg/dL)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="Normal: 20-60"
                      value={laboratorio.urea}
                      onChange={(e) => handleLabChange("urea", e.target.value)}
                      className="h-9 text-sm"
                      data-testid="lab-urea"
                    />
                  </div>
                  
                  {/* Creatinina */}
                  <div>
                    <Label className="text-xs text-slate-600">Creatinina (mg/dL)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="Normal: 0.8-1.6"
                      value={laboratorio.creatinina}
                      onChange={(e) => handleLabChange("creatinina", e.target.value)}
                      className="h-9 text-sm"
                      data-testid="lab-creatinina"
                    />
                  </div>
                  
                  {/* SDMA */}
                  <div>
                    <Label className="text-xs text-slate-600">SDMA (μg/dL)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="Normal: <18"
                      value={laboratorio.sdma}
                      onChange={(e) => handleLabChange("sdma", e.target.value)}
                      className="h-9 text-sm"
                      data-testid="lab-sdma"
                    />
                  </div>
                  
                  {/* Fósforo */}
                  <div>
                    <Label className="text-xs text-slate-600">Fósforo (mg/dL)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="Normal: 3-6"
                      value={laboratorio.fosforo}
                      onChange={(e) => handleLabChange("fosforo", e.target.value)}
                      className="h-9 text-sm"
                      data-testid="lab-fosforo"
                    />
                  </div>
                  
                  {/* Potasio */}
                  <div>
                    <Label className="text-xs text-slate-600">Potasio (mEq/L)</Label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="Normal: 3.5-5.5"
                      value={laboratorio.potasio}
                      onChange={(e) => handleLabChange("potasio", e.target.value)}
                      className="h-9 text-sm"
                      data-testid="lab-potasio"
                    />
                  </div>
                  
                  {/* Densidad Urinaria */}
                  <div>
                    <Label className="text-xs text-slate-600">Densidad Urinaria</Label>
                    <Input
                      type="number"
                      step="0.001"
                      placeholder="Normal: >1.035"
                      value={laboratorio.densidad_urinaria}
                      onChange={(e) => handleLabChange("densidad_urinaria", e.target.value)}
                      className="h-9 text-sm"
                      data-testid="lab-densidad"
                    />
                  </div>
                </div>
                
                {/* Proteinuria Switch */}
                <div className="flex items-center justify-between mt-4 p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Beaker className="w-4 h-4 text-slate-500" />
                    <Label className="text-sm text-slate-700">Proteinuria presente</Label>
                  </div>
                  <Switch
                    checked={laboratorio.proteinuria}
                    onCheckedChange={(checked) => handleLabChange("proteinuria", checked)}
                    data-testid="lab-proteinuria"
                  />
                </div>
                
                <p className="text-xs text-slate-500 mt-3">
                  Los datos de laboratorio modifican el peso de los ejes y pueden establecer jerarquías (primario/secundario).
                </p>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>

        {/* Submit Button */}
        <Button
          data-testid="analyze-button"
          onClick={handleAnalizar}
          disabled={loading || !problemas.trim()}
          className="w-full h-12 text-base font-semibold bg-blue-800 hover:bg-blue-900 active:scale-[0.98] transition-transform"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              Analizando...
            </>
          ) : (
            <>
              Analizar caso clínico
              <ArrowRight className="w-5 h-5 ml-2" />
            </>
          )}
        </Button>

        <p className="mt-4 text-center text-xs text-slate-400">
          Sistema de apoyo al razonamiento clínico veterinario
        </p>
      </div>

      {/* Right: Hero Section */}
      <div className="hero-section">
        <img 
          src="https://images.pexels.com/photos/6234607/pexels-photo-6234607.jpeg"
          alt="Veterinario examinando mascota"
          className="hero-image"
        />
        <div className="hero-overlay" />
        <div className="absolute bottom-8 left-8 right-8 glass rounded-xl p-6">
          <h3 className="text-xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Razonamiento clínico estructurado
          </h3>
          <p className="text-slate-600 text-sm">
            Observa cómo los datos objetivos (laboratorio) modifican la jerarquía de ejes diagnósticos, 
            sin generar diagnósticos definitivos.
          </p>
        </div>
      </div>
    </div>
  );
}
