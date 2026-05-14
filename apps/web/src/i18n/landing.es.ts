// apps/web/src/i18n/landing.es.ts
//
// Spanish (Latin American neutral, formal "usted") copy for the
// ChartNav public landing page.
//
// Style guide:
//   docs/website/chartnav-spanish-localization-style-guide.md
//
// Same shape as landing.en.ts. Every safety / non-goal assertion in
// English has a corresponding Spanish version with the same claim
// discipline — never stronger than the English copy, never positive
// where the English copy is negative.

import type { LandingCopy, ModuleCard, SafetyModelRow, WorkflowStage } from "./types";

const MODULES_ES: ModuleCard[] = [
  {
    id: "scribe",
    title: "Ciclo de vida de la sesión de transcripción asistida",
    body:
      "Genera un borrador estructurado a partir del texto fuente o " +
      "de una transcripción. El proveedor revisa y finaliza de forma " +
      "explícita — nunca de manera automática. Las sesiones " +
      "finalizadas son inmutables.",
  },
  {
    id: "proposals",
    title: "Revisión de propuestas para el diagrama retiniano",
    body:
      "Genera propuestas de anotación OD/OS a partir del texto de " +
      "hallazgos finalizado. Son sugerencias de solo lectura; nada " +
      "se aplica al diagrama hasta que el proveedor las aplique de " +
      "forma explícita.",
  },
  {
    id: "diagram",
    title: "Lienzo de dibujo retiniano OD/OS",
    body:
      "Anotaciones OD/OS hechas por el proveedor con coordenadas " +
      "normalizadas. Los artefactos guardados se versionan; los " +
      "artefactos firmados son inmutables en su sitio — las " +
      "ediciones crean una bifurcación explícita.",
  },
  {
    id: "summary",
    title: "Resumen en lenguaje sencillo para el paciente",
    body:
      "Borrador en lenguaje claro construido a partir del contenido " +
      "de transcripción finalizado. El proveedor edita, revisa y " +
      "finaliza. ChartNav nunca envía el resumen al paciente.",
  },
  {
    id: "brief",
    title: "Resumen clínico previo a la visita",
    body:
      "Vista derivada de los registros clínicos disponibles, con " +
      "vacíos de datos explícitos. Muestra lo que está y lo que no " +
      "está en el expediente antes de la visita. No es una decisión " +
      "clínica.",
  },
  {
    id: "queue",
    title: "Cola de revisión de acciones del proveedor",
    body:
      "Solo tareas de revisión — firmar el diagrama sin firmar, " +
      "finalizar el resumen, revisar el lenguaje del expediente. " +
      "Sugerido → aceptado → completado. Lo descartado y lo " +
      "completado son inmutables. Nunca es una orden.",
  },
  {
    id: "demo",
    title: "Modo demo guiado",
    body:
      "Capa de presentación opcional (?demo=1) con un guía de 8 " +
      "pasos del flujo de trabajo, indicaciones en pantalla y un " +
      "botón Reiniciar. Determinista por diseño; sin llamadas a la " +
      "API; sin efectos secundarios sobre el estado clínico.",
  },
  {
    id: "pilot",
    title: "Paquete de preparación para piloto",
    body:
      "Paquete de ocho documentos que cubre preparación, despliegue, " +
      "incorporación administrativa, revisión de seguridad, manual " +
      "de soporte, transición demo→piloto, limitaciones conocidas y " +
      "métricas de éxito.",
  },
];

const WORKFLOW_ES: WorkflowStage[] = [
  {
    id: "scribe",
    label: "Sesión de transcripción",
    short: "Borrador → revisión → finalización",
  },
  {
    id: "proposals",
    label: "Propuestas de hallazgos",
    short: "Sugerencias de solo lectura",
  },
  {
    id: "diagram",
    label: "Diagrama OD/OS",
    short: "Aplicar, guardar, firmar",
  },
  {
    id: "summary",
    label: "Resumen para el paciente",
    short: "Borrador revisado por el proveedor",
  },
  {
    id: "brief",
    label: "Resumen previo a la visita",
    short: "Contexto del expediente derivado",
  },
  {
    id: "queue",
    label: "Cola de revisión de acciones",
    short: "Sugerido → aceptado → completado",
  },
  {
    id: "demo",
    label: "Demo guiado",
    short: "Listo para piloto",
  },
];

