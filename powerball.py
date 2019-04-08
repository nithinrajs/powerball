import random

class PowerBall:
	def __init__(self, pool, lottery):
		self.id = ""
		self.pool = pool
		self.lottery = lottery

	def GenerateRandom(self, num):
		randlist = []
		for i in range(0, num):
			randlist.append(random.randint(0,69))
		print(randlist)
		return randlist

	def CalPrize(self, num):
		count = 0
		for i in num:
			if i in self.lottery:
				count = count + 1

		if count == 3:
			prize = 0.2 * self.pool
			return prize

		elif count == 4:
			prize = 0.3 * self.pool
			return prize

		elif count == 5:
			prize = 0.5 * self.pool
			return prize			


def main():
	print("WELCOME TO POWERBALL!!")
	lottery = [12, 24 ,35, 55, 22]
	game = PowerBall(1000, lottery)
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
			


if __name__=="__main__":
	main()
