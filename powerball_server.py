import asyncio
from powerball import PowerBall

class ServerProtocol(asyncio.Protocol):

	def __init__(self):
		self.lottery = [12, 24 ,35, 55, 22]
		self.game = PowerBall(1000, lottery)

	def connection_made(self, transport):
		self.transport = transport

	def data_received(self, data):
		message = str(data.decode())
		

def main():
	loop = asyncio.get_event_loop()
	bind = loop.create_server(ServerProtocol, "127.0.0.1", 9999)
	server = loop.run_until_complete(bind)

	quit = False

	while quit == False:
		choice = int(input("\nSelect from the following options:\n1. Pick your numbers\n2. Game Rules\n3. Claim your prize!\n4. Return to Homepage\n"))
		if choice == 1:
			num = int(input("Number of tickets you want to buy: "))
			s = input("Do you want to choose your numbers? (Y)es or (N)o: ")
			if (s == "Yes") or (s == "Y") or (s == "yes") or (s == "y"):
				lottery = input("Enter your numbers seperated by a comma: ")
				tickets = lottery.split(",")
				tickets = [int(i) for i in tickets]

			else:
				tickets = game.GenerateRandom(num)

			print("Your tickets are: {}".format(tickets))
			
		elif choice == 2:
			print("EACH GAME IS WORTH 10 BITPOINTS\n1. Select five numbers from 1 to 69 or you can also choose a 'Randomly Generated Ticket' that gives you 5 randonly generated numbers\n2. Every Monday and Thursday the PowerBall rolls and 5 random winning numbers are displayed on our home page\n3. If 3 or more of your ticket numbers match with the winning numbers on the PowerBall, you win according to the Prizes listed\n4. To claim your prize, go to our home page and choose the 'Claim Prize' option")
			
		elif choice == 3:
			num = input("Enter your numbers seperated by a comma: ")
			arr = num.split(",")
			arr = [int(i) for i in arr]
			prize = game.CalPrize(arr)
			if prize != "":
				print("\nCongrats! You won {} BITPOINTS".format(prize))
			else:
				print("\nSorry!, You didnt win anything")

		elif choice == 4:
			quit = True

	try:
		loop.run_forever()

	except KeyboardInterrupt:
		server.close()
		loop.run_until_complete(server.wait_closed())
		loop.close()

if __name__ == "__main__":
	main()
