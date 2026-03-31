# Flujo 11 — Bloqueos: BLOQUEADA_POR_DISEÑO vs INVESTIGACIÓN_REQUERIDA
> Proceso: Árbol de decisión del Domain Orchestrator cuando no puede producir un plan válido.
> Fuente: `registry/orchestrator.md` §Paso 6 — coordinación de gates

```mermaid
flowchart TD
    START([Domain Orchestrator no puede producir plan válido]) --> TREE

    subgraph TREE["Árbol de decisión — aplicar en orden estricto"]
        P1{"Pregunta 1:\n¿Puede el DO describir en\nuna frase qué debe construir?"}
        P1 -->|NO| BD1["BLOQUEADA_POR_DISEÑO\ncausa: spec insuficiente — el DO no sabe qué"]
        P1 -->|SÍ| P2

        P2{"Pregunta 2:\n¿Puede el DO enumerar\n≥ 2 alternativas técnicas\nconcretas para implementarlo?"}
        P2 -->|NO| BD2["BLOQUEADA_POR_DISEÑO\ncausa: no puede ni formular opciones\n— el qué no está suficientemente definido"]
        P2 -->|SÍ| P3

        P3{"Pregunta 3:\n¿Puede el DO evaluar esas alternativas\ncon la spec, el stack y los\nrequisitos disponibles?"}
        P3 -->|SÍ| DO_DECIDE["El DO debe decidir y continuar\n(no hay bloqueo — la decisión\nestá dentro de su scope)"]
        P3 -->|NO| IR["INVESTIGACIÓN_REQUERIDA\nsabe qué, enumera cómo,\npero no puede decidir sin evidencia adicional"]
    end

    subgraph BD_FLOW["Flujo BLOQUEADA_POR_DISEÑO"]
        BD_R1["DO reporta al Master:"]
        BD_R2["ESTADO: BLOQUEADA_POR_DISEÑO\nTAREA: feature/<tarea>\nCAUSA: spec insuficiente\nGAP_DETECTADO: <qué info falta>\nEj: 'RF-03 no especifica algoritmo de cifrado en reposo'\nPREGUNTA_AL_USUARIO: <pregunta concreta y cerrada>\nACCIÓN_ESPERADA: usuario aclara → DO reintenta"]
        BD_R1 --> BD_R2
        BD_R2 --> BD_USER["Master presenta pregunta al usuario\n— sin recomendar — la elección es del usuario"]
        BD_USER --> BD_RESP{Respuesta del usuario}
        BD_RESP --> BD_UNLOCK["DO reintenta planificación\ncon información aclarada"]
    end

    subgraph IR_FLOW["Flujo INVESTIGACIÓN_REQUERIDA"]
        IR_R1["DO reporta al Master:"]
        IR_R2["ESTADO: INVESTIGACIÓN_REQUERIDA\nTAREA: feature/<tarea>\nCAUSA: conocimiento técnico insuficiente para decidir\nDECISIÓN_BLOQUEADA: <qué no puede decidir y por qué>\nEj: 'No puedo elegir Redis vs Memcached vs dict in-memory\nsin conocer el comportamiento de carga esperado'"]
        IR_R1 --> IR_R2
        IR_R2 --> IR_OPTS
    end

    subgraph IR_OPTS["Opciones al usuario (Master presenta ambas sin recomendar)"]
        OA["OPCIÓN A — Respuesta directa:\nPREGUNTA: <pregunta técnica específica y acotada>\nSI_USUARIO_RESPONDE:\nDO se desbloquea inmediatamente, sin tarea RES"]
        OB["OPCIÓN B — Tarea de investigación:\nRQ_PROPUESTA: <pregunta acotada, ≤3 sub-preguntas>\nSCOPE: <qué entra y qué NO entra>\nFUENTES_ESPERADAS: <tipo de fuentes>\nDEPENDENCIA: tarea RES debe completarse antes de feature/<tarea>\nSI_USUARIO_APRUEBA:\nMaster agrega tarea RES al DAG con dependencia hacia adelante"]
    end

    subgraph DAG_EXT["Si usuario elige Opción B — DAG dinámico"]
        DE1["Master crea dag_extension.md en staging/<objetivo>:\n(NO modificar specs/active/architecture.md — contrato inmutable)"]
        DE2["| ID | Tarea | Modo | Origen | Depende de | Desbloquea |\n| T-EXT-01 | [nombre RES] | RES | INVESTIGACIÓN_REQUERIDA | — | [tarea bloqueada] |"]
        DE1 --> DE2
        DE2 --> DE3["AuditAgent registra creación de dag_extension.md\nen acciones_realizadas.txt\nAl cierre: Master pregunta al usuario si incorporar\nal contrato permanente (decisión humana)"]
    end

    subgraph ESTADOS["Estados válidos del grafo"]
        ES1["BLOQUEADA          → dependencias sin completar"]
        ES2["LISTA              → dependencias OK, esperando activación"]
        ES3["EN_EJECUCIÓN       → DO y expertos activos"]
        ES4["GATE_PENDIENTE     → esperando gate"]
        ES5["COMPLETADA         → en staging, gate aprobado"]
        ES6["BLOQUEADA_POR_DISEÑO → spec insuficiente\n   Desbloqueo: usuario aclara requisito → DO reintenta"]
        ES7["INVESTIGACIÓN_REQUERIDA → conocimiento insuficiente\n   Desbloqueo: A) usuario responde directamente\n               B) tarea RES aprobada y completada"]
        ES8["INVALIDADA         → usuario modificó objetivo\n   trabajo ya realizado ya no es válido"]
    end

    BD1 --> BD_FLOW
    BD2 --> BD_FLOW
    IR --> IR_FLOW
    IR_FLOW --> IR_OPTS
    OA -->|Usuario responde| BD_UNLOCK
    OB -->|Usuario aprueba| DAG_EXT
```
