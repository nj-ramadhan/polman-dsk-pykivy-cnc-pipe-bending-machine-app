from pymodbus.client import ModbusSerialClient
client = ModbusSerialClient('COM3', baudrate=19200, bytesize=8, parity="N", stopbits=2, timeout=1, strict=False)

# discrete_inputs = client.read_discrete_inputs(1, 14)   # start reading from address 0 
# discrete_inputs.setBit(3, 1)                       # set address 3 to value 1 
# discrete_inputs.setBit(1,1)
# print(discrete_inputs.getBit(0))
# print(discrete_inputs.getBit(1))
# print(discrete_inputs.bits[:])
# print()

client.write_coils(1536, [True, True, True, True, True, True, True, True])
# client.write_coil(1536, True)
# client.write_coil(1537, True)
# client.write_coil(1538, True)

client.write_coils(1536, [False, False, False, False, True, True, True, True])
client.write_coils(1536, [False, False, False, False, False, False, False, False])
# client.write_coil(1536, False)
# client.write_coil(1537, False)
# client.write_coil(1538, False)
# reading_coil = client.read_coils(0, 14)  # start reading from address 1
# print(reading_coil.bits[:])