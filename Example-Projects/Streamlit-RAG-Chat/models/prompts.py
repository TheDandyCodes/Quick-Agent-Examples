EXTRACTION_PROMPT = """
    Eres un experto en detectar secciones a rellenar en formularios de subvención.

    El documento está compuesto por un conjunto de secciones y subsecciones. Estas secciones exigen ser
    completadas para solicitar una subvención. 

    Tu deber es extraer todas estas preguntas/secciones importantes del siguiente documento y organizarlas
    por sección principal.

    Un ejemplo sencillo del contenido de un documento y las secciones que deben ser extraidas sería:
    **Documento:**
    ```
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
            "questions": ["Nombre de la entidad"]
        },
        {
            "name": "Denominación del Programa",
            "questions": ["Denominación del Programa"]
        },
        {
            "name": "Idoneidad de la entidad",
            "questions": [
            "Señale, escuetamente, la experiencia de la entidad en programas de similar naturaleza al propuesto, destacando los años o intervalo de años en que se dio esa experiencia.",
            "Señale los medios materiales, humanos, metodológicos y tecnológicos con los que actualmente cuenta la entidad para desarrollar correctamente el programa."
            ]
        }
        ]
    }
    ```

    **NOTA**: 
    Hay algunas subsecciones con sub-subsecciones dentro de ellas, en este caso, estas ultimas sub-subsecciones deben ser
    añadidas al texto de la subsección a la que pertenecen. Por ejemplo, la subsección:
    "6.1. Definición y justificación exacta y clara de la necesidad preexistente cuya cobertura
    pretende abordarse a través del programa. El problema o necesidad a la que se responde
    debe ser de relevancia a nivel estatal" tiene las siguientes sub-subsecciones:
    - Definición de las necesidad o problemática social preexistente
    - Estudios y/o estadísticas que avalen la existencia de esa necesidad o
        problemática.
    En estos casos, el resultado final debe ser:
    ```
    **Formato de salida esperado:**
    ```json
    {
        "sections": [
        ...,
        {
            "name": "Calidad del diseño global del programa.",
            "questions": [
            "Definición y justificación exacta y clara de la necesidad preexistente cuya cobertura
            pretende abordarse a través del programa. El problema o necesidad a la que se responde
            debe ser de relevancia a nivel estatal: Definición de las necesidad o problemática social preexistente.",
            "Definición y justificación exacta y clara de la necesidad preexistente cuya cobertura
            pretende abordarse a través del programa. El problema o necesidad a la que se responde
            debe ser de relevancia a nivel estatal: Estudios y/o estadísticas que avalen la existencia de esa necesidad o
            problemática.",
            ]
        },
        ...
        ]
    }
    ```

    Extrae las secciones y subsecciones, eliminando los números de sección (como "1.", "5.1.", etc.) 
    de los textos de las preguntas, pero manteniendo la agrupación según la sección principal.
    """