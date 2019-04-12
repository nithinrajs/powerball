import playground
import hashlib
import random, datetime
import sys, time, os, logging, asyncio
from collections import deque
from playground.network.common import PlaygroundAddress
from playground.network.common import StackingProtocol, StackingProtocolFactory, StackingTransport
from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT16,UINT32,STRING,BUFFER,BOOL


SC_flag = "check"


class Timer:                                        #Timer to check for timeouts
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.ensure_future(self.job())

    async def job(self):                           
        await asyncio.sleep(self._timeout)
        await self._callback()

class PIMPPacket(PacketType):                       #Packet Definitions
    DEFINITION_IDENTIFIER = "roastmyprofessor.pimp.PIMPPacket"
    DEFINITION_VERSION = "1.0"
    FIELDS = [
        ("seqNum", UINT32),
        ("ackNum", UINT32),
        ("ACK", BOOL),
        ("RST", BOOL),
        ("SYN", BOOL),
        ("FIN", BOOL),
        ("RTR", BOOL),
        ("checkSum", BUFFER),
        ("data", BUFFER)
    ]

    def cal_checksum(self):
        self.checkSum = b""
        GNByte = self.__serialize__()
        hash_value = hashlib.md5()
        hash_value.update(GNByte)
        return hash_value.digest()
    
    def updateChecksum(self):
        self.checkSum = self.cal_checksum()

    def verifyChecksum(self):
        oldChksum = self.checkSum
        newChksum = self.cal_checksum()
        #print("old checksum = " + str(oldChksum) + " \n New checksum=" + str(newChksum))
        if oldChksum == newChksum:
            return True
        else:
            return False

    @classmethod
    def SynPacket(cls, seq):
        pkt = cls()
        pkt.ACK = False
        pkt.SYN = True
        pkt.FIN = False
        pkt.RTR = False
        pkt.RST = False
        pkt.seqNum = seq
        pkt.data = b'0'
        pkt.ackNum = b'0'
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        print("!!!!!!!!!!!!!!!!!!!!!!!!SENT SYN with Seq Num=" + str(pkt.seqNum) + "      " + str(pkt.checkSum))
        return pkt
        
    @classmethod
    def AckPacket(cls, syn, ack):
        pkt = cls()
        pkt.ACK = True
        pkt.SYN = False
        pkt.FIN = False
        pkt.RTR = False
        pkt.RST = False
        pkt.seqNum = syn
        pkt.ackNum = ack
        pkt.data = b'0'
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        print("!!!!!!!!!!!!!!!!!!!!!!!!SENT Ack !!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum)+ "      " + str(pkt.checkSum))
        return pkt

    @classmethod
    def SynAckPacket(cls, seq, ack):
        pkt = cls()
        pkt.ACK = True
        pkt.SYN = True
        pkt.FIN = False
        pkt.RTR = False
        pkt.RST = False
        pkt.seqNum = seq
        pkt.ackNum = ack
        pkt.data = b'0'
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        print("!!!!!!!!!!!!!!!!!!!!!!!!SENT SYNACK!!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum)+ "      " + str(pkt.checkSum))
        return pkt

    @classmethod
    def DataPacket(cls, seq, ack, data):
        pkt = cls()
        pkt.ACK = False
        pkt.SYN = False
        pkt.FIN = False
        pkt.RTR = False
        pkt.RST = False
        pkt.seqNum = seq
        pkt.ackNum = ack
        pkt.data = data
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        print("!!!!!!!!!!!!!!!!!!!!!!!!SENT DATA PACKET !!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum)+ "      " + str(len(pkt.data)) )
        return pkt

    @classmethod
    def RtrPacket(cls, seq, ack):
        pkt = cls()
        pkt.ACK = False
        pkt.SYN = False
        pkt.FIN = False
        pkt.RTR = True
        pkt.RST = False
        pkt.seqNum = seq
        pkt.ackNum = ack
        pkt.data = b'0'
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT RTR PACKET !!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum))
        return pkt

    @classmethod
    def FinPacket(cls, seq, ack):
        pkt = cls()
        pkt.ACK = False
        pkt.SYN = False
        pkt.FIN = True
        pkt.RTR = False
        pkt.RST = False
        pkt.seqNum = seq
        pkt.ackNum = ack
        pkt.data = b'0'
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        return pkt

    @classmethod
    def RstPacket(cls, seq, ack):
        pkt = cls()
        pkt.ACK = False
        pkt.SYN = False
        pkt.FIN = False
        pkt.RTR = False
        pkt.RST = True
        pkt.seqNum = seq
        pkt.ackNum = ack
        pkt.data = b'0'
        pkt.checkSum = b'0'
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT RST PACKET !!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum))
        return pkt


