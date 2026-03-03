import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { 
  Stethoscope, ArrowLeft, Dog, Cat, TrendingUp, ListChecks, 
  FileText, Activity, FlaskConical, AlertCircle, ChevronRight,
  Eye, EyeOff, Target, Layers, Download, Loader2
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Mapeo de tipos DAMNIT-V a colores y descripciones
const DAMNIT_MAP = {
  "D": { label: "Degenerativo", color: "bg-purple-100 text-purple-700" },
  "A": { label: "Anomalía/Autoinmune", color: "bg-pink-100 text-pink-700" },
  "M": { label: "Metabólico", color: "bg-amber-100 text-amber-700" },
  "N": { label: "Neoplásico", color: "bg-red-100 text-red-700" },
  "I": { label: "Infeccioso/Inflamatorio", color: "bg-green-100 text-green-700" },
  "T": { label: "Tóxico/Traumático", color: "bg-orange-100 text-orange-700" },
  "V": { label: "Vascular", color: "bg-blue-100 text-blue-700" },
  "O": { label: "Obstructivo", color: "bg-slate-100 text-slate-700" },
  "?": { label: "Sin clasificar", color: "bg-gray-100 text-gray-500" }
};

export default function ResultsPage() {
  const navigate = useNavigate();
  const [results, setResults] = useState(null);
  const [modoEstudio, setModoEstudio] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [originalRequest, setOriginalRequest] = useState(null);

  useEffect(() => {
    const storedResults = sessionStorage.getItem("vetEjesResults");
    const storedRequest = sessionStorage.getItem("vetEjesRequest");
    if (storedResults) {
      setResults(JSON.parse(storedResults));
      if (storedRequest) {
        setOriginalRequest(JSON.parse(storedRequest));
      }
    } else {
      navigate("/");
    }
  }, [navigate]);

  const handleExportPDF = async () => {
    if (!originalRequest) {
      toast.error("No se encontraron los datos originales del análisis");
      return;
    }
    
    setExporting(true);
    try {
      const response = await axios.post(`${API}/exportar-pdf`, originalRequest, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      
      // Usar window.open como alternativa más segura
      const link = document.createElement('a');
      link.href = url;
      link.download = `vetajes_analisis_${new Date().toISOString().slice(0,10)}.pdf`;
      link.style.display = 'none';
      link.click();
      
      // Limpiar URL después de un timeout
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 100);
      
      toast.success("PDF exportado correctamente");
    } catch (error) {
      console.error("Error al exportar PDF:", error);
      toast.error("Error al generar el PDF");
    } finally {
      setExporting(false);
    }
  };

  if (!results) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-slate-400">Cargando resultados...</div>
      </div>
    );
  }

  const allEjes = [...(results.ejes_primarios || []), ...(results.ejes_secundarios || [])];
  const maxScore = Math.max(...allEjes.map(e => e.score), 1);

  const getScoreColor = (score) => {
    const ratio = score / maxScore;
    if (ratio >= 0.8) return "text-blue-800";
    if (ratio >= 0.5) return "text-blue-600";
    return "text-slate-600";
  };

  const EjeCard = ({ eje, index, isPrimary }) => (
    <Card 
      className={`score-card card-hover ${isPrimary ? 'ring-2 ring-blue-800 ring-offset-2' : ''}`}
      data-testid={`eje-card-${eje.eje}`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge 
              className={isPrimary ? "bg-blue-800 text-white" : "bg-slate-200 text-slate-600"}
            >
              {isPrimary ? "PRIMARIO" : "SECUNDARIO"}
            </Badge>
            {modoEstudio && (
              <Badge variant="outline" className="text-xs">
                #{index + 1}
              </Badge>
            )}
          </div>
          <Activity className="w-5 h-5 text-slate-300" />
        </div>
        <CardTitle className="text-lg capitalize mt-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
          {eje.eje.replace(/_/g, ' ')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Score - Solo en modo estudio */}
        {modoEstudio && (
          <div className="mb-4">
            <span className={`score-value ${getScoreColor(eje.score)}`}>
              {eje.score}
            </span>
            <span className="text-sm text-slate-400 ml-1">pts</span>
            
            <div className="h-2 bg-slate-100 rounded-full overflow-hidden mt-2">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${isPrimary ? 'bg-blue-800' : 'bg-slate-400'}`}
                style={{ width: `${(eje.score / maxScore) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Resumen de activación - Siempre visible */}
        <div className="mb-4 p-3 bg-slate-50 rounded-lg">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
            <Target className="w-3 h-3 inline mr-1" />
            ¿Qué lo activó?
          </p>
          <p className="text-sm text-slate-700">
            {eje.resumen_activacion}
          </p>
        </div>

        {/* Contribuciones detalladas - Solo en modo estudio */}
        {modoEstudio && eje.contribuciones && eje.contribuciones.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Contribuciones al score
            </p>
            <div className="space-y-1">
              {eje.contribuciones.map((c, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    {c.tipo === "laboratorio" ? (
                      <FlaskConical className="w-3 h-3 text-amber-600" />
                    ) : (
                      <ChevronRight className="w-3 h-3 text-slate-400" />
                    )}
                    <span className="text-slate-600">{c.hallazgo}</span>
                  </div>
                  <Badge variant="secondary" className="text-xs font-mono">
                    +{c.peso}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Categorías - Siempre visible pero simplificado en modo clínico */}
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            <Layers className="w-3 h-3 inline mr-1" />
            Categorías diagnósticas (DAMNIT-V)
          </p>
          <div className="flex flex-wrap gap-1">
            {eje.categorias_diagnosticas?.categorias?.slice(0, modoEstudio ? 6 : 3).map((cat, i) => (
              <Badge 
                key={i} 
                className={`text-xs font-normal ${DAMNIT_MAP[cat.tipo_damnit || "?"]?.color || DAMNIT_MAP["?"].color}`}
              >
                {modoEstudio && <span className="font-bold mr-1">{cat.tipo_damnit}</span>}
                {cat.nombre || cat}
              </Badge>
            ))}
            {eje.categorias_diagnosticas?.categorias?.length > (modoEstudio ? 6 : 3) && (
              <Badge variant="secondary" className="text-xs">
                +{eje.categorias_diagnosticas.categorias.length - (modoEstudio ? 6 : 3)}
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => navigate("/")}
                data-testid="back-button"
                className="text-slate-500 hover:text-blue-800"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Nuevo análisis
              </Button>
              <div className="h-6 w-px bg-slate-200" />
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-800 rounded-lg flex items-center justify-center">
                  <Stethoscope className="w-4 h-4 text-white" />
                </div>
                <span className="font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  VetEjes
                </span>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Mode Toggle */}
              <div className="flex items-center gap-2 bg-slate-100 rounded-lg px-3 py-2">
                <EyeOff className={`w-4 h-4 ${!modoEstudio ? 'text-blue-800' : 'text-slate-400'}`} />
                <Switch
                  checked={modoEstudio}
                  onCheckedChange={setModoEstudio}
                  data-testid="mode-toggle"
                />
                <Eye className={`w-4 h-4 ${modoEstudio ? 'text-blue-800' : 'text-slate-400'}`} />
                <span className="text-sm font-medium text-slate-600 ml-1">
                  {modoEstudio ? "Estudio" : "Clínico"}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="flex items-center gap-1">
                  {results.especie === "perro" ? <Dog className="w-3 h-3" /> : <Cat className="w-3 h-3" />}
                  {results.especie}
                </Badge>
                {results.laboratorio_incluido && (
                  <Badge className="bg-amber-100 text-amber-700 flex items-center gap-1">
                    <FlaskConical className="w-3 h-3" />
                    Lab
                  </Badge>
                )}
                
                {/* Export PDF Button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleExportPDF}
                  disabled={exporting || !originalRequest}
                  data-testid="export-pdf-btn"
                  className="border-blue-200 text-blue-800 hover:bg-blue-50"
                >
                  {exporting ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  {exporting ? "Exportando..." : "Exportar PDF"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Title Section */}
        <div className="mb-6 animate-fade-in">
          <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Análisis de Ejes Diagnósticos
          </h1>
          <p className="text-slate-600">
            {results.problemas_analizados} problema{results.problemas_analizados !== 1 ? 's' : ''} analizado{results.problemas_analizados !== 1 ? 's' : ''}
            {results.laboratorio_incluido && ' • Datos de laboratorio incluidos'}
          </p>
        </div>

        {/* Reglas de jerarquía aplicadas */}
        {results.reglas_jerarquia_aplicadas && results.reglas_jerarquia_aplicadas.length > 0 && (
          <Card className="mb-6 border-amber-200 bg-amber-50" data-testid="hierarchy-rules">
            <CardContent className="pt-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                <div>
                  <p className="font-semibold text-amber-800 mb-2">Reglas clínicas aplicadas:</p>
                  <ul className="space-y-1">
                    {results.reglas_jerarquia_aplicadas.map((regla, i) => (
                      <li key={i} className="text-sm text-amber-700">{regla}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Ejes Primarios */}
        {results.ejes_primarios && results.ejes_primarios.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <Target className="w-5 h-5 text-blue-800" />
              Ejes Primarios
              <span className="text-sm font-normal text-slate-500">¿Dónde está el problema principal?</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-testid="primary-ejes">
              {results.ejes_primarios.map((eje, index) => (
                <EjeCard key={eje.eje} eje={eje} index={index} isPrimary={true} />
              ))}
            </div>
          </div>
        )}

        {/* Ejes Secundarios */}
        {results.ejes_secundarios && results.ejes_secundarios.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <Layers className="w-5 h-5 text-slate-500" />
              Ejes Secundarios
              <span className="text-sm font-normal text-slate-500">Consecuencias o factores asociados</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6" data-testid="secondary-ejes">
              {results.ejes_secundarios.map((eje, index) => (
                <EjeCard key={eje.eje} eje={eje} index={index} isPrimary={false} />
              ))}
            </div>
          </div>
        )}

        {/* Detailed Tabs - Solo en modo estudio */}
        {modoEstudio && (
          <Tabs defaultValue="categorias" className="animate-fade-in">
            <TabsList className="mb-4 bg-white border border-slate-200">
              <TabsTrigger value="categorias" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-800">
                <FileText className="w-4 h-4 mr-2" />
                Detalles DAMNIT-V
              </TabsTrigger>
              <TabsTrigger value="trazabilidad" className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-800">
                <ListChecks className="w-4 h-4 mr-2" />
                Trazabilidad Completa
              </TabsTrigger>
            </TabsList>

            <TabsContent value="categorias">
              <Card className="bg-white">
                <CardHeader>
                  <CardTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Clasificación DAMNIT-V
                  </CardTitle>
                  <CardDescription>
                    Mecanismos fisiopatológicos por categoría diagnóstica
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-4 md:grid-cols-8 gap-2 mb-6">
                    {Object.entries(DAMNIT_MAP).filter(([k]) => k !== "?").map(([key, val]) => (
                      <div key={key} className={`text-center p-2 rounded-lg ${val.color}`}>
                        <span className="font-bold text-lg">{key}</span>
                        <p className="text-xs mt-1">{val.label}</p>
                      </div>
                    ))}
                  </div>
                  <Separator className="my-4" />
                  <div className="space-y-4">
                    {allEjes.map((eje) => (
                      <div key={eje.eje} className="p-4 bg-slate-50 rounded-lg">
                        <h4 className="font-semibold capitalize mb-2">{eje.eje.replace(/_/g, ' ')}</h4>
                        <p className="text-sm text-slate-600 mb-3">
                          {eje.categorias_diagnosticas?.texto_explicativo}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {eje.categorias_diagnosticas?.categorias?.map((cat, i) => (
                            <Badge 
                              key={i} 
                              className={`${DAMNIT_MAP[cat.tipo_damnit || "?"]?.color || DAMNIT_MAP["?"].color}`}
                            >
                              <span className="font-bold mr-1">{cat.tipo_damnit}</span>
                              {cat.nombre || cat}
                              {cat.prioridad && <span className="ml-1 opacity-60">#{cat.prioridad}</span>}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="trazabilidad">
              <Card className="bg-white">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    <TrendingUp className="w-5 h-5 text-blue-800" />
                    Trazabilidad Completa
                  </CardTitle>
                  <CardDescription>
                    Cada hallazgo y su contribución al cálculo de scores
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[500px]">
                    <Table className="trace-table" data-testid="traceability-table">
                      <TableHeader>
                        <TableRow>
                          <TableHead>Tipo</TableHead>
                          <TableHead>Hallazgo Original</TableHead>
                          <TableHead>Normalizado</TableHead>
                          <TableHead>Eje</TableHead>
                          <TableHead className="text-right">Peso</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {results.trazabilidad.map((regla, index) => (
                          <TableRow key={index}>
                            <TableCell>
                              {regla.tipo === "laboratorio" ? (
                                <Badge className="bg-amber-100 text-amber-700">
                                  <FlaskConical className="w-3 h-3 mr-1" />
                                  Lab
                                </Badge>
                              ) : (
                                <Badge variant="secondary">Problema</Badge>
                              )}
                            </TableCell>
                            <TableCell className="font-medium">{regla.problema}</TableCell>
                            <TableCell>
                              <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                                {regla.problema_normalizado}
                              </code>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline" className="capitalize">
                                {regla.eje.replace(/_/g, ' ')}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right font-semibold text-blue-800">
                              +{regla.peso}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        )}

        {/* Disclaimer */}
        <Card className="mt-8 bg-slate-100 border-slate-200">
          <CardContent className="pt-4">
            <p className="text-sm text-slate-600 text-center">
              <strong>Nota:</strong> Este sistema es una herramienta de apoyo al razonamiento clínico. 
              No genera diagnósticos definitivos. Las decisiones clínicas deben basarse en la evaluación 
              completa del paciente por un profesional veterinario.
            </p>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
