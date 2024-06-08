signed_integer = -1
  
# Adding 1<<32 to convert signed to 
# unsigned integer 
unsigned_integer = signed_integer+(1 << 16) 
print(unsigned_integer) 


unsigned_integer = 65535
  
val_feed_pv = int(unsigned_integer) if (int(unsigned_integer) <= 32768) else (int(unsigned_integer) - 65536)
print(val_feed_pv) 