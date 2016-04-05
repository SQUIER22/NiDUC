
#Klasa ARQModel ma na celu wczytanie pliku wejsciowego .wav
#nastepnie wczytanie kolejnych jego bajtow i przedstawienie ich w formie 0 i 1 
#zamiast '\xXX' np.: '\xaa' = '10101010'
#model dzieli na paczki po n=1,2,4,8,16,32,64,128 bajtow 
#(najczytelniej jest n=8, n=32 powinno byc optymalne do testow)
#model dodaje rowniez bit parzystosci jako n+1 element paczki 
#i bajt ktory zawiera informacje o ilosci jedynek w pakiecie
#bajt ilosci jedynek jest w paczce jako n+2 element
#przykladowa paczka dla n=8: 
#['10110101', '10111111', '00000000', '10010001', '10100101', '10010100', '11111111', '10110001', 1, 34]
#indeksy 	[0:n-1] 	to miejsce danych
#indeks 	n 			to bit parzystosci
#indeks 	n + 1 		to ilosc jedynek w pakiecie danych
#rozmiar paczki to n+2
#
#rozmiar pliku wave.wav z gita to dokladnie 6 000 000(+- 1) bajtow! 
#wiec mozna dzielic na paczki po 1,2,4,8,16,32,64,128 bajtow (choc 128 jest ryzykowne)



from __future__ import print_function
import wave
import array
import random