const SAFETY_MODEL_ES: SafetyModelRow[] = [
  {
    state: "Borrador",
    body:
      "Todos los artefactos asistidos por IA comienzan como borrador " +
      "para que el proveedor los revise. Nada se considera final " +
      "hasta que haya un clic explícito.",
  },
  {
    state: "Revisión",
    body:
      "El proveedor edita y marca el artefacto como revisado de " +
      "forma explícita. Es requisito antes de finalizar.",
  },
  {
    state: "Finalización",
    body:
      "La finalización explícita sella el artefacto y lo vuelve " +
      "inmutable. Las nuevas ediciones a un artefacto retiniano " +
      "firmado crean una bifurcación explícita.",
  },
  {
    state: "Auditoría",
    body:
      "Cada modificación emite una fila de auditoría que contiene " +
      "solo metadatos. El cuerpo de las secciones, el texto del " +
      "resumen, el texto de la transcripción y las secciones del " +
      "resumen previo nunca llegan al registro de auditoría.",
  },
  {
    state: "Aislamiento por organización",
    body:
      "El acceso entre organizaciones devuelve 404 patient_not_found. " +
      "Cada SELECT por origen vuelve a aplicar el filtro de " +
      "organización para defensa en profundidad.",
  },
  {
    state: "RBAC",
    body:
      "Los roles de administrador y clínico pueden escribir en todo " +
      "el flujo. El rol de revisor es de solo lectura. Los intentos " +
      "de escritura del revisor devuelven 403 role_forbidden.",
  },
];

// Spanish non-goals — exact parity with English NON_GOALS list. Same
// claim discipline; never softer, never stronger.
const NON_GOALS_ES: string[] = [
  "No es un EHR certificado. ChartNav funciona junto a su EHR existente; no lo reemplaza.",
  "No cuenta con certificación HIPAA. Un piloto con PHI real (información médica protegida real) requiere BAA, revisión de seguridad, autenticación de producción, hosting aprobado, monitoreo, respaldos, contactos de incidente y aprobación escrita de la práctica.",
  "No realiza diagnóstico autónomo. La interpretación clínica permanece con el proveedor.",
  "No completa automáticamente la PIO (presión intraocular), la refracción ni la relación copa-disco.",
  "No interpreta exámenes de OCT, fotografías de fondo de ojo ni campos visuales.",
  "No selecciona la potencia de la lente intraocular ni la dosis de anti-VEGF.",
  "No coloca órdenes, no envía referencias, no presenta reclamaciones ni gestiona seguros.",
  "No envía mensajes automáticos al paciente. No hay superficie orientada al paciente.",
  "No es una integración actual con ningún proveedor específico de dispositivos de imagen.",
];

const SAFETY_BULLETS_ES: string[] = [
  "Soporte de flujo de trabajo revisado por el proveedor.",
  "ChartNav no diagnostica, no crea órdenes, no envía referencias, no factura ni envía mensajes automáticos al paciente.",
  "Todo artefacto clínico requiere revisión explícita del proveedor antes de considerarse final.",
];

