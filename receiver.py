from socket import *
import sys
import threading
from utils import *
from time import sleep
from datetime import datetime


def get_date_time_str():
	now = datetime.now()
	dt = now.strftime("%m/%d/%Y %H:%M:%S")
	return dt


# Check the number of command line arguments
if len(sys.argv) < 4:
	print("Usage: python sender.py <connection_id> <loss_rate> <corrupt_rate> <max_delay>")
	exit()
# Server IP address (str)
# Server Port number (int)
server_IP = "gaia.cs.umass.edu"
server_Port = 20000

# Connection ID of the client
ID_str = sys.argv[1]
ID = int(ID_str)

# loss_rate
loss_rate_str = sys.argv[2]
loss_rate = float(loss_rate_str)

# corrupt_rate
currupt_rate_str = sys.argv[3]# Connection ID of the client
ID_str = sys.argv[1]
ID = int(ID_str)

# loss_rate
loss_rate_str = sys.argv[2]
loss_rate = float(loss_rate_str)

# corrupt_rate
currupt_rate_str = sys.argv[3]
corrupt_rate = float(currupt_rate_str)

# max_delay
max_delay_str = sys.argv[4]
max_delay = int(max_delay_str)

# sender or receiver
sender_or_receiver = "R"

# Message: in the form of "HELLO R <loss_rate> <corrupt_rate> <max_delay> <ID>" with a white space between them
Message = "HELLO" + " " + sender_or_receiver + " " + loss_rate_str + " " + currupt_rate_str + " " + max_delay_str + " " + ID_str
print("Message: {}".format(Message))



###### Print out INFO ######
name = "Ziwei Hu"
print("\nName: {} \tDate/Time: {}\n".format(name, get_date_time_str()))


###### Create a TCP socket ######
s = socket(AF_INET, SOCK_STREAM)
# Set the maximum wait time for the client
maxWaitTime = 15
s.settimeout(maxWaitTime)


######  Connect through TCP socket  ######
try:
	# Connect to the server
	print("[-] Connecting to the {}:{}".format(server_IP, server_Port))
	s.connect((server_IP, server_Port))
except OSError:
	print("[-] A connect request was made on an already connected socket")
	s.close()
except ConnectionRefusedError:
	print("[-] connection was REFUSED.")
	s.close()
	exit()
print("[+] Connected.")



###### Sending HELLO message to the server ######
msg_OK = False
waiting = False
while not msg_OK:
	sleep(0.1)
	try:
		# Send the message if not received WAITING message from the server
		if not waiting:
			print("[-] Sending a message: [{}]".format(Message))
			s.send(bytes(Message, encoding="utf-8"))
			sleep(1)

		# Receive a message from the server
		print("[-] Receiving...")
		msg_len, msg = rdt_rcv(s)
		msg_split = msg.split()
		sleep(1)
		if len(msg) != 0:
			print("[+] Received a message: [{}]".format(msg))
			if msg_split[0] == "OK":
				# When get OK message, then proceed to the next step
				msg_OK = True
				break
			if msg_split[0] == "ERROR":
				# When get ERROR message, then exit the program after closing the socket
				s.close()
				exit()
			if msg_split[0] == "WAITING":
				# When get WAITING message, then wait for the next message
				waiting = True
		else:
			# When received no data from the server
			print("No data")
			sleep(0.1)
	except KeyboardInterrupt:
		print("KeyboardInterrupt")
		s.close()
		exit()
	except timeout:
		# After Maximum time, the server is closing the opened socket and exit.
		print("TCP Server Closing... Max time out reached: {} seconds".format(maxWaitTime))
		s.close()
		exit()
	except ConnectionResetError:
		print("connection was CLOSED.")
		s.close()
		exit()



###### Finite State Machine ######
FSM = {"State 1": 1, # Wait for call 0 from below
	   "State 2": 2, # Wait for call 1 from below
	  }
state = FSM["State 1"]

###### Statistics ######
rcv_bytes = ""
num_pkt_snt = 0
num_pkt_rcv = 0
num_crpt_msg_rcv = 0

