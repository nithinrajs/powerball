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

class Timer2:                                        #Timer to check for 
    def __init__(self, timeout, callback, param):
        self._timeout = timeout
        self._callback = callback
        self.param = param
        self._task = asyncio.ensure_future(self.job())

    async def job(self):                           
        await asyncio.sleep(self._timeout)
        await self._callback(self.param)

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
        pkt.data = b''
        pkt.ackNum = b'0'
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT SYN with Seq Num=" + str(pkt.seqNum) + "      " + str(pkt.checkSum))
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
        pkt.data = b''
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT Ack !!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum))
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
        pkt.data = b''
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT SYNACK!!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum)+ "      " + str(pkt.checkSum))
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
        pkt.data = b''
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
        pkt.data = b''
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT FIN PACKET !!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum) + "data =" + str(len(pkt.data)))
        return pkt

    @classmethod
    def FinAckPacket(cls, seq, ack):
        pkt = cls()
        pkt.ACK = True
        pkt.SYN = False
        pkt.FIN = True
        pkt.RTR = False
        pkt.RST = False
        pkt.seqNum = seq
        pkt.ackNum = ack
        pkt.data = b''
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
        pkt.data = b''
        pkt.updateChecksum()
        #print("!!!!!!!!!!!!!!!!!!!!!!!!SENT RST PACKET !!!!!!!!!!!!!!!!!!!!!!!!!" + "Seq="+str(pkt.seqNum) + "Ack="+str(pkt.ackNum))
        return pkt