export const LANDING_ES: LandingCopy = {
  docTitle:
    "ChartNav MD — Flujo clínico oftalmológico y documentación revisada por proveedores",
  docDescription:
    "ChartNav ayuda a coordinar flujos de trabajo oftalmológicos: preparación administrativa, evaluación técnica inicial, revisión de metadatos de imágenes, seguimiento de retina y glaucoma, documentación revisada por proveedores y coordinación interna. No es un EHR certificado. No cuenta con certificación HIPAA por defecto.",

  brandLogoAlt: "ChartNav",

  heroTitle:
    "ChartNav es la capa de flujo operativo para clínicas oftalmológicas — revisada por el proveedor en cada paso.",
  heroSub:
    "Desde la preparación administrativa hasta la evaluación técnica inicial, la revisión de metadatos de imágenes y el cierre por parte del proveedor — diseñado para los flujos de la atención oftalmológica. Paneles por rol, seguimiento estructurado de retina y glaucoma, una canalización de metadatos de imágenes, revisión del diagrama retiniano OD/OS y documentación revisada por el proveedor en un mismo espacio de trabajo. Revisado por el proveedor en cada paso. Controlado por el proveedor en cada transición.",
  heroSafetyLine:
    "Soporte de flujo de trabajo revisado por el proveedor. ChartNav no diagnostica, no crea órdenes, no envía referencias, no factura ni envía mensajes automáticos al paciente. ChartNav no interpreta exámenes de OCT, fotografías de fondo de ojo ni campos visuales. ChartNav no presenta reclamaciones ni gestiona seguros.",
  heroCtaPrimary: "Solicitar una demo con paciente ficticio",
  heroCtaSecondary: "Ver cómo funciona el flujo",

  workflowHeading: "De la nota a un expediente listo para retina",
  workflowLead: "Siete pasos explícitos. El proveedor dirige cada transición.",
  workflow: WORKFLOW_ES,
  workflowSvgAriaLabel: "Flujo clínico oftalmológico de ChartNav",
  workflowSvgTitle: "Flujo clínico oftalmológico de ChartNav",

  ophthalmologyHeading: "Diseñado para oftalmología, de principio a fin",
  ophthalmologyBullets: [
    {
      strong: "Lienzo retiniano OD/OS.",
      rest:
        "Coordenadas normalizadas para cada ojo. Dibujar, firmar y bifurcar son conceptos de primera clase — no funciones añadidas a un generador genérico de notas SOAP.",
    },
    {
      strong: "Vocabulario de hallazgos alineado con el expediente.",
      rest:
        "Drusas, hemorragia en mancha/punto, hemorragia en llama, microaneurisma, neovascularización. No es una librería de atajos de atención primaria.",
    },
    {
      strong: "Ubicación superior / inferior / nasal / temporal.",
      rest:
        "Las anotaciones llevan su posición relativa a la mácula y al disco en cada ojo, de modo que el siguiente proveedor vea la misma imagen que usted vio.",
    },
    {
      strong: "Firma del diagrama revisada por el proveedor.",
      rest:
        "Los artefactos firmados son inmutables en su sitio. Las ediciones crean una bifurcación explícita con un puntero al original; la firma original se conserva.",
    },
    {
      strong: "Flujo documental con sabor oftalmológico.",
      rest:
        "Vocabulario cerrado de nota estructurada (motivo de consulta, HEA, examen, evaluación, plan). La plantilla del resumen para el paciente se compone a partir del contenido oftalmológico ya guardado (agudeza visual, PIO, plan, seguimiento).",
    },
  ],

  providerControlHeading: "El proveedor controla cada paso",
  providerControlLead:
    "Los borradores esperan revisión explícita. Finalizar es un clic. Los artefactos firmados son inmutables. ChartNav presenta contexto estructurado del expediente — el proveedor decide.",
  providerControlSvgAriaLabel: "Modelo de estado: el proveedor en control",
  providerControlSvgTitle: "Modelo de estado: el proveedor en control",
  providerControlReviewLabel: "revisar",
  providerControlFinalizeLabel: "finalizar",
  providerControlImmutableNote:
    "Los artefactos finalizados son inmutables. Las nuevas ediciones a artefactos retinianos firmados crean una bifurcación explícita.",
  providerControlDraftLabel: "Borrador",
  providerControlReviewedLabel: "Revisado",
  providerControlFinalizedLabel: "Finalizado",
  safetyModel: SAFETY_MODEL_ES,

  modulesHeading: "Qué incluye el flujo de trabajo",
  modulesLead: "Ocho módulos. Todos construidos. Todos revisados por el proveedor.",
  modules: MODULES_ES,

  beforeAfterHeading: "Antes de ChartNav · Con ChartNav",
  beforeHeading: "Antes",
  afterHeading: "Con ChartNav",
  beforeItems: [
    "Las notas libres se dispersan por el expediente.",
    "Los hallazgos retinianos viven solo como texto narrativo.",
    "Los diagramas OD/OS son en papel o ad hoc.",
    "Los resúmenes para el paciente se escriben desde cero.",
    "No hay preparación estructurada del expediente antes de la visita.",
  ],
  afterItems: [
    "Vocabulario estructurado de nota oftalmológica, revisado por el proveedor.",
    "Hallazgos retinianos vinculados a las anotaciones del lienzo OD/OS.",
    "Diagramas OD/OS versionados y firmados; las ediciones crean bifurcación explícita.",
    "Borradores del resumen para el paciente compuestos a partir del contenido finalizado del expediente.",
    "El resumen previo a la visita muestra conteos por fuente y vacíos explícitos.",
  ],

  demoPilotHeading: "Diseñado para conversaciones de piloto",
  demoPilotBody:
    "Las demos en vivo se ejecutan únicamente con datos de demostración ficticios. Los datos reales de pacientes requieren un Acuerdo de Asociado Comercial (BAA u equivalente), una revisión de seguridad del despliegue y un modo de piloto controlado — consulte el paquete de preparación para piloto para los puntos de control.",
  demoPilotBullets: [
    {
      strong: "Demo en vivo con paciente ficticio.",
      rest: "Cinco minutos, siete pasos, cada paso revisado por el proveedor.",
    },
    {
      strong: "Conversación de piloto controlado.",
      rest:
        "Lista de preparación para piloto, guía de despliegue, paquete de revisión de seguridad — con redacción segura para el comprador en todo momento.",
    },
    {
      strong: "Flujo con el proveedor en control.",
      rest:
        "Conversemos cómo el modelo de estado borrador / revisado / finalizado encaja en su práctica oftalmológica.",
    },
  ],
  demoPilotCtaPrimary: "Conversar un piloto oftalmológico controlado",
  demoPilotCtaSecondary: "Revisar el flujo con el proveedor en control",

  nonGoalsHeading: "Lo que ChartNav no hace",
  nonGoals: NON_GOALS_ES,
  safetyBullets: SAFETY_BULLETS_ES,

  footerOperatedBy: "ChartNav es operado por ARCG.",
  footerRenderedPrefix: "Página renderizada el",
  footerProductAppPrefix: "La aplicación del producto está en ",
  footerProductAppLink: "el espacio de trabajo de ChartNav",
  footerProductAppSuffix:
    ". La guía de demo de la Fase 13 y el Modo Demo Guiado de la Fase 15 son opcionales allí. El paquete de preparación para piloto vive en",

  switcherLabel: "Idioma",
  switcherEnglishLabel: "English",
  switcherSpanishLabel: "Español",
};
