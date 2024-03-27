## TP0

### Ejercicio 1
<p align = "justify" > Simplemente se copió la parte del archivo correspondiente al cliente 1 y se la pegó reemplazando las apariciones del id por 2. </p>

### Ejercicio 1.1

<p align = "justify" > Se realizó un script de bash para poder generar la cantidad de clientes deseada pasada como parámetro. Este script genera un nuevo docker-compose-dev.yaml. y para correrlo se debe ejecutar ./make-docker-compose.sh < cantidad de clientes >  </p>

### Ejercicio 2
<p align = "justify" > Para no tener que rebuildear las imágenes ante un cambio en los archivos de configuración, se modificó el docker-compose para que dentro de los contenedores se pudiera acceder a la configuración a través de volúmenes. También se eliminó del Dockerfile del cliente la línea en la que se copiaba el archivo config.yaml, ya que a partir de este ejercicio se puede acceder a él por el volumen. </p>

### Ejercicio 3
<p align = "justify" > Para corroborar el correcto funcionamiento del EchoServer se creo el script test-netcat.sh, el cual genera un mensaje aleatorio de seis caracteres usando el comando mktemp, lo envía al servidor y compara con la respuesta obtenida, informado el resultado por consola. Como no estaba permitido instalar netcat en la máquina host, se corre el script dentro de un contenedor de docker dentro de la misma red definida en el docker-compose. Para correr esto se debe ejecutar primero make docker-compose-up, buildear la imagen del Dockerfile agregado en este ejercicio y luego ejecutar docker run --network tp0_testing_net < id_imagen >  </p>

### Ejercicio 4
<p align = "justify" > Para agregar el manejo de señales en el cliente se creó el canal sigchnl para que escuchase las interrupciones de tipo SIGINT y SIGTERM. Al finalizar cada iteración del loop en StartClientLoop() se agregó un select para poder distinguir si se debía pasar a la siguiente iteración por haberse cumplido el tiempo LoopPeriod definido en la configuración o si se debía salir del bucle por la llegada de una señal. </p>

<p align = "justify" > En el servidor se definió la función __graceful_shutdown(), la cual cierra el socket en el que se aceptan nuevas conexiones y setea una una variable flag para saber que debe finalizar el while. Al cerrarse ese socket se lanza una excepción de tipo OSError al intentar aceptar una nueva conexión en __accept_new_connection(), por lo que se la atrapa y se devuelve None para marcarle a la función invocante que no debe proseguir con la atención de ese cliente </p>

### Ejercicio 5
<p align = "justify" > Se leen los datos de la apuesta del archivo de configuración y se envían con el siguiente formato: dos bytes con el largo del payload, un byte con el número de agencia y el payload que consiste en los datos de la apuesta (excepto el número de agencia) separados por comas, utilizando Big Endian y realizando el envío en un loop revisando la cantidad escrita, para evitar el problema deshort-write. </p>

<p align = "justify" > El servidor recibe una cantidad mínima de cuatro bytes (el de la agencia, los dos de largo y uno de payload) y determina cuántos debe recibir en total en base a los bytes 0 y 1. Lee en un loop para evitar el problema de short-read, almacena la apuesta y devuelve un ACK que consiste en un paquete de un byte con el número de agencia, para que el cliente pueda corroborar la recepción de la apuesta. </p>

<p align = "justify" > En retrospectiva, hubiese sido mejor analizar los ejercicios 5, 6 y 7 en conjunto para diseñar desde el principio el protocolo y no tener que ir cambiándolo como se va a describir en los puntos siguientes. También fue excesivo haberle asignado dos bytes al largo máximo de una apuesta, teniendo en cuenta que el largo máximo de una línea en los archivo provistos fue de 59, apenas más de la quinta parte del máximo valor posible representable con un byte. </p>