class PIMPProtocol(StackingProtocol):
    LISTEN= 100
    SER_SENT_SYNACK= 102
    SER_ESTABLISHED= 103
    SER_CLOSING= 104
    CLI_INITIAL= 200
    CLI_SENT_SYN= 201
    CLI_ESTABLISHED= 202
    CLI_CLOSING= 203


    def __init__(self):
        super().__init__()
        self.pimppacket = PIMPPacket()
        self.deserializer = self.pimppacket.Deserializer()
        self.seqNum = random.getrandbits(32)
        self.Server_seqNum = 0
        self.SeqNum = random.getrandbits(32)
        self.Client_seqNum = 0
        self.Server_state = self.LISTEN
        self.Client_state = self.CLI_INITIAL

        self.keys = ["ACK", "SYN", "FIN", "RTR", "RST", "seqNum", "ackNum", "data"]
        
        self.ServerTxWindow = []
        self.ClientTxWindow = []
        self.ServerRxWindow = []
        self.ClientRxWindow = []


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

    def send_fin(self, transport, seq, ack):
        finpacket = self.pimppacket.FinPacket(seq,ack)
        transport.write(finpacket.__serialize__())

    def send_finack(self, transport, seq, ack):
        finackpacket = self.pimppacket.FinAckPacket(seq,ack)
        transport.write(finackpacket.__serialize__())

    def Remove(self, duplicate): 
        final_list = [] 
        for e in duplicate: 
            if e["seqNum"] not in final_list: 
                final_list.append(e) 
        return final_list 

    def processpktdata(self, transport, seq, ack):
        length1 =len(self.ServerRxWindow)
        while length1 > 0:
            pkt = self.ServerRxWindow.pop(0)
            length1 -= 1
            #print("pkt seqNum" +str(pkt["seqNum"]))
            #print(self.Client_seqNum)
            #print(len(pkt["data"]))
            if pkt["seqNum"] == self.Client_seqNum:
                #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                self.higherProtocol().data_received(pkt["data"])
                self.SeqNum = pkt["ackNum"] 
                self.Client_seqNum = pkt["seqNum"] + len(pkt["data"])
                self.send_Ack(self.transport, self.SeqNum, self.Client_seqNum)
                pkt = ""

            elif pkt["seqNum"] < self.Client_seqNum:
                self.send_Ack(self.transport, pkt["ackNum"], pkt["seqNum"] + len(pkt["data"]))


            else:
                self.ServerRxWindow.append(pkt)
                self.ServerRxWindow = sorted(self.ServerRxWindow, key = lambda i: i['seqNum'])
                pkt = ""

        #print(self.ServerRxWindow)


    def clientprocesspktdata(self, transport, seq, ack):
        length1 =len(self.ClientRxWindow)
        while length1 > 0:
            pkt = self.ClientRxWindow.pop(0)
            length1 -= 1
            if pkt["seqNum"] == self.Server_seqNum:
                self.higherProtocol().data_received(pkt["data"])
                self.seqNum = pkt["ackNum"] 
                self.Server_seqNum = pkt["seqNum"] + len(pkt["data"])
                self.send_Ack(self.transport, self.seqNum, self.Server_seqNum)
                pkt = ""

            elif pkt["seqNum"] < self.Server_seqNum:
                self.send_Ack(self.transport, pkt["ackNum"], pkt["seqNum"] + len(pkt["data"]))

            else:
                self.ClientRxWindow.append(pkt)
                self.ClientRxWindow = sorted(self.ClientRxWindow, key = lambda i: i['seqNum'])
                pkt = ""

    def server_resend_data(self, transport):
        if len(self.ServerTxWindow) != 0:
            for repkt in self.ServerTxWindow:
                datapacket = self.pimppacket.DataPacket(repkt["seqNum"], repkt["ackNum"], repkt["data"])
                transport.write(datapacket.__serialize__())
                #print("Sent Server Resend!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        #else:
            #print("<><><><><><>EMPTY BUFFER<><><><><><><><><><")

    def client_resend_data(self, transport):
        if len(self.ClientTxWindow) != 0:
            for repkt in self.ClientTxWindow:
                datapacket = self.pimppacket.DataPacket(repkt["seqNum"], repkt["ackNum"], repkt["data"])
                transport.write(datapacket.__serialize__())
                #print("Sent Cleint REsend!!!!!!!!!!!!!!!!!!!!!111")

        #else:
         #   print("<><><><><><>EMPTY BUFFER<><><><><><><><><><")

    def server_send_data(self, transport, data):
        ServerTxBuffer = {}
        ServerTxBuffer = dict.fromkeys(self.keys,None)
        datapacket = self.pimppacket.DataPacket(self.SeqNum, self.Client_seqNum, data)
        transport.write(datapacket.__serialize__())
        ServerTxBuffer.update(ACK=datapacket.ACK, SYN=datapacket.SYN, FIN=datapacket.FIN, RTR=datapacket.RTR, RST=datapacket.RST, seqNum=datapacket.seqNum, ackNum=datapacket.ackNum, data=datapacket.data)
        self.ServerTxWindow.append(ServerTxBuffer)
        self.SeqNum = self.SeqNum  + len(datapacket.data)
        timer = Timer2(5, self.server_resend_data,transport)
        

    def client_send_data(self, transport, data):
        ClientTxBuffer = {}
        ClientTxBuffer = dict.fromkeys(self.keys,None)
        datapacket = self.pimppacket.DataPacket(self.seqNum, self.Server_seqNum, data)
        transport.write(datapacket.__serialize__())
        ClientTxBuffer.update(ACK=datapacket.ACK, SYN=datapacket.SYN, FIN=datapacket.FIN, RTR=datapacket.RTR, RST=datapacket.RST, seqNum=datapacket.seqNum, ackNum=datapacket.ackNum, data=datapacket.data)
        self.ClientTxWindow.append(ClientTxBuffer)
        self.seqNum = self.seqNum + len(datapacket.data)
        timer = Timer2(5, self.client_resend_data,transport)



class PIMPTransport(StackingTransport):
    def __init__(self, transport, send_data, finpacket):
        super().__init__(transport)
        self.PACKET_BUFF = []
        self.transport = transport
        self.send_data = send_data
        self.finpacket = finpacket

    def close(self):
        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.finpacket(self.transport)

        
    def pack(self,length, data):
        PacketSize = 1500
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
        length = len(data)
        BUFF = []
        global SC_flag
        
        if length <= 1500: 
            self.send_data(self.transport, data)
        
        else:
            BUFF = self.pack(length, data)
            for d in BUFF: 
                self.send_data(self.transport, d)


