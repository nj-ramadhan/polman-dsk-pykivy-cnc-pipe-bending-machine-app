from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient('192.168.1.111')
client.connect()
# discrete_inputs = client.read_discrete_inputs(1, 14)   # start reading from address 0 
# discrete_inputs.setBit(3, 1)                       # set address 3 to value 1 
# discrete_inputs.setBit(1,1)
# print(discrete_inputs.getBit(0))
# print(discrete_inputs.getBit(1))
# print(discrete_inputs.bits[:])
# print()

# client.write_coils(1536, [True, True, True, True, True, True, True, True], slave=1)
# time.sleep(1)
# client.write_coil(1536, True)
# client.write_coil(1537, True)
# client.write_coil(1538, True)

# client.write_coils(1536, [False, False, False, False, True, True, True, True], slave=1)
# time.sleep(1)
# client.write_coils(1536, [False, False, False, False, False, False, False, False], slave=1)
# client.write_coil(1536, False)
# client.write_coil(1537, False)
# client.write_coil(1538, False)
reading_coil = client.read_coils(1536, 8, slave=1)
print(reading_coil.bits)
# client.write_register(512, 1000, slave=1) #V0
client.close()