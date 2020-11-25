#Bernardo Urriza, Antonio Rivera, Gerardo Arizmendi
#Desarrollado para Raspberry Pi / NVIDIA Jetson en Python 3.
#Se instalan paquetes y librerías mediante git, pip3, curl y otros componentes básicos.
#Se sigue "Build Instructions" en la referencia de la librería Mercury (en un Python wrapper) para el módulo M6E.
#https://github.com/gotthardp/python-mercuryapi/tree/f9bf9c939240bc1400c4b38f85dfafe95d332529#mercuryreaderuri-baudrate115200-antenna-protocol
#Referencias para la librería encargada de la conexión con Firebase:
#https://github.com/thisbejim/Pyrebase
#https://blog.devcolor.org/heating-up-with-firebase-tutorial-on-how-to-integrate-firebase-into-your-app-6ce97440175d

import pyrebase
import mercury

PotenciaLectura = 19 #dBm, para leer etiquetas
PotenciaEscritura = 19 #dBm, para escribir a etiquetas

#Objeto para hacer lectura del módulo M6E
reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=115200)
reader.set_region("EU3") #Para una modulación FHSS de 4 diferentes frecuencias al rededor de 866 MHz
reader.set_read_plan([1], "GEN2", epc_target=None, bank=["epc"], read_power=(PotenciaLectura*100))
#Se leen los EPCs de todas las etiquetas presentes, potencias esperadas en centidBm

#Sobre el chip M6E
print("\nTemperatura del chip en grados centígrados:")
print(reader.get_temperature())
#Se recomienda hacer uso de un disipador de calor para usos prolongados

#Sobre las antenas
print("\nAntenas disponibles:")
print(reader.get_antennas())
print("\nRango de potencias soportadas en centidBm:")
print(reader.get_power_range())

#Sobre la modulación
print("\nFrecuencias usadas para FHSS em kHz:")
print(reader.get_hop_table())
print("\nIntervalo entre saltos de FHSS en ms:")
print(reader.get_hop_time())


#Se configura Firebase para manipular los EPCs desde la nube
config = {
  "apiKey": "AIzaSyDIPBHyX22JwNw_AOGMrTwDaXDPkAyGKKw",
  "authDomain": "t3c-inc.firebaseapp.com",
  "databaseURL": "https://t3c-inc.firebaseio.com",
  "storageBucket": "t3c-inc.appspot.com",
  "serviceAccount": "/home/baua/Documents/RFID/serviceAccount.json"
}
firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
user = auth.sign_in_with_email_and_password("test01@gmail.com", "12345678i")
db = firebase.database()
user['idToken']
deviceID = "M6E-1"
print('\nEsperando indicación de lectura/escritura desde la app')

while True:

	#Se leen las potencias de la base de datos en caso de que la app las haya modificado
	NuevaPotenciaLectura = int(db.child("devices").child(deviceID).get().val()["read power"])
	if (NuevaPotenciaLectura != PotenciaLectura):
		PotenciaLectura = NuevaPotenciaLectura
		reader.set_read_plan([1], "GEN2", epc_target=None, bank=["epc"], read_power=(PotenciaLectura*100))
		print('\nSe ha programado la potencia de lectura a "{}" dBm'.format(PotenciaLectura))

	NuevaPotenciaEscritura = int(db.child("devices").child(deviceID).get().val()["write power"])
	if (NuevaPotenciaEscritura != PotenciaEscritura):
		PotenciaEscritura = NuevaPotenciaEscritura
		reader.set_read_powers([(1, PotenciaEscritura*100)])
		print('\nSe ha programado la potencia de escritura a "{}" dBm'.format(PotenciaEscritura))

	if (db.child("devices").child(deviceID).get().val()["read"]):

		#Algoritmo para lectura de etiquetas y subida a base de datos:

		#Lectura de etiquetas
		print("\nLecturas de EPC: ")
		EPCs = reader.read(timeout=3000)

		#Se preparan los EPCs en forma de String para subir a base de datos (EPC separados por comas)
		NumeroDeTags = len(EPCs)
		EPCsString = str(set(map(lambda t: t.epc, EPCs)))
		EPCsString = EPCsString.replace("{b'",'')
		EPCsString = EPCsString.replace("'}",'')
		EPCsString = EPCsString.replace("', b'",',')
		print(EPCsString) 

		#Se suben las lecturas a Firebase junto con otros datos reelevantes
		print('\nSubiendo a base de datos ...')
		configM6E = {"read power": PotenciaLectura, "write power": PotenciaEscritura, "read EPC" : EPCsString, "write EPC":"null", "read": False, "write":False}
		db.child("devices").child(deviceID).set(configM6E, user['idToken'])
		print('Base de datos actualizada')
		print('Esperando indicación de lectura/escritura desde la app')

	if (db.child("devices").child(deviceID).get().val()["write"]):

		#Algoritmo para bajada de base de datos y ecritura de nuevo EPC en la etiqueta:

		#Se preparan los EPCs en forma de bytes para escribir en la etiqueta
		old_epc = db.child("devices").child(deviceID).child("read EPC").get().val()
		new_epc = db.child("devices").child(deviceID).child("write EPC").get().val()
		old_epc = bytes(old_epc, 'utf-8')
		new_epc = bytes(new_epc, 'utf-8')

		#Se escribe un nuevo EPC
		if reader.write(epc_code=new_epc, epc_target=old_epc):
			print('\nSe ha reemplazado "{}" con "{}"'.format(old_epc, new_epc))
			configM6E = {"read power": PotenciaLectura, "write power": PotenciaEscritura, "read EPC" : "null", "write EPC":"null", "read": False, "write":False, "EPC":True}
			#La bandera EPC en True indica que la escritura fue exitosa
			db.child("devices").child(deviceID).set(configM6E, user['idToken'])
		else:
			print('\nNo se encuentra la etiqueta')
			configM6E = {"read power": PotenciaLectura, "write power": PotenciaEscritura, "read EPC" : "null", "write EPC":"null", "read": False, "write":False, "EPC":False}
			#La bandera EPC en False indica que la escritura fue fallida
			db.child("devices").child(deviceID).set(configM6E, user['idToken'])
		print('Base de datos actualizada')
		print('Esperando indicación de lectura/escritura desde la app')