class PIMPProtocol(StackingProtocol):
    def __init__(self):
        super().__init__()
        self.pimppacket = PIMPPacket()
        self.deserializer = self.pimppacket.Deserializer()
        self.seqNum = random.getrandbits(32)
        self.Server_seqNum = 0
        self.SeqNum = random.getrandbits(32)
        self.Client_seqNum = 0

        self.keys = ["ACK", "SYN", "FIN", "RTR", "RST", "seqNum", "ackNum", "data"]
        
        self.ServerTxWindow = []
        self.ClientTxWindow = []
        self.ServerRxWindow = []


    def sendSynAck(self, transport, seq, ack):
        synackpacket = self.pimppacket.SynAckPacket(seq, ack)   
        transport.write(synackpacket.__serialize__())

    def send_rst(self, transport, seq, ack):
        rstpacket = self.pimppacket.RstPacket(seq, ack)
        transport.write(rstpacket.__serialize__())

    def send_syn(self, transport, seq):
        synpacket = self.pimppacket.SynPacket(seq)
        transport.write(synpacket.__serialize__())

    def send_Ack(self, transport, seq, ack):
        ackpacket = self.pimppacket.AckPacket(seq, ack)
        transport.write(ackpacket.__serialize__())

    def send_rst(self, transport, seq, ack):
        rstpacket = self.pimppacket.RstPacket(seq, ack)
        transport.write(rstpacket.__serialize__())
    
    def send_rtr(self, transport, seq, ack):
        rtrpacket = self.pimppacket.RtrPacket(seq,ack)
        transport.write(rtrpacket.__serialize__())

    def processpktdata(self, transport, seq, ack):
        """sendack = [x for x in self.ServerRxWindow if x["seqNum"] <= seq]
        for pkt in sendack:
            self.higherProtocol().data_received(pkt["data"])
            print(str(pkt["data"]))"""

        self.send_Ack(self.transport, seq, ack)
        self.ServerRxWindow = [i for i in self.ServerRxWindow if i["seqNum"] > ack]
        for i in self.ServerRxWindow:
            print("Removing >> "+ str(i))
            print("\n")

        if len(self.ServerRxWindow) == 0:
            print("Currently Emptied\n") 


    def server_send_data(self, transport, data):
        ServerTxBuffer = {}
        print("Server")
        ServerTxBuffer = dict.fromkeys(self.keys,None)
        #print("Seq Num = " + str(self.SeqNum))
        #print("Ack Num = " + str(self.Client_seqNum))
        datapacket = self.pimppacket.DataPacket(self.SeqNum, self.Client_seqNum, data)
        transport.write(datapacket.__serialize__())
        ServerTxBuffer.update(ACK=datapacket.ACK, SYN=datapacket.SYN, FIN=datapacket.FIN, RTR=datapacket.RTR, RST=datapacket.RST, seqNum=datapacket.seqNum, ackNum=datapacket.ackNum, data=datapacket.data)
        self.ServerTxWindow.append(ServerTxBuffer)
        #print(self.ServerTxWindow)
        self.SeqNum = datapacket.seqNum  + len(datapacket.data)
        
        


    def client_send_data(self, transport, data):
        ClientTxBuffer = {}
        print("Client")
        ClientTxBuffer = dict.fromkeys(self.keys,None)
        datapacket = self.pimppacket.DataPacket(self.seqNum, self.Server_seqNum, data)
        #print("This is the" + str(datapacket) + "This is its seq " + str(datapacket.seqNum) + "This is its ack " + str(datapacket.ackNum))
        transport.write(datapacket.__serialize__())
        ClientTxBuffer.update(ACK=datapacket.ACK, SYN=datapacket.SYN, FIN=datapacket.FIN, RTR=datapacket.RTR, RST=datapacket.RST, seqNum=datapacket.seqNum, ackNum=datapacket.ackNum, data=datapacket.data)
        #print(ClientTxBuffer)
        #print("\n\n")
        self.ClientTxWindow.append(ClientTxBuffer)
        #print(self.ClientTxWindow)
        #print("\n\n")
        self.seqNum = self.seqNum + len(datapacket.data)
        
        

    async def check_timeout(self):
        if self.resend_flag == True and self.Server_state == self.SER_SENT_SYNACK:
            self.sendSynAck(self.transport, self.SeqNum -1, self.Client_seqNum)
            self.resend_flag = False
        elif self.resend_flag == True and self.SER_ESTABLISHED:
            self.resend_flag = False
            pass
        else:
            pass

