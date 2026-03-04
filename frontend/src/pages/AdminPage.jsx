import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { ScrollArea } from "../components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { 
  Stethoscope, ArrowLeft, Save, RefreshCw, CheckCircle2, 
  XCircle, History, BookOpen, Scale, FolderTree, Loader2
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("sinonimos");
  const [sinonimos, setSinonimos] = useState("");
  const [reglas, setReglas] = useState("");
  const [categorias, setCategorias] = useState("");
  const [historial, setHistorial] = useState([]);
  const [loading, setLoading] = useState({ sinonimos: false, reglas: false, categorias: false });
  const [saving, setSaving] = useState({ sinonimos: false, reglas: false, categorias: false });
  const [versions, setVersions] = useState({ sinonimos: 0, reglas: 0, categorias: 0 });
  const [jsonValid, setJsonValid] = useState({ sinonimos: true, reglas: true, categorias: true });

  const fetchConfig = async (tipo) => {
    setLoading(prev => ({ ...prev, [tipo]: true }));
    try {
      const response = await axios.get(`${API}/config/${tipo}`);
      const jsonStr = JSON.stringify(response.data.contenido, null, 2);
      
      if (tipo === "sinonimos") {
        setSinonimos(jsonStr);
      } else if (tipo === "reglas") {
        setReglas(jsonStr);
      } else {
        setCategorias(jsonStr);
      }
      
      setVersions(prev => ({ ...prev, [tipo]: response.data.version || 0 }));
      setJsonValid(prev => ({ ...prev, [tipo]: true }));
    } catch (error) {
      console.error(`Error fetching ${tipo}:`, error);
      toast.error(`Error al cargar ${tipo}`);
    } finally {
      setLoading(prev => ({ ...prev, [tipo]: false }));
    }
  };

  const fetchHistorial = async () => {
    try {
      const response = await axios.get(`${API}/config/historial`);
      setHistorial(response.data.historial);
    } catch (error) {
      console.error("Error fetching historial:", error);
    }
  };

  useEffect(() => {
    fetchConfig("sinonimos");
    fetchConfig("reglas");
    fetchConfig("categorias");
    fetchHistorial();
  }, []);

  const validateJson = (value, tipo) => {
    try {
      JSON.parse(value);
      setJsonValid(prev => ({ ...prev, [tipo]: true }));
      return true;
    } catch {
      setJsonValid(prev => ({ ...prev, [tipo]: false }));
      return false;
    }
  };

  const handleJsonChange = (value, tipo) => {
    if (tipo === "sinonimos") setSinonimos(value);
    else if (tipo === "reglas") setReglas(value);
    else setCategorias(value);
    
    validateJson(value, tipo);
  };

  const saveConfig = async (tipo) => {
    const value = tipo === "sinonimos" ? sinonimos : tipo === "reglas" ? reglas : categorias;
    
    if (!validateJson(value, tipo)) {
      toast.error("JSON inválido. Corrige los errores antes de guardar.");
      return;
    }

    setSaving(prev => ({ ...prev, [tipo]: true }));
    try {
      const contenido = JSON.parse(value);
      await axios.put(`${API}/config/${tipo}`, { contenido });
      toast.success(`${tipo.charAt(0).toUpperCase() + tipo.slice(1)} guardados correctamente`);
      fetchConfig(tipo);
      fetchHistorial();
    } catch (error) {
      console.error(`Error saving ${tipo}:`, error);
      toast.error(`Error al guardar ${tipo}`);
    } finally {
      setSaving(prev => ({ ...prev, [tipo]: false }));
    }
  };

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const EditorSection = ({ tipo, value, icon: Icon, title, description }) => (
    <Card className="bg-white">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
              <Icon className="w-5 h-5 text-blue-800" />
            </div>
            <div>
              <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                {title}
                <Badge variant="secondary">v{versions[tipo]}</Badge>
                {jsonValid[tipo] ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
              </CardTitle>
              <CardDescription>{description}</CardDescription>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchConfig(tipo)}
              disabled={loading[tipo]}
              data-testid={`refresh-${tipo}`}
            >
              <RefreshCw className={`w-4 h-4 mr-1 ${loading[tipo] ? 'animate-spin' : ''}`} />
              Recargar
            </Button>
            <Button
              size="sm"
              onClick={() => saveConfig(tipo)}
              disabled={saving[tipo] || !jsonValid[tipo]}
              className="bg-blue-800 hover:bg-blue-900"
              data-testid={`save-${tipo}`}
            >
              {saving[tipo] ? (
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-1" />
              )}
              Guardar
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Textarea
          data-testid={`editor-${tipo}`}
          value={value}
          onChange={(e) => handleJsonChange(e.target.value, tipo)}
          className={`json-editor font-mono text-sm min-h-[400px] ${
            !jsonValid[tipo] ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20' : ''
          }`}
          spellCheck={false}
        />
        {!jsonValid[tipo] && (
          <p className="mt-2 text-sm text-red-500 flex items-center gap-1">
            <XCircle className="w-4 h-4" />
            JSON inválido. Revisa la sintaxis.
          </p>
        )}
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
              <Link to="/">
                <Button variant="ghost" size="sm" className="text-slate-500 hover:text-blue-800" data-testid="back-home">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Volver al inicio
                </Button>
              </Link>
              <div className="h-6 w-px bg-slate-200" />
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-800 rounded-lg flex items-center justify-center">
                  <Stethoscope className="w-4 h-4 text-white" />
                </div>
                <span className="font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                  VetEjes
                </span>
                <Badge variant="outline">Admin</Badge>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
            Panel de Administración
          </h1>
          <p className="text-slate-600">
            Edita las configuraciones de sinónimos, reglas y categorías del sistema de análisis.
          </p>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="mb-6 bg-white border border-slate-200">
            <TabsTrigger 
              value="sinonimos" 
              className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-800"
              data-testid="tab-sinonimos"
            >
              <BookOpen className="w-4 h-4 mr-2" />
              Sinónimos
            </TabsTrigger>
            <TabsTrigger 
              value="reglas" 
              className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-800"
              data-testid="tab-reglas"
            >
              <Scale className="w-4 h-4 mr-2" />
              Reglas
            </TabsTrigger>
            <TabsTrigger 
              value="categorias" 
              className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-800"
              data-testid="tab-categorias"
            >
              <FolderTree className="w-4 h-4 mr-2" />
              Categorías
            </TabsTrigger>
            <TabsTrigger 
              value="historial" 
              className="data-[state=active]:bg-blue-50 data-[state=active]:text-blue-800"
              data-testid="tab-historial"
            >
              <History className="w-4 h-4 mr-2" />
              Historial
            </TabsTrigger>
          </TabsList>

          <TabsContent value="sinonimos" className="animate-fade-in">
            <EditorSection
              tipo="sinonimos"
              value={sinonimos}
              icon={BookOpen}
              title="Diccionario de Sinónimos"
              description="Mapeo de términos comunes a términos normalizados"
            />
          </TabsContent>

          <TabsContent value="reglas" className="animate-fade-in">
            <EditorSection
              tipo="reglas"
              value={reglas}
              icon={Scale}
              title="Reglas de Peso"
              description="Pesos por problema y eje diagnóstico"
            />
          </TabsContent>

          <TabsContent value="categorias" className="animate-fade-in">
            <EditorSection
              tipo="categorias"
              value={categorias}
              icon={FolderTree}
              title="Categorías Diagnósticas"
              description="Categorías y textos explicativos por eje"
            />
          </TabsContent>

          <TabsContent value="historial" className="animate-fade-in">
            <Card className="bg-white">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                    <History className="w-5 h-5 text-blue-800" />
                  </div>
                  <div>
                    <CardTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                      Historial de Versiones
                    </CardTitle>
                    <CardDescription>
                      Registro de todos los cambios realizados en las configuraciones
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[500px]">
                  <Table data-testid="history-table">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Versión</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Fecha</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {historial.map((item, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            <Badge variant="outline" className="capitalize">
                              {item.tipo}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-semibold">
                            v{item.version}
                          </TableCell>
                          <TableCell>
                            {item.activa ? (
                              <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                                Activa
                              </Badge>
                            ) : (
                              <Badge variant="secondary">
                                Histórica
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-slate-500">
                            {formatDate(item.created_at)}
                          </TableCell>
                        </TableRow>
                      ))}
                      {historial.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center text-slate-400 py-8">
                            No hay registros en el historial
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