class PIMPServerProtocol(PIMPProtocol):
        def __init__(self):
            super().__init__()
            global SC_flag
            SC_flag = "Server"
            self.resend_flag = True
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
            
        def server_fin_pkt(self, transport):
            if(self.Server_state != self.SER_CLOSING):
                self.Server_state = self.SER_CLOSING
                self.higherProtocol().connection_lost(None)
                self.send_fin(transport, self.SeqNum, self.Client_seqNum)
        
        async def check_timeout(self):
            if self.resend_flag == True and self.Server_state == self.SER_SENT_SYNACK:
                self.sendSynAck(self.transport, self.SeqNum -1, self.Client_seqNum)
                self.resend_flag = False

            elif self.resend_flag == True and self.Server_state == self.SER_CLOSING:
                self.transport.close()
                self.resend_flag = False
            else:
                pass            

        def data_received(self, data):
            self.deserializer.update(data)
            for pkt in self.deserializer.nextPackets():
                if pkt.verifyChecksum():
                    if pkt.SYN == True and pkt.ACK == False and self.Server_state == self.LISTEN:
                        self.Client_seqNum = pkt.seqNum + 1
                        self.sendSynAck(self.transport, self.SeqNum, self.Client_seqNum)
                        self.resend_flag = True
                        timer = Timer(3, self.check_timeout)
                        self.SeqNum += 1
                        self.Server_state = self.SER_SENT_SYNACK

                    elif pkt.SYN == True and pkt.ACK == False and self.Server_state == self.SER_SENT_SYNACK:
                        self.sendSynAck(self.transport, self.SeqNum, self.Client_seqNum)
                        self.resend_flag = True
                        timer = Timer(3, self.check_timeout)
                        self.SeqNum += 1
                        self.Server_state = self.SER_SENT_SYNACK

                    elif pkt.SYN == False and pkt.ACK == True and self.Server_state == self.SER_SENT_SYNACK:
                        if self.SeqNum == pkt.ackNum and self.Client_seqNum == pkt.seqNum:
                            self.resend_flag = False
                            self.Server_state = self.SER_ESTABLISHED
                            pimp_transport = PIMPTransport(self.transport,self.server_send_data, self.server_fin_pkt)
                            self.higherProtocol().connection_made(pimp_transport)
                            #print("!!!!!!!!!!!Server Connection Established!!!!!!!!!!!!!!!!!!!")


                    elif (pkt.SYN == False) and (pkt.ACK == True) and pkt.FIN == False and (self.Server_state != self.SER_SENT_SYNACK) and (self.Server_state != self.SER_ESTABLISHED) and self.Server_state != self.SER_CLOSING:
                        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!DROPPING PACKET 'ACK SENT BEFORE SYNACK'")

                    elif pkt.SYN == False and pkt.ACK == False and self.Server_state == self.SER_ESTABLISHED and len(pkt.data) != 0:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!server data received")
                        ServerRxBuffer = {}
                        ServerRxBuffer = dict.fromkeys(self.keys,None)
                        ServerRxBuffer.update(ACK=pkt.ACK, SYN=pkt.SYN, FIN=pkt.FIN, RTR=pkt.RTR, RST=pkt.RST, seqNum=pkt.seqNum, ackNum=pkt.ackNum, data=pkt.data)
                        self.ServerRxWindow.append(ServerRxBuffer)
                        self.ServerRxWindow = sorted(self.ServerRxWindow, key = lambda i: i['seqNum'])
                        self.ServerRxWindow = self.Remove(self.ServerRxWindow)
                        #print("\n\nRXserver\n")
                        #print(self.ServerRxWindow)
                        self.processpktdata(self.transport, self.SeqNum, self.Client_seqNum)

                    elif pkt.SYN == False and pkt.ACK == True and self.Server_state == self.SER_ESTABLISHED:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ACk Received")
                        self.SeqNum = pkt.ackNum
                        self.ServerTxWindow = [l for l in self.ServerTxWindow if l["seqNum"] > pkt.ackNum]
                        #print(self.ServerTxWindow)

                    elif pkt.FIN == True and self.Server_state == self.SER_ESTABLISHED:
                        #Recover outstanding data
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!SEND FIN ACK")
                        self.resend_flag = True
                        self.Server_state = self.SER_CLOSING
                        self.higherProtocol().connection_lost(None)
                        self.send_finack(self.transport, pkt.ackNum, pkt.seqNum+1)
                        timer = Timer(3, self.check_timeout)

                    elif pkt.FIN == True and self.Server_state == self.SER_CLOSING:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!SEND ACK")
                        self.send_Ack(self.transport, pkt.ackNum, pkt.seqNum+1)
                        self.Server_state = self.LISTEN

                    elif pkt.ACK == True and self.Server_state == self.SER_CLOSING:
                        self.Server_state = self.LISTEN

                    elif pkt.RST == True:
                        self.Server_state = self.LISTEN

                    else:
                        print("!!!!!!!!!!!!!!!!!!!!Something!!!!!!!!!!") 

                else:
                    self.send_rtr(self.transport, self.SeqNum, self.Client_seqNum)


                                                    
