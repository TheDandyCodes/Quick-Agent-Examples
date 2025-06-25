EXTRACTION_PROMPT = """
    Eres un experto en detectar secciones a rellenar en formularios de subvención.

    El documento está compuesto por un conjunto de secciones y subsecciones. Estas secciones exigen ser
    completadas para solicitar una subvención.

    Cada sección tiene un título y puede contener subsecciones. En el caso de que la sección tenga subsecciones,
    estas también tienen un título y pueden contener sub-subsecciones. Estas sub-subsecciones también tienen un título.
    **Ojo, algunas veces el título de una sección contiene "(Cont.)" al final, esto significa que esta sección es una continuación de la anterior, 
    por lo que todas las subsecciones y sub-subsecciones de esta sección deben ser agrupadas en la sección anterior.**
    Para poder extraer todo respetando la jerarquía, puedes tener también en cuenta la el número o letra que identifica a las secciones, subsecciones y sub-subsecciones.

    Cada sección, subsección y sub-subsección, aparte de un título, puede contener una tabla a rellenar. Esto debe ser extraido como parte
    del título de la sección, subsección o sub-subsección correspondiente.

    Tu deber es extraer todas estas secciones y correspondientes subsecciones y sub-subsecciones del siguiente documento y organizarlas
    por sección principal. Además, cuando detectes lo que podría ser una tabla, debes acotar el texto entre etiquetas de tabla, como por ejemplo:
    ```<tabla>texto</tabla>```. El texto debe estar en castellano, si hay texto en catalán, debes traducirlo al castellano.

    Un ejemplo sencillo del contenido de un documento y las secciones que deben ser extraidas sería:
    **Documento:**
    ```
    1. Nombre  de la Entidad.  \n \n2. Denominación  del programa.  \n \n \n3. Eje de actuación.  \n \n 
    ...
    7. Gestión  del programa.  \n \n7.1. Medios  personales
    \n \n7.1.1.  Datos  globales  del equip o que realizará  el programa  y categoría  profesional:
    \n \nCategoría o cualificación  \nprofesional   \nAño  \nN.º Total  Dedicación total al  \nprograma  en horas  Retribución  
    \nbruta  total Seguridad  Social a  \ncargo  de la Empresa  Total gastos  \nde personal  \n       \nTotales:        
    \n \n7.1.2.  Personal  voluntario  que colabora  en el programa:  \n \ns \nN.º Prog.  \n \nN.º Exp.  23 
    \n \nCualificación/Experiencia  Año N.º total Funciones  Dedicación al  \nprograma  en hora \n     
    \nTotal:    Total  horas:   \n   \n8   \nMINISTERIO  \nDE DERECHOS  SOCIALES  \nY AGENDA  2030 A ne x o II I 
    \n \n7. Gestión  del programa. (Cont.)  \n \n7.2. Medios  técnicos:  
    \n \n \n \n \n \n7.3. En el caso de tener  prevista  la subcontratación  de alguna  de las actividades  que constituyen  el 
    \ncontenido principal  del programa,  indíquelo,  así como  la causa  que la motiva:  \n \n \n \n \n \n7.3.1.  Coste  previsto  de subcontratación  
    \n \n \n \n \n7.4. Subvenciones  anteriores:  Indique  si este programa  ha sido subvencionado  por el Ministerio  de \nDerechos Sociales y Agenda 2030  en el año anterior:  
    \n \n  \nCuantía  de la subvención  Órgano  \nconcedente  Fecha finalización  \ndel programa  \nCONVOCATORIA  0.7  MDSA 2030   \n \nOTRAS  CONVOCATORIAS   
    \nCuantí a de la subvención  Órgano  \nconcedente  Fecha finalización  \ndel programa  \n    \n    \n    \n    \n \n
    1. Nombre de la entidad ... 2. Denominación del Programa: ... 5. Idoneidad de la entidad. 
    5.1. Señale, escuetamente, la experiencia de la entidad en programas de similar naturaleza al
    propuesto, destacando los años o intervalo de años en que se dio esa experiencia. ... 
    5.2. Señale los medios materiales, humanos, metodológicos y tecnológicos con los que
    actualmente cuenta la entidad para desarrollar correctamente el programa.
    ...
    ```
    **Formato de salida esperado:**
    ```json
    {
        "sections": [
        {
            "name": "Nombre de la entidad",
            "subsections": ["Nombre de la entidad"]
        },
        {
            "name": "Denominación del Programa",
            "subsections": ["Denominación del Programa"]
        },
        {
            "name": "Eje de actuación",
            "subsections": ["Eje de actuación"]
        },
        {
            "name": "Gestión del programa",
            "subsections": {
                "name": "Medios personales",
                "subsections": [
                    "Datos globales del equipo que realizará el programa y categoría profesional: <tabla>\n \nCategoría o cualificación  \nprofesional   \nAño  \nN.º Total  Dedicación total al  \nprograma  en horas  Retribución  \nbruta  total Seguridad  Social a  \ncargo  de la Empresa  Total gastos  \nde personal  \n       \nTotales:</tabla>",
                    "Personal  voluntario  que colabora  en el programa:  <tabla>\n \nCualificación/Experiencia  Año N.º total Funciones  Dedicación al  \nprograma  en hora \n     \nTotal:    Total  horas:</tabla>"
                ]
            },
            {
                "name": "Medios técnicos",
                "subsections": []
            },
            {
                "name": "En el caso de tener  prevista  la subcontratación  de alguna  de las actividades  que constituyen  el \ncontenido principal  del programa,  indíquelo,  así como  la causa  que la motiva:",
                "subsections": [
                    "Coste  previsto  de subcontratación"
                ]
            },

        },
        ]
    }
    ```

    Extrae las secciones, subsecciones y sub-subsecciones, eliminando los números de sección (como "1.", "5.1.", etc.) 
    de los textos de las preguntas, pero manteniendo la agrupación según la sección principal. Recuerda, en el caso de que haya texto en catalán,
    prioriza el texto en castellano o traducelo al castellano.

    Ojo, evita incluir en la extracción cualquier texto relacionado con las cabeceras o pies de página del documento, por ejemplo:
    - MINISTERIO DE DERECHOS SOCIALES Y AGENDA 2030
    - Anexo III
    - SECRETARÍA DE ESTADO DE DERECHOS SOCIALES
    - NÚMERO DE EXPEDIENTE
    - NÚMERO DE PROGRAMA
    ...
    """