class PIMPTransport(StackingTransport):
    def __init__(self, transport, send_data):
        super().__init__(transport)
        self.PACKET_BUFF = []
        self.transport = transport
        self.send_data = send_data


        
    def pack(self,length, data):
        PacketSize = 4000
        leed = 0
        end = PacketSize
        TEMP_BUFF = []
        while(length > 0):
            push = data[leed : end]
            length = length - PacketSize
            leed = end
            end = end + PacketSize
            TEMP_BUFF.append(push)
        return(TEMP_BUFF)
        
    def write(self, data):
        #pkt = PIMPPacket()
        length = len(data)
        BUFF = []
        global SC_flag
        
        if length <= 4000: 
            self.send_data(self.transport, data)
        
        else:
            BUFF = self.pack(length, data)
            for d in BUFF: 
                self.send_data(self.transport, d)


class PIMPServerProtocol(PIMPProtocol):
        LISTEN= 100
        SER_SENT_SYNACK= 102
        SER_ESTABLISHED= 103

        def __init__(self):
            #print("!!!!!!!!!!IN SERVER!!!!!!!!!!!")
            super().__init__()
            global SC_flag
            SC_flag = "Server"

            self.Server_state = self.LISTEN
            self.resend_flag = True

            #self.keys = ["ACK", "SYN", "FIN", "RTR", "RST", "seqNum", "ackNum", "data"]

            
            self.RxWindowSize = 3000
            
        def logging_initialize(self):
            self.logger = logging.getLogger('transport_log')
            self.logger.setLevel(logging.DEBUG)
            fd = logging.FileHandler('Server.log')
            fd.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.ERROR)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fd.setFormatter(formatter)
            ch.setFormatter(formatter)
            self.logger.addHandler(fd)
            self.logger.addHandler(ch)
        
        def connection_made(self, transport):
            self.transport = transport
            
        def data_received(self, data):
            #print(data)
            self.deserializer.update(data)
            for pkt in self.deserializer.nextPackets():
                if pkt.verifyChecksum():
                    if pkt.SYN == True and pkt.ACK == False and self.Server_state == self.LISTEN:
                        #print("!!!!!!!!!!!!Packet Received with Syn Number!!!!!!" + str(pkt.seqNum))
                        self.Client_seqNum = pkt.seqNum + 1
                        self.sendSynAck(self.transport, self.SeqNum, self.Client_seqNum)
                        self.resend_flag = True
                        timer = Timer(3, self.check_timeout)
                        self.SeqNum += 1
                        self.Server_state = self.SER_SENT_SYNACK

                    elif pkt.SYN == False and pkt.ACK == True and self.Server_state == self.SER_SENT_SYNACK:
                        if self.SeqNum == pkt.ackNum and self.Client_seqNum == pkt.seqNum:
                            #print("!!!!!!!!!!!!!!!!Ack Packet Received !!!!!!!!!!!!!!!!!!!!!")
                            self.resend_flag = False
                            self.Server_state = self.SER_ESTABLISHED
                            ################################################################################3
                            pimp_transport = PIMPTransport(self.transport,self.server_send_data)
                            self.higherProtocol().connection_made(pimp_transport)
                            #print("!!!!!!!!!!!Server Connection Established!!!!!!!!!!!!!!!!!!!")


                    elif (pkt.SYN == False) and (pkt.ACK == True) and (self.Server_state != self.SER_SENT_SYNACK) and (self.Server_state != self.SER_ESTABLISHED):
                        print("DROPPING PACKET 'ACK SENT BEFORE SYNACK'")

                    elif pkt.SYN == False and pkt.ACK == False and self.Server_state == self.SER_ESTABLISHED and pkt.data != 0:
                        ServerRxBuffer = {}
                        ServerRxBuffer = dict.fromkeys(self.keys,None)
                        ServerRxBuffer.update(ACK=pkt.ACK, SYN=pkt.SYN, FIN=pkt.FIN, RTR=pkt.RTR, RST=pkt.RST, seqNum=pkt.seqNum, ackNum=pkt.ackNum, data=pkt.data)
                        self.ServerRxWindow.append(ServerRxBuffer)
                        #print(self.ServerRxWindow)
                        self.SeqNum = pkt.ackNum 
                        self.Client_seqNum = pkt.seqNum + len(pkt.data)
                        print("Server sequence number updated" + str(self.SeqNum))
                        print("Server ACk number updated" + str(self.Client_seqNum) + "\n")
                        #for j in self.ServerRxWindow:
                         #   print(j)
                        #print("\n!!!!!!!!!!!!!!!!!DATA PACKET RECIEVED!!!!!!!!!!!!!!!!!!!!\n")
                        self.higherProtocol().data_received(pkt.data)
                        if len(self.ServerRxWindow) >= 9:
                            #print("seq>> "+str(self.SeqNum))
                            #print("ack>> "+str(self.Client_seqNum))
                            #print("I am HERE jjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj")
                            self.processpktdata(self.transport, self.SeqNum, self.Client_seqNum)

                    else:
                        print("!!!!SOMETHING!!!")

                else:
                    #print("SOMETHING!!!")
                    self.send_rtr(self.transport, self.SeqNum, self.Client_seqNum)


                                                    