class ARQModel:
	
	bin_file = []	#bajty pliku .wav
	rate = 32000	#rating pliku .wav
	packages = []	#bin_file podzielony na paczki
	bytesinpack = 0	#po ile bajtow dany byly pakowane
	errors = 0
	
	def __init__(self):		#konstruktor modulu arq, wczytuje plik i konwertuje go na ciag bajtow!
		self.rate = 32000
		self.bin_file = []
		self.packages = []
		self.bytesinpack = 0
		errors = 0
		
	def loadfile(self, filepath):
		print("\n<ARQ> Reading file...")
		tmpw = wave.open(filepath, "rb")	
		bytes = tmpw.readframes(tmpw.getnframes())
		tmpw.close()
		print("\n<ARQ> Converting to bytes...")
		self.bin_file = [ord(char) for char in bytes]
		self.bin_file = [bin(char)[2:].zfill(8) for char in self.bin_file]	#wynikowa lista bajtow w reprezentacji zer i jedynek
		
	def printnbytes(self, begin, end):	#wypisuje bajty z podanego zakresu
		for i in range(begin, end):
			print(self.bin_file[i], end= " ")
			
	def converttowave(self, output):	#tworzy plik wav z ciagu bajtow
		print("\n<ARQ> Converting to bytes...")
		
		self.bin_file = [int(bit, 2) for bit in self.bin_file]	#do integerow
		self.bin_file = array.array('B', self.bin_file).tostring() #do bajtow w postaci '\xdd'
		self.output_wave(output, self.bin_file)
	
	def output_wave(self, path, frames):
		output = wave.open(path,'w')	#tylko do zapisu
		output.setparams((2,2,self.rate,0,'NONE','not compressed'))		#2 kanaly, szerokosc? probki, rating, kompresja
		print("\n<ARQ> Exporting to .wav...")
		output.writeframes(frames)
		output.close()
		
	def packsofn(self, bytesinpack):	#dzielenie zaladowanego pliku na paczki po zadanej ilosci bajtow
		begin = 0
		end = bytesinpack
		self.bytesinpack = bytesinpack
		for i in range(0, (len(self.bin_file)/bytesinpack)):
			pack = self.bin_file[begin:end]
			self.packages.append(pack)
			begin += bytesinpack
			end += bytesinpack
	
	def addevenbyte(self):	#dodawanie bitu parzystosci i ilosci jedynek do kazdej paczki
		onesinpackage = 0	#dodanie 1 jesli ilosc jedynek w paczce jest parzysta, 0 wpp
		for pack in self.packages:
			pack = self.countones(pack)
	
	def countones(self, pack):
		onesinpackage = 0
		for byte in pack:
				for char in byte:
					if(char == '1'):
						onesinpackage += 1
		if(onesinpackage % 2 == 0):
			pack.append(1)
			pack.append(onesinpackage)
		else:
			pack.append(0)
			pack.append(onesinpackage)

		return pack
	
	def unpack(self):
		print("\n<ARQ> Unpacking...")
		for pack in self.packages:	#dla kazdego pakietu w otrzymanej paczce
			self.bin_file.extend(pack)	#wyciag z paczki i dodaj do 'pliku'
	
	def receivepacks(self, pack): #odbiera JEDEN pakiet danych i sprawdza jego poprawnosc
		onesinpackage = 0
		evenbit = 0
		tocheck = [el for el in pack]
		packones = tocheck.pop()	#ilosc jedynek w pakiecie
		packeven = tocheck.pop()	#bit parzystosci
		
		for byte in tocheck:	#sprawdzanie bajtow DANYCH
			for bit in byte:	#sprawdzanie kazdego bitu w kazdym bajcie	
				if(bit == '1'):
					onesinpackage += 1
		
		#sprawdzenie poprawnosci pakietu
		if(onesinpackage == packones):	#sprawdzenie ilosci jedynek w pakiecie
			if(onesinpackage%2 == 0):	#sprawdzenie bitu parzystosci
				if(1 == packeven):	#jesli sie zgadza przyjmij paczke bez bitow ochronnych
					pack.pop()
					pack.pop()
					self.packages.append(pack)
					return 'ack'	#odeslij potwierdzenie odebrania
				else:
					return 'nack'	#pakiet nie byl poprawny, nadaj jeszcze raz
			else:
				if(0 == packeven):	#to samo!
					pack.pop()
					pack.pop()
					self.packages.append(pack)
					return 'ack'
				else:
					return 'nack'
		else:
			return 'nack'
	
	def sendviaSAW(self, destARQ, n):		#wysylanie pliku w paczkach po n bajtow do docelowego dekodera destARQ
		self.synchronizeARQs(destARQ, n)		#synchronizacja modulow (ustawienie ilosci bajtow w paczkach)
		
		print("\n<ARQ> Packing...")
		self.packsofn(n) 	#packowanie danych
		
		print("\n<ARQ> Adding secure bytes...")
		self.addevenbyte()	#dodanie bitow sprawdzajacych poprawnosc
		
		print("\n<ARQ> Sending packages...")
		for pack in self.packages: 
			ack = destARQ.receivepacks(self.addnoise(pack))	#proba wyslania paczki/ czekanie na odpowiedz destARQ
			while(ack == 'nack'):		#dopoki paczka nie jest odebrana poprawnie, bedzie wysylana do skutku
				ack = destARQ.receivepacks(self.addnoise(pack))	#wysylanie do skutku
				self.errors += 1

	#def sendviaGOBACK(self, destARQ, bytesinpack, packsinwindow):
		#synchronizeARQs(destARQ, bytesinpack)
				
	def synchronizeARQs(self, destARQ, bytesinpack):	#synchronizuje moduly arq
		destARQ.bytesinpack = bytesinpack
		self.bytesinpack = bytesinpack

	def addnoise(self, pack):	#prymitywne zaszumienie pakietu
		grain = random.randint(0,1000)	#losowa liczba z przedzialu 0, 1000
		noise = [el for el in pack]		#przekopiowanie pakietu zeby nie ulegla zniszczeniu
		ones = noise.pop()		#pozbywamy sie bitow ochronnych
		even = noise.pop()
		string = ''
		if(grain % 432 == 0):	#jesli wylosowana liczba jest podzielna przez 432 to pakiet bedzie zaszumiany
			for byte in noise:
				for bit in byte:
					if(random.randint(1,20) == 3):	#okolo 5%szans ze dany bit zostanie zmieniony
						if(bit == '1'):
							string += '0'
						else:
							string += '1'
					else:
						string += bit
			noise = self.convertbitstringtopack(string)	#konwersja otrzymanego zaszumianego pakietu na paczke
			if(random.randint(1,20) == 4):	#okolo 5%szans ze bity sprawdzajace poprawnosc zostana znieksztalcone
				even = random.randint(0,1)
				ones = random.randint(0, (8*self.bytesinpack))
			noise.append(even)	
			noise.append(ones)	
			return noise	#zwrocenie zaszumianej probki
		else:
			return pack #czysta probka
		
		
	def convertbitstringtopack(self, string):	#konwertuje napis '01010001...11100' na paczke po n bajtow
		pack = []
		tmp = ''
		for i in range(0, len(string)):
			if(i % 8 == 0 and i != 0):
				pack.append(tmp)
				tmp = ''
			tmp += string[i]
			
			if(i == len(string)-1):
				pack.append(tmp)
		
		return pack
			

#-----------------------SYMULACJA-----------------------#

print("\n#-----------------------SYMULACJA-----------------------#\n")
#inicjalizacja dekoderow ARQ		
sourceARQ = ARQModel()	#zrodlowy ARQ
destARQ = ARQModel()	#docelowy ARQ
	
sourceARQ.loadfile('wave.wav')	#wczytanie pliku do wykonania symulacji

sourceARQ.sendviaSAW(destARQ, 64)	#wysylanie (symulacja) pliku do destARQ w paczkach po 32 bajty
print("\n<ARQ> File sended.\tErrors: ", sourceARQ.errors, "/", len(sourceARQ.packages))		#wypisanie ilosci blednie odebranych paczek

destARQ.unpack()	#rozpakowanie otrzymanych danych
destARQ.converttowave('receivedviaSAW.wav')		#utworzenie pliku wynikowego

print("\n\n#--------------------KONIEC SYMULACJI-------------------#\n")