class PIMPClientProtocol(PIMPProtocol):
        
        def __init__(self):
            super().__init__()
            self.resend_flag = True
            self.keys = ["ACK", "SYN", "FIN", "RTR", "RST", "seqNum", "ackNum", "data"]
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
            elif self.resend_flag == True and self.Client_state == self.CLI_CLOSING:
                self.transport.close()
                self.resend_flag = False
            else:
                pass
        
        def client_fin_pkt(self, transport):
            if(self.Client_state != self.CLI_CLOSING):
                self.Client_state = self.CLI_CLOSING
                self.higherProtocol().connection_lost(None)
                self.send_fin(transport, self.seqNum, self.Server_seqNum)
            


        def data_received(self, data):
            self.deserializer.update(data)
            for pkt in self.deserializer.nextPackets():
                if pkt.verifyChecksum():
                    if pkt.SYN == True and pkt.ACK == True and self.Client_state == self.CLI_SENT_SYN:
                        if self.seqNum == pkt.ackNum:
                            self.Server_seqNum = pkt.seqNum + 1
                            self.seqNum = pkt.ackNum
                            self.resend_flag = False
                            self.send_Ack(self.transport, self.seqNum, self.Server_seqNum)
                            self.Client_state = self.CLI_ESTABLISHED
                            #################################################################################
                            pimp_transport = PIMPTransport(self.transport,self.client_send_data, self.client_fin_pkt)
                            self.higherProtocol().connection_made(pimp_transport)
                            #print("!!!!!!!!!!!Client Connection Established!!!!!!!!!!!!!!!!!!!")

                        elif self.seqNum != pkt.ackNum:
                            self.Server_seqNum = pkt.seqNum + 1
                            self.seqNum = pkt.ackNum
                            self.send_rst(self.transport, self.seqNum, self.Server_seqNum)
                            self.Client_state = self.CLI_INITIAL
                            self.connection_made(self.transport)

                    elif pkt.SYN == False and pkt.ACK == False and self.Client_state == self.CLI_ESTABLISHED and len(pkt.data) != 0:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!client data received" )
                        ClientRxBuffer = {}
                        ClientRxBuffer = dict.fromkeys(self.keys,None)
                        ClientRxBuffer.update(ACK=pkt.ACK, SYN=pkt.SYN, FIN=pkt.FIN, RTR=pkt.RTR, RST=pkt.RST, seqNum=pkt.seqNum, ackNum=pkt.ackNum, data=pkt.data)
                        self.ClientRxWindow.append(ClientRxBuffer)
                        self.ClientRxWindow = sorted(self.ClientRxWindow, key = lambda i: i['seqNum'])
                        self.ClientRxWindow = self.Remove(self.ClientRxWindow)
                        self.clientprocesspktdata(self.transport, self.seqNum, self.Server_seqNum)

                    elif pkt.SYN == False and pkt.ACK == True and self.Client_state == self.CLI_ESTABLISHED:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ACk Received")
                        self.seqNum = pkt.ackNum
                        self.ClientTxWindow = [q for q in self.ClientTxWindow if q["seqNum"] > pkt.ackNum]
                        #print(self.ClientTxWindow)

                    elif pkt.FIN == True and self.Client_state == self.CLI_ESTABLISHED:
                        ####### Recover Outstanding data
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!SENT FINACK")
                        self.resend_flag = True
                        self.Client_state = self.CLI_CLOSING
                        self.higherProtocol().connection_lost(None)
                        self.send_finack(self.transport, pkt.ackNum, pkt.seqNum+1)
                        timer = Timer(3, self.check_timeout)

                    elif pkt.FIN == True and self.Client_state == self.CLI_CLOSING:
                        #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!SENT ACK")
                        self.send_Ack(self.transport, pkt.ackNum, pkt.seqNum+1)
                        asyncio.get_event_loop().stop()

                    elif pkt.ACK == True and self.Client_state == self.CLI_CLOSING:
                        asyncio.get_event_loop().stop()    

                    else:
                        self.Server_seqNum = pkt.seqNum + 1
                        self.seqNum = pkt.ackNum
                        self.send_rst(self.transport, self.seqNum, self.Server_seqNum)
                        self.Client_state = self.CLI_INITIAL
                        self.connection_made(self.transport)

                else:
                    self.send_rtr(self.transport, self.seqNum, self.Server_seqNum)



PIMPClientFactory = StackingProtocolFactory.CreateFactoryType(lambda: PIMPClientProtocol())
PIMPServerFactory = StackingProtocolFactory.CreateFactoryType(lambda: PIMPServerProtocol())