class PIMPClientProtocol(PIMPProtocol):

        CLI_INITIAL= 200
        CLI_SENT_SYN= 201
        CLI_ESTABLISHED= 202
        
        def __init__(self):
            super().__init__()
            self.Client_state = self.CLI_INITIAL
            self.resend_flag = True
            self.keys = ["ACK", "SYN", "FIN", "RTR", "RST", "seqNum", "ackNum", "data"]
            #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!INside CLIENT!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            global SC_flag
            SC_flag = "Client"
            
           
        def logging_initialize(self):
            self.logger = logging.getLogger('transport_log')
            self.logger.setLevel(logging.DEBUG)
            fd = logging.FileHandler('Client.log')
            fd.setLevel(logging.DEBUG)
            ch = logging.StreamHandler()
            ch.setLevel(logging.ERROR)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fd.setFormatter(formatter)
            ch.setFormatter(formatter)
            self.logger.addHandler(fd)
            self.logger.addHandler(ch)

        def connection_made(self, transport):
            self.transport = transport
            if self.Client_state == self.CLI_INITIAL:
                #print("@@@@@IN CLIENT@@@@")
                self.send_syn(self.transport, self.seqNum)
                time1 = datetime.datetime.now()
                timer = Timer(3, self.check_timeout)
                self.seqNum += 1
                self.Client_state = self.CLI_SENT_SYN


        async def check_timeout(self):
            if self.resend_flag == True and self.Client_state == self.CLI_SENT_SYN:
                self.send_syn(self.transport, self.seqNum-1)
                self.resend_flag = False
            elif self.resend_flag == True and self.Client_state == self.CLI_ESTABLISHED:
                self.send_Ack(self.transport, self.seqNum, self.Server_seqNum - 1)
                self.resend_flag = False
            else:
                pass
        
        def data_received(self, data):
            #print(data)
            self.deserializer.update(data)
            for pkt in self.deserializer.nextPackets():
                if pkt.verifyChecksum():
                    if pkt.SYN == True and pkt.ACK == True and self.Client_state == self.CLI_SENT_SYN:
                        if self.seqNum == pkt.ackNum:
                            #print("!!!!!!!!!!!!SYNACK Packet Received with Syn Num" + str(pkt.seqNum) + "Ack Num" + str(pkt.ackNum))
                            self.Server_seqNum = pkt.seqNum + 1
                            self.seqNum = pkt.ackNum
                            self.resend_flag = False
                            print("CLient seq number" + str(self.seqNum) + "\n Ack number" + str(self.Server_seqNum))
                            self.send_Ack(self.transport, self.seqNum, self.Server_seqNum)
                            self.Client_state = self.CLI_ESTABLISHED
                            #################################################################################
                            pimp_transport = PIMPTransport(self.transport,self.client_send_data)
                            self.higherProtocol().connection_made(pimp_transport)
                            #BUF = PIMPTransport.write(pkt.data)
                            #print(BUF)
                            #self.send_data(self.transport, self.seqNum, self.Server_seqNum, BUF)
                            print("!!!!!!!!!!!Client Connection Established!!!!!!!!!!!!!!!!!!!")

                        elif self.seqNum != pkt.ackNum:
                            #print("!!!!!!!!!SENDING RST PACKET!!!!!!!!")
                            self.Server_seqNum = pkt.seqNum + 1
                            self.send_rst(self.transport, self.seqNum, self.Server_seqNum)
                            self.Client_state = self.CLI_INITIAL

                    elif pkt.SYN == False and pkt.ACK == False and self.Client_state == self.CLI_ESTABLISHED and pkt.data != 0:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                        self.seqNum = pkt.ackNum 
                        self.Server_seqNum = pkt.seqNum + len(pkt.data)
                        RECV_BUFF = pkt.data
                        print("!!!!!!!!!!!!!!!!!!!len" + str(len(pkt.data)))
                        #print(RECV_BUFF)
                        #print("\n!!!!!!!!!!!!!!!!!DATA PACKET RECIEVED!!!!!!!!!!!!!!!!!!!!\n")
                        self.higherProtocol().data_received(pkt.data)
                        #print("PAcket sent to higher layer")
                        #Process the data packet recieved


                    elif pkt.SYN == False and pkt.ACK == True and self.Client_state == self.CLI_ESTABLISHED:
                        print("Ack for Data is Here")
                        self.seqNum = pkt.ackNum
                        self.Server_seqNum = pkt.seqNum + 1 # Doubtful
                        self.ClientTxWindow = [q for q in self.ClientTxWindow if q["seqNum"] < self.seqNum]
                        #for w in self.ClientTxWindow:
                         #   print(w)


                else:
                    #print("SOMETHING!!!")
                    self.send_rtr(self.transport, self.seqNum, self.Server_seqNum)



PIMPClientFactory = StackingProtocolFactory.CreateFactoryType(lambda: PIMPClientProtocol())
PIMPServerFactory = StackingProtocolFactory.CreateFactoryType(lambda: PIMPServerProtocol())