### Ejercicio 6
<p align = "justify" > Para este ejercicio se leen una cierta cantidad configurable de apuestas del archivo y se las envía en un paquete con el siguiente formato: Un byte para el id de la agencia, dos para el largo total del payload y luego los bytes de las apuestas con el formato explicado en el punto 5, sin el byte de la agencia. Antes de agregar los bytes de una apuesta al paquete, se verifica que el tamaño de este no supere el máximo permitido. Si lo hace, se envía el paquete y se comienza con esa apuesta el paquete siguiente. </p>

<p align = "justify" >  El error cometido en ese ejercicio fue haber abierto una conexión por cada batch enviado y no enviar todos reutilizándola y finalizando con otro tipo de paquete para notificarle al servidor el fin de las apuestar por parte de esa agencia. </p>

### Ejercicio 7
Para este ejercicio se cambio nuevamente el protocolo para contemplar que ahora tanto cliente como servidor podían enviar/recibir distintos tipos de paquete. Todos los paquetes comienzan con un byte que identifica su tipo:
 - 0: Batch de apuestas: un byte para el tipo, uno para el id de la agencia, dos para el largo del payload y luego el payload como fue explicado en el punto anterior.
 - 1: Notificación al servidor de que la agencia envió todas las apuestas: un byte para el tipo y otro para el id de la agencia.
 - 2: Pedido de ganadores: un byte para el tipo y otro para el id de la agencia.
 - 3: ACK del paquete de tipo 0: un byte para el tipo
 - 4: ACK del paquete de tipo 1: un byte para el tipo
 - 5: Respuesta al paquete de tipo 2: un byte para el tipo, otro para el resultado de la query (0 si es una respuesta con los ganadores, 1 en caso de que no todas las agencias hayan notificado el fin de sus envíos), dos bytes para el largo del payload y luego el payload, que consiste en los documentos de los ganadores separados por comas.

### Ejercicio 8
<p align = "justify" > Para agregar el procesamiento de mensajes en paralelo en el servidor genera un nuevo proceso para cada conexión utilizando la biblioteca multiprocessing de Python de la siguiente manera: una vez aceptada una conexión, se crea un nuevo proceso para que ejecute la función __handle_client_connection() pasándole como argumentos el lock del archivo en el cual se almacenan las apuestas y la lista de los clientes que ya han notificado al servidor que terminaron de enviar todas las apuestas. El lock es adquirido antes de cualquier lectura/escritura del archivo y liberado inmediatamente después de esta. Para poder garantizar la exclusión mutua a la lista de clientes, se la define como un objeto de la clase Array de la biblioteca multiprocessing, y se obtiene su lock antes leerla al momento de saber si puede enviarle sus ganadores a una agencia o escritura al momento de marcar que el cliente ha enviado todas las apuestas. </p>
<p align = "justify" > Para cerrar gracefully las conexiones se agrega un flag de tipo Value de la biblioteca multiprocessing, el cual comienza con valor cero y se cambia a uno al recibir una de las señales manejadas. Este valor se chequea al finalizar cada iteración en la función __handle_client_connection() para saber si debe interrumpir la recepción de paquetes. </p>
<p align = "justify" > En este ejercicio se corrige un error existente desde el punto 5 en los anteriores con respecto a la cantidad de conexiones que le tomaba a un cliente enviar toda la información. Previamente, se creaba una nueva conexión para el envío de cada batch y se cerraba luego de recibir su ACK, lo cual es sumamente ineficiente si la cantidad de apuestas es alta. Se modifica para que el cliente envíe todos los batchs en la misma conexión y el servidor permanezca escuchando hasta recibir un mensaje de tipo NOTIFY. También se corrige el manejo en caso de que un paquete exceda el tamaño máximo permitido.</p>

# TP0: Docker + Comunicaciones + Concurrencia