sleep(0.5)
while True:
	if state == FSM["State 1"]:
		print("\nState 1")
		print("receiving...")
		try:
			rcvpkt_len, rcvpkt = rdt_rcv(s)
		except ConnectionAbortedError:
			print("[-] Connection was closed.")
			break
		if rcvpkt_len == 0:
			print("No data received.")
			break
		num_pkt_rcv += 1
		print("State 1 - received : [{}] bytes, [{}]".format(rcvpkt_len, rcvpkt))
		if not isCorrupt(rcvpkt) and has_seq(rcvpkt, 0):
			print("\tState 1 - not isCorrupt() && has_seq(0)")
			print("\trcv_bytes:[{}]".format(rcv_bytes))
			rcv_bytes += extract(rcvpkt)
			print("\trcv_bytes:[{}]".format(rcv_bytes))
			data = rcvpkt[4:-6]
			print("\tdata:[{}]".format(data), end=" ")
			chk_rcv = checksum(data)
			print("\t     chk_rcv:[{}]".format(chk_rcv))
			send_pkt = make_pkt_rcv(0, 0, chk_rcv)
			print("\t\tsending.... [{}]".format(send_pkt))
			udt_send(s, send_pkt)
			num_pkt_snt += 1
			sleep(0.1)
			state = FSM["State 2"]
		elif isCorrupt(rcvpkt) or has_seq(rcvpkt, 1):
			if isCorrupt(rcvpkt):
				print("[-] Corrupted message: [{}]".format(rcvpkt))
				num_crpt_msg_rcv += 1
			else:
				print("[-] expected seq: {}   received seq: {}".format(0, rcvpkt[0]))
			print("\tState 1 - isCorrupt() || has_seq(1)")
			chk_rcv = checksum(data)
			print("\tchk_rcv:[{}]".format(chk_rcv))
			send_pkt = make_pkt_rcv(0, 1, chk_rcv)
			print("\t\tsending.... [{}]".format(send_pkt))
			udt_send(s, send_pkt)
			sleep(0.1)
	if state == FSM["State 2"]:
		print("\nState 2")
		print("receiving...")
		try:
			rcvpkt_len, rcvpkt = rdt_rcv(s)
			num_pkt_rcv += 1
		except ConnectionAbortedError:
			print("[-] Connection was closed.")
			break
		print("State 2 - received : [{}] bytes, [{}]".format(rcvpkt_len, rcvpkt))
		if not isCorrupt(rcvpkt) and has_seq(rcvpkt, 1):
			print("\tState 2 - not isCorrupt() && has_seq(1)")
			# rcv_bytes += extract(rcvpkt)
			# rcv_bytes += extract(rcvpkt)
			print("\trcv_bytes:[{}]".format(rcv_bytes))
			data = rcvpkt[4:-6]
			print("\tdata:[{}]".format(data), end=" ")
			chk_rcv = checksum(data)
			print("\t     chk_rcv:[{}]".format(chk_rcv))
			send_pkt = make_pkt_rcv(0, 1, chk_rcv)
			print("\t\tsending.... [{}]".format(send_pkt))
			udt_send(s, send_pkt)
			num_pkt_snt += 1
			sleep(0.1)
			state = FSM["State 1"]
		elif isCorrupt(rcvpkt) or has_seq(rcvpkt, 0):
			if isCorrupt(rcvpkt):
				print("[-] Corrupted message: [{}]".format(rcvpkt))
				num_crpt_msg_rcv += 1
			else:
				print("[-] expected seq: {}   received seq: {}".format(1, rcvpkt[0]))
			print("\tState 2 - isCorrupt() || has_seq(0)")
			send_pkt = make_pkt_rcv(0, 0, chk_rcv)
			print("\t\tsending.... [{}]".format(send_pkt))
			udt_send(s, send_pkt)
			sleep(0.1)


print("\n\nName: {} \tDate/Time: {}".format(name, get_date_time_str()))
chk_rcv_bytes = checksum(rcv_bytes)
print("Checksum of total received bytes: [{}]".format(chk_rcv_bytes))
print("# of packets sent:      {}".format(num_pkt_snt))
print("# of packets received:  {}".format(num_pkt_rcv))
print("# of corrupted message: {}".format(num_crpt_msg_rcv))
print("received data:\n[{}]".format(rcv_bytes))

###### Closing the connection ######
print("[-] Closing the connection...")
s.close()
print("[+] Connection is closed.")
exit()