En el presente repositorio se provee un ejemplo de cliente-servidor el cual corre en containers con la ayuda de [docker-compose](https://docs.docker.com/compose/). El mismo es un ejemplo práctico brindado por la cátedra para que los alumnos tengan un esqueleto básico de cómo armar un proyecto de cero en donde todas las dependencias del mismo se encuentren encapsuladas en containers. El cliente (Golang) y el servidor (Python) fueron desarrollados en diferentes lenguajes simplemente para mostrar cómo dos lenguajes de programación pueden convivir en el mismo proyecto con la ayuda de containers.

Por otro lado, se presenta una guía de ejercicios que los alumnos deberán resolver teniendo en cuenta las consideraciones generales descriptas al pie de este archivo.

## Instrucciones de uso
El repositorio cuenta con un **Makefile** que posee encapsulado diferentes comandos utilizados recurrentemente en el proyecto en forma de targets. Los targets se ejecutan mediante la invocación de:

* **make \<target\>**:
Los target imprescindibles para iniciar y detener el sistema son **docker-compose-up** y **docker-compose-down**, siendo los restantes targets de utilidad para el proceso de _debugging_ y _troubleshooting_.

Los targets disponibles son:
* **docker-compose-up**: Inicializa el ambiente de desarrollo (buildear docker images del servidor y cliente, inicializar la red a utilizar por docker, etc.) y arranca los containers de las aplicaciones que componen el proyecto.
* **docker-compose-down**: Realiza un `docker-compose stop` para detener los containers asociados al compose y luego realiza un `docker-compose down` para destruir todos los recursos asociados al proyecto que fueron inicializados. Se recomienda ejecutar este comando al finalizar cada ejecución para evitar que el disco de la máquina host se llene.
* **docker-compose-logs**: Permite ver los logs actuales del proyecto. Acompañar con `grep` para lograr ver mensajes de una aplicación específica dentro del compose.
* **docker-image**: Buildea las imágenes a ser utilizadas tanto en el servidor como en el cliente. Este target es utilizado por **docker-compose-up**, por lo cual se lo puede utilizar para testear nuevos cambios en las imágenes antes de arrancar el proyecto.
* **build**: Compila la aplicación cliente para ejecución en el _host_ en lugar de en docker. La compilación de esta forma es mucho más rápida pero requiere tener el entorno de Golang instalado en la máquina _host_.

### Servidor
El servidor del presente ejemplo es un EchoServer: los mensajes recibidos por el cliente son devueltos inmediatamente. El servidor actual funciona de la siguiente forma:
1. Servidor acepta una nueva conexión.
2. Servidor recibe mensaje del cliente y procede a responder el mismo.
3. Servidor desconecta al cliente.
4. Servidor procede a recibir una conexión nuevamente.

### Cliente
El cliente del presente ejemplo se conecta reiteradas veces al servidor y envía mensajes de la siguiente forma.
1. Cliente se conecta al servidor.
2. Cliente genera mensaje incremental.
recibe mensaje del cliente y procede a responder el mismo.
3. Cliente envía mensaje al servidor y espera mensaje de respuesta.
Servidor desconecta al cliente.
4. Cliente vuelve al paso 2.

Al ejecutar el comando `make docker-compose-up` para comenzar la ejecución del ejemplo y luego el comando `make docker-compose-logs`, se observan los siguientes logs:

```
$ make docker-compose-logs
docker compose -f docker-compose-dev.yaml logs -f
client1  | time="2023-03-17 04:36:59" level=info msg="action: config | result: success | client_id: 1 | server_address: server:12345 | loop_lapse: 20s | loop_period: 5s | log_level: DEBUG"
client1  | time="2023-03-17 04:36:59" level=info msg="action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°1\n"
server   | 2023-03-17 04:36:59 DEBUG    action: config | result: success | port: 12345 | listen_backlog: 5 | logging_level: DEBUG
server   | 2023-03-17 04:36:59 INFO     action: accept_connections | result: in_progress
server   | 2023-03-17 04:36:59 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2023-03-17 04:36:59 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°1
server   | 2023-03-17 04:36:59 INFO     action: accept_connections | result: in_progress
server   | 2023-03-17 04:37:04 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2023-03-17 04:37:04 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°2
server   | 2023-03-17 04:37:04 INFO     action: accept_connections | result: in_progress
client1  | time="2023-03-17 04:37:04" level=info msg="action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°2\n"
server   | 2023-03-17 04:37:09 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2023-03-17 04:37:09 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°3
server   | 2023-03-17 04:37:09 INFO     action: accept_connections | result: in_progress
client1  | time="2023-03-17 04:37:09" level=info msg="action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°3\n"
server   | 2023-03-17 04:37:14 INFO     action: accept_connections | result: success | ip: 172.25.125.3
server   | 2023-03-17 04:37:14 INFO     action: receive_message | result: success | ip: 172.25.125.3 | msg: [CLIENT 1] Message N°4
client1  | time="2023-03-17 04:37:14" level=info msg="action: receive_message | result: success | client_id: 1 | msg: [CLIENT 1] Message N°4\n"
server   | 2023-03-17 04:37:14 INFO     action: accept_connections | result: in_progress
client1  | time="2023-03-17 04:37:19" level=info msg="action: timeout_detected | result: success | client_id: 1"
client1  | time="2023-03-17 04:37:19" level=info msg="action: loop_finished | result: success | client_id: 1"
client1 exited with code 0
```

## Parte 1: Introducción a Docker
En esta primera parte del trabajo práctico se plantean una serie de ejercicios que sirven para introducir las herramientas básicas de Docker que se utilizarán a lo largo de la materia. El entendimiento de las mismas será crucial para el desarrollo de los próximos TPs.

### Ejercicio N°1:
Modificar la definición del DockerCompose para agregar un nuevo cliente al proyecto.

### Ejercicio N°1.1:
Definir un script (en el lenguaje deseado) que permita crear una definición de DockerCompose con una cantidad configurable de clientes.

### Ejercicio N°2:
Modificar el cliente y el servidor para lograr que realizar cambios en el archivo de configuración no requiera un nuevo build de las imágenes de Docker para que los mismos sean efectivos. La configuración a través del archivo correspondiente (`config.ini` y `config.yaml`, dependiendo de la aplicación) debe ser inyectada en el container y persistida afuera de la imagen (hint: `docker volumes`).

### Ejercicio N°3:
Crear un script que permita verificar el correcto funcionamiento del servidor utilizando el comando `netcat` para interactuar con el mismo. Dado que el servidor es un EchoServer, se debe enviar un mensaje al servidor y esperar recibir el mismo mensaje enviado. Netcat no debe ser instalado en la máquina _host_ y no se puede exponer puertos del servidor para realizar la comunicación (hint: `docker network`).

### Ejercicio N°4:
Modificar servidor y cliente para que ambos sistemas terminen de forma _graceful_ al recibir la signal SIGTERM. Terminar la aplicación de forma _graceful_ implica que todos los _file descriptors_ (entre los que se encuentran archivos, sockets, threads y procesos) deben cerrarse correctamente antes que el thread de la aplicación principal muera. Loguear mensajes en el cierre de cada recurso (hint: Verificar que hace el flag `-t` utilizado en el comando `docker compose down`).

## Parte 2: Repaso de Comunicaciones

Las secciones de repaso del trabajo práctico plantean un caso de uso denominado **Lotería Nacional**. Para la resolución de las mismas deberá utilizarse como base al código fuente provisto en la primera parte, con las modificaciones agregadas en el ejercicio 4.

### Ejercicio N°5:
Modificar la lógica de negocio tanto de los clientes como del servidor para nuestro nuevo caso de uso.

#### Cliente
Emulará a una _agencia de quiniela_ que participa del proyecto. Existen 5 agencias. Deberán recibir como variables de entorno los campos que representan la apuesta de una persona: nombre, apellido, DNI, nacimiento, numero apostado (en adelante 'número'). Ej.: `NOMBRE=Santiago Lionel`, `APELLIDO=Lorca`, `DOCUMENTO=30904465`, `NACIMIENTO=1999-03-17` y `NUMERO=7574` respectivamente.

Los campos deben enviarse al servidor para dejar registro de la apuesta. Al recibir la confirmación del servidor se debe imprimir por log: `action: apuesta_enviada | result: success | dni: ${DNI} | numero: ${NUMERO}`.

#### Servidor
Emulará a la _central de Lotería Nacional_. Deberá recibir los campos de la cada apuesta desde los clientes y almacenar la información mediante la función `store_bet(...)` para control futuro de ganadores. La función `store_bet(...)` es provista por la cátedra y no podrá ser modificada por el alumno.
Al persistir se debe imprimir por log: `action: apuesta_almacenada | result: success | dni: ${DNI} | numero: ${NUMERO}`.

#### Comunicación:
Se deberá implementar un módulo de comunicación entre el cliente y el servidor donde se maneje el envío y la recepción de los paquetes, el cual se espera que contemple:
* Definición de un protocolo para el envío de los mensajes.
* Serialización de los datos.
* Correcta separación de responsabilidades entre modelo de dominio y capa de comunicación.
* Correcto empleo de sockets, incluyendo manejo de errores y evitando los fenómenos conocidos como [_short read y short write_](https://cs61.seas.harvard.edu/site/2018/FileDescriptors/).

### Ejercicio N°6:
Modificar los clientes para que envíen varias apuestas a la vez (modalidad conocida como procesamiento por _chunks_ o _batchs_). La información de cada agencia será simulada por la ingesta de su archivo numerado correspondiente, provisto por la cátedra dentro de `.data/datasets.zip`.
Los _batchs_ permiten que el cliente registre varias apuestas en una misma consulta, acortando tiempos de transmisión y procesamiento. La cantidad de apuestas dentro de cada _batch_ debe ser configurable. Realizar una implementación genérica, pero elegir un valor por defecto de modo tal que los paquetes no excedan los 8kB. El servidor, por otro lado, deberá responder con éxito solamente si todas las apuestas del _batch_ fueron procesadas correctamente.

### Ejercicio N°7:
Modificar los clientes para que notifiquen al servidor al finalizar con el envío de todas las apuestas y así proceder con el sorteo.
Inmediatamente después de la notificacion, los clientes consultarán la lista de ganadores del sorteo correspondientes a su agencia.
Una vez el cliente obtenga los resultados, deberá imprimir por log: `action: consulta_ganadores | result: success | cant_ganadores: ${CANT}`.

El servidor deberá esperar la notificación de las 5 agencias para considerar que se realizó el sorteo e imprimir por log: `action: sorteo | result: success`.
Luego de este evento, podrá verificar cada apuesta con las funciones `load_bets(...)` y `has_won(...)` y retornar los DNI de los ganadores de la agencia en cuestión. Antes del sorteo, no podrá responder consultas por la lista de ganadores.
Las funciones `load_bets(...)` y `has_won(...)` son provistas por la cátedra y no podrán ser modificadas por el alumno.

## Parte 3: Repaso de Concurrencia

### Ejercicio N°8:
Modificar el servidor para que permita aceptar conexiones y procesar mensajes en paralelo.
En este ejercicio es importante considerar los mecanismos de sincronización a utilizar para el correcto funcionamiento de la persistencia.

En caso de que el alumno implemente el servidor Python utilizando _multithreading_,  deberán tenerse en cuenta las [limitaciones propias del lenguaje](https://wiki.python.org/moin/GlobalInterpreterLock).

## Consideraciones Generales
Se espera que los alumnos realicen un _fork_ del presente repositorio para el desarrollo de los ejercicios.
El _fork_ deberá contar con una sección de README que indique como ejecutar cada ejercicio.
La Parte 2 requiere una sección donde se explique el protocolo de comunicación implementado.
La Parte 3 requiere una sección que expliquen los mecanismos de sincronización utilizados.

Finalmente, se pide a los alumnos leer atentamente y **tener en cuenta** los criterios de corrección provistos [en el campus](https://campusgrado.fi.uba.ar/mod/page/view.php?id=73393).